from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import List
import time


LOGGER = logging.getLogger("openlase.cross_demo")

CROSS_HALF_EXTENT = 0.1  # size of cross cursor per output dimension
DRAW_LEVEL = 1.0


@dataclass(frozen=True)
class OLColor:
    """RGB color triple."""
    r: float
    g: float
    b: float


@dataclass(frozen=True)
class OLPoint:
    """One vertex of the scan path."""
    x: float
    y: float
    color: OLColor = OLColor(DRAW_LEVEL, DRAW_LEVEL, DRAW_LEVEL)


class JackLaserClient:
    """
    Extremely dumb JACK client that just outputs:
      out_x, out_y, out_r, out_g, out_b, out_e, out_switch
    following a predefined scan path.
    Now with update_position(x, y), which offsets the whole path.
    """

    def __init__(self, client_name: str) -> None:
        self._lock = threading.Lock()

        self._client_name = client_name

        # scan path data
        self._path: List[OLPoint] = []
        self._path_len = 0
        self._scan_index = 0
        self._blanking = True
        self._need_settle = True

        # global offset (applied to every point when outputting)
        # これが update_position() で動的に書き換えられる
        self._offset_x = 0.0
        self._offset_y = 0.0

        self._last_x = 0.0
        self._last_y = 0.0

    def open(self) -> None:
        import jack  # requires python-jack-client

        self._jack = jack
        try:
            print("Creating JACK client...")
            self._client = jack.Client(self._client_name, use_exact_name=True)
            print("JACK client created.")
        except jack.JackError as exc:
            raise RuntimeError("Failed to connect to the JACK server") from exc

        # create output ports
        self._ports = {
            "out_x": self._client.outports.register("out_x"),
            "out_y": self._client.outports.register("out_y"),
            "out_r": self._client.outports.register("out_r"),
            "out_g": self._client.outports.register("out_g"),
            "out_b": self._client.outports.register("out_b"),
            "out_e": self._client.outports.register("out_e"),
            "out_switch": self._client.outports.register("out_switch"),
        }

        # process callback
        self._client.set_process_callback(self._process)
        self._client.set_shutdown_callback(self._on_shutdown)

        self._client.activate()

        LOGGER.info(
            "cross_demo JACK client '%s' active (samplerate=%d)",
            self._client_name,
            self._client.samplerate,
        )

    def update_settle(self, need_settle: bool) -> None:
        with self._lock:
            self._need_settle = need_settle

    def update_path(self, path: List[OLPoint]) -> None:
        """Update the scan path to a new list of points.

        This path is defined in 'local shape space' (like centered crosshair).
        The final output position = path point + current offset.
        """
        with self._lock:
            self._path = path
            self._path_len = len(path)
            self._scan_index = 0

    def update_position(self, x: float, y: float) -> None:
        """Update the global offset applied to every point.

        No clamp. You said "とりあえずクランプなしでいい", so yes,
        we can shoot the scanners straight into the sun if you feed garbage.
        """
        with self._lock:
            self._offset_x = x
            self._offset_y = y

    def update_blanking(self, blanking: bool) -> None:
        with self._lock:
            self._blanking = blanking

    # JACK callbacks -------------------------------------------------

    def _on_shutdown(self, reason: str | None) -> None:
        LOGGER.warning("JACK server requested shutdown: %s", reason)

    def _process(self, frames: int) -> None:
        """
        JACK RT callback. For each audio frame, we output one point from
        the current scan path. The path loops.

        We now apply the current offset to p.x and p.y before writing them out.
        """
        try:
            o_x = self._ports["out_x"].get_array()[:frames]
            o_y = self._ports["out_y"].get_array()[:frames]
            o_r = self._ports["out_r"].get_array()[:frames]
            o_g = self._ports["out_g"].get_array()[:frames]
            o_b = self._ports["out_b"].get_array()[:frames]
            o_e = self._ports["out_e"].get_array()[:frames]
            o_switch = self._ports["out_switch"].get_array()[:frames]

            # Copy shared state under lock into locals so that RT loop
            # doesn't hold the lock while filling all frames.
            with self._lock:
                idx = self._scan_index
                path = self._path
                plen = self._path_len
                off_x = self._offset_x
                off_y = self._offset_y
                blanking = self._blanking
                need_settle = self._need_settle

            if plen == 0 or blanking:
                # no path defined, kill beam (or at least try)
                x = 0
                y = 0
                o_r.fill(0.0)
                o_g.fill(0.0)
                o_b.fill(0.0)
                o_e.fill(0.0)
                o_x.fill(x)
                o_y.fill(y)
                o_switch.fill(0.0)
            else:
                # fill buffers
                p = path[idx]
                x = p.x + off_x
                y = p.y + off_y

                if need_settle:
                    with self._lock:
                        self._need_settle = False
                    n = min(64, frames)
                    # for i in range(n):
                    #     o_r[i] = 0.0
                    #     o_g[i] = 0.0
                    #     o_b[i] = 0.0
                    #     o_e[i] = 0.0
                    #     o_x[i] = x
                    #     o_y[i] = y
                    #     o_switch[i] = 1.0
                    # frames -= n
                else:
                    n = 0

                for i in range(frames):
                    p = path[idx]

                    # position with offset applied
                    x = p.x + off_x
                    y = p.y + off_y

                    if n > 0:
                        n -= 1
                        o_r[i] = 0.0
                        o_g[i] = 0.0
                        o_b[i] = 0.0
                        o_e[i] = 0.0
                        o_x[i] = x
                        o_y[i] = y
                        o_switch[i] = 1.0
                        continue

                    o_x[i] = x
                    o_y[i] = y

                    # RGB intensity
                    o_r[i] = p.color.r
                    o_g[i] = p.color.g
                    o_b[i] = p.color.b

                    # gate lines (for now, always on if we have a path)
                    o_e[i] = 1.0
                    o_switch[i] = 1.0

                    idx += 1
                    if idx >= plen:
                        idx = 0

            self._last_x = x
            self._last_y = y

            # write back updated scan index
            with self._lock:
                self._scan_index = idx

        except Exception:
            # don't ever raise in RT thread unless you like xruns and sadness
            LOGGER.exception("Error in JACK process callback")

    def close(self) -> None:
        LOGGER.info("Shutting down JACK cross_demo client")
        try:
            self._client.deactivate()
        except self._jack.JackError:
            LOGGER.exception("Failed to deactivate JACK client cleanly")
        finally:
            # tiny spin wait before closing the client
            start = time.perf_counter()
            end = start + 0.1
            while time.perf_counter() < end:
                pass

            self._client.close()
