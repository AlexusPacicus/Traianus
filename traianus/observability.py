"""
Observability layer for Traianus: structured logging.

Provides:
- structlog JSON logging with request_id binding
- request_id generation and propagation helpers
- high-resolution timer for latency measurement

Dependencies: structlog (available in the project venv).
"""
import time
import uuid

import structlog

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
