from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
from pyspark.sql.types import BooleanType, DoubleType, IntegerType, LongType, StringType

from simulator.events import DEFAULT_CONFIG_PATH
from simulator.user_journey import EVENT_TOPICS, JourneyGenerator, SimulationConfig, summarize_events
from streaming.schemas.events import EVENT_SCHEMA, TOPIC_TABLES


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_client() -> bigquery.Client:
    credentials = service_account.Credentials.from_service_account_file(
        require_env("GCP_SERVICE_ACCOUNT_JSON_PATH")
    )
    return bigquery.Client(credentials=credentials, project=require_env("GCP_PROJECT_ID"))


def bq_type(spark_type: Any) -> str:
    if isinstance(spark_type, StringType):
        return "STRING"
    if isinstance(spark_type, (IntegerType, LongType)):
        return "INTEGER"
    if isinstance(spark_type, DoubleType):
        return "FLOAT"
    if isinstance(spark_type, BooleanType):
        return "BOOLEAN"
    return "STRING"


def event_field_type(field_name: str, spark_type: Any) -> str:
    if field_name == "event_date":
        return "DATE"
    if field_name in {"event_timestamp", "qualified_at"}:
        return "TIMESTAMP"
    return bq_type(spark_type)


def event_schema() -> list[bigquery.SchemaField]:
    fields = [
        bigquery.SchemaField(field.name, event_field_type(field.name, field.dataType), mode="NULLABLE")
        for field in EVENT_SCHEMA.fields
    ]
    fields.extend(
        [
            bigquery.SchemaField("event_properties", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("kafka_topic", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("kafka_partition", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("kafka_offset", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("raw_payload", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP", mode="NULLABLE"),
        ]
    )
    return fields


def identity_schema() -> list[bigquery.SchemaField]:
    return [
        bigquery.SchemaField("device_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("advertiser_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("first_seen_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("last_seen_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("mapping_source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("identity_confidence", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
    ]


def normalize_event(event: dict[str, Any], offset: int) -> dict[str, Any]:
    payload = {key: value for key, value in event.items() if key != "topic"}
    record = {field.name: payload.get(field.name) for field in EVENT_SCHEMA.fields}
    record.update(
        {
            "event_properties": json.dumps(
                {
                    key: value
                    for key, value in payload.items()
                    if key not in {field.name for field in EVENT_SCHEMA.fields}
                },
                sort_keys=True,
            ),
            "kafka_topic": event["topic"],
            "kafka_partition": 0,
            "kafka_offset": offset,
            "raw_payload": json.dumps(payload, sort_keys=True),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return record


def identity_records(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mappings: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for event in events:
        if not event.get("device_id") or not event.get("user_id"):
            continue
        key = (
            event["device_id"],
            event["user_id"],
            event["advertiser_id"],
            event["product_id"],
        )
        existing = mappings.get(key)
        event_at = event["event_timestamp"]
        if existing is None:
            mappings[key] = {
                "device_id": event["device_id"],
                "user_id": event["user_id"],
                "advertiser_id": event["advertiser_id"],
                "product_id": event["product_id"],
                "first_seen_at": event_at,
                "last_seen_at": event_at,
                "mapping_source": event["event_type"],
                "identity_confidence": 1.0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            existing["first_seen_at"] = min(existing["first_seen_at"], event_at)
            existing["last_seen_at"] = max(existing["last_seen_at"], event_at)
            existing["mapping_source"] = event["event_type"]
            existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    return list(mappings.values())


def load_json(
    client: bigquery.Client,
    table_id: str,
    rows: list[dict[str, Any]],
    schema: list[bigquery.SchemaField],
    write_disposition: str,
) -> None:
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=write_disposition,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )
    if table_id.endswith("bronze_events_union"):
        job_config.clustering_fields = ["advertiser_id", "campaign_id", "device_id"]
    job = client.load_table_from_json(rows, table_id, job_config=job_config)
    job.result()


def backfill(config_path: Path, n_users: int, replace: bool) -> dict[str, Any]:
    load_dotenv(REPO_ROOT / ".env")
    config = SimulationConfig.from_yaml(config_path)
    events = JourneyGenerator(config).generate_all(n_users=n_users)
    summary = summarize_events(events)

    project_id = require_env("GCP_PROJECT_ID")
    dataset = require_env("BIGQUERY_DATASET_RAW")
    client = create_client()
    schema = event_schema()
    write_disposition = "WRITE_TRUNCATE" if replace else "WRITE_APPEND"

    normalized = [normalize_event(event, offset) for offset, event in enumerate(events)]
    load_json(
        client,
        f"{project_id}.{dataset}.bronze_events_union",
        normalized,
        schema,
        write_disposition,
    )

    for topic, table in TOPIC_TABLES.items():
        topic_rows = [row for row in normalized if row["kafka_topic"] == topic]
        load_json(
            client,
            f"{project_id}.{dataset}.{table}",
            topic_rows,
            schema,
            write_disposition,
        )

    load_json(
        client,
        f"{project_id}.{dataset}.device_to_user",
        identity_records(events),
        identity_schema(),
        write_disposition,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill simulator events directly to BigQuery bronze.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--n-users", type=int, default=10000)
    parser.add_argument("--append", action="store_true", help="Append instead of replacing demo bronze data.")
    args = parser.parse_args()

    summary = backfill(args.config, n_users=args.n_users, replace=not args.append)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
