"""Logging helpers for OpenLase tools."""

from __future__ import annotations

import logging


class RelativeTimeFormatter(logging.Formatter):
    """Formatter that prefixes log records with relative time in seconds."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatter
        relative_seconds = record.relativeCreated / 1000.0
        record.relative_time = f"{relative_seconds:0.3f}"
        try:
            return super().format(record)
        finally:
            del record.relative_time
