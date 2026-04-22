from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pandas as pd

from .features import build_customer_360
from .io import read_table, write_table
from .logging_utils import StepLogger, colorize, get_logger, logger_uses_color


DEFAULT_INPUTS = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
}


INPUT_PATTERNS = {
    "customers": ["*customers*.csv", "*customers*.parquet", "*customer*.csv"],
    "orders": ["*orders_dataset*.csv", "*orders*.csv", "*orders*.parquet"],
    "order_items": ["*order_items*.csv", "*items*.csv", "*order_items*.parquet"],
    "order_payments": [
        "*order_payments*.csv",
        "*payments*.csv",
        "*order_payments*.parquet",
    ],
    "order_reviews": ["*order_reviews*.csv", "*reviews*.csv", "*order_reviews*.parquet"],
}


def _resolve_user_path(path_value: str | Path, data_dir: Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate
    return data_dir / candidate


def _score_candidate(file_path: Path, table_key: str) -> int:
    name = file_path.name.lower()
    score = 0
    if "olist" in name:
        score += 3
    if "dataset" in name:
        score += 2
    if table_key in name:
        score += 4

    token_map = {
        "customers": ["customer", "customers"],
        "orders": ["orders_dataset", "orders"],
        "order_items": ["order_items", "items"],
        "order_payments": ["order_payments", "payments"],
        "order_reviews": ["order_reviews", "reviews"],
    }
    for token in token_map.get(table_key, []):
        if token in name:
            score += 2

    if name.endswith(".csv"):
        score += 1
    return score


def _filter_ambiguous_orders(files: list[Path], table_key: str) -> list[Path]:
    if table_key != "orders":
        return files
    blocked = ("order_items", "order_payments", "order_reviews")
    return [f for f in files if not any(token in f.name.lower() for token in blocked)]


def _find_best_candidate(data_dir: Path, table_key: str) -> Path | None:
    patterns = INPUT_PATTERNS[table_key]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(p for p in data_dir.glob(pattern) if p.is_file())
        candidates.extend(p for p in data_dir.rglob(pattern) if p.is_file())

    uniq = sorted({p.resolve() for p in candidates})
    uniq_paths = [Path(p) for p in uniq]
    uniq_paths = _filter_ambiguous_orders(uniq_paths, table_key)
    if not uniq_paths:
        return None

    ranked = sorted(
        uniq_paths,
        key=lambda p: (_score_candidate(p, table_key), -len(p.name)),
        reverse=True,
    )
    return ranked[0]


def _build_missing_input_message(
    data_dir: Path,
    missing_keys: list[str],
    resolved: dict[str, Path],
) -> str:
    expected_lines = [
        f"- {key}: {DEFAULT_INPUTS[key]}"
        for key in DEFAULT_INPUTS
    ]
    resolved_lines = [
        f"- {key}: {path}"
        for key, path in resolved.items()
    ]
    existing_files = sorted(
        str(p.relative_to(data_dir))
        for p in data_dir.rglob("*")
        if p.is_file()
    )
    file_lines = existing_files[:30] if existing_files else ["(no files found)"]

    return (
        f"Missing required input tables under: {data_dir}\n\n"
        f"Missing keys: {', '.join(missing_keys)}\n\n"
        "Expected defaults:\n"
        + "\n".join(expected_lines)
        + "\n\nResolved files:\n"
        + ("\n".join(resolved_lines) if resolved_lines else "(none)")
        + "\n\nFound files:\n"
        + "\n".join(f"- {line}" for line in file_lines)
        + "\n\nDownload Olist files and place them in data/raw, or provide explicit file paths via:\n"
        "--customers-file --orders-file --order-items-file --order-payments-file --order-reviews-file"
    )


def _resolve_input_paths(
    data_dir: Path,
    input_paths: dict[str, str | Path] | None = None,
) -> dict[str, Path]:
    input_paths = input_paths or {}
    resolved: dict[str, Path] = {}
    missing: list[str] = []

    for key, default_name in DEFAULT_INPUTS.items():
        explicit = input_paths.get(key)
        if explicit:
            explicit_path = _resolve_user_path(explicit, data_dir)
            if explicit_path.exists():
                resolved[key] = explicit_path
                continue
            raise FileNotFoundError(
                f"Explicit file for '{key}' not found: {explicit_path}"
            )

        default_path = data_dir / default_name
        if default_path.exists():
            resolved[key] = default_path
            continue

        best = _find_best_candidate(data_dir, key)
        if best is not None:
            resolved[key] = best
            continue

        missing.append(key)

    if missing:
        raise FileNotFoundError(_build_missing_input_message(data_dir, missing, resolved))
    return resolved


def run_customer360_pipeline(
    data_dir: str | Path,
    output_path: str | Path,
    ga_file: str | Path | None = None,
    reference_date: str | pd.Timestamp | None = None,
    input_paths: dict[str, str | Path] | None = None,
) -> Path:
    logger = get_logger()
    use_color = logger_uses_color(logger)
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    total_steps = 1 + len(DEFAULT_INPUTS) + (1 if ga_file else 0) + 2
    steps = StepLogger(logger=logger, total_steps=total_steps, use_color=use_color)
    pipeline_start = perf_counter()

    steps.next(f"Resolving input files from {data_dir}")
    resolve_start = perf_counter()
    resolved_inputs = _resolve_input_paths(data_dir, input_paths=input_paths)
    resolve_elapsed = perf_counter() - resolve_start
    for key, path in resolved_inputs.items():
        logger.info(
            "  -> %s: %s",
            colorize(key, "blue", use_color, bold=True),
            path,
        )
    logger.info("  -> input resolution completed in %.2fs", resolve_elapsed)

    loaded: dict[str, pd.DataFrame] = {}
    for key in DEFAULT_INPUTS:
        steps.next(f"Loading {key} table")
        read_start = perf_counter()
        frame = read_table(resolved_inputs[key])
        loaded[key] = frame
        logger.info(
            "  -> %s rows x %s cols loaded from %s in %.2fs",
            f"{len(frame):,}",
            len(frame.columns),
            resolved_inputs[key],
            perf_counter() - read_start,
        )

    ga_events = None
    if ga_file:
        steps.next("Loading optional GA events table")
        ga_start = perf_counter()
        ga_path = _resolve_user_path(ga_file, data_dir)
        ga_events = read_table(ga_path)
        logger.info(
            "  -> %s rows x %s cols loaded from %s in %.2fs",
            f"{len(ga_events):,}",
            len(ga_events.columns),
            ga_path,
            perf_counter() - ga_start,
        )

    steps.next("Building customer_360 feature table")
    build_start = perf_counter()
    customer_360 = build_customer_360(
        customers=loaded["customers"],
        orders=loaded["orders"],
        order_items=loaded["order_items"],
        order_payments=loaded["order_payments"],
        order_reviews=loaded["order_reviews"],
        ga_events=ga_events,
        reference_date=reference_date,
        logger=logger,
    )
    logger.info(
        "  -> customer_360 built with %s rows x %s cols in %.2fs",
        f"{len(customer_360):,}",
        len(customer_360.columns),
        perf_counter() - build_start,
    )

    steps.next(f"Writing output table to {output_path}")
    write_start = perf_counter()
    out_path = write_table(customer_360, output_path)
    logger.info("  -> output write completed in %.2fs", perf_counter() - write_start)
    logger.info(
        "%s Pipeline finished in %.2fs",
        colorize("[DONE]", "magenta", use_color, bold=True),
        perf_counter() - pipeline_start,
    )
    return out_path
