"""Command line interface for :mod:`pylase.qplayvid`.

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
import logging
from typing import Sequence

from pylase.logging_utils import RelativeTimeFormatter
from pylase.pyplayvid.player import PlayerCtx
from pylase.pyplayvid.settings import PlayerSettings
from pylase.pyplayvid.utils import DEBUG2, LOGGER

__all__ = ["parse_args", "main"]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play video files with OpenLase using pylase")
    parser.add_argument("source", help="Path to a video file or a camera index (integer)")
    parser.add_argument("--fps", type=float, default=None, help="Override the detected frame rate")
    parser.add_argument(
        "--decoder",
        default="pyav",
        choices=["pyav", "ffmpeg", "auto"],
        help="Video decoding backend to use",
    )
    parser.add_argument("--loop", action="store_true", help="Restart playback automatically when the video ends")
    parser.add_argument(
        "--no-color",
        dest="color",
        action="store_false",
        help="Render everything in white instead of sampling the video colors",
    )
    parser.set_defaults(color=True)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG2", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    parser.add_argument(
        "--stats-interval",
        type=int,
        default=60,
        help="How many frames between statistics reports (0 disables reporting)",
    )
    parser.add_argument(
        "--benchmark-interval",
        type=float,
        default=1.0,
        help="Seconds between benchmark timing logs (0 disables reporting)",
    )

    parser.add_argument("--canny", dest="canny", action="store_true", help="Use Canny edge detection")
    parser.add_argument(
        "--threshold-mode",
        dest="canny",
        action="store_false",
        help="Use a simple brightness threshold instead of Canny",
    )
    parser.set_defaults(canny=True)
    parser.add_argument(
        "--split-threshold",
        dest="split_threshold",
        action="store_true",
        help="Adapt the threshold based on the detected background brightness",
    )
    parser.add_argument(
        "--no-split-threshold",
        dest="split_threshold",
        action="store_false",
        help="Disable adaptive thresholding",
    )
    parser.set_defaults(split_threshold=False)

    parser.add_argument("--blur", type=int, default=100, help="Gaussian blur (percent * 0.01 -> sigma)")
    parser.add_argument("--scale", type=int, default=100, help="Scale the decoded frame before tracing")
    parser.add_argument("--threshold", type=int, default=30, help="Primary threshold value")
    parser.add_argument("--threshold2", type=int, default=20, help="Secondary threshold value")
    parser.add_argument("--darkval", type=int, default=96, help="Dark background threshold")
    parser.add_argument("--lightval", type=int, default=160, help="Light background threshold")
    parser.add_argument("--offset", type=int, default=0, help="Border offset for background sampling")
    parser.add_argument("--decimation", type=int, default=3, help="Skip every N-1 traced points")
    parser.add_argument("--minsize", type=int, default=10, help="Minimum segment length")
    parser.add_argument("--startwait", type=int, default=8, help="Blanking samples before each frame")
    parser.add_argument("--endwait", type=int, default=3, help="Blanking samples after each frame")
    parser.add_argument("--dwell", type=int, default=2, help="Corner dwell samples")
    parser.add_argument("--offspeed", type=int, default=50, help="Blanking speed (percent)")
    parser.add_argument("--snap", type=int, default=10, help="Corner snapping strength")
    parser.add_argument("--minrate", type=int, default=15, help="Minimum output frame rate (0 disables)")
    parser.add_argument("--overscan", type=int, default=0, help="Extra overscan applied to the output")

    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    level = DEBUG2 if args.log_level == "DEBUG2" else getattr(logging, args.log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(RelativeTimeFormatter("%(relative_time)s %(levelname)s %(message)s"))
    logging.basicConfig(level=level, handlers=[handler])

    settings = PlayerSettings.from_namespace(args)

    try:
        ctx = PlayerCtx(
            args.source,
            settings,
            loop=args.loop,
            fps_override=args.fps,
            use_color=args.color,
            stats_interval=args.stats_interval,
            benchmark_interval=args.benchmark_interval,
            decoder=args.decoder,
        )
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        return 1

    try:
        ctx.playvid_play()
        ctx.wait_until_finished()
    except KeyboardInterrupt:
        LOGGER.info("Interrupted by user")
        ctx.playvid_stop()
        return 1
    except Exception:  # pragma: no cover - best effort logging
        LOGGER.exception("Playback failed")
        ctx.playvid_stop()
        return 1
    else:
        ctx.playvid_stop()
    return 0
