"""Helpers for the Python OpenLase playback pipeline.

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

# from .audio import AudioPlayer
# try:  # pragma: no cover - optional Qt dependency
#     from .gui_simple import SimplePlayerWindow, parse_simple_args, run_simple_gui
# except ImportError:  # pragma: no cover - PySide not installed
#     SimplePlayerWindow = None  # type: ignore[assignment]
#     parse_simple_args = None  # type: ignore[assignment]
#     run_simple_gui = None  # type: ignore[assignment]
# from .media import (
#     DecodedVideoFrame,
#     FFmpegVideoFrame,
#     FFmpegVideoSource,
#     NullVideoSource,
#     PyAVVideoSource,
#     VideoSource,
#     detect_frame_geometry,
#     find_media_streams,
#     open_video_source,
# )
# from .player import DisplayMode, PlayerCtx
# from .render import (
#     compute_border_mean,
#     configure_render_params,
#     create_tracer,
#     iter_objects,
#     render_objects,
#     update_threshold,
# )
# from .settings import (
#     AUDIO_BUF,
#     OL_AUDIO_RATE,
#     OL_SAMPLE_RATE,
#     PlayerEvent,
#     PlayerSettings,
#     VideoFrame,
# )
# from .state import FrameSync, PlaybackState
# from .utils import DEBUG2, LOGGER, PerSecondAverager

# __all__ = [
#     "AUDIO_BUF",
#     "AudioPlayer",
#     "DEBUG2",
#     "DecodedVideoFrame",
#     "DisplayMode",
#     "FFmpegVideoFrame",
#     "FFmpegVideoSource",
#     "FrameSync",
#     "LOGGER",
#     "NullVideoSource",
#     "OL_AUDIO_RATE",
#     "OL_SAMPLE_RATE",
#     "PerSecondAverager",
#     "PlaybackState",
#     "PlayerCtx",
#     "PlayerEvent",
#     "PlayerSettings",
#     "PyAVVideoSource",
#     "VideoFrame",
#     "VideoSource",
#     "compute_border_mean",
#     "configure_render_params",
#     "create_tracer",
#     "detect_frame_geometry",
#     "find_media_streams",
#     "iter_objects",
#     "open_video_source",
#     "render_objects",
#     "update_threshold",
# ]
