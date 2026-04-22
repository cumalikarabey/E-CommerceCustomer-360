from __future__ import annotations

import pandas as pd

from customer360.rfm import add_rfm_scores


def test_add_rfm_scores_output_columns() -> None:
    df = pd.DataFrame(
        {
            "customer_unique_id": ["a", "b", "c", "d", "e"],
            "recency_days": [2, 14, 30, 60, 90],
            "order_count": [9, 6, 3, 2, 1],
            "total_revenue": [1000, 600, 300, 120, 50],
        }
    )

    out = add_rfm_scores(df)

    for col in [
        "recency_score",
        "frequency_score",
        "monetary_score",
        "rfm_score",
        "rfm_segment",
    ]:
        assert col in out.columns

    assert out["recency_score"].between(1, 5).all()
    assert out["frequency_score"].between(1, 5).all()
    assert out["monetary_score"].between(1, 5).all()

