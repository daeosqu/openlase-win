#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
        OpenLase - a realtime laser graphics toolkit

Simplified laser UI:
- 左クリック: 中央にクロスヘア (BASEモード)
- 左クリック + 右クリック: マウス位置を高出力点で照射 (BURNモード)
- それ以外: 黒パス (IDLE)

この版は JackLaserClient(update_path) ベースのみを使用。
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import math
from dataclasses import dataclass
from typing import Callable, List, Optional

from qtpy import QtCore, QtGui, QtWidgets

from .jack_laser_client import JackLaserClient, OLPoint, OLColor
from .path_builder import PathBuilder

LOGGER = logging.getLogger("openlase.burn_mouse2")

# ===== runtime parameters =====
BASE_LEVEL = 0.5              # 左だけ押した時の「安全(?)」レベル
BURN_LEVEL = 1.00            # 左+右でのブースト点光
CROSS_HALF_EXTENT = 0.1       # crosshair size in scanner space (-1..1)
POINT_DWELL = 200             # BURNモード用: 点で止まるサンプル数
IDLE_DWELL = 200              # IDLEモード用: 黒点のサンプル数
DRAW_LEVEL = BASE_LEVEL       # クロスヘアの線の明るさ(ベース時)


# ---------------------------------------------------------------------------
# HUD info for status panel
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PointerHUDInfo:
    """Info for on-screen status/debug panel. Hardware側は参照しない。"""
    global_pos: QtCore.QPoint   # desktop pixel coordinates
    inside: bool                # cursor currently inside the pad
    emitting: bool              # "should be emitting light now"
    burned: bool                # BURN mode active?
    brightness_pct: int         # 0..100 for human eyes
    mode_label: str             # "BASE (crosshair)" / "BURN (point)" / "idle"


# ---------------------------------------------------------------------------
# Crosshair / point / dark path builders
# ---------------------------------------------------------------------------


def add_line_segment(
        pts: List[OLPoint],
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: OLColor,
        steps: int,
) -> None:
    """Append a linear interpolation from (x1,y1) to (x2,y2).
    Generates exactly `steps` samples, inclusive of both ends.

    NOTE:
    - If steps == 1, you just get the start point.
    - Otherwise, i runs [0 .. steps-1] and t goes [0.0 .. 1.0].
    """

    if steps <= 0:
        return  # nothing to do, silently ignore

    if steps == 1:
        pts.append(OLPoint(x1, y1, color))
        return

    for i in range(steps):
        t = i / (steps - 1)
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        pts.append(OLPoint(x, y, color))


def add_circle_segment(
        pts: List[OLPoint],
        cx: float,
        cy: float,
        radius: float,
        steps: int,
        color: OLColor,
        start_phase: float = 0.0,
        sweep: float = 1.0,
) -> None:
    """Append a circular path to pts.

    Args:
        pts: output list to append OLPoint to.
        cx, cy: circle center.
        radius: circle radius.
        steps: number of samples to generate (>=2 recommended).
        color: color for all samples.
        start_phase: normalized starting position on the circle.
            0.0 -> angle = 0 rad (point = (cx+radius, cy+0))
            0.25 -> angle = pi/2
            0.5 -> angle = pi
            0.75 -> angle = 3pi/2
            1.0 is same as 0.0
        sweep: how much of the circle to draw, in turns.
            1.0 -> full 360 deg
            0.5 -> 180 deg
            can be negative for clockwise.
    """

    import math

    if steps < 2:
        return

    base_angle = 2.0 * math.pi * start_phase
    total_angle = 2.0 * math.pi * sweep

    for i in range(steps):
        # t goes 0..1 across the requested sweep
        t = i / (steps - 1)
        ang = base_angle + total_angle * t
        x = cx + radius * math.cos(ang)
        y = cy + radius * math.sin(ang)
        pts.append(OLPoint(x, y, color))


def build_cross_path() -> List[OLPoint]:
    """中心(0,0)にクロスヘアを描くスキャンパターン."""
    pts: List[OLPoint] = []

    steps = 100        # interpolation steps per line (odd preferred)
    outer_circle_steps = 80
    inner_circle_steps = 16
    dot_circle_steps = 8

    outer_circle_radius = CROSS_HALF_EXTENT * 0.7
    inner_circle_radius = CROSS_HALF_EXTENT * 0.2
    dot_circle_radius = CROSS_HALF_EXTENT * 0.01

    end_wait = 10      # linger at line end
    #center_delta = (1.0 / steps) * 2
    center_delta = (1.0 / steps)
    center_dwell = 5
    center_power = min(1.0, DRAW_LEVEL * 2.0)

    # 線は緑、中心は赤を少し強め
    on = OLColor(0.0, DRAW_LEVEL, 0.0)
    off = OLColor(0.0, 0.0, 0.0)
    center_color = OLColor(center_power, 0.0, 0.0)
    dot_color = OLColor(1.0, 1.0, 1.0)

    # -------------------------------------------------
    # 1. outer circle
    #    We'll do a full 360 deg CCW from angle 0 -> 2pi.
    #    Start angle 0 means (outer_circle_radius, 0).
    # -------------------------------------------------

    add_line_segment(pts, 0, 0, outer_circle_radius, 0, off, 20)

    # # circle (0.7, 0) - (0.7, 0)
    # for i in range(outer_circle_steps):
    #     t = i / (outer_circle_steps - 1)
    #     ang = 2.0 * math.pi * t
    #     x = outer_circle_radius * math.cos(ang)
    #     y = outer_circle_radius * math.sin(ang)
    #     pts.append(OLPoint(x, y, on))

    add_circle_segment(pts, 0, 0, outer_circle_radius, outer_circle_steps, on)
    add_line_segment(pts, pts[-1].x, pts[-1].y, CROSS_HALF_EXTENT, 0, off, end_wait)
    add_line_segment(pts, pts[-1].x, pts[-1].y, 0, 0, off, 10)

    # horizontal: (+A, 0) -> (-A, 0)
    for i in range(steps):
        t = i / (steps - 1)
        x = CROSS_HALF_EXTENT + t * (-CROSS_HALF_EXTENT - CROSS_HALF_EXTENT)
        y = 0.0
        if abs(x) < center_delta and abs(y) < center_delta:
            for _j in range(center_dwell):
                pts.append(OLPoint(x, y, off))
        else:
            pts.append(OLPoint(x, y, on))

    # # linger at +A
    # last_x = x
    # last_y = y
    # for _i in range(end_wait):
    #     pts.append(OLPoint(last_x, last_y, on))
    add_line_segment(pts, x, y, CROSS_HALF_EXTENT, 0, off, end_wait)

    # blanking and move: (+A, 0) -> (0, -A)
    for i in range(steps):
        t = i / (steps - 1)
        x = CROSS_HALF_EXTENT + t * (0.0 - CROSS_HALF_EXTENT)
        y = 0.0 + t * (-CROSS_HALF_EXTENT - 0.0)
        pts.append(OLPoint(x, y, off))

    # vertical: (0, -A) -> (0, +A)
    for i in range(steps):
        t = i / (steps - 1)
        x = 0
        y = -CROSS_HALF_EXTENT + t * (2 * CROSS_HALF_EXTENT)
        if abs(x) < center_delta and abs(y) < center_delta:
            for _j in range(center_dwell):
                pts.append(OLPoint(x, y, off))
        else:
            pts.append(OLPoint(x, y, on))

    add_line_segment(pts, 0, 0, inner_circle_radius, 0, off, 20)

    # circle (0.7, 0) - (0.7, 0)
    for i in range(inner_circle_steps):
        t = i / (inner_circle_steps - 1)
        ang = 2.0 * math.pi * t
        x = inner_circle_radius * math.cos(ang)
        y = inner_circle_radius * math.sin(ang)
        pts.append(OLPoint(x, y, center_color))

    add_line_segment(pts, x, y, dot_circle_radius, 0, off, 10)

    # circle (0.7, 0) - (0.7, 0)
    for i in range(dot_circle_steps):
        t = i / (dot_circle_steps - 1)
        ang = 2.0 * math.pi * t
        x = dot_circle_radius * math.cos(ang)
        y = dot_circle_radius * math.sin(ang)
        pts.append(OLPoint(x, y, dot_color))

    add_line_segment(pts, x, y, 0, 0, off, 2)

    return pts



def build_cross_path() -> List[OLPoint]:
    on = OLColor(0.0, 0.0, 1.0)             # normal green line
    off = OLColor(0.0, 0.0, 0.0)                   # laser off / blanking
    center_burn = min(1.0, DRAW_LEVEL * 2.0)
    center_col = OLColor(center_burn, 0.0, 0.0)   # bright red-ish for center dwell
    print("Building crosshair path...")
    planner = PathBuilder(
        max_vel=0.002,
        max_accel_deg=18.0,
        corner_dwell_samples=10,
        corner_dwell_dim=0.5,
        settle_samples=350,
        start_wait=0,
        end_wait=15,
        off_color=off,
    )

    # 1. 想定する初期状態
    approx_start_x = 0
    approx_start_y = 0
    planner.move_to(approx_start_x, approx_start_y)

    # 基準位置に誘導して静止（安定化）
    planner.arm(safe_x=0.0, safe_y=0.0)

    # 2. 照準の外円
    # start_phase=0.0 なら (radius,0) からCCWで描き始める。
    outer_radius = CROSS_HALF_EXTENT * 0.9
    planner.circle(
        cx=0.0,
        cy=0.0,
        radius=outer_radius,
        color=on,
        start_phase=0.0,
        sweep=1.0,          # 360deg CCW
    )

    # 左端へ移動
    planner.jump_to(-CROSS_HALF_EXTENT, 0.0)

    # 3.1. 水平ライン（左）
    planner.line_to(0.0, 0.0, on)

    # 3.2. センター
    center_dwell_samples = 5  # あまり明るすぎると威力が強すぎるので注意
    cx = planner._x
    cy = planner._y
    for _ in range(center_dwell_samples):
        planner._emit(cx, cy, center_col)

    # 3.3. 水平ライン（左）
    planner.line_to(CROSS_HALF_EXTENT, 0.0, on)

    # 4. 垂直ライン ===
    planner.jump_to(0.0, -CROSS_HALF_EXTENT)

    # 4.1. 下から中央(0,0)
    planner.line_to(0.0, 0.0, on)

    # 4.2. センター
    cx = planner._x
    cy = planner._y
    for _ in range(center_dwell_samples):
        planner._emit(cx, cy, center_col)

    # 4.3. 中央から上端
    planner.line_to(0.0, CROSS_HALF_EXTENT, on)

    # 中央に戻す（arm() で挙動が安定しやすい）
    #planner.jump_to(0, 0)

    # できあがったパスを返す
    pts = planner.build()
    return pts





def build_point_path(x: float, y: float, level: float) -> List[OLPoint]:
    """BURNモード用: 指定座標(x,y)で止まり照射し続ける短いループ."""
    pts: List[OLPoint] = []

    color_on = OLColor(level, level, level)
    color_off = OLColor(0.0, 0.0, 0.0)

    # dwell bright at (x,y)
    for _i in range(POINT_DWELL):
        pts.append(OLPoint(x, y, color_on))

    # tiny blank dwell at same spot to cool / retrace a bit
    off_span = max(5, POINT_DWELL // 20)
    for _i in range(off_span):
        pts.append(OLPoint(x, y, color_off))

    return pts


def build_dark_path() -> List[OLPoint]:
    """IDLEパス。出力を真っ黒で維持してレーザー消したっぽく見せる."""
    pts: List[OLPoint] = []
    off = OLColor(0.0, 0.0, 0.0)
    for _i in range(IDLE_DWELL):
        pts.append(OLPoint(0.0, 0.0, off))
    return pts


# ---------------------------------------------------------------------------
# Helper: Qt5/Qt6 compatible globalPos
# ---------------------------------------------------------------------------

def _get_global_pos_qpoint(event: QtGui.QMouseEvent) -> QtCore.QPoint:
    """
    Qt6: event.globalPosition() -> QPointF
    Qt5: event.globalPos()      -> QPoint
    どっちでも QPoint を返すようにする。
    """
    if hasattr(event, "globalPosition"):
        # Qt6 path
        gp = event.globalPosition()
        return QtCore.QPoint(int(gp.x()), int(gp.y()))
    else:
        # Qt5 path
        return event.globalPos()


# ---------------------------------------------------------------------------
# UI panel widget
# ---------------------------------------------------------------------------

class StatusPanel(QtWidgets.QWidget):
    """Tiny always-on-top panel that mirrors the current pointer position."""

    __arp_persist__ = True

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowTitle("Laser Panel")
        self.setWindowFlag(QtCore.Qt.Tool, True)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._position_label = QtWidgets.QLabel("X: 0  Y: 0")
        self._inside_label = QtWidgets.QLabel("Pad: outside")
        self._level_label = QtWidgets.QLabel("Output: 0")
        self._mode_label = QtWidgets.QLabel("Mode: idle")

        for label in (
            self._position_label,
            self._inside_label,
            self._level_label,
            self._mode_label,
        ):
            label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            layout.addWidget(label)

    def update_hud(self, hud: PointerHUDInfo) -> None:
        """Update UI labels based on the reported HUD info."""
        self._position_label.setText(
            f"X: {hud.global_pos.x():4d}  Y: {hud.global_pos.y():4d}"
        )
        self._inside_label.setText("Pad: inside" if hud.inside else "Pad: outside")

        if hud.emitting:
            self._level_label.setText(f"Output: {hud.brightness_pct}")
        else:
            self._level_label.setText("Output: 0")

        self._mode_label.setText(f"Mode: {hud.mode_label}")


# ---------------------------------------------------------------------------
# Controller / event bridge
# ---------------------------------------------------------------------------

class LaserController(QtCore.QObject):
    """
    Tracks pointer/buttons, decides mode, and pushes a scan path
    to JackLaserClient via update_path(path).

    Modes:
      - BASE (left only): crosshair at (0,0)
      - BURN (left+right): single bright point at cursor
      - idle (else): black parked point
    """

    hudChanged = QtCore.Signal(PointerHUDInfo)

    def __init__(self, jack: JackLaserClient) -> None:
        super().__init__()
        self._jack = jack
        self._pad: Optional[QtWidgets.QWidget] = None

        # pointer state
        self._left_pressed = False
        self._right_pressed = False
        self._inside = False
        self._x = 0.0         # normalized scanner X (-1..1)
        self._y = 0.0         # normalized scanner Y (-1..1)
        self._global_pos = QtCore.QPoint(0, 0)
        self._last_mode = "idle"

        # cache things that don't change every frame
        self._cross_path_cache: List[OLPoint] = build_cross_path()
        self._dark_path_cache: List[OLPoint] = build_dark_path()
        self._point_path_cache = build_point_path(0, 0, 255)

        # initialization flag
        self._jack_initialized = False

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # pragma: no cover - GUI lifecycle
        """Schedule one-shot post-show work after we're actually visible."""
        super().showEvent(event)

        # if not self._jack_initialized:
        #     self._jack_initialized = True
        #     QtCore.QTimer.singleShot(0, self._publish)

    def attach_pad(self, pad_widget: QtWidgets.QWidget) -> None:
        """Register the pad widget used to normalise pointer coordinates."""
        self._pad = pad_widget

    # Event bridge -----------------------------------------------------

    def handle_pointer(
        self,
        local_pos: QtCore.QPointF,
        global_pos: QtCore.QPointF,
    ) -> None:
        """Mouse moved (or synthetic move to center on startup)."""
        self._global_pos = QtCore.QPoint(int(global_pos.x()), int(global_pos.y()))

        pad = self._pad
        width = max(1, pad.width()) if pad is not None else 1
        height = max(1, pad.height()) if pad is not None else 1

        # clamp local pointer to pad rect
        x_px = max(0.0, min(float(local_pos.x()), float(width)))
        y_px = max(0.0, min(float(local_pos.y()), float(height)))

        # are we logically inside active pad?
        self._inside = (
            0.0 <= local_pos.x() <= width and
            0.0 <= local_pos.y() <= height
        )

        # convert to scanner coords (-1..1) with +y up
        self._x = (x_px / float(width)) * 2.0 - 1.0
        self._y = 1.0 - (y_px / float(height)) * 2.0

        self._publish()

    def handle_left(self, pressed: bool) -> None:
        """Left button = arm/disarm."""
        self._left_pressed = pressed
        # if not pressed:
        #     # drop burn if main trigger released
        #     self._right_pressed = False
        self._publish()

    def handle_right(self, pressed: bool) -> None:
        """Right button = BURN (only valid if left is already down)."""
        # if not self._left_pressed:
        #     return
        self._right_pressed = pressed
        self._publish()

    def handle_leave(self) -> None:
        """Pointer left pad widget."""
        self._inside = False
        self._publish()

    # Internals -------------------------------------------------------

    def _current_level(self) -> float:
        """Brightness scalar 0..1 based on buttons."""
        if self._right_pressed:
            return BURN_LEVEL
        if not self._left_pressed:
            return 0.0
        return BASE_LEVEL

    def _decide_mode(self, level: float) -> str:
        """Return one of: 'idle', 'base', 'burn'."""
        if self._right_pressed:
            return "burn"
        emitting = (self._left_pressed and level > 0.0 and self._inside)
        if not emitting:
            return "idle"
        return "base"

    def _update_jack_path(self, mode: str, level: float) -> None:
        """Push appropriate OLPoint list to the JackLaserClient."""

        path = None

        if mode == "base":
            # BASE: crosshair at center
            path = self._cross_path_cache
            self._jack.update_position(self._x, self._y)
            self._jack.update_blanking(False)
        elif mode == "burn":
            # BURN: bright single point at cursor
            path = self._point_path_cache
            self._jack.update_position(self._x, self._y)
            self._jack.update_blanking(False)
        else:
            path = self._dark_path_cache
            # idle: dark parked point
            self._jack.update_blanking(True)

        if self._last_mode != mode:
            LOGGER.debug(f"Laser mode change: {self._last_mode} -> {mode}")
            self._jack.update_settle(True)
            if path is not None:
                self._jack.update_path(path)

        self._last_mode = mode

    def _emit_hud(self, mode: str, level: float) -> None:
        """Emit PointerHUDInfo for status panel."""
        emitting = (mode != "idle")
        burned = (mode == "burn")
        brightness_pct = int(round(level * 100)) if emitting else 0

        if mode == "idle":
            mode_label = "idle"
        elif mode == "burn":
            mode_label = "BURN (point)"
        else:
            mode_label = "BASE (crosshair)"

        hud = PointerHUDInfo(
            global_pos=self._global_pos,
            inside=self._inside,
            emitting=emitting,
            burned=burned,
            brightness_pct=brightness_pct,
            mode_label=mode_label,
        )
        self.hudChanged.emit(hud)

    def _publish(self) -> None:
        """Compute level, pick mode, update JACK, update HUD."""
        if not self._jack_initialized:
            self._jack_initialized = True
            try:
                self._jack.open()
            except Exception as exc:
                LOGGER.exception("Initial JACK publish failed")
                raise

        level = self._current_level()
        mode = self._decide_mode(level)

        # talk to JACK
        self._update_jack_path(mode, level)

        # talk to human
        self._emit_hud(mode, level)


# ---------------------------------------------------------------------------
# LaserPad widget
# ---------------------------------------------------------------------------

class LaserPad(QtWidgets.QWidget):
    """Square pad to aim/trigger laser output."""

    __arp_persist__ = True

    def __init__(self, controller: LaserController) -> None:
        super().__init__(None)
        self.setWindowTitle("Laser Pad")
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CrossCursor)
        self._controller = controller

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # pragma: no cover - GUI
        global_pos = _get_global_pos_qpoint(event)
        self._controller.handle_pointer(event.position(), QtCore.QPointF(global_pos))
        event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # pragma: no cover - GUI
        global_pos = _get_global_pos_qpoint(event)
        if event.button() == QtCore.Qt.LeftButton:
            self._controller.handle_left(True)
            self._controller.handle_pointer(event.position(), QtCore.QPointF(global_pos))
        elif event.button() == QtCore.Qt.RightButton:
            self._controller.handle_right(True)
        event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # pragma: no cover - GUI
        global_pos = _get_global_pos_qpoint(event)
        if event.button() == QtCore.Qt.LeftButton:
            self._controller.handle_left(False)
        elif event.button() == QtCore.Qt.RightButton:
            self._controller.handle_right(False)
        # still update pointer/hud position on release
        self._controller.handle_pointer(event.position(), QtCore.QPointF(global_pos))
        event.accept()

    def leaveEvent(self, event: QtCore.QEvent) -> None:  # pragma: no cover - GUI
        self._controller.handle_leave()
        super().leaveEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # pragma: no cover - GUI
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#202124"))
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # Outer border
        border_pen = QtGui.QPen(QtGui.QColor("#8ab4f8"))
        border_pen.setWidth(4)
        painter.setPen(border_pen)
        painter.drawRect(self.rect().adjusted(2, 2, -2, -2))

        # Center crosshair (visual aid only)
        center_pen = QtGui.QPen(QtGui.QColor("#ffffff"))
        center_pen.setWidth(1)
        painter.setPen(center_pen)
        cx = self.width() / 2
        cy = self.height() / 2
        painter.drawLine(int(cx), 0, int(cx), self.height())
        painter.drawLine(0, int(cy), self.width(), int(cy))
        painter.end()



class LaserPad(QtWidgets.QWidget):
    """Square pad to aim/trigger laser output."""

    __arp_persist__ = True

    def __init__(self, controller: LaserController) -> None:
        super().__init__(None)
        self.setWindowTitle("Laser Pad")
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CrossCursor)
        self._controller = controller
        self._margin_frac = 0.05  # 5%

    def _clamp_into_inner_box(self, p: QtCore.QPointF) -> QtCore.QPointF:
        """
        Map widget-local point p to the allowed inner box.

        Example with width=height=100 and margin_frac=0.10:
        - Raw (0,0)      -> (10,10)
        - Raw (5,50)     -> (10,50)
        - Raw (50,50)    -> (50,50)
        - Raw (100,100)  -> (90,90)
        """
        w = self.width()
        h = self.height()

        if w <= 0 or h <= 0:
            return p  # degenerate, avoid div0

        # convert to 0..1
        fx = p.x() / w
        fy = p.y() / h

        inner_min = self._margin_frac              # e.g. 0.10
        inner_max = 1.0 - self._margin_frac        # e.g. 0.90

        # clamp to [inner_min, inner_max]
        if fx < inner_min:
            fx = inner_min
        elif fx > inner_max:
            fx = inner_max

        if fy < inner_min:
            fy = inner_min
        elif fy > inner_max:
            fy = inner_max

        # back to pixels
        out_x = fx * w
        out_y = fy * h
        return QtCore.QPointF(out_x, out_y)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # pragma: no cover - GUI
        global_pos = _get_global_pos_qpoint(event)

        clamped_local = self._clamp_into_inner_box(event.position())

        self._controller.handle_pointer(clamped_local, QtCore.QPointF(global_pos))
        event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # pragma: no cover - GUI
        global_pos = _get_global_pos_qpoint(event)

        if event.button() == QtCore.Qt.LeftButton:
            self._controller.handle_left(True)

            clamped_local = self._clamp_into_inner_box(event.position())
            self._controller.handle_pointer(clamped_local, QtCore.QPointF(global_pos))

        elif event.button() == QtCore.Qt.RightButton:
            self._controller.handle_right(True)

        event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # pragma: no cover - GUI
        global_pos = _get_global_pos_qpoint(event)

        if event.button() == QtCore.Qt.LeftButton:
            self._controller.handle_left(False)
        elif event.button() == QtCore.Qt.RightButton:
            self._controller.handle_right(False)

        clamped_local = self._clamp_into_inner_box(event.position())
        self._controller.handle_pointer(clamped_local, QtCore.QPointF(global_pos))

        event.accept()

    def leaveEvent(self, event: QtCore.QEvent) -> None:  # pragma: no cover - GUI
        self._controller.handle_leave()
        super().leaveEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # pragma: no cover - GUI
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#202124"))
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # Outer border for the whole widget (visual)
        border_pen = QtGui.QPen(QtGui.QColor("#8ab4f8"))
        border_pen.setWidth(4)
        painter.setPen(border_pen)
        painter.drawRect(self.rect().adjusted(2, 2, -2, -2))

        # Draw the "full output range" box (10%..90%)
        w = self.width()
        h = self.height()
        m = self._margin_frac
        left   = m * w
        top    = m * h
        right  = (1.0 - m) * w
        bottom = (1.0 - m) * h

        safe_pen = QtGui.QPen(QtGui.QColor("#4caf50"))
        safe_pen.setStyle(QtCore.Qt.DashLine)
        safe_pen.setWidth(2)
        painter.setPen(safe_pen)
        painter.drawRect(QtCore.QRectF(left, top, right - left, bottom - top))

        # Center crosshair (just UI aid)
        center_pen = QtGui.QPen(QtGui.QColor("#ffffff"))
        center_pen.setWidth(1)
        painter.setPen(center_pen)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        painter.drawLine(int(cx), 0, int(cx), self.height())
        painter.drawLine(0, int(cy), self.width(), int(cy))

        painter.end()


# ---------------------------------------------------------------------------
# Window placement / shortcuts / arg parsing / main
# ---------------------------------------------------------------------------

def _place_windows(panel: StatusPanel, pad: QtWidgets.QWidget) -> None:
    """Place status panel and pad window sensibly."""
    screen = QtWidgets.QApplication.primaryScreen()
    geometry = screen.availableGeometry() if screen else QtCore.QRect(0, 0, 800, 600)

    # panel near top-left
    panel.move(geometry.x(), geometry.y())

    # pad centered as large square
    side = int(min(geometry.width(), geometry.height()) * 0.6)
    side = max(200, side)
    pad.resize(side, side)
    pad_x = geometry.x() + (geometry.width() - side) // 2
    pad_y = geometry.y() + (geometry.height() - side) // 2
    pad.move(pad_x, pad_y)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simplified burn mouse UI")
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level (default: INFO)",
    )
    return parser.parse_args(argv)


def _install_escape_shortcuts(
    panel: QtWidgets.QWidget,
    pad: QtWidgets.QWidget,
    quit_callback: Callable[[], None],
) -> None:
    """Allow closing the application via the Escape key."""
    for widget in (panel, pad):
        shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Escape), widget)
        shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        shortcut.activated.connect(quit_callback)
        # keep a reference so GC doesn't reap it
        widget._esc_shortcut = shortcut  # type: ignore[attr-defined]


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    qt_app = QtWidgets.QApplication(sys.argv if argv is None else ["burn-mouse"])

    # SIGINT -> quit Qt event loop
    def _handle_sigint(signum: int, frame: Optional[object]) -> None:
        del signum, frame
        QtCore.QTimer.singleShot(0, qt_app.quit)

    signal.signal(signal.SIGINT, _handle_sigint)

    # Connect JACK
    try:
        jack = JackLaserClient("burn-mouse")
    except Exception as exc:
        LOGGER.exception("Failed to initialise JACK client: %s", exc)
        return 1

    # Build UI+controller
    panel = StatusPanel()
    controller = LaserController(jack)
    pad = LaserPad(controller)

    # tie Qt lifetime
    controller.setParent(pad)
    controller.attach_pad(pad)

    # HUD updates
    controller.hudChanged.connect(panel.update_hud)

    # ESC to quit
    _install_escape_shortcuts(panel, pad, qt_app.quit)

    # layout windows
    _place_windows(panel, pad)
    panel.show()
    pad.show()

    # Shutdown JACK cleanly when app quits
    def _shutdown() -> None:
        try:
            jack.close()
        finally:
            qt_app.deleteLater()

    qt_app.aboutToQuit.connect(_shutdown)

    # Initialize controller state as if pointer is centered already
    pad_center_local = QtCore.QPointF(pad.width() / 2, pad.height() / 2)
    pad_center_global_qp = pad.mapToGlobal(
        QtCore.QPoint(int(pad_center_local.x()), int(pad_center_local.y()))
    )
    pad_center_global = QtCore.QPointF(
        float(pad_center_global_qp.x()), float(pad_center_global_qp.y())
    )
    controller.handle_pointer(pad_center_local, pad_center_global)

    return int(qt_app.exec_())


if __name__ == "__main__":
    sys.exit(main())
