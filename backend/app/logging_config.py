from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_SECRET_KEYS = {
    "access_token",
    "token",
    "authorization",
    "api_key",
    "openai_api_key",
    "workable_access_token",
    "password",
    "secret",
    "bearer",
}


class JsonFormatter(logging.Formatter):
    """Minimal structured JSON logs. Values for known secret keys are redacted."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(_redact(extra))
        return json.dumps(payload, default=str)


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in _SECRET_KEYS:
            redacted[key] = "[redacted]"
        else:
            redacted[key] = value
    return redacted


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
