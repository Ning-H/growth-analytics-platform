# Streaming Ingestion

Phase 3 reads local Kafka topics and writes raw bronze tables to BigQuery.

## Jobs

- `streaming/ingest_to_bigquery.py`: reads all simulator topics, parses JSON with Spark schemas, adds Kafka metadata, and writes one BigQuery bronze table per topic family plus `bronze_events_union`.
- `streaming/identity_resolution.py`: reads signup events and maintains a deterministic `device_to_user` mapping in BigQuery using `MERGE`.

## Run Locally

Prerequisites:

- Docker/Kafka running from `make kafka-up`.
- Python 3.13+ with project dependencies installed by `uv`.
- `.env` populated with `GCP_PROJECT_ID`, `GCP_SERVICE_ACCOUNT_JSON_PATH`, `BIGQUERY_DATASET_RAW`, and `KAFKA_BOOTSTRAP_SERVERS`.
- BigQuery datasets `growth_raw` and `growth_analytics` already created.

Run the bronze stream:

```bash
make stream-up
```

Stop local Spark processes:

```bash
make stream-down
```

## Schema Evolution

Events include `schema_version`. Bronze keeps the original `raw_payload` plus parsed columns. Backward-compatible fields can be added as nullable columns. Breaking changes should increment `schema_version`, add a new parser branch, and preserve older payloads for replay.

Production upgrade: use Avro or Protobuf with a schema registry and compatibility checks. JSON is intentional here because it is easier to inspect in Kafka UI and good enough for a portfolio demo.

## Late-Arriving Events

Spark applies a 10-minute watermark on `event_timestamp`. Bronze writes are append-only, so late events remain visible. Downstream dbt models should use incremental windows or backfill jobs to repair derived marts when late conversions arrive.

## Failure And Recovery

Checkpoint directories live under `checkpoints/`. Restarting a job with the same checkpoint resumes from the committed Kafka offsets. To intentionally replay from the beginning during development, stop the stream and run:

```bash
make stream-down
```

That removes checkpoints and allows the stream to consume from `KAFKA_STARTING_OFFSETS`, which defaults to `earliest`.

## Smoke Check

After running the simulator and stream, validate in BigQuery:

```sql
SELECT event_type, COUNT(*)
FROM `YOUR_PROJECT_ID.growth_raw.bronze_events_union`
GROUP BY 1
ORDER BY 2 DESC;
```
