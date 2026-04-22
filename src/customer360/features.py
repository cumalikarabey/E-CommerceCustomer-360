from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
import pandas as pd

from .rfm import add_rfm_scores


ORDERS_REQUIRED = {
    "order_id",
    "customer_id",
    "order_status",
    "order_purchase_timestamp",
    "order_estimated_delivery_date",
    "order_delivered_customer_date",
}
CUSTOMERS_REQUIRED = {"customer_id", "customer_unique_id"}
ITEMS_REQUIRED = {"order_id", "price", "freight_value"}
PAYMENTS_REQUIRED = {"order_id", "payment_value"}
REVIEWS_REQUIRED = {"order_id", "review_score"}


def _validate_columns(df: pd.DataFrame, required: Iterable[str], table_name: str) -> None:
    missing = set(required) - set(df.columns)
    if missing:
        raise KeyError(f"{table_name} missing columns: {sorted(missing)}")


def _to_datetime(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def _prepare_order_level(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    order_payments: pd.DataFrame,
    order_reviews: pd.DataFrame,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    if logger:
        logger.info("    [features] validating required columns")
    _validate_columns(customers, CUSTOMERS_REQUIRED, "customers")
    _validate_columns(orders, ORDERS_REQUIRED, "orders")
    _validate_columns(order_items, ITEMS_REQUIRED, "order_items")
    _validate_columns(order_payments, PAYMENTS_REQUIRED, "order_payments")
    _validate_columns(order_reviews, REVIEWS_REQUIRED, "order_reviews")

    if logger:
        logger.info("    [features] parsing order timestamps")
    orders = _to_datetime(
        orders,
        [
            "order_purchase_timestamp",
            "order_estimated_delivery_date",
            "order_delivered_customer_date",
        ],
    )

    if logger:
        logger.info("    [features] aggregating order_items")
    item_agg = (
        order_items.assign(
            item_total_value=order_items["price"].fillna(0) + order_items["freight_value"].fillna(0)
        )
        .groupby("order_id", as_index=False)
        .agg(
            item_count=("order_id", "size"),
            gross_item_value=("item_total_value", "sum"),
        )
    )

    if logger:
        logger.info("    [features] aggregating payments and reviews")
    payment_agg = order_payments.groupby("order_id", as_index=False).agg(
        total_payment_value=("payment_value", "sum")
    )

    review_agg = order_reviews.groupby("order_id", as_index=False).agg(
        avg_review_score=("review_score", "mean"),
        review_count=("review_score", "size"),
    )

    order_level = (
        orders.merge(customers[["customer_id", "customer_unique_id"]], on="customer_id", how="left")
        .merge(item_agg, on="order_id", how="left")
        .merge(payment_agg, on="order_id", how="left")
        .merge(review_agg, on="order_id", how="left")
    )

    order_level["item_count"] = order_level["item_count"].fillna(0).astype(int)
    order_level["gross_item_value"] = order_level["gross_item_value"].fillna(0.0)
    order_level["total_payment_value"] = order_level["total_payment_value"].fillna(
        order_level["gross_item_value"]
    )
    order_level["order_value"] = order_level["total_payment_value"].fillna(0.0)

    order_level["delivery_delay_days"] = (
        order_level["order_delivered_customer_date"] - order_level["order_estimated_delivery_date"]
    ).dt.days

    delivered_mask = order_level["order_delivered_customer_date"].notna()
    estimated_mask = order_level["order_estimated_delivery_date"].notna()
    order_level["promised_delivery_met"] = (
        delivered_mask
        & estimated_mask
        & (order_level["order_delivered_customer_date"] <= order_level["order_estimated_delivery_date"])
    )

    order_level["is_problem_order"] = order_level["order_status"].isin(["canceled", "unavailable"])

    if logger:
        logger.info(
            "    [features] order level table ready: %s rows x %s cols",
            f"{len(order_level):,}",
            len(order_level.columns),
        )

    return order_level


def _prepare_ga_channels(ga_events: pd.DataFrame | None) -> pd.DataFrame | None:
    if ga_events is None or ga_events.empty:
        return None
    if "customer_unique_id" not in ga_events.columns:
        return None

    channel_candidates = [
        "acquisition_channel",
        "source_medium",
        "channel_grouping",
        "traffic_source",
    ]
    ts_candidates = ["event_timestamp", "session_start", "event_date"]

    channel_col = next((c for c in channel_candidates if c in ga_events.columns), None)
    if channel_col is None:
        return None

    ga = ga_events.copy()
    ts_col = next((c for c in ts_candidates if c in ga.columns), None)
    if ts_col is not None:
        ga[ts_col] = pd.to_datetime(ga[ts_col], errors="coerce")
        ga = ga.sort_values(ts_col, kind="stable")

    grp = ga.groupby("customer_unique_id", as_index=False)
    first = grp[channel_col].first().rename(columns={channel_col: "first_acquisition_channel"})
    last = grp[channel_col].last().rename(columns={channel_col: "latest_acquisition_channel"})
    count = grp.size().rename(columns={"size": "ga_event_count"})

    return first.merge(last, on="customer_unique_id", how="left").merge(
        count, on="customer_unique_id", how="left"
    )


def build_customer_360(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    order_payments: pd.DataFrame,
    order_reviews: pd.DataFrame,
    ga_events: pd.DataFrame | None = None,
    reference_date: str | pd.Timestamp | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    if logger:
        logger.info("    [features] starting customer_360 build")
    order_level = _prepare_order_level(
        customers=customers,
        orders=orders,
        order_items=order_items,
        order_payments=order_payments,
        order_reviews=order_reviews,
        logger=logger,
    )

    if reference_date is None:
        inferred = order_level["order_purchase_timestamp"].max()
        reference_ts = pd.Timestamp(inferred).normalize()
    else:
        reference_ts = pd.Timestamp(reference_date).normalize()
    if logger:
        logger.info("    [features] snapshot reference_date=%s", reference_ts.date())

    if logger:
        logger.info("    [features] aggregating lifecycle metrics per customer")
    lifecycle = order_level.groupby("customer_unique_id", as_index=False).agg(
        first_order_date=("order_purchase_timestamp", "min"),
        last_order_date=("order_purchase_timestamp", "max"),
        order_count=("order_id", "nunique"),
        total_revenue=("order_value", "sum"),
        avg_order_value=("order_value", "mean"),
        median_order_value=("order_value", "median"),
        problem_order_count=("is_problem_order", "sum"),
        problem_order_rate=("is_problem_order", "mean"),
        avg_review_score=("avg_review_score", "mean"),
        low_review_ratio=("avg_review_score", lambda s: (s <= 2).mean()),
        on_time_delivery_rate=("promised_delivery_met", "mean"),
        avg_delivery_delay_days=("delivery_delay_days", "mean"),
        p95_delivery_delay_days=("delivery_delay_days", lambda s: s.quantile(0.95)),
    )

    lifecycle["recency_days"] = (
        reference_ts - lifecycle["last_order_date"].dt.normalize()
    ).dt.days.astype("Int64")
    lifecycle["order_lifecycle_days"] = (
        lifecycle["last_order_date"].dt.normalize() - lifecycle["first_order_date"].dt.normalize()
    ).dt.days.astype("Int64")

    cutoff_12m = reference_ts - pd.Timedelta(days=365)
    frequency_12m = (
        order_level.loc[order_level["order_purchase_timestamp"] >= cutoff_12m]
        .groupby("customer_unique_id", as_index=False)
        .agg(order_count_last_12m=("order_id", "nunique"))
    )
    lifecycle = lifecycle.merge(frequency_12m, on="customer_unique_id", how="left")

    ga_features = _prepare_ga_channels(ga_events)
    if ga_features is not None:
        if logger:
            logger.info("    [features] merging GA channel features")
        lifecycle = lifecycle.merge(ga_features, on="customer_unique_id", how="left")
    elif logger and ga_events is not None:
        logger.info("    [features] GA file loaded but required channel columns not found; skipping")

    lifecycle["order_count_last_12m"] = lifecycle["order_count_last_12m"].fillna(0).astype(int)
    lifecycle["problem_order_count"] = lifecycle["problem_order_count"].fillna(0).astype(int)

    for col in [
        "problem_order_rate",
        "avg_review_score",
        "low_review_ratio",
        "on_time_delivery_rate",
        "avg_delivery_delay_days",
        "p95_delivery_delay_days",
        "avg_order_value",
        "median_order_value",
    ]:
        lifecycle[col] = lifecycle[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    if "first_acquisition_channel" in lifecycle.columns:
        lifecycle["first_acquisition_channel"] = lifecycle["first_acquisition_channel"].fillna("unknown")
    if "latest_acquisition_channel" in lifecycle.columns:
        lifecycle["latest_acquisition_channel"] = lifecycle["latest_acquisition_channel"].fillna("unknown")
    if "ga_event_count" in lifecycle.columns:
        lifecycle["ga_event_count"] = lifecycle["ga_event_count"].fillna(0).astype(int)

    if logger:
        logger.info("    [features] computing RFM scores and segment labels")
    lifecycle = add_rfm_scores(
        lifecycle,
        recency_col="recency_days",
        frequency_col="order_count",
        monetary_col="total_revenue",
    )

    lifecycle["snapshot_date"] = reference_ts
    lifecycle = lifecycle.sort_values(
        by=["rfm_score", "total_revenue"], ascending=[False, False]
    ).reset_index(drop=True)

    if logger:
        logger.info(
            "    [features] customer_360 ready: %s rows x %s cols",
            f"{len(lifecycle):,}",
            len(lifecycle.columns),
        )

    return lifecycle
