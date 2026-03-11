"""Shared utilities for the :mod:`pylase.qplayvid` player.

OpenLase - a realtime laser graphics toolkit

Copyright (C) 2025 The OpenLase Contributors

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 2.1 or version 3.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Callable, Dict, Iterator, List, Optional, Tuple

__all__ = [
    "LOGGER",
    "DEBUG2",
    "_timing_scope",
    "PerSecondAverager",
]

LOGGER = logging.getLogger("openlase.qplayvid")

DEBUG2 = logging.DEBUG - 1
DEBUG3 = logging.DEBUG - 2
DEBUG4 = logging.DEBUG - 3
logging.addLevelName(DEBUG2, "DEBUG2")
logging.addLevelName(DEBUG3, "DEBUG3")
logging.addLevelName(DEBUG4, "DEBUG4")
setattr(logging, "DEBUG2", DEBUG2)
setattr(logging, "DEBUG3", DEBUG3)
setattr(logging, "DEBUG4", DEBUG4)


def _logger_debug2(self: logging.Logger, message: str, *args: object, **kwargs: object) -> None:
    if self.isEnabledFor(DEBUG2):
        self._log(DEBUG2, message, args, **kwargs)


setattr(logging.Logger, "debug2", _logger_debug2)


def _logger_debug3(self: logging.Logger, message: str, *args: object, **kwargs: object) -> None:
    if self.isEnabledFor(DEBUG3):
        self._log(DEBUG3, message, args, **kwargs)


setattr(logging.Logger, "debug3", _logger_debug3)


def _logger_debug4(self: logging.Logger, message: str, *args: object, **kwargs: object) -> None:
    if self.isEnabledFor(DEBUG4):
        self._log(DEBUG4, message, args, **kwargs)


setattr(logging.Logger, "debug4", _logger_debug4)


@contextmanager
def _timing_scope(label: str, *, level: int = logging.DEBUG) -> Iterator[Callable[[], float]]:
    """Yield a callable returning the elapsed time and log it on exit."""

    start = time.perf_counter()
    elapsed: List[float] = []

    def stop() -> float:
        if not elapsed:
            elapsed.append(time.perf_counter() - start)
        return elapsed[0]

    try:
        yield stop
    finally:
        duration = stop() * 1000.0
        LOGGER.log(level, "%s took %.3f ms", label, duration)


class PerSecondAverager:
    """Aggregate timing metrics and emit rolling averages."""

    def __init__(self, label: str, *, interval: float = 1.0) -> None:
        self.label = label
        self.interval = max(0.0, float(interval))
        self._start = time.perf_counter()
        self._count = 0
        self._totals: Dict[str, float] = {}

    def add(self, **metrics: float) -> Optional[Tuple[Dict[str, float], int, float]]:
        """Record metric durations in seconds and return averages when ready."""

        self._count += 1
        for key, value in metrics.items():
            self._totals[key] = self._totals.get(key, 0.0) + value

        now = time.perf_counter()
        elapsed = now - self._start
        if self.interval <= 0.0 or elapsed < self.interval or self._count == 0:
            return None

        averages = {key: total / self._count for key, total in self._totals.items()}
        count = self._count
        duration = elapsed

        self._start = now
        self._count = 0
        self._totals.clear()

        return averages, count, duration


__exclude_from_traceback__ = True
