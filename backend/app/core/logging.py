import json
import logging
from collections.abc import Mapping
from datetime import datetime, timezone

from app.core.config import settings


_STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "id",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}

_SENSITIVE_EXACT_KEYS = {
    "authorization",
    "cookie",
    "set_cookie",
    "password",
    "secret",
    "secret_key",
    "encryption_key",
    "api_key",
    "supabase_service_role_key",
    "token",
    "access_token",
    "refresh_token",
    "pre_auth_token",
}

_SENSITIVE_SUFFIXES = (
    "_password",
    "_secret",
    "_secret_key",
    "_api_key",
    "_access_token",
    "_refresh_token",
)


def _normalize_log_key(key: object) -> str:
    return str(key).strip().lower().replace("-", "_")


def _is_sensitive_log_key(key: object) -> bool:
    normalized = _normalize_log_key(key)
    return normalized in _SENSITIVE_EXACT_KEYS or normalized.endswith(
        _SENSITIVE_SUFFIXES
    )


def _redact_log_value(value):
    """Recursively redact secret-bearing values from structured log metadata."""
    if isinstance(value, Mapping):
        return {
            str(key): "***REDACTED***"
            if _is_sensitive_log_key(key)
            else _redact_log_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_redact_log_value(item) for item in value]
    return value


class JSONFormatter(logging.Formatter):
    """Format MedFlow logs as JSON with defense-in-depth secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "module": record.module,
            "funcName": record.funcName,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key in _STANDARD_LOG_RECORD_FIELDS:
                continue
            if _is_sensitive_log_key(key):
                log_obj[key] = "***REDACTED***"
            else:
                log_obj[key] = _redact_log_value(value)

        # Logging must never crash the request path because an extra value is not
        # JSON-native. Stringifying an unusual metadata value is safer than
        # dropping the entire security event.
        return json.dumps(log_obj, default=str)


def setup_logging():
    """Initialize the MedFlow structured logging pipeline."""
    logger = logging.getLogger("medflow")

    if not logger.handlers:
        handler = logging.StreamHandler()
        if settings.ENV == "production":
            handler.setFormatter(JSONFormatter())
            logger.setLevel(logging.INFO)
        else:
            handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            logger.setLevel(logging.DEBUG)

        logger.addHandler(handler)
        logger.propagate = False

    return logger


log = setup_logging()
