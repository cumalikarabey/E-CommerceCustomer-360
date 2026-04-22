from __future__ import annotations

from pathlib import Path

import pandas as pd


def _drop_unnamed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop accidental unnamed columns from imperfect CSV exports."""
    keep = [col for col in df.columns if not str(col).lower().startswith("unnamed:")]
    return df.loc[:, keep]


def read_table(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path, low_memory=False)
        return _drop_unnamed_columns(df)
    if file_path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(file_path)
        return _drop_unnamed_columns(df)

    raise ValueError(
        f"Unsupported file format: {file_path.suffix}. Use csv/parquet."
    )


def write_table(df: pd.DataFrame, path: str | Path) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.suffix.lower() == ".csv":
        df.to_csv(file_path, index=False)
    elif file_path.suffix.lower() in {".parquet", ".pq"}:
        df.to_parquet(file_path, index=False)
    else:
        raise ValueError(
            f"Unsupported output format: {file_path.suffix}. Use csv/parquet."
        )

    return file_path
