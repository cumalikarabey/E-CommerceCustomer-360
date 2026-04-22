from __future__ import annotations

from pathlib import Path

import pandas as pd

from customer360.pipeline import run_customer360_pipeline


def test_pipeline_builds_customer_360(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    customers = pd.DataFrame(
        {
            "customer_id": ["c1", "c2", "c3"],
            "customer_unique_id": ["u1", "u1", "u2"],
        }
    )
    orders = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3"],
            "customer_id": ["c1", "c2", "c3"],
            "order_status": ["delivered", "canceled", "delivered"],
            "order_purchase_timestamp": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "order_estimated_delivery_date": ["2024-01-06", "2024-02-10", "2024-03-08"],
            "order_delivered_customer_date": ["2024-01-05", None, "2024-03-10"],
        }
    )
    items = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3"],
            "price": [100.0, 50.0, 200.0],
            "freight_value": [10.0, 5.0, 20.0],
        }
    )
    payments = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3"],
            "payment_value": [110.0, 55.0, 220.0],
        }
    )
    reviews = pd.DataFrame(
        {
            "order_id": ["o1", "o3"],
            "review_score": [5, 2],
        }
    )

    customers.to_csv(raw / "olist_customers_dataset.csv", index=False)
    orders.to_csv(raw / "olist_orders_dataset.csv", index=False)
    items.to_csv(raw / "olist_order_items_dataset.csv", index=False)
    payments.to_csv(raw / "olist_order_payments_dataset.csv", index=False)
    reviews.to_csv(raw / "olist_order_reviews_dataset.csv", index=False)

    out_path = tmp_path / "customer_360.csv"
    output_file = run_customer360_pipeline(
        data_dir=raw,
        output_path=out_path,
        reference_date="2024-04-01",
    )

    assert output_file.exists()
    result = pd.read_csv(output_file)
    assert len(result) == 2
    assert set(result["customer_unique_id"]) == {"u1", "u2"}
    assert "rfm_segment" in result.columns
    assert "problem_order_rate" in result.columns


def test_pipeline_supports_custom_input_file_names(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    customers = pd.DataFrame(
        {
            "customer_id": ["c1"],
            "customer_unique_id": ["u1"],
        }
    )
    orders = pd.DataFrame(
        {
            "order_id": ["o1"],
            "customer_id": ["c1"],
            "order_status": ["delivered"],
            "order_purchase_timestamp": ["2024-01-01"],
            "order_estimated_delivery_date": ["2024-01-06"],
            "order_delivered_customer_date": ["2024-01-05"],
        }
    )
    items = pd.DataFrame({"order_id": ["o1"], "price": [100.0], "freight_value": [10.0]})
    payments = pd.DataFrame({"order_id": ["o1"], "payment_value": [110.0]})
    reviews = pd.DataFrame({"order_id": ["o1"], "review_score": [5]})

    customers.to_csv(raw / "customers.csv", index=False)
    orders.to_csv(raw / "orders.csv", index=False)
    items.to_csv(raw / "items.csv", index=False)
    payments.to_csv(raw / "payments.csv", index=False)
    reviews.to_csv(raw / "reviews.csv", index=False)

    output = tmp_path / "out.csv"
    run_customer360_pipeline(
        data_dir=raw,
        output_path=output,
        reference_date="2024-04-01",
        input_paths={
            "customers": "customers.csv",
            "orders": "orders.csv",
            "order_items": "items.csv",
            "order_payments": "payments.csv",
            "order_reviews": "reviews.csv",
        },
    )
    result = pd.read_csv(output)
    assert len(result) == 1
    assert result.loc[0, "customer_unique_id"] == "u1"
