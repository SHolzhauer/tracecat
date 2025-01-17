import os
from pathlib import Path

HTTP_MAX_RETRIES = 10
LLM_MAX_RETRIES = 3

TRACECAT_DIR = (
    Path(os.environ.get("TRACECAT_DIR", "~/.tracecat")).expanduser().resolve()
)
TRACECAT__SCHEDULE_INTERVAL_SECONDS = os.environ.get(
    "TRACECAT__SCHEDULE_INTERVAL_SECONDS", 60
)
TRACECAT__SCHEDULE_MAX_CONNECTIONS = 6
TRACECAT__APP_ENV = os.environ.get("TRACECAT__APP_ENV", "dev")
TRACECAT__API_URL = os.environ.get("TRACECAT__API_URL", "http://localhost:8000")
TRACECAT__PUBLIC_RUNNER_URL = os.environ.get(
    "TRACECAT__PUBLIC_RUNNER_URL", "http://localhost:8001"
)
TRACECAT__DB_URI = os.environ.get(
    "TRACECAT__DB_URI",
    "postgresql+psycopg://postgres:postgres@postgres_db:5432/postgres",
)

TRACECAT__TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
TRACECAT__TRIAGE_DIR = TRACECAT_DIR / "triage"
TRACECAT__TRIAGE_DIR.mkdir(parents=True, exist_ok=True)

TRACECAT__SERVICE_ROLES_WHITELIST = ["tracecat-runner", "tracecat-api", "tracecat-cli"]

# Temporal configs
TEMPORAL__CLUSTER_URL = os.environ.get(
    "TEMPORAL__CLUSTER_URL", "http://localhost:7233"
)  # AKA Temporal target host
TEMPORAL__CLUSTER_NAMESPACE = os.environ.get(
    "TEMPORAL__CLUSTER_NAMESPACE", "default"
)  # Temporal namespace
TEMPORAL__TLS_ENABLED = os.environ.get("TEMPORAL__TLS_ENABLED", False)
TEMPORAL__TLS_ENABLED = os.environ.get("TEMPORAL__TLS_ENABLED", False)
TEMPORAL__TLS_CLIENT_CERT = os.environ.get("TEMPORAL__TLS_CLIENT_CERT")
TEMPORAL__TLS_CLIENT_PRIVATE_KEY = os.environ.get("TEMPORAL__TLS_CLIENT_PRIVATE_KEY")

# Tenacity Retry Settings
RETRY_EXPONENTIAL_MULTIPLIER = 1
RETRY_MIN_WAIT_TIME = 1
RETRY_MAX_WAIT_TIME = 60
RETRY_STOP_AFTER_ATTEMPT = 5
