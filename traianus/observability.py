"""
Observability layer for Traianus: structured logging and Prometheus metrics.

Provides:
- structlog JSON logging with request_id binding
- Prometheus counters/histograms for the /ingesta/vector endpoint
- request_id generation and propagation helpers

Dependencies: prometheus_client, structlog (both available in the project venv).
"""
import time
import uuid

import structlog
from prometheus_client import Counter, Histogram

INGESTA_VECTOR_REQUESTS = Counter(
    "ingesta_vector_requests_total",
    "Total vector ingestion requests",
    labelnames=["status", "reason"],
)

INGESTA_VECTOR_LATENCY = Histogram(
    "ingesta_vector_latency_seconds",
    "End-to-end request latency for /ingesta/vector",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

INGESTA_VECTOR_PROJECTION_LATENCY = Histogram(
    "ingesta_vector_projection_latency_seconds",
    "Spectral projection phase latency",
    buckets=(0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05),
)

INGESTA_VECTOR_GATE_REJECTS = Counter(
    "ingesta_vector_gate_rejects_total",
    "Requests rejected by C1 gate (topological key failed)",
)

INGESTA_VECTOR_PERSIST_CONFLICTS = Counter(
    "ingesta_vector_persist_conflicts_total",
    "PK conflicts on insert_node_revision",
)

_logger_configured = False


def configure_structlog():
    global _logger_configured
    if _logger_configured:
        return
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _logger_configured = True


def get_logger(request_id=None):
    configure_structlog()
    logger = structlog.get_logger("traianus.vector")
    if request_id:
        logger = logger.bind(request_id=request_id)
    return logger


def generate_request_id():
    return str(uuid.uuid4())


def now_seconds():
    return time.perf_counter()
