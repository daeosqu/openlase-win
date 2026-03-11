"""Simple PySide-based GUI wrapper around :mod:`pylase.pyplayvid` playback.

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
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable, Optional, Sequence

from .player import DisplayMode, PlayerCtx
from .settings import PlayerSettings
from .utils import DEBUG2, LOGGER

try:  # pragma: no cover - import resolution depends on environment
    from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
except ImportError:  # pragma: no cover - PySide2 not available
    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
    except ImportError as exc:  # pragma: no cover - no Qt bindings
        raise ImportError("PySide2 or PySide6 is required for the simple pyplayvid GUI") from exc

__all__ = ["SimplePlayerWindow", "parse_simple_args", "run_simple_gui"]

if hasattr(QtCore.Qt, "AlignCenter"):
    _ALIGN_CENTER = QtCore.Qt.AlignCenter
else:  # pragma: no cover - PySide6 enum-style flags
    _ALIGN_CENTER = QtCore.Qt.AlignmentFlag.AlignCenter

if hasattr(QtCore.Qt, "Horizontal"):
    _ORIENTATION_HORIZONTAL = QtCore.Qt.Horizontal
else:  # pragma: no cover - PySide6 enum-style flags
    _ORIENTATION_HORIZONTAL = QtCore.Qt.Orientation.Horizontal

if hasattr(QtCore.Qt, "KeepAspectRatio"):
    _KEEP_ASPECT = QtCore.Qt.KeepAspectRatio
else:  # pragma: no cover - PySide6 enum-style flags
    _KEEP_ASPECT = QtCore.Qt.AspectRatioMode.KeepAspectRatio

if hasattr(QtCore.Qt, "SmoothTransformation"):
    _SMOOTH_TRANSFORM = QtCore.Qt.SmoothTransformation
else:  # pragma: no cover - PySide6 enum-style flags
    _SMOOTH_TRANSFORM = QtCore.Qt.TransformationMode.SmoothTransformation


class _PreviewDispatcher(QtCore.QObject):
    frameReady = QtCore.Signal(object)


class SimplePlayerWindow(QtWidgets.QWidget):
    """Minimal Qt window exposing basic playback controls."""

    poll_interval_ms = 100

    def __init__(
        self,
        source: str,
        settings: Optional[PlayerSettings] = None,
        *,
        loop: bool = False,
        fps_override: Optional[float] = None,
        use_color: bool = True,
        stats_interval: int = 0,
        benchmark_interval: float = 1.0,
        decoder: str = "pyav",
        player_factory: Callable[..., PlayerCtx] = PlayerCtx,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._source = source
        self._settings = settings or PlayerSettings()
        self._loop = loop
        self._fps_override = fps_override
        self._use_color = use_color
        self._stats_interval = max(0, stats_interval)
        self._benchmark_interval = max(0.0, float(benchmark_interval))
        self._decoder = decoder
        self._player_factory = player_factory
        self._ctx: Optional[PlayerCtx] = None

        self._slider_duration_ms = 0
        self._slider_duration_seconds = 0.0
        self._slider_scrubbing = False
        self._last_known_frames = 0
        self._last_known_position = 0.0
        self._preview_image_cache = None

        self._preview_dispatcher = _PreviewDispatcher()
        self._preview_dispatcher.frameReady.connect(self._update_preview)

        self._init_ui()

        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.setInterval(self.poll_interval_ms)
        self._poll_timer.timeout.connect(self._poll_player)
        self._poll_timer.start()

    # ------------------------------------------------------------------
    # Qt event handlers
    # ------------------------------------------------------------------
    def closeEvent(self, event: QtCore.QEvent) -> None:  # type: ignore[override]
        self._shutdown_player()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        self.setWindowTitle(self._window_title())

        layout = QtWidgets.QVBoxLayout(self)

        self._frame_label = QtWidgets.QLabel("Frame: 0", self)
        self._frame_label.setAlignment(_ALIGN_CENTER)
        layout.addWidget(self._frame_label)

        self._position_slider = QtWidgets.QSlider(_ORIENTATION_HORIZONTAL, self)
        self._position_slider.setObjectName("positionSlider")
        self._position_slider.sliderPressed.connect(self._handle_slider_pressed)
        self._position_slider.sliderMoved.connect(self._handle_slider_moved)
        self._position_slider.sliderReleased.connect(self._handle_slider_released)
        layout.addWidget(self._position_slider)
        self._reset_slider()

        self._preview_label = QtWidgets.QLabel("Preview unavailable", self)
        self._preview_label.setObjectName("previewLabel")
        self._preview_label.setAlignment(_ALIGN_CENTER)
        self._preview_label.setMinimumSize(240, 135)
        self._preview_label.setStyleSheet(
            "background-color: #202020; color: #aaaaaa; border: 1px solid #404040;"
        )
        layout.addWidget(self._preview_label)

        button_row = QtWidgets.QHBoxLayout()
        layout.addLayout(button_row)

        self._play_button = QtWidgets.QPushButton("Play", self)
        self._play_button.clicked.connect(self._handle_play)
        button_row.addWidget(self._play_button)

        self._pause_button = QtWidgets.QPushButton("Pause", self)
        self._pause_button.clicked.connect(self._handle_pause)
        self._pause_button.setEnabled(False)
        button_row.addWidget(self._pause_button)

        self._stop_button = QtWidgets.QPushButton("Stop", self)
        self._stop_button.clicked.connect(self._handle_stop)
        self._stop_button.setEnabled(False)
        button_row.addWidget(self._stop_button)

    def _window_title(self) -> str:
        name = Path(self._source).name or self._source
        return f"pyplayvid (simple) - {name}"

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
    def _handle_play(self) -> None:
        ctx = self._ensure_context()
        if ctx is None:
            return
        try:
            ctx.playvid_play()
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Play command failed")
            self._show_error("Playback error", str(exc))
            self._discard_context()
        self._poll_player()

    def _handle_pause(self) -> None:
        ctx = self._ctx
        if ctx is None:
            return
        try:
            ctx.playvid_pause()
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Pause command failed")
            self._show_error("Playback error", str(exc))
            self._discard_context()
        self._poll_player()

    def _handle_stop(self) -> None:
        self._shutdown_player()
        self._frame_label.setText("Frame: 0")
        self._update_buttons(DisplayMode.STOP)

    # ------------------------------------------------------------------
    # Player coordination
    # ------------------------------------------------------------------
    def _ensure_context(self) -> Optional[PlayerCtx]:
        if self._ctx is not None:
            return self._ctx
        LOGGER.debug("Creating PlayerCtx for %s", self._source)
        try:
            settings = replace(self._settings)
        except TypeError:  # pragma: no cover - defensive fallback
            settings = PlayerSettings(**vars(self._settings))
        try:
            ctx = self._player_factory(
                self._source,
                settings,
                loop=self._loop,
                fps_override=self._fps_override,
                use_color=self._use_color,
                stats_interval=self._stats_interval,
                benchmark_interval=self._benchmark_interval,
                decoder=self._decoder,
            )
        except Exception as exc:
            LOGGER.exception("Failed to initialise PlayerCtx")
            self._show_error("Initialisation error", str(exc))
            return None
        self._ctx = ctx
        self._configure_slider_for_context(ctx)
        try:
            ctx.playvid_set_framecb(self._handle_preview_frame)
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to register frame callback")
        return ctx

    def _shutdown_player(self) -> None:
        ctx = self._ctx
        if ctx is None:
            return
        try:
            try:
                ctx.playvid_set_framecb(None)
            except Exception:  # pragma: no cover - defensive logging
                LOGGER.exception("Failed to detach frame callback")
            ctx.playvid_stop()
        except Exception:  # pragma: no cover - best effort shutdown
            LOGGER.exception("Stopping player failed")
        finally:
            self._discard_context()

    def _discard_context(self) -> None:
        self._ctx = None
        self._reset_slider()
        self._clear_preview()

    def _poll_player(self) -> None:
        ctx = self._ctx
        if ctx is None:
            self._update_buttons(DisplayMode.STOP)
            return
        try:
            with ctx.display_mode_lock:
                mode = ctx.display_mode
        except AttributeError:  # pragma: no cover - unexpected API drift
            mode = DisplayMode.STOP
        frames = 0
        position_seconds = 0.0
        try:
            with ctx.event_mutex:
                frames = getattr(ctx.player_event, "frames", 0)
                position_seconds = getattr(ctx.player_event, "time", 0.0)
        except AttributeError:  # pragma: no cover - unexpected API drift
            frames = 0
            position_seconds = 0.0
        self._last_known_frames = frames
        self._last_known_position = position_seconds
        if not self._slider_scrubbing:
            duration = self._slider_duration_seconds if self._slider_duration_ms > 0 else None
            self._set_status_label(frames, position_seconds, duration)
        self._update_slider_position(position_seconds)
        self._update_buttons(mode)
        if getattr(ctx, "finished_event", None) is not None:
            try:
                finished = ctx.finished_event.is_set()
            except Exception:  # pragma: no cover - defensive logging
                finished = False
            if finished and mode != DisplayMode.STOP:
                LOGGER.info("Playback finished; stopping player")
                self._shutdown_player()

    def _update_buttons(self, mode: DisplayMode) -> None:
        playing = mode == DisplayMode.PLAY
        paused = mode == DisplayMode.PAUSE
        active = playing or paused
        self._play_button.setEnabled(not playing)
        self._pause_button.setEnabled(playing)
        self._stop_button.setEnabled(active)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _show_error(self, title: str, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, title, message)

    # def _configure_slider_for_context(self, ctx: PlayerCtx) -> None:
    #     try:
    #         duration = ctx.playvid_get_duration()
    #     except Exception:  # pragma: no cover - defensive logging
    #         LOGGER.exception("Failed to query playback duration")
    #         duration = 0.0
    #     if duration and duration > 0:
    #         duration_ms = int(round(duration * 1000.0))
    #         self._slider_duration_seconds = duration
    #     else:
    #         duration_ms = 0
    #         self._slider_duration_seconds = 0.0
    #     self._slider_duration_ms = duration_ms
    #     if duration_ms > 0:
    #         self._position_slider.setEnabled(True)
    #         self._position_slider.setRange(0, duration_ms)
    #         single_step = max(1, duration_ms // 100)
    #         self._position_slider.setSingleStep(single_step)
    #         self._position_slider.setPageStep(max(single_step, duration_ms // 10))
    #     else:
    #         self._position_slider.setEnabled(False)
    #         self._position_slider.setRange(0, 0)
    #     self._position_slider.setValue(0)
    #     start_position = 0.0 if duration_ms > 0 else None
    #     duration_arg = duration if duration_ms > 0 else None
    #     self._set_status_label(0, start_position, duration_arg)
    #     self._last_known_frames = 0
    #     self._last_known_position = 0.0

    def _configure_slider_for_context(self, ctx: PlayerCtx) -> None:
        try:
            duration = ctx.playvid_get_duration()
        except Exception:  # defensive logging
            LOGGER.exception("Failed to query playback duration")
            duration = 0.0

        # --- sanity check (PCM 対策) ---
        if not duration or duration < 0 or duration > 86400:  # 24時間超は異常
            duration = 0.0
            try:
                stream = getattr(ctx, "audio_stream", None)
                if stream is not None:
                    sr = getattr(stream, "rate", 0) or getattr(
                        getattr(stream, "codec_context", None), "sample_rate", 0
                    )
                    frames = getattr(stream, "frames", 0)
                    if sr > 0 and frames > 0:
                        duration = frames / float(sr)
            except Exception:
                pass

        if duration > 0:
            duration_ms = min(int(round(duration * 1000.0)), 2**31 - 1)  # Qt int safety
            self._slider_duration_seconds = duration
        else:
            duration_ms = 0
            self._slider_duration_seconds = 0.0

        self._slider_duration_ms = duration_ms

        if duration_ms > 0:
            self._position_slider.setEnabled(True)
            self._position_slider.setRange(0, duration_ms)
            single_step = max(1, duration_ms // 100)
            self._position_slider.setSingleStep(single_step)
            self._position_slider.setPageStep(max(single_step, duration_ms // 10))
        else:
            self._position_slider.setEnabled(False)
            self._position_slider.setRange(0, 0)

        self._position_slider.setValue(0)
        start_position = 0.0 if duration_ms > 0 else None
        duration_arg = duration if duration_ms > 0 else None
        self._set_status_label(0, start_position, duration_arg)
        self._last_known_frames = 0
        self._last_known_position = 0.0

    def _reset_slider(self) -> None:
        self._slider_duration_ms = 0
        self._slider_duration_seconds = 0.0
        self._slider_scrubbing = False
        if hasattr(self, "_position_slider"):
            self._position_slider.setEnabled(False)
            self._position_slider.setRange(0, 0)
            self._position_slider.setValue(0)
        self._last_known_frames = 0
        self._last_known_position = 0.0
        self._set_status_label(0, None, None)

    def _clear_preview(self) -> None:
        self._preview_image_cache = None
        if hasattr(self, "_preview_label"):
            self._preview_label.setPixmap(QtGui.QPixmap())
            self._preview_label.setText("Preview unavailable")

    def _update_slider_position(self, position_seconds: float) -> None:
        if self._slider_duration_ms <= 0 or self._slider_scrubbing:
            return
        value = max(0, min(self._slider_duration_ms, int(round(position_seconds * 1000.0))))
        if self._position_slider.value() != value:
            self._position_slider.setValue(value)

    def _handle_slider_pressed(self) -> None:
        if not self._position_slider.isEnabled():
            return
        self._slider_scrubbing = True

    def _handle_slider_moved(self, value: int) -> None:
        if not self._slider_scrubbing or self._slider_duration_ms <= 0:
            return
        seconds = value / 1000.0
        duration = self._slider_duration_seconds if self._slider_duration_ms > 0 else None
        self._set_status_label(self._last_known_frames, seconds, duration)

    def _handle_slider_released(self) -> None:
        if not self._slider_scrubbing:
            return
        self._slider_scrubbing = False
        self._apply_slider_seek(self._position_slider.value())

    def _apply_slider_seek(self, value: int) -> None:
        if self._slider_duration_ms <= 0:
            return
        ctx = self._ctx
        if ctx is None:
            return
        seconds = value / 1000.0
        if self._slider_duration_seconds > 0.0:
            seconds = max(0.0, min(self._slider_duration_seconds, seconds))
        try:
            ctx.playvid_seek(seconds)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Seek command failed")
            self._show_error("Seek error", str(exc))
            self._discard_context()
            return
        duration = self._slider_duration_seconds if self._slider_duration_ms > 0 else None
        self._last_known_position = seconds
        self._set_status_label(self._last_known_frames, seconds, duration)
        clamped_value = int(round(seconds * 1000.0))
        if self._position_slider.value() != clamped_value:
            self._position_slider.setValue(clamped_value)

    def _set_status_label(
        self,
        frames: int,
        position: Optional[float],
        duration: Optional[float],
    ) -> None:
        if position is None:
            self._frame_label.setText(f"Frame: {frames}")
            return
        safe_position = max(0.0, position)
        if duration is not None and duration > 0.0:
            safe_position = min(safe_position, duration)
            self._frame_label.setText(
                f"Frame: {frames} ({self._format_seconds(safe_position)} / {self._format_seconds(duration)})"
            )
        else:
            self._frame_label.setText(f"Frame: {frames} ({self._format_seconds(safe_position)})")

    @staticmethod
    def _format_seconds(value: float) -> str:
        total_ms = max(0, int(round(value * 1000.0)))
        seconds_total, milliseconds = divmod(total_ms, 1000)
        minutes_total, seconds = divmod(seconds_total, 60)
        hours, minutes = divmod(minutes_total, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    # ------------------------------------------------------------------
    # Preview handling
    # ------------------------------------------------------------------
    def _handle_preview_frame(self, frame) -> None:
        self._preview_dispatcher.frameReady.emit(frame)

    @QtCore.Slot(object)
    def _update_preview(self, frame) -> None:
        image = getattr(frame, "video_frame", None)
        if image is None:
            return
        if image.ndim != 3 or image.shape[2] not in (3, 4):
            LOGGER.debug("Skipping preview frame with unsupported shape: %s", image.shape)
            return
        if image.shape[2] == 4:
            rgb = image[:, :, :3][:, :, ::-1].copy()
        else:
            rgb = image[:, :, ::-1].copy()
        self._preview_image_cache = rgb
        height, width, _channels = rgb.shape
        bytes_per_line = rgb.strides[0]
        qimage = QtGui.QImage(rgb.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimage)
        target_size = self._preview_label.size()
        if target_size.width() > 0 and target_size.height() > 0:
            pixmap = pixmap.scaled(target_size, _KEEP_ASPECT, _SMOOTH_TRANSFORM)
        self._preview_label.setText("")
        self._preview_label.setPixmap(pixmap)


def parse_simple_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the simple PySide GUI for pyplayvid playback")
    parser.add_argument("source", help="Video file to play or camera index")
    parser.add_argument("--fps", type=float, default=None, help="Override detected FPS")
    parser.add_argument("--loop", action="store_true", help="Loop playback when the video ends")
    parser.add_argument(
        "--decoder",
        default="pyav",
        choices=["pyav", "ffmpeg", "auto"],
        help="Video decoder backend",
    )
    parser.add_argument(
        "--no-color",
        dest="color",
        action="store_false",
        help="Render output without sampling colours",
    )
    parser.set_defaults(color=True)
    parser.add_argument(
        "--stats-interval",
        type=int,
        default=0,
        help="Frames between stats callbacks (0 disables)",
    )
    parser.add_argument(
        "--benchmark-interval",
        type=float,
        default=1.0,
        help="Seconds between benchmark timing logs (0 disables reporting)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG2", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def _exec_qapplication(app: QtWidgets.QApplication) -> int:
    execute = getattr(app, "exec", None)
    if execute is None:
        execute = getattr(app, "exec_")
    return execute()


def run_simple_gui(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_simple_args(argv)
    level_name = args.log_level.upper()
    level = DEBUG2 if level_name == "DEBUG2" else getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level)
    app = QtWidgets.QApplication.instance()
    owns_app = False
    if app is None:
        app = QtWidgets.QApplication(["pyplayvid-simple"])
        owns_app = True
    window = SimplePlayerWindow(
        args.source,
        PlayerSettings(),
        loop=args.loop,
        fps_override=args.fps,
        use_color=args.color,
        stats_interval=args.stats_interval,
        benchmark_interval=args.benchmark_interval,
        decoder=args.decoder,
    )
    window.show()
    try:
        return _exec_qapplication(app)
    finally:
        if owns_app:
            app.quit()


if __name__ == "__main__":
    raise SystemExit(run_simple_gui())
