"""Data structures shared between the pyplayvid GUI and playback core."""

# OpenLase - a realtime laser graphics toolkit
#
# Copyright (C) 2025 The OpenLase Contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2.1 or version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

__all__ = ["PreviewFrame", "PointPath"]

PointPath = np.ndarray


@dataclass(slots=True)
class PreviewFrame:
    """Snapshot of the most recent frame for GUI previews."""

    index: int
    timestamp: float
    duration: float
    frame_size: Tuple[int, int]
    video_frame: np.ndarray
    laser_paths: List[PointPath]
    debug_frame: Optional[np.ndarray] = None
    pts: float = -1.0

    def copy_for_gui(self) -> "PreviewFrame":
        """Return a shallow copy with NumPy arrays duplicated for GUI usage."""

        video_copy = self.video_frame.copy()
        debug_copy = self.debug_frame.copy() if self.debug_frame is not None else None
        paths_copy = [path.copy() for path in self.laser_paths]
        return PreviewFrame(
            index=self.index,
            timestamp=self.timestamp,
            duration=self.duration,
            frame_size=self.frame_size,
            video_frame=video_copy,
            laser_paths=paths_copy,
            debug_frame=debug_copy,
            pts=self.pts,
        )
