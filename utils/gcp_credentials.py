from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def setup_credentials() -> None:
    """Ensure GCP_SERVICE_ACCOUNT_JSON_PATH points to a valid file.

    On Streamlit Cloud (and other environments where a keyfile can't be stored on
    disk), set GCP_SERVICE_ACCOUNT_JSON to the raw JSON content of the service
    account key. This function writes it to a temp file and sets
    GCP_SERVICE_ACCOUNT_JSON_PATH so all downstream code — Python clients, dbt,
    MetricFlow subprocesses — can find it without any further changes.
    """
    json_content = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if not json_content:
        return

    path = os.getenv("GCP_SERVICE_ACCOUNT_JSON_PATH", "")
    if path and Path(path).exists():
        return

    # Validate the JSON before writing so the error is clear.
    try:
        json.loads(json_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"GCP_SERVICE_ACCOUNT_JSON is not valid JSON: {exc}") from exc

    cred_path = Path(tempfile.gettempdir()) / "gcp_sa.json"
    cred_path.write_text(json_content)
    os.environ["GCP_SERVICE_ACCOUNT_JSON_PATH"] = str(cred_path)
