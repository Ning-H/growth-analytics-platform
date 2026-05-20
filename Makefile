.PHONY: setup simulate stream dbt-run dashboard test

setup:
	uv sync --python 3.11

simulate:
	@echo "Simulator will be implemented in a later phase."

stream:
	@echo "Streaming ingestion will be implemented in a later phase."

dbt-run:
	@echo "dbt transformations will be implemented in a later phase."

dashboard:
	@echo "Streamlit dashboard will be implemented in a later phase."

test:
	uv run pytest || test $$? -eq 5
