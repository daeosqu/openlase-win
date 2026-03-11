"""Rendering helpers for :mod:`pylase.qplayvid`.

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

from typing import Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import pylase as ol

from .settings import PlayerSettings, OL_SAMPLE_RATE
from .utils import LOGGER

__all__ = [
    "configure_render_params",
    "create_tracer",
    "compute_border_mean",
    "update_threshold",
    "iter_objects",
    "render_objects",
]


def configure_render_params(settings: PlayerSettings, width: int, height: int) -> ol.RenderParams:
    LOGGER.debug(
        "Configuring render params for %dx%d with settings=%s", width, height, settings
    )
    params = ol.RenderParams()
    params.rate = OL_SAMPLE_RATE
    params.on_speed = 2.0 / 100.0
    params.off_speed = settings.offspeed * 0.002
    params.start_wait = settings.startwait
    params.end_wait = settings.endwait
    params.start_dwell = settings.dwell
    params.end_dwell = settings.dwell
    params.snap = (settings.snap * 2.0) / float(max(width, height))
    params.render_flags = ol.RENDER_GRAYSCALE
    params.min_length = settings.minsize
    params.max_framelen = 0 if settings.minrate == 0 else int(params.rate / settings.minrate)
    return params


def create_tracer(settings: PlayerSettings, width: int, height: int) -> ol.Tracer:
    LOGGER.debug(
        "Creating tracer (%dx%d) canny=%s blur=%.2f threshold=%d/%d",
        width,
        height,
        settings.canny,
        settings.blur / 100.0,
        settings.threshold,
        settings.threshold2,
    )
    tracer = ol.Tracer(width, height)
    tracer.mode = ol.TRACE_CANNY if settings.canny else ol.TRACE_THRESHOLD
    tracer.sigma = settings.blur / 100.0
    tracer.threshold = settings.threshold
    tracer.threshold2 = settings.threshold2
    return tracer


def compute_border_mean(frame: np.ndarray, edge_offset: int) -> float:
    height, width = frame.shape[:2]
    edge_offset = max(0, min(edge_offset, min(width, height) // 2 - 1))
    x0 = edge_offset
    x1 = width - edge_offset
    y0 = edge_offset
    y1 = height - edge_offset
    if x1 <= x0 or y1 <= y0:
        return float(frame.mean())
    top = frame[y0, x0:x1]
    bottom = frame[y1 - 1, x0:x1]
    left = frame[y0:y1, x0]
    right = frame[y0:y1, x1 - 1]
    border = np.concatenate((top, bottom, left, right))
    mean_value = float(border.mean())
    LOGGER.debug2(
        "Border mean computed (offset=%d, mean=%.3f)",
        edge_offset,
        mean_value,
    )
    return mean_value


def update_threshold(
    tracer: ol.Tracer,
    settings: PlayerSettings,
    frame: np.ndarray,
    min_dim: int,
    bg_white: Optional[bool],
) -> Optional[bool]:
    if settings.canny:
        return None
    threshold_value = settings.threshold
    if settings.split_threshold:
        edge_offset = int(min_dim * settings.offset / 100.0)
        border_mean = compute_border_mean(frame, edge_offset)
        mid = (settings.darkval + settings.lightval) / 2.0
        if bg_white is None:
            bg_white = border_mean > mid
        if bg_white and border_mean < settings.darkval:
            bg_white = False
        elif not bg_white and border_mean > settings.lightval:
            bg_white = True
        threshold_value = settings.threshold2 if bg_white else settings.threshold
    tracer.threshold = int(threshold_value)
    LOGGER.debug2(
        "Threshold update: value=%d bg_white=%s split=%s", tracer.threshold, bg_white, settings.split_threshold
    )
    return bg_white


def iter_objects(
    objects: Iterable[Sequence[Tuple[int, int]]],
    decimation: int,
) -> Iterable[List[Tuple[int, int]]]:
    for obj in objects:
        if not obj:
            continue
        if decimation <= 1:
            yield list(obj)
            continue
        reduced = [pt for idx, pt in enumerate(obj) if idx % decimation == 0]
        if len(reduced) >= 2:
            LOGGER.debug3("Decimated object from %d to %d points", len(obj), len(reduced))
            yield reduced


def render_objects(
    objects: Iterable[Sequence[Tuple[int, int]]],
    color_frame: Optional[np.ndarray],
    scale_x: float,
    scale_y: float,
    center_x: float,
    center_y: float,
) -> None:
    ol.loadIdentity3()
    ol.loadIdentity()
    rendered = 0
    for obj in objects:
        if len(obj) < 2:
            continue
        ol.begin(ol.LINESTRIP)
        for x, y in obj:
            fx = (x - center_x) * scale_x
            fy = -(y - center_y) * scale_y
            if color_frame is not None:
                cx = min(max(int(round(x)), 0), color_frame.shape[1] - 1)
                cy = min(max(int(round(y)), 0), color_frame.shape[0] - 1)
                r, g, b = (int(v) for v in color_frame[cy, cx])
                color = (r << 16) | (g << 8) | b
            else:
                color = ol.C_WHITE
            ol.vertex((fx, fy), color)
        ol.end()
        rendered += 1
    LOGGER.debug3("Rendered %d object strips", rendered)
