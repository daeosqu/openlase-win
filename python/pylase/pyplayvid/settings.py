"""Configuration structures and dataclasses for :mod:`pylase.qplayvid`.

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

import argparse
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .utils import LOGGER

__all__ = [
    "PlayerSettings",
    "PlayerEvent",
    "VideoFrame",
    "OL_SAMPLE_RATE",
    "get_audio_rate",
    "AUDIO_BUF",
]


@dataclass
class PlayerSettings:
    """Mirrors the classic ``qplayvid`` tuning parameters."""

    canny: bool = True
    split_threshold: bool = False
    blur: int = 100
    scale: int = 100
    threshold: int = 30
    threshold2: int = 20
    darkval: int = 96
    lightval: int = 160
    offset: int = 0
    decimation: int = 2
    minsize: int = 10
    startwait: int = 8
    endwait: int = 3
    dwell: int = 2
    offspeed: int = 50
    snap: int = 10
    minrate: int = 15
    overscan: int = 0

    @classmethod
    def from_namespace(cls, ns: argparse.Namespace) -> "PlayerSettings":
        settings = cls()
        for field in cls.__dataclass_fields__:
            if hasattr(ns, field):
                setattr(settings, field, getattr(ns, field))
        settings.decimation = max(1, settings.decimation)
        settings.scale = max(1, settings.scale)
        settings.blur = max(0, settings.blur)
        settings.minsize = max(0, settings.minsize)
        settings.dwell = max(0, settings.dwell)
        settings.offspeed = max(0, settings.offspeed)
        settings.snap = max(0, settings.snap)
        settings.minrate = max(0, settings.minrate)
        return settings


@dataclass
class PlayerEvent:
    time: float = 0.0
    ftime: float = 0.0
    frames: int = 0
    objects: int = 0
    points: int = 0
    resampled_points: int = 0
    resampled_blacks: int = 0
    padding_points: int = 0
    pts: float = -1.0
    ended: int = 0


@dataclass
class VideoFrame:
    """Raw frame produced by the decoder thread."""

    index: int
    pts: float
    timestamp: float
    seekid: int
    image: np.ndarray


OL_SAMPLE_RATE = int(os.environ.get("OL_SAMPLE_RATE", "48000"))
_AUDIO_RATE_CACHE: Optional[int] = None
_AUDIO_RATE_WARNED = False


def get_audio_rate() -> int:
    """Resolve the JACK audio sample rate lazily for video playback."""

    global _AUDIO_RATE_CACHE, _AUDIO_RATE_WARNED

    if _AUDIO_RATE_CACHE is not None:
        return _AUDIO_RATE_CACHE

    audio_env = os.environ.get("OL_AUDIO_RATE")
    if audio_env and not _AUDIO_RATE_WARNED:
        LOGGER.warning(
            "Ignoring OL_AUDIO_RATE=%s; JACK server rate will be used instead",
            audio_env,
        )
        _AUDIO_RATE_WARNED = True

    jack_rate = 0
    try:
        import pylase as ol

        jack_rate = ol.getJackRate()
    except AttributeError:  # pragma: no cover - legacy bindings
        LOGGER.warning(
            "Installed pylase binding does not expose getJackRate(); defaulting to %d Hz",
            OL_SAMPLE_RATE,
        )
    except Exception as exc:  # pragma: no cover - diagnostic
        LOGGER.warning(
            "Failed to query JACK sample rate (%s); defaulting to %d Hz",
            exc,
            OL_SAMPLE_RATE,
        )

    if not jack_rate:
        jack_rate = OL_SAMPLE_RATE

    _AUDIO_RATE_CACHE = int(jack_rate)
    return _AUDIO_RATE_CACHE

AUDIO_BUF = 3
