"""Logging configuration: structlog with correlation IDs and box formatting."""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

from openclaw_lite.logging.formatter import structlog_box_processor

# Context variable for request-scoped correlation IDs
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def _inject_correlation_id(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Automatically attach the current correlation ID to every log event."""
    cid = correlation_id_var.get("")
    if cid and "correlation_id" not in event_dict:
        event_dict["correlation_id"] = cid
    return event_dict


def configure_logging(*, level: int = logging.INFO) -> None:
    """Initialize structlog with box-drawing formatter and stdlib integration.

    Call this once at application startup.
    """
    # Configure stdlib logging to pass through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            _inject_correlation_id,
            structlog_box_processor,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound with the given module name."""
    return structlog.get_logger(name)
