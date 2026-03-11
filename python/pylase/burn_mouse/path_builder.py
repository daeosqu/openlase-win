from typing import List, Optional
import math

from .jack_laser_client import OLColor, OLPoint


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _scale_color(c: OLColor, s: float) -> OLColor:
    """Return color scaled in brightness by factor s."""
    return OLColor(c.r * s, c.g * s, c.b * s)


class PathBuilder:
    """Path planner for galvanometer-safe laser drawing.

    Features:
    - adaptive sampling limited by max_vel (per-sample travel distance cap)
    - start_wait / end_wait dwell at segment boundaries
    - dimmed dwell at sharp turns to avoid overburn at corners
    - automatic blanked relocation ("jump") with same kinematic limits
    - explicit arming sequence to safely establish a known starting state
    """

    def __init__(
        self,
        max_vel: float = 0.02,          # max distance per sample
        max_accel_deg: float = 45.0,    # if turn sharper than this => corner dwell
        corner_dwell_samples: int = 8,  # dwell samples injected at sharp corners
        corner_dwell_dim: float = 0.4,  # brightness scale for that dwell
        settle_samples: int = 6,        # OFF samples to sit still during arm()
        start_wait: int = 4,            # lit dwell at start of each lit segment/arc
        end_wait: int = 4,              # lit dwell at end of each lit segment/arc
        off_color: Optional[OLColor] = None,
    ) -> None:

        self._pts: List[OLPoint] = []

        # current galvo tip position (best guess after last emit)
        self._x: float = 0.0
        self._y: float = 0.0

        # last motion direction we actually executed
        self._prev_dx: Optional[float] = None
        self._prev_dy: Optional[float] = None

        # motion shaping params
        self._max_vel = max_vel
        self._max_accel_deg = max_accel_deg
        self._corner_dwell_samples = corner_dwell_samples
        self._corner_dwell_dim = corner_dwell_dim
        self._settle_samples = settle_samples

        # new: explicit dwell at segment start/end
        self._start_wait = start_wait
        self._end_wait = end_wait

        # temp next-dir (used just before moving to inject dwell)
        self._next_dx: Optional[float] = None
        self._next_dy: Optional[float] = None

        # color for blanked travel
        self._off_color = off_color if off_color is not None else OLColor(0.0, 0.0, 0.0)

        # arming state
        self._armed = False

    def build(self) -> List[OLPoint]:
        """Return total generated scan path."""
        return self._pts

    # ---------------------------------
    # low-level helpers
    # ---------------------------------

    def _emit(self, x: float, y: float, color: OLColor) -> None:
        """Record a sample output point, update internal cursor."""
        self._pts.append(OLPoint(x, y, color))
        self._x = x
        self._y = y

    def _angle_between(self, ax: float, ay: float, bx: float, by: float) -> float:
        """Angle (deg) between two vectors."""
        da = math.hypot(ax, ay)
        db = math.hypot(bx, by)
        if da == 0.0 or db == 0.0:
            return 0.0
        dot = (ax * bx + ay * by) / (da * db)
        if dot > 1.0:
            dot = 1.0
        elif dot < -1.0:
            dot = -1.0
        ang = math.acos(dot)
        return ang * (180.0 / math.pi)

    def _corner_dwell_if_needed(self, base_color: OLColor) -> None:
        """If we're about to change direction sharply,
        inject a short dimmed dwell at current point so the galvo settles.
        This is called BEFORE we actually start moving in the new direction.
        """
        if self._prev_dx is None or self._prev_dy is None:
            return
        if self._next_dx is None or self._next_dy is None:
            return

        turn_deg = self._angle_between(
            self._prev_dx, self._prev_dy,
            self._next_dx, self._next_dy,
        )

        if turn_deg >= self._max_accel_deg:
            dim_col = _scale_color(base_color, self._corner_dwell_dim)
            x0 = self._x
            y0 = self._y
            for _ in range(self._corner_dwell_samples):
                self._emit(x0, y0, dim_col)

    def _emit_hold(self, x: float, y: float, color: OLColor, count: int) -> None:
        """Emit 'count' samples at the same spot, same color."""
        for _ in range(count):
            print(f"Hold at ({x:.4f}, {y:.4f}) color ({color.r:.2f}, {color.g:.2f}, {color.b:.2f})")
            self._emit(x, y, color)

    def _adaptive_segment(
        self,
        x2: float,
        y2: float,
        color: OLColor,
        lit: bool,
    ) -> None:
        """Move from current pos to (x2,y2) with galvo-friendly sampling.

        - Split into steps so each per-sample movement <= max_vel.
        - Respect sharp turn dwell.
        - Optionally apply start_wait (if lit) before we *leave* the start point
          with the new color.
        - Always apply end_wait (if lit) after we arrive at the end point.

        'lit' means "we intend this segment to be visible". If lit=False,
        we are blanking travel. In that case:
          - we still respect velocity limits for safety
          - we do NOT do start/end dwell holds with color because
            blanking dwell is already cheap and long holds of off_color
            are handled elsewhere (arm settle, etc.).
        """

        x1 = self._x
        y1 = self._y
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)

        # set pending direction so corner dwell logic can fire
        self._next_dx = dx
        self._next_dy = dy

        # 1. before starting the new direction, see if this is a harsh turn.
        #    that injects dimmed dwell at CURRENT point.
        self._corner_dwell_if_needed(base_color=color)

        # 2. apply start_wait if this is a lit segment.
        #    logic: "hold laser on at the *starting* point before slewing away"
        if lit and self._start_wait > 0:
            self._emit_hold(x1, y1, color, self._start_wait)

        # 3. now actually interpolate along the path
        if dist == 0.0:
            # no spatial move; just emit one sample
            self._emit(x1, y1, color)
        else:
            steps = max(2, math.ceil(dist / self._max_vel))
            for i in range(steps):
                t = i / (steps - 1)
                px = _lerp(x1, x2, t)
                py = _lerp(y1, y2, t)
                self._emit(px, py, color)

        # 4. at the destination, if lit, apply end_wait
        if lit and self._end_wait > 0:
            self._emit_hold(x2, y2, color, self._end_wait)

        # update "previous direction"
        self._prev_dx = dx
        self._prev_dy = dy

        # clear pending direction
        self._next_dx = None
        self._next_dy = None

    # ---------------------------------
    # public API
    # ---------------------------------

    def move_to(self, x: float, y: float) -> None:
        """Set internal cursor without emitting anything.
        Caller supplies 'best guess' of current mirror position.
        """
        self._x = x
        self._y = y
        self._prev_dx = None
        self._prev_dy = None
        self._next_dx = None
        self._next_dy = None
        # not armed yet

    def arm(self, safe_x: float, safe_y: float) -> None:
        """Bring galvo safely to a known baseline and settle there OFF.

        Steps:
          1. blank travel (off_color) from current guess to (safe_x, safe_y)
             using adaptive motion.
          2. dwell off_color for _settle_samples to let mirrors calm.
          3. reset motion memory.
          4. mark 'armed' so future lit drawing is allowed.
        """
        # Step 1: blanked relocation
        self._adaptive_segment(safe_x, safe_y, self._off_color, lit=False)

        # Step 2: settle off
        hold_x = self._x
        hold_y = self._y
        self._emit_hold(hold_x, hold_y, self._off_color, self._settle_samples)

        # Step 3: reset motion state
        self._prev_dx = None
        self._prev_dy = None
        self._next_dx = None
        self._next_dy = None

        # Step 4: we're allowed to emit lit segments after this
        self._armed = True

    def jump_to(self, x: float, y: float) -> None:
        """Blanked relocation with adaptive kinematics."""
        self._adaptive_segment(x, y, self._off_color, lit=False)

    def line_to(self, x: float, y: float, color: OLColor) -> None:
        """Draw lit line from current point to (x,y).
        If we're not armed yet, we refuse to light and move blank instead.
        """
        if not self._armed:
            self._adaptive_segment(x, y, self._off_color, lit=False)
            return

        self._adaptive_segment(x, y, color, lit=True)

    def circle(
        self,
        cx: float,
        cy: float,
        radius: float,
        color: OLColor,
        start_phase: float = 0.0,
        sweep: float = 1.0,
    ) -> None:
        """Draw an arc (possibly full circle).

        Behavior:
          - jump_to() blanked to arc start
          - if armed, emit lit arc with start_wait/end_wait and corner dwell
          - if not armed, emit same geometry but off_color only
        """

        # where the arc begins
        start_ang = 2.0 * math.pi * start_phase
        sx = cx + radius * math.cos(start_ang)
        sy = cy + radius * math.sin(start_ang)

        # always blank to start of arc
        self.jump_to(sx, sy)

        sweep_ang = 2.0 * math.pi * sweep
        arc_len = abs(sweep_ang) * radius
        steps = max(2, math.ceil(arc_len / self._max_vel))

        # entering tangent direction (used as "next direction" for dwell)
        sgn = 1.0 if sweep >= 0.0 else -1.0
        enter_dx = -math.sin(start_ang) * radius * sgn
        enter_dy =  math.cos(start_ang) * radius * sgn

        self._next_dx = enter_dx
        self._next_dy = enter_dy

        if self._armed:
            # Before actually tracing arc, treat arc start like a "segment start":
            # - corner dwell check (dimmed)
            # - start_wait at first point
            self._corner_dwell_if_needed(base_color=color)

            # start_wait at the first lit point
            if self._start_wait > 0:
                self._emit_hold(self._x, self._y, color, self._start_wait)

            # trace arc lit
            for i in range(steps):
                t = i / (steps - 1)
                ang = start_ang + sweep_ang * t
                px = cx + radius * math.cos(ang)
                py = cy + radius * math.sin(ang)
                self._emit(px, py, color)

            # end_wait at final point
            if self._end_wait > 0:
                self._emit_hold(self._x, self._y, color, self._end_wait)

            # update prev dir to tangent at end
            end_ang = start_ang + sweep_ang
            end_dx = -math.sin(end_ang) * radius * sgn
            end_dy =  math.cos(end_ang) * radius * sgn
            self._prev_dx = end_dx
            self._prev_dy = end_dy
        else:
            # not armed: same geometry but off_color, and we skip start/end_wait
            for i in range(steps):
                t = i / (steps - 1)
                ang = start_ang + sweep_ang * t
                px = cx + radius * math.cos(ang)
                py = cy + radius * math.sin(ang)
                self._emit(px, py, self._off_color)

            # we didn't define a "real" driven direction when unarmed
            self._prev_dx = None
            self._prev_dy = None

        self._next_dx = None
        self._next_dy = None
