"""Structured JSON logging with per-request correlation context."""

import contextvars
import json
import logging.config
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


@dataclass
class LogContext:
    request_id: str | None = None
    agency_id: int | None = None
    user_id: int | None = None
    method: str | None = None
    path: str | None = None
    status: int | None = None
    duration_ms: float | None = None
    body_size: int | None = None


_log_context_var: contextvars.ContextVar[LogContext | None] = contextvars.ContextVar(
    "log_context", default=None
)
_configured = False

SLOW_REQUEST_THRESHOLD_MS = 500.0


def get_log_context() -> LogContext:
    ctx = _log_context_var.get()
    if ctx is None:
        ctx = LogContext()
        _log_context_var.set(ctx)
    return ctx


def set_log_context(**kwargs) -> contextvars.Token:
    ctx = get_log_context()
    for k, v in kwargs.items():
        if hasattr(ctx, k):
            setattr(ctx, k, v)
    return _log_context_var.set(ctx)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = get_log_context()
        obj: dict = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": ctx.request_id or request_id_var.get(),
            "method": ctx.method,
            "path": ctx.path,
            "status": ctx.status,
            "duration_ms": ctx.duration_ms,
        }
        if ctx.agency_id is not None:
            obj["agency_id"] = ctx.agency_id
        if ctx.user_id is not None:
            obj["user_id"] = ctx.user_id
        if ctx.body_size is not None:
            obj["body_size"] = ctx.body_size
        if ctx.duration_ms is not None and ctx.duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            obj["slow"] = True
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
