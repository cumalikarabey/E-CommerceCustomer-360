from __future__ import annotations

import argparse

from customer360.logging_utils import configure_logging
from customer360.pipeline import run_customer360_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Customer 360 table.")
    parser.add_argument(
        "--data-dir",
        default="data/raw",
        help="Folder containing Olist source tables.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/customer_360.parquet",
        help="Output file path (.csv or .parquet).",
    )
    parser.add_argument(
        "--ga-file",
        default=None,
        help="Optional GA event file with customer_unique_id and channel fields.",
    )
    parser.add_argument(
        "--reference-date",
        default=None,
        help="Optional snapshot date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--customers-file",
        default=None,
        help="Optional customers input file path.",
    )
    parser.add_argument(
        "--orders-file",
        default=None,
        help="Optional orders input file path.",
    )
    parser.add_argument(
        "--order-items-file",
        default=None,
        help="Optional order items input file path.",
    )
    parser.add_argument(
        "--order-payments-file",
        default=None,
        help="Optional order payments input file path.",
    )
    parser.add_argument(
        "--order-reviews-file",
        default=None,
        help="Optional order reviews input file path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Show only warnings/errors.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color logs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(verbose=not args.quiet, use_color=not args.no_color)
    out = run_customer360_pipeline(
        data_dir=args.data_dir,
        output_path=args.output,
        ga_file=args.ga_file,
        reference_date=args.reference_date,
        input_paths={
            "customers": args.customers_file,
            "orders": args.orders_file,
            "order_items": args.order_items_file,
            "order_payments": args.order_payments_file,
            "order_reviews": args.order_reviews_file,
        },
    )
    print(f"Customer 360 table generated: {out}")


if __name__ == "__main__":
    main()
