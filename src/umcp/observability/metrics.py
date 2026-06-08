"""Observability — Prometheus metrics."""

from prometheus_client import Counter, Histogram, Gauge


# --- Gateway metrics ---
TOOL_CALL_COUNTER = Counter(
    "umcp_tool_calls_total",
    "Total tool calls",
    ["server", "tool", "result"],
)

AUTH_SUCCESS_COUNTER = Counter(
    "umcp_auth_success_total",
    "Successful authentications",
    ["role"],
)

AUTH_FAILURE_COUNTER = Counter(
    "umcp_auth_failure_total",
    "Failed authentications",
    ["reason"],
)

# --- Anonymization metrics ---
ANONYMIZATIONS_COUNTER = Counter(
    "umcp_anonymizations_total",
    "Total entity anonymizations",
    ["entity_type", "detector"],
)

DEANONYMIZATIONS_COUNTER = Counter(
    "umcp_deanonymizations_total",
    "Total entity deanonymizations",
    ["entity_type"],
)

# --- Privacy metrics ---
PII_LEAK_COUNTER = Counter(
    "umcp_pii_leaks_total",
    "Total PII leaks detected",
)

K_ANONYMITY_GAUGE = Gauge(
    "umcp_k_anonymity",
    "Current k-anonymity value",
)

VAULT_SIZE_GAUGE = Gauge(
    "umcp_vault_mappings_total",
    "Total vault mappings active",
)

# --- Audit metrics ---
AUDIT_CHAIN_LENGTH = Gauge(
    "umcp_audit_chain_length",
    "Total events in audit chain",
)

CHAIN_VALIDATION_GAUGE = Gauge(
    "umcp_audit_chain_valid",
    "Whether the audit chain is valid (1=valid, 0=invalid)",
)

# --- Performance metrics ---
PIPELINE_DURATION = Histogram(
    "umcp_pipeline_duration_seconds",
    "Duration of anonymization pipeline",
    ["detector"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

TOOL_DURATION = Histogram(
    "umcp_tool_duration_seconds",
    "Duration of tool execution",
    ["server", "tool"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)