from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, from_json, lit, to_date

from streaming.schemas.events import EVENT_SCHEMA


CHECKPOINT_ROOT = Path("checkpoints/identity")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_spark() -> SparkSession:
    service_account_path = require_env("GCP_SERVICE_ACCOUNT_JSON_PATH")
    spark = (
        SparkSession.builder.appName("growth-analytics-identity-resolution")
        .config("spark.sql.session.timeZone", "UTC")
        .config("credentialsFile", service_account_path)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def create_bigquery_client() -> bigquery.Client:
    service_account_path = require_env("GCP_SERVICE_ACCOUNT_JSON_PATH")
    credentials = service_account.Credentials.from_service_account_file(service_account_path)
    return bigquery.Client(credentials=credentials, project=require_env("GCP_PROJECT_ID"))


def ensure_mapping_table(client: bigquery.Client, table_id: str) -> None:
    schema = [
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
    table = bigquery.Table(table_id, schema=schema)
    try:
        client.get_table(table_id)
    except Exception:
        client.create_table(table, exists_ok=True)


def merge_identity_batch(batch_df: DataFrame, batch_id: int) -> None:
    if batch_df.rdd.isEmpty():
        return

    project_id = require_env("GCP_PROJECT_ID")
    dataset = require_env("BIGQUERY_DATASET_RAW")
    destination = f"{project_id}.{dataset}.device_to_user"
    staging = f"{project_id}.{dataset}._device_to_user_stage_{batch_id}"
    client = create_bigquery_client()
    ensure_mapping_table(client, destination)

    pdf = (
        batch_df.select(
            "device_id",
            "user_id",
            "advertiser_id",
            "product_id",
            col("event_timestamp").alias("first_seen_at"),
            col("event_timestamp").alias("last_seen_at"),
            col("event_type").alias("mapping_source"),
            "identity_confidence",
            "updated_at",
        )
        .dropDuplicates(["device_id", "user_id", "advertiser_id", "product_id"])
        .toPandas()
    )
    if pdf.empty:
        return

    load_job = client.load_table_from_dataframe(
        pdf,
        staging,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    load_job.result()

    merge_sql = f"""
    MERGE `{destination}` target
    USING `{staging}` source
    ON target.device_id = source.device_id
       AND target.user_id = source.user_id
       AND target.advertiser_id = source.advertiser_id
       AND target.product_id = source.product_id
    WHEN MATCHED THEN UPDATE SET
      last_seen_at = GREATEST(target.last_seen_at, TIMESTAMP(source.last_seen_at)),
      mapping_source = source.mapping_source,
      identity_confidence = source.identity_confidence,
      updated_at = TIMESTAMP(source.updated_at)
    WHEN NOT MATCHED THEN INSERT (
      device_id, user_id, advertiser_id, product_id, first_seen_at, last_seen_at,
      mapping_source, identity_confidence, updated_at
    )
    VALUES (
      source.device_id, source.user_id, source.advertiser_id, source.product_id,
      TIMESTAMP(source.first_seen_at), TIMESTAMP(source.last_seen_at), source.mapping_source,
      source.identity_confidence, TIMESTAMP(source.updated_at)
    )
    """
    client.query(merge_sql).result()
    client.delete_table(staging, not_found_ok=True)


def main() -> None:
    load_dotenv(dotenv_path=".env")
    spark = create_spark()
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    raw_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", "signups")
        .option("startingOffsets", os.getenv("KAFKA_STARTING_OFFSETS", "earliest"))
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed = (
        raw_stream.select(from_json(col("value").cast("string"), EVENT_SCHEMA).alias("event"))
        .select("event.*")
        .where(col("device_id").isNotNull() & col("user_id").isNotNull())
        .withColumn("event_timestamp", col("event_timestamp").cast("timestamp"))
        .withColumn("event_date", to_date(col("event_date")))
        .withColumn("identity_confidence", lit(1.0))
        .withColumn("updated_at", current_timestamp())
        .withWatermark("event_timestamp", "10 minutes")
    )

    query = (
        parsed.writeStream.foreachBatch(merge_identity_batch)
        .option("checkpointLocation", str(CHECKPOINT_ROOT / "device_to_user"))
        .outputMode("append")
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()
