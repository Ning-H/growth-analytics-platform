.PHONY: setup kafka-up kafka-down simulate simulate-dry-run simulate-historical simulate-live stream stream-up stream-down dbt-deps dbt-seed dbt-run dbt-test dbt-docs mf-validate mf-list mf-query-test nl-chat nl-eval dashboard test

setup:
	uv sync --python 3.13

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
	$(MAKE) stream-up

stream-up:
	mkdir -p logs
	nohup bash streaming/run_spark.sh bronze > logs/bronze_stream.log 2>&1 & echo $$! > logs/bronze_stream.pid
	nohup bash streaming/run_spark.sh identity > logs/identity_stream.log 2>&1 & echo $$! > logs/identity_stream.pid
	@echo "Started Spark streams. Logs: logs/bronze_stream.log logs/identity_stream.log"

stream-down:
	@if test -f logs/bronze_stream.pid; then kill $$(cat logs/bronze_stream.pid) 2>/dev/null || true; rm logs/bronze_stream.pid; fi
	@if test -f logs/identity_stream.pid; then kill $$(cat logs/identity_stream.pid) 2>/dev/null || true; rm logs/identity_stream.pid; fi
	rm -rf checkpoints

dbt-deps:
	uv run dotenv -f .env run -- dbt deps --project-dir dbt_project

dbt-seed:
	uv run dotenv -f .env run -- dbt seed --project-dir dbt_project --profiles-dir dbt_project

dbt-run:
	uv run dotenv -f .env run -- dbt run --project-dir dbt_project --profiles-dir dbt_project

dbt-test:
	uv run dotenv -f .env run -- dbt test --project-dir dbt_project --profiles-dir dbt_project

dbt-docs:
	uv run dotenv -f .env run -- dbt docs generate --project-dir dbt_project --profiles-dir dbt_project

mf-validate:
	uv run dotenv -f .env run -- dbt parse --project-dir dbt_project --profiles-dir dbt_project --no-partial-parse
	cd dbt_project && uv run dotenv -f ../.env run -- mf validate-configs

mf-list:
	uv run dotenv -f .env run -- dbt parse --project-dir dbt_project --profiles-dir dbt_project --no-partial-parse
	cd dbt_project && uv run dotenv -f ../.env run -- mf list metrics

mf-query-test:
	uv run dotenv -f .env run -- dbt parse --project-dir dbt_project --profiles-dir dbt_project --no-partial-parse
	cd dbt_project && uv run dotenv -f ../.env run -- mf query --metrics dau --group-by metric_time --limit 7
	cd dbt_project && uv run dotenv -f ../.env run -- mf query --metrics attributed_revenue_time_decay --group-by attribution_record_time_decay__channel --limit 10
	cd dbt_project && uv run dotenv -f ../.env run -- mf query --metrics retention_rate --group-by cohort_week__weeks_since_signup --limit 10

nl-chat:
	uv run dotenv -f .env run -- python -m nl_interface.agent

nl-eval:
	uv run dotenv -f .env run -- python -m nl_interface.eval.run_eval

dashboard:
	uv run dotenv -f .env run -- streamlit run dashboard/app.py

test:
	uv run pytest || test $$? -eq 5
