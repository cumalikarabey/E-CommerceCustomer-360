from __future__ import annotations

import numpy as np
import pandas as pd


def _score_by_rank(series: pd.Series, bins: int = 5, high_is_good: bool = True) -> pd.Series:
    """Create stable 1..bins score from rank percentiles."""
    values = series.astype(float).copy()
    fill_value = float(values.median()) if values.notna().any() else 0.0
    values = values.fillna(fill_value)

    pct = values.rank(pct=True, method="average")
    if high_is_good:
        score = np.ceil(pct * bins)
    else:
        score = np.ceil((1.0 - pct) * bins)

    return pd.Series(score, index=series.index).clip(1, bins).astype(int)


def _assign_rfm_segment(row: pd.Series) -> str:
    r = row["recency_score"]
    f = row["frequency_score"]
    m = row["monetary_score"]

    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 4 and f >= 3:
        return "Loyal Customers"
    if r >= 4 and f <= 2:
        return "New Customers"
    if r <= 2 and f >= 3 and m >= 3:
        return "At Risk"
    if r <= 2 and f <= 2:
        return "Hibernating"
    if m >= 4:
        return "Big Spenders"
    return "Potential Loyalists"


def add_rfm_scores(
    customer_df: pd.DataFrame,
    recency_col: str = "recency_days",
    frequency_col: str = "order_count",
    monetary_col: str = "total_revenue",
    bins: int = 5,
) -> pd.DataFrame:
    df = customer_df.copy()

    required = {recency_col, frequency_col, monetary_col}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing RFM columns: {sorted(missing)}")

    df["recency_score"] = _score_by_rank(df[recency_col], bins=bins, high_is_good=False)
    df["frequency_score"] = _score_by_rank(df[frequency_col], bins=bins, high_is_good=True)
    df["monetary_score"] = _score_by_rank(df[monetary_col], bins=bins, high_is_good=True)
    df["rfm_score"] = (
        df["recency_score"] + df["frequency_score"] + df["monetary_score"]
    ).astype(int)
    df["rfm_segment"] = df.apply(_assign_rfm_segment, axis=1)

    return df

