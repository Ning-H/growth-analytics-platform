# Streamlit Community Cloud Deploy Notes

Use these settings for the hosted dashboard.

## App Settings

- Repository: `Ning-H/growth-analytics-platform`
- Branch: `main`
- Main file path: `dashboard/app.py`
- Python version: `3.13`

The dashboard has its own dependency file at `dashboard/requirements.txt`. Streamlit Cloud checks the entrypoint folder before the repository root, so this avoids installing the local-only Spark/Kafka simulator stack for the hosted app.

## Secrets

Paste these into the Streamlit Cloud app secrets editor. Do not paste the local `.env` file exactly, because local file paths such as `/Users/ning/.gcp/...json` do not exist in Streamlit Cloud.

```toml
GCP_PROJECT_ID = "your-gcp-project-id"
BIGQUERY_DATASET_RAW = "growth_raw"
BIGQUERY_DATASET_ANALYTICS = "growth_analytics"
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"

GCP_SERVICE_ACCOUNT_JSON = """
{
  "type": "service_account",
  "project_id": "your-gcp-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
"""
```

The deployed app writes `GCP_SERVICE_ACCOUNT_JSON` to a temporary file at runtime and points dbt/MetricFlow at that file. This is why Cloud should use JSON content, while local development can keep using `GCP_SERVICE_ACCOUNT_JSON_PATH`.

