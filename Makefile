.PHONY: setup kafka-up kafka-down simulate simulate-dry-run simulate-historical simulate-live stream dbt-run dashboard test

setup:
	uv sync --python 3.11

kafka-up:
	docker compose up -d zookeeper kafka kafka-ui

kafka-down:
	docker compose down

simulate:
	uv run python -m simulator.events --mode historical

simulate-dry-run:
	uv run python -m simulator.events --dry-run --n-users 1000

simulate-historical:
	uv run python -m simulator.events --mode historical

simulate-live:
	uv run python -m simulator.events --mode live

stream:
	@echo "Streaming ingestion will be implemented in a later phase."

dbt-run:
	@echo "dbt transformations will be implemented in a later phase."

dashboard:
	@echo "Streamlit dashboard will be implemented in a later phase."

test:
	uv run pytest || test $$? -eq 5
