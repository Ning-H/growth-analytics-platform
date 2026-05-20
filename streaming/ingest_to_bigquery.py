from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, from_json, to_date, to_json, struct

from streaming.schemas.events import EVENT_SCHEMA, TOPIC_TABLES, TOPICS


CHECKPOINT_ROOT = Path("checkpoints/bronze")
TEMP_GCS_BUCKET_ENV = "BIGQUERY_TEMP_GCS_BUCKET"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_spark() -> SparkSession:
    service_account_path = require_env("GCP_SERVICE_ACCOUNT_JSON_PATH")
    spark = (
        SparkSession.builder.appName("growth-analytics-bronze-ingest")
        .config("spark.sql.session.timeZone", "UTC")
        .config("credentialsFile", service_account_path)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def parse_kafka_events(raw_stream: DataFrame) -> DataFrame:
    payload = col("value").cast("string")
    parsed = raw_stream.select(
        col("topic").alias("kafka_topic"),
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        payload.alias("raw_payload"),
        from_json(payload, EVENT_SCHEMA).alias("event"),
    )

    event_columns = [
        col(f"event.{field.name}").alias(field.name)
        for field in EVENT_SCHEMA.fields
    ]
    event_properties = to_json(
        struct(
            *[
                col(f"event.{field.name}").alias(field.name)
                for field in EVENT_SCHEMA.fields
                if field.name not in {
                    "event_id",
                    "event_type",
                    "event_timestamp",
                    "event_date",
                    "schema_version",
                    "advertiser_id",
                    "product_id",
                    "campaign_id",
                    "ad_group_id",
                    "creative_id",
                    "objective",
                    "channel",
                    "device_id",
                    "user_id",
                    "session_id",
                    "audience_segment_id",
                    "targeting_tag_ids",
                    "country",
                    "region",
                    "city",
                    "device_type",
                    "platform",
                    "ingest_source",
                }
            ]
        )
    )

    return (
        parsed.select(
            *event_columns,
            event_properties.alias("event_properties"),
            "kafka_topic",
            "kafka_partition",
            "kafka_offset",
            "raw_payload",
        )
        .withColumn("event_timestamp", col("event_timestamp").cast("timestamp"))
        .withColumn("event_date", to_date(col("event_date")))
        .withColumn("ingested_at", current_timestamp())
        .withWatermark("event_timestamp", "10 minutes")
    )


def bigquery_writer_options(table: str) -> dict[str, str]:
    dataset = require_env("BIGQUERY_DATASET_RAW")
    project_id = require_env("GCP_PROJECT_ID")
    options = {
        "table": f"{project_id}.{dataset}.{table}",
        "writeMethod": "direct",
        "partitionField": "event_date",
        "clusteredFields": "advertiser_id,campaign_id,device_id",
    }
    temp_bucket = os.getenv(TEMP_GCS_BUCKET_ENV)
    if temp_bucket:
        options["temporaryGcsBucket"] = temp_bucket
    return options


def write_batch_to_bigquery(batch_df: DataFrame, batch_id: int) -> None:
    if batch_df.rdd.isEmpty():
        return

    (
        batch_df.write.format("bigquery")
        .options(**bigquery_writer_options("bronze_events_union"))
        .mode("append")
        .save()
    )

    for topic, table in TOPIC_TABLES.items():
        topic_df = batch_df.where(col("kafka_topic") == topic)
        if topic_df.rdd.isEmpty():
            continue
        (
            topic_df.write.format("bigquery")
            .options(**bigquery_writer_options(table))
            .mode("append")
            .save()
        )


def main() -> None:
    load_dotenv(dotenv_path=".env")
    spark = create_spark()
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", ",".join(TOPICS))
        .option("startingOffsets", os.getenv("KAFKA_STARTING_OFFSETS", "earliest"))
        .option("failOnDataLoss", "false")
        .load()
    )
    parsed = parse_kafka_events(raw_stream)

    query = (
        parsed.writeStream.foreachBatch(write_batch_to_bigquery)
        .option("checkpointLocation", str(CHECKPOINT_ROOT / "bronze_events_union"))
        .outputMode("append")
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()
