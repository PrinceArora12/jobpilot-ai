"""
Structured logging setup (spec section 73).

Emits JSON-friendly structured log lines via structlog so events like
job_detected / application_submitted can be grep'd and parsed in later phases.
"""
import logging
import sys

import structlog


def configure_logging(debug: bool = True) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
    )
    # Third-party DB driver internals are noisy at DEBUG and rarely useful —
    # keep our own app logs at DEBUG without drowning in driver chatter.
    for noisy_logger in ("aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG if debug else logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "jobpilot"):
    return structlog.get_logger(name)
