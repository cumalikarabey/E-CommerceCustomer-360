.PHONY: install test build360 ui

install:
	pip install -e .[dev]

test:
	pytest -q

build360:
	python scripts/build_customer360.py --data-dir data/raw --output data/processed/customer_360.parquet

ui:
	streamlit run ui/customer360_dashboard.py
