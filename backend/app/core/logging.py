"""Structured JSON logging with per-request correlation context."""

import contextvars
import json
import logging.config
import sys
from datetime import UTC, datetime

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_configured = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj: dict = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        extras = getattr(record, "_json", None)
        if isinstance(extras, dict):
            obj.update(extras)
        return json.dumps(obj, default=str)


def setup_logging(force: bool = False) -> None:
    """Idempotent global logging configuration (JSON lines to stdout)."""
    global _configured
    if _configured and not force:
        return
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": "app.core.logging.JsonFormatter"}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": sys.stdout,
                }
            },
            "root": {"handlers": ["console"], "level": "INFO"},
        }
    )
    _configured = True
