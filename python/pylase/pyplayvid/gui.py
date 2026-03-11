"""Feature-rich Qt GUI for :mod:`pylase.pyplayvid` playback."""

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

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from pylase.logging_utils import RelativeTimeFormatter

from .gui_types import PreviewFrame
from .player import DisplayMode, PlayerCtx
from .settings import PlayerEvent, PlayerSettings
from .utils import DEBUG2

try:  # pragma: no cover - Qt bindings depend on runtime environment
    from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
except ImportError:  # pragma: no cover - fallback to PySide6 when available
    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
    except ImportError as exc:  # pragma: no cover - PySide missing entirely
        raise ImportError("PySide2 or PySide6 is required for the pyplayvid GUI") from exc

__all__ = [
    "PlayerWindow",
    "PlayerController",
    "parse_args",
    "run_gui",
]

LOGGER = logging.getLogger("openlase.pyplayvid.gui")

if hasattr(QtCore.Qt, "AlignCenter"):
    _ALIGN_CENTER = QtCore.Qt.AlignCenter
    _ALIGN_LEFT = QtCore.Qt.AlignLeft
else:  # pragma: no cover - PySide6 enum namespace
    _ALIGN_CENTER = QtCore.Qt.AlignmentFlag.AlignCenter
    _ALIGN_LEFT = QtCore.Qt.AlignmentFlag.AlignLeft

if hasattr(QtGui.QImage, "Format_RGB888"):
    _QIMAGE_RGB888 = QtGui.QImage.Format_RGB888
else:  # pragma: no cover - PySide6 enum namespace
    _QIMAGE_RGB888 = QtGui.QImage.Format.Format_RGB888


# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------


class FlowLayout(QtWidgets.QLayout):
    """Lightweight flow layout adapted from :mod:`qplayvidex`."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        margin: int = 0,
        spacing: int = -1,
    ) -> None:
        super().__init__(parent)
        self._items: List[QtWidgets.QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing if spacing >= 0 else 6)

    def addItem(self, item: QtWidgets.QLayoutItem) -> None:  # pragma: no cover - Qt layout API
        self._items.append(item)

    def count(self) -> int:  # pragma: no cover - Qt layout API
        return len(self._items)

    def itemAt(self, index: int) -> Optional[QtWidgets.QLayoutItem]:  # pragma: no cover
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> Optional[QtWidgets.QLayoutItem]:  # pragma: no cover
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> QtCore.Qt.Orientations:  # pragma: no cover - trivial
        return QtCore.Qt.Orientations()

    def hasHeightForWidth(self) -> bool:  # pragma: no cover - trivial
        return True

    def heightForWidth(self, width: int) -> int:  # pragma: no cover - trivial
        return self._do_layout(QtCore.QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QtCore.QRect) -> None:  # pragma: no cover - trivial
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QtCore.QSize:  # pragma: no cover - trivial
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:  # pragma: no cover - trivial
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QtCore.QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QtCore.QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        for item in self._items:
            widget = item.widget()
            if widget is None or not widget.isVisible():
                continue
            next_x = x + item.sizeHint().width() + self.spacing()
            if next_x - self.spacing() > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + self.spacing()
                next_x = x + item.sizeHint().width() + self.spacing()
                line_height = 0
            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()


class VideoFrameWidget(QtWidgets.QFrame):
    """Widget displaying RGB video frames inside a bordered panel."""

    def __init__(self, title: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setMinimumSize(220, 180)
        self._original_pixmap = QtGui.QPixmap()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._title = QtWidgets.QLabel(title, self)
        font = self._title.font()
        font.setBold(True)
        self._title.setFont(font)
        self._title.setAlignment(_ALIGN_LEFT)
        layout.addWidget(self._title)

        self._image_label = QtWidgets.QLabel("No frame", self)
        self._image_label.setAlignment(_ALIGN_CENTER)
        self._image_label.setMinimumSize(200, 150)
        layout.addWidget(self._image_label, 1)

        self._info_label = QtWidgets.QLabel("", self)
        layout.addWidget(self._info_label)

    def clear(self) -> None:
        self._image_label.setText("No frame")
        self._image_label.setPixmap(QtGui.QPixmap())
        self._info_label.setText("")
        self._original_pixmap = QtGui.QPixmap()

    def set_frame(self, frame: np.ndarray, index: int, timestamp: float) -> None:
        if frame.ndim == 2:
            rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        bytes_per_line = channels * width
        image = QtGui.QImage(rgb.data, width, height, bytes_per_line, _QIMAGE_RGB888).copy()
        self._original_pixmap = QtGui.QPixmap.fromImage(image)
        self._update_scaled_pixmap()
        self._info_label.setText(f"Frame {index} @ {timestamp:.3f}s")

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # pragma: no cover - Qt callback
        self._update_scaled_pixmap()
        super().resizeEvent(event)

    def _update_scaled_pixmap(self) -> None:
        if self._original_pixmap.isNull():
            return
        scaled = self._original_pixmap.scaled(
            self._image_label.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)


class LaserPreviewWidget(QtWidgets.QFrame):
    """Widget rendering traced laser paths using :class:`QtGui.QPainter`."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setMinimumSize(220, 180)
        self._paths: List[np.ndarray] = []
        self._frame_size: Tuple[int, int] = (1, 1)
        self._info = QtWidgets.QLabel("No frame", self)
        self._info.setAlignment(_ALIGN_LEFT)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        title = QtWidgets.QLabel("Laser preview", self)
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(_ALIGN_LEFT)
        layout.addWidget(title)
        self._canvas = QtWidgets.QWidget(self)
        self._canvas.setMinimumSize(200, 150)
        self._canvas.installEventFilter(self)
        layout.addWidget(self._canvas, 1)
        layout.addWidget(self._info)

    def set_frame(self, frame: PreviewFrame) -> None:
        self._paths = [path.copy() for path in frame.laser_paths]
        self._frame_size = frame.frame_size
        self._info.setText(f"Frame {frame.index} @ {frame.timestamp:.3f}s")
        self._canvas.update()

    def clear(self) -> None:
        self._paths = []
        self._canvas.update()
        self._info.setText("No frame")

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:  # pragma: no cover - Qt callback
        if watched is self._canvas and event.type() == QtCore.QEvent.Type.Paint:
            self._paint_canvas()
            return True
        return super().eventFilter(watched, event)

    def _paint_canvas(self) -> None:
        painter = QtGui.QPainter(self._canvas)
        painter.fillRect(self._canvas.rect(), QtCore.Qt.GlobalColor.black)
        if not self._paths:
            painter.end()
            return
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        pen = QtGui.QPen(QtCore.Qt.GlobalColor.green)
        pen.setWidth(2)
        painter.setPen(pen)

        width = max(1, self._frame_size[0])
        height = max(1, self._frame_size[1])
        rect = self._canvas.rect().adjusted(8, 8, -8, -8)
        scale_x = rect.width() / float(width)
        scale_y = rect.height() / float(height)

        for path in self._paths:
            if path.shape[0] < 2:
                continue
            painter_path = QtGui.QPainterPath()
            first = path[0]
            painter_path.moveTo(
                rect.left() + float(first[0]) * scale_x,
                rect.top() + float(first[1]) * scale_y,
            )
            for point in path[1:]:
                painter_path.lineTo(
                    rect.left() + float(point[0]) * scale_x,
                    rect.top() + float(point[1]) * scale_y,
                )
            painter.drawPath(painter_path)
        painter.end()


class SliderSpinBox(QtWidgets.QWidget):
    """Combined slider/spin box control emitting integer value changes."""

    valueChanged = QtCore.Signal(int)

    def __init__(
        self,
        minimum: int,
        maximum: int,
        value: int,
        *,
        step: int = 1,
        parent: Optional[QtWidgets.QWidget] = None,
        object_name: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self._blocking = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._slider.setRange(minimum, maximum)
        self._slider.setSingleStep(step)
        span = max(1, maximum - minimum)
        self._slider.setPageStep(max(step, span // 10))
        self._slider.setTracking(True)
        if object_name:
            self._slider.setObjectName(f"{object_name}_slider")
        layout.addWidget(self._slider, 1)

        self._spin = QtWidgets.QSpinBox(self)
        self._spin.setRange(minimum, maximum)
        self._spin.setSingleStep(step)
        if object_name:
            self._spin.setObjectName(f"{object_name}_spin")
        layout.addWidget(self._spin)

        self._slider.valueChanged.connect(self._sync_from_slider)
        self._spin.valueChanged.connect(self._sync_from_spin)

        self.setValue(value)

    @property
    def slider(self) -> QtWidgets.QSlider:
        return self._slider

    @property
    def spinbox(self) -> QtWidgets.QSpinBox:
        return self._spin

    def value(self) -> int:
        return self._spin.value()

    def setValue(self, value: int) -> None:
        self._blocking = True
        try:
            self._slider.setValue(value)
            self._spin.setValue(value)
        finally:
            self._blocking = False

    def _sync_from_slider(self, value: int) -> None:
        if self._blocking:
            return
        self._blocking = True
        try:
            if self._spin.value() != value:
                self._spin.setValue(value)
        finally:
            self._blocking = False
        self.valueChanged.emit(value)

    def _sync_from_spin(self, value: int) -> None:
        if self._blocking:
            return
        self._blocking = True
        try:
            if self._slider.value() != value:
                self._slider.setValue(value)
        finally:
            self._blocking = False
        self.valueChanged.emit(value)


class SettingsPanel(QtWidgets.QGroupBox):
    """Panel exposing :class:`PlayerSettings` controls."""

    settings_changed = QtCore.Signal(object)

    def __init__(self, settings: PlayerSettings, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Tracing parameters", parent)
        self._updating = False
        self._current_settings = replace(settings)
        self._controls: Dict[str, QtWidgets.QWidget] = {}
        layout = QtWidgets.QFormLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        bool_fields = [
            ("canny", "Use Canny edge detection"),
            ("split_threshold", "Adaptive threshold"),
        ]
        for key, label in bool_fields:
            checkbox = QtWidgets.QCheckBox(label, self)
            checkbox.setChecked(getattr(settings, key))
            checkbox.toggled.connect(lambda _checked: self._emit_settings())
            layout.addRow(checkbox)
            self._controls[key] = checkbox

        spin_fields = [
            ("blur", "Blur (%)", 0, 1000),
            ("scale", "Scale (%)", 1, 400),
            ("threshold", "Threshold", 0, 255),
            ("threshold2", "Threshold 2", 0, 255),
            ("decimation", "Decimation", 1, 16),
            ("minsize", "Minimum segment", 0, 1000),
            ("dwell", "Corner dwell", 0, 50),
            ("offspeed", "Blanking speed", 0, 200),
            ("overscan", "Overscan (%)", 0, 200),
        ]

        for key, label, minimum, maximum in spin_fields:
            control = SliderSpinBox(
                minimum,
                maximum,
                getattr(settings, key),
                parent=self,
                object_name=key,
            )
            control.valueChanged.connect(self._emit_settings)
            layout.addRow(label, control)
            self._controls[key] = control

    def current_settings(self) -> PlayerSettings:
        settings = replace(self._current_settings)
        for key, widget in self._controls.items():
            if isinstance(widget, QtWidgets.QCheckBox):
                setattr(settings, key, widget.isChecked())
            elif isinstance(widget, SliderSpinBox):
                setattr(settings, key, widget.value())
        return settings

    def update_settings(self, settings: PlayerSettings) -> None:
        self._current_settings = replace(settings)
        self._updating = True
        try:
            for key, widget in self._controls.items():
                value = getattr(settings, key)
                if isinstance(widget, QtWidgets.QCheckBox):
                    widget.setChecked(bool(value))
                elif isinstance(widget, SliderSpinBox):
                    widget.setValue(int(value))
        finally:
            self._updating = False
        self._emit_settings()

    def _emit_settings(self) -> None:
        if self._updating:
            return
        new_settings = self.current_settings()
        self._current_settings = replace(new_settings)
        self.settings_changed.emit(new_settings)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


class PlayerWindow(QtWidgets.QMainWindow):
    """Comprehensive GUI mirroring the :mod:`qplayvidex` layout."""

    play_requested = QtCore.Signal()
    pause_requested = QtCore.Signal()
    stop_requested = QtCore.Signal()
    seek_requested = QtCore.Signal(float)
    settings_requested = QtCore.Signal(object)
    window_closed = QtCore.Signal()

    def __init__(
        self,
        source: str,
        settings: PlayerSettings,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"pyplayvid - {Path(source).name}")
        self.resize(1200, 760)

        self._duration = 0.0
        self._seeking = False
        self._seek_enabled = True
        self._last_mode = DisplayMode.STOP

        central = QtWidgets.QWidget(self)
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(10)

        self._timeline = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, central)
        self._timeline.setRange(0, 1000)
        self._timeline.sliderPressed.connect(self._on_slider_pressed)
        self._timeline.sliderReleased.connect(self._on_slider_released)
        self._timeline.sliderMoved.connect(self._on_slider_moved)
        root_layout.addWidget(self._timeline)

        controls_row = QtWidgets.QHBoxLayout()
        controls_row.setSpacing(8)
        root_layout.addLayout(controls_row)

        self._play_button = QtWidgets.QPushButton("Play", central)
        self._pause_button = QtWidgets.QPushButton("Pause", central)
        self._stop_button = QtWidgets.QPushButton("Stop", central)

        self._play_button.clicked.connect(self.play_requested)
        self._pause_button.clicked.connect(self.pause_requested)
        self._stop_button.clicked.connect(self.stop_requested)

        for widget in (self._play_button, self._pause_button, self._stop_button):
            controls_row.addWidget(widget)
        controls_row.addStretch(1)

        self._laser_toggle = QtWidgets.QCheckBox("Laser preview", central)
        self._laser_toggle.setChecked(True)
        self._video_toggle = QtWidgets.QCheckBox("Video preview", central)
        self._video_toggle.setChecked(True)
        self._debug_toggle = QtWidgets.QCheckBox("Debug preview", central)
        self._debug_toggle.setChecked(False)

        toggles = (self._laser_toggle, self._video_toggle, self._debug_toggle)
        for toggle in toggles:
            toggle.stateChanged.connect(self._refresh_preview_visibility)
            controls_row.addWidget(toggle)

        split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, central)
        root_layout.addWidget(split, 1)

        preview_container = QtWidgets.QWidget(split)
        preview_layout = QtWidgets.QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(6)

        self._preview_area = QtWidgets.QWidget(preview_container)
        self._preview_flow = FlowLayout(self._preview_area, spacing=8)
        self._preview_area.setLayout(self._preview_flow)
        preview_layout.addWidget(self._preview_area, 1)

        self._placeholder = QtWidgets.QLabel("Select at least one preview", preview_container)
        self._placeholder.setAlignment(_ALIGN_CENTER)
        self._placeholder.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        preview_layout.addWidget(self._placeholder, 1)

        split.addWidget(preview_container)

        self._laser_widget = LaserPreviewWidget()
        self._video_widget = VideoFrameWidget("Video preview")
        self._debug_widget = VideoFrameWidget("Debug preview")

        self._preview_flow.addWidget(self._laser_widget)
        self._preview_flow.addWidget(self._video_widget)
        self._preview_flow.addWidget(self._debug_widget)

        settings_panel = SettingsPanel(settings, split)
        settings_panel.settings_changed.connect(self.settings_requested.emit)
        split.addWidget(settings_panel)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)

        status = QtWidgets.QHBoxLayout()
        status.setSpacing(12)
        root_layout.addLayout(status)

        self._status_position = QtWidgets.QLabel("00:00.000", central)
        self._status_frame = QtWidgets.QLabel("Frame 0", central)
        self._status_meta = QtWidgets.QLabel("", central)
        for widget in (self._status_position, self._status_frame, self._status_meta):
            status.addWidget(widget)
        status.addStretch(1)

        self.setCentralWidget(central)
        self._refresh_preview_visibility()

    # ------------------------------------------------------------------
    # Qt events
    # ------------------------------------------------------------------

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # pragma: no cover - Qt callback
        self.window_closed.emit()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Preview management
    # ------------------------------------------------------------------

    def _refresh_preview_visibility(self) -> None:
        widgets = [
            (self._laser_widget, self._laser_toggle.isChecked()),
            (self._video_widget, self._video_toggle.isChecked()),
            (self._debug_widget, self._debug_toggle.isChecked()),
        ]
        any_visible = any(flag for _widget, flag in widgets)
        self._preview_area.setVisible(any_visible)
        self._placeholder.setVisible(not any_visible)
        for widget, visible in widgets:
            widget.setVisible(visible)

    def display_preview(self, frame: PreviewFrame) -> None:
        if self._laser_toggle.isChecked():
            self._laser_widget.set_frame(frame)
        else:
            self._laser_widget.clear()
        if self._video_toggle.isChecked():
            self._video_widget.set_frame(frame.video_frame, frame.index, frame.timestamp)
        else:
            self._video_widget.clear()
        if self._debug_toggle.isChecked():
            if frame.debug_frame is not None:
                self._debug_widget.set_frame(frame.debug_frame, frame.index, frame.timestamp)
            else:
                self._debug_widget.clear()
        else:
            self._debug_widget.clear()
        self._status_frame.setText(f"Frame {frame.index}")
        self._status_position.setText(self._format_time(frame.timestamp))
        if self._duration > 0 and not self._seeking:
            value = int((frame.timestamp / self._duration) * 1000.0)
            self._timeline.blockSignals(True)
            self._timeline.setValue(max(0, min(1000, value)))
            self._timeline.blockSignals(False)

    def set_metadata(
        self,
        fps: float,
        width: int,
        height: int,
        frames: int,
        duration: float,
    ) -> None:
        parts = [f"{width}x{height}"]
        if fps > 0:
            parts.append(f"{fps:.2f} fps")
        if frames > 0:
            parts.append(f"{frames} frames")
        self._status_meta.setText(" | ".join(parts))
        self.set_duration(duration)

    def set_duration(self, duration: float) -> None:
        self._duration = max(0.0, duration)
        self._timeline.setEnabled(self._duration > 0 and self._seek_enabled)

    def enable_seek(self, enabled: bool) -> None:
        self._seek_enabled = enabled
        self._timeline.setEnabled(enabled and self._duration > 0)

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def set_playback_mode(self, mode: DisplayMode) -> None:
        self._last_mode = mode
        playing = mode == DisplayMode.PLAY
        paused = mode == DisplayMode.PAUSE
        self._play_button.setEnabled(not playing)
        self._pause_button.setEnabled(playing)
        self._stop_button.setEnabled(True)
        if mode == DisplayMode.STOP:
            self._timeline.blockSignals(True)
            self._timeline.setValue(0)
            self._timeline.blockSignals(False)
            self._status_position.setText("00:00.000")
            self._status_frame.setText("Frame 0")

    def update_event(self, event: PlayerEvent) -> None:
        if event.pts >= 0:
            timestamp = event.pts
        else:
            timestamp = event.time
        self._status_position.setText(self._format_time(timestamp))
        self._status_frame.setText(f"Frame {event.frames}")
        if self._duration > 0 and not self._seeking:
            value = int((timestamp / self._duration) * 1000.0)
            self._timeline.blockSignals(True)
            self._timeline.setValue(max(0, min(1000, value)))
            self._timeline.blockSignals(False)
        if event.ended:
            self.set_playback_mode(DisplayMode.STOP)

    def show_error(self, title: str, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, title, message)

    # ------------------------------------------------------------------
    # Slider callbacks
    # ------------------------------------------------------------------

    def _on_slider_pressed(self) -> None:
        if not self._seek_enabled:
            return
        self._seeking = True

    def _on_slider_moved(self, value: int) -> None:
        if not self._seek_enabled or self._duration <= 0:
            return
        timestamp = (value / 1000.0) * self._duration
        self._status_position.setText(self._format_time(timestamp))
        if self._seeking:
            self.seek_requested.emit(timestamp)

    def _on_slider_released(self) -> None:
        if not self._seek_enabled or self._duration <= 0:
            self._seeking = False
            return
        value = self._timeline.value()
        timestamp = (value / 1000.0) * self._duration
        self._seeking = False
        self.seek_requested.emit(timestamp)

    @staticmethod
    def _format_time(seconds: float) -> str:
        millis = int(round(seconds * 1000.0))
        mins, millis = divmod(millis, 60000)
        secs, millis = divmod(millis, 1000)
        return f"{mins:02d}:{secs:02d}.{millis:03d}"


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class PlayerController(QtCore.QObject):
    """Bridge between the Qt GUI and :class:`PlayerCtx`."""

    metadata_ready = QtCore.Signal(float, int, int, int, float)
    event_ready = QtCore.Signal(object)
    preview_ready = QtCore.Signal(object)
    mode_changed = QtCore.Signal(object)
    error = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(
        self,
        source: str,
        settings: PlayerSettings,
        *,
        loop: bool,
        fps_override: Optional[float],
        use_color: bool,
        decoder: str,
        stats_interval: int,
        benchmark_interval: float,
    ) -> None:
        super().__init__()
        self._source = source
        self._settings = settings
        self._loop = loop
        self._fps_override = fps_override
        self._use_color = use_color
        self._decoder = decoder
        self._stats_interval = max(1, stats_interval)
        self._benchmark_interval = max(0.0, float(benchmark_interval))
        self._ctx: Optional[PlayerCtx] = None
        self._mode = DisplayMode.STOP

    # Qt slots ---------------------------------------------------------

    @QtCore.Slot()
    def initialise(self) -> None:
        LOGGER.debug("Initialising PlayerCtx for %s", self._source)
        try:
            self._ctx = PlayerCtx(
                self._source,
                self._settings,
                loop=self._loop,
                fps_override=self._fps_override,
                use_color=self._use_color,
                stats_interval=self._stats_interval,
                benchmark_interval=self._benchmark_interval,
                decoder=self._decoder,
                event_callback=self._handle_event,
                frame_callback=self._handle_preview,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to initialise PlayerCtx")
            self.error.emit(str(exc))
            self.finished.emit()
            return

        duration = self._ctx.playvid_get_duration()
        frames = getattr(self._ctx.video_source, "frame_count", 0)
        self.metadata_ready.emit(self._ctx.fps, self._ctx.width, self._ctx.height, frames, duration)
        self.mode_changed.emit(self._mode)
        LOGGER.debug("PlayerCtx ready: %sx%s @ %.3f FPS", self._ctx.width, self._ctx.height, self._ctx.fps)

    @QtCore.Slot()
    def play(self) -> None:
        if not self._ctx:
            return
        self._ctx.playvid_play()
        self._mode = DisplayMode.PLAY
        self.mode_changed.emit(self._mode)

    @QtCore.Slot()
    def pause(self) -> None:
        if not self._ctx:
            return
        self._ctx.playvid_pause()
        self._mode = DisplayMode.PAUSE
        self.mode_changed.emit(self._mode)

    @QtCore.Slot()
    def stop(self) -> None:
        if not self._ctx:
            return
        self._ctx.playvid_stop()
        self._mode = DisplayMode.STOP
        self.mode_changed.emit(self._mode)

    @QtCore.Slot(float)
    def seek(self, position: float) -> None:
        if not self._ctx:
            return
        try:
            self._ctx.playvid_seek(position)
        except RuntimeError as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Seek failed")
            self.error.emit(str(exc))

    @QtCore.Slot(object)
    def update_settings(self, settings: PlayerSettings) -> None:
        if not self._ctx:
            self._settings = settings
            return
        LOGGER.debug("Updating player settings from GUI")
        self._settings = settings
        self._ctx.playvid_update_settings(settings)

    @QtCore.Slot()
    def shutdown(self) -> None:
        if not self._ctx:
            self.finished.emit()
            return
        try:
            self._ctx.playvid_stop()
        finally:
            self._ctx = None
            self._mode = DisplayMode.STOP
            self.mode_changed.emit(self._mode)
            self.finished.emit()

    # Internal callbacks ----------------------------------------------

    def _handle_event(self, event: PlayerEvent) -> None:
        self.event_ready.emit(event)
        if event.ended:
            self._mode = DisplayMode.STOP
            self.mode_changed.emit(self._mode)

    def _handle_preview(self, frame: PreviewFrame) -> None:
        self.preview_ready.emit(frame)


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Qt GUI frontend for pylase.pyplayvid")
    parser.add_argument("source", help="Video file or capture index")
    parser.add_argument("--fps", type=float, default=None, help="Override detected FPS")
    parser.add_argument("--decoder", default="pyav", choices=["pyav", "ffmpeg", "auto"], help="Video decoder backend")
    parser.add_argument("--loop", action="store_true", help="Loop playback")
    parser.add_argument("--no-color", dest="color", action="store_false", help="Disable colour sampling")
    parser.set_defaults(color=True)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG2", "DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    parser.add_argument("--stats-interval", type=int, default=1, help="Frames between event updates (1 recommended for GUI)")
    parser.add_argument(
        "--benchmark-interval",
        type=float,
        default=1.0,
        help="Seconds between decoder/render benchmark logs (0 disables reporting)",
    )
    return parser.parse_args(argv)


def run_gui(argv: Sequence[str]) -> int:
    args = parse_args(argv)

    level = DEBUG2 if args.log_level == "DEBUG2" else getattr(logging, args.log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(RelativeTimeFormatter("%(relative_time)s %(levelname)s %(message)s"))
    logging.basicConfig(level=level, handlers=[handler])

    settings = PlayerSettings.from_namespace(args)

    app = QtWidgets.QApplication(sys.argv)
    window = PlayerWindow(args.source, settings)
    window.show()

    controller = PlayerController(
        args.source,
        settings,
        loop=args.loop,
        fps_override=args.fps,
        use_color=args.color,
        decoder=args.decoder,
        stats_interval=args.stats_interval,
        benchmark_interval=args.benchmark_interval,
    )
    thread = QtCore.QThread()
    controller.moveToThread(thread)

    thread.started.connect(controller.initialise)
    controller.finished.connect(thread.quit)
    controller.finished.connect(controller.deleteLater)
    thread.finished.connect(thread.deleteLater)

    window.play_requested.connect(controller.play)
    window.pause_requested.connect(controller.pause)
    window.stop_requested.connect(controller.stop)
    window.seek_requested.connect(controller.seek)
    window.settings_requested.connect(controller.update_settings)
    window.window_closed.connect(controller.shutdown)
    app.aboutToQuit.connect(controller.shutdown)

    controller.metadata_ready.connect(window.set_metadata)
    controller.event_ready.connect(window.update_event)
    controller.preview_ready.connect(window.display_preview)
    controller.mode_changed.connect(window.set_playback_mode)
    controller.error.connect(lambda msg: window.show_error("Playback error", msg))

    thread.start()
    exit_code = app.exec()
    if thread.isRunning():
        thread.quit()
        thread.wait()
    return exit_code


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(run_gui(sys.argv[1:]))
