#!/usr/bin/env bash
set -euo pipefail

JOB="${1:-bronze}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export GOOGLE_APPLICATION_CREDENTIALS="${GCP_SERVICE_ACCOUNT_JSON_PATH:-}"
export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

PACKAGES="org.apache.spark:spark-sql-kafka-0-10_2.13:4.1.1,com.google.cloud.spark:spark-4.1-bigquery:0.44.1-preview"

case "$JOB" in
  bronze)
    SCRIPT="streaming/ingest_to_bigquery.py"
    ;;
  identity)
    SCRIPT="streaming/identity_resolution.py"
    ;;
  *)
    echo "Unknown job: $JOB. Use 'bronze' or 'identity'." >&2
    exit 2
    ;;
esac

exec uv run spark-submit \
  --packages "$PACKAGES" \
  --conf "spark.hadoop.google.cloud.auth.service.account.enable=true" \
  --conf "spark.hadoop.google.cloud.auth.service.account.json.keyfile=${GCP_SERVICE_ACCOUNT_JSON_PATH}" \
  "$SCRIPT"
