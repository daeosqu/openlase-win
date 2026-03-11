# jack_ab_matrix_switch.py
# -*- coding: utf-8 -*-
"""
Six-channel A/B matrix mixer for JACK with three modes:
  - mix:       fixed 0.5 sum (A + B)
  - exclusive: auto B-priority switching with threshold/hold/crossfade
  - ctrl:      external blend control via in_switch (0..1), smoothed by slew limiter

Ports (per user spec):
  A inputs:  in_b, in_g, in_r, in_e, in_x, in_y
  B inputs:  either:
               --b-style in2 -> in_b2, in_g2, in_r2, in_e2, in_x2, in_y2
               --b-style alt -> alt_in_b, alt_in_g, alt_in_r, alt_in_e, alt_in_x, alt_in_y
  Outputs:   out_b, out_g, out_r, out_e, out_x, out_y
  Control:   in_switch   (mono audio-rate control, 0..1 => B gain, 1-ctrl => A gain)

Requirements:
    pip install jack-client numpy
"""

import argparse
import math
import threading
import time
from typing import Dict

import jack
import numpy as np


CHS = ["x", "y", "r", "g", "b", "e"]  # channel suffixes


def rms_dbfs(x: np.ndarray) -> float:
    """Compute RMS in dBFS for float32 [-1,1]. Safe for silence."""
    m = float(np.mean(x * x))
    if m <= 1e-20:
        return -120.0
    return 10.0 * math.log10(m)


def hard_clip_inplace(x: np.ndarray) -> None:
    """Hard clip to [-1, 1] in-place. Keeps full scale intact."""
    np.clip(x, -1.0, 1.0, out=x)


class Slew:
    """Simple per-block slew limiter for control signals."""
    def __init__(self, max_delta_per_sample: float) -> None:
        self.v = 0.0
        self.max_dps = max_delta_per_sample

    def step_block(self, target: float, n: int) -> float:
        """Advance toward target with per-sample delta limit; return new value."""
        dv = target - self.v
        max_dv = self.max_dps * max(1, n)
        if dv > max_dv:
            dv = max_dv
        elif dv < -max_dv:
            dv = -max_dv
        self.v += dv
        return self.v


class ABMatrix:
    """
    JACK client implementing 6-channel A/B matrix with optional control input.

    Modes:
      - mix:       fixed 0.5*(A+B)
      - exclusive: auto B-priority switching (threshold + hold + crossfade)
      - ctrl:      in_switch controls blend (0..1), smoothed
    """

    def __init__(
        self,
        mode: str,
        threshold_db: float,
        hold_ms: int,
        xfade_ms: int,
        ctrl_slew_ms: int,
        verbose: bool,
        b_style: str,
    ) -> None:
        self.client = jack.Client("ab-matrix")
        self.sr = self.client.samplerate
        self.mode = mode
        self.thr_db = threshold_db
        self.hold_s = max(0.0, hold_ms / 1000.0)
        self.xfade_total = max(0, int(self.sr * xfade_ms / 1000.0))
        self.verbose = verbose

        # Ports
        self.a_in: Dict[str, jack.Port] = {}
        self.b_in: Dict[str, jack.Port] = {}
        self.out: Dict[str, jack.Port] = {}
        self._b_style = b_style  # "in2" or "alt"

        def _b_name(ch: str) -> str:
            if self._b_style == "alt":
                return f"alt_in_{ch}"
            return f"in_{ch}2"

        # Register inputs/outputs. Registration order can influence some UIs' listing.
        for c in CHS:
            # B first (optional, to group alt_in_* together visually), then A, then OUT.
            self.b_in[c] = self.client.inports.register(_b_name(c))
        for c in CHS:
            self.a_in[c] = self.client.inports.register(f"in_{c}")
        for c in CHS:
            self.out[c] = self.client.outports.register(f"out_{c}")

        # Control input (mono). If unconnected, JACK provides zeros.
        self.ctrl = self.client.inports.register("in_switch")

        # Exclusive-mode state
        self.active = "A"  # "A" or "B" or "none"
        self.last_above_ts = {"A": -1e9, "B": -1e9}
        self._xfade_remaining = 0
        self._xfade_from = "A"

        # Ctrl-mode state: slew limiter; full-scale move in approx ctrl_slew_ms
        max_delta_per_sample = 1.0 / max(1, int(self.sr * ctrl_slew_ms / 1000.0))
        self._slew = Slew(max_delta_per_sample)
        self._ctrl_val = 0.0  # smoothed 0..1

        # Meters for status printing
        self._levels = {"A": -120.0, "B": -120.0}
        self._lock = threading.Lock()

        @self.client.set_process_callback
        def _process(frames: int) -> None:
            self._process(frames)

        # @self.client.set_xrun_callback
        # def _xrun(delay: float) -> None:
        #     # Avoid printing in RT context.
        #     return

        self.client.activate()

        if self.verbose:
            t = threading.Thread(target=self._status_loop, daemon=True)
            t.start()

    def close(self) -> None:
        try:
            self.client.deactivate()
        finally:
            self.client.close()

    # ----------------- RT callback -----------------

    def _process(self, frames: int) -> None:
        # Buffers as zero-copy numpy views
        a_bufs = {c: self.a_in[c].get_array() for c in CHS}
        b_bufs = {c: self.b_in[c].get_array() for c in CHS}
        o_bufs = {c: self.out[c].get_array() for c in CHS}
        ctrl_buf = self.ctrl.get_array()

        if self.mode == "mix":
            # out = 0.5*(A+B)
            for c in CHS:
                np.add(a_bufs[c], b_bufs[c], out=o_bufs[c])
                o_bufs[c] *= 0.5
                hard_clip_inplace(o_bufs[c])
            self._update_meters_block(a_bufs, b_bufs)
            return

        if self.mode == "ctrl":
            # Control is 0..1, use mean of block, clamp, slew.
            target = float(np.mean(ctrl_buf))
            if not np.isfinite(target):
                target = 0.0
            target = max(0.0, min(1.0, target))
            self._ctrl_val = self._slew.step_block(target, frames)
            gB = self._ctrl_val
            gA = 1.0 - gB

            for c in CHS:
                np.multiply(a_bufs[c], gA, out=o_bufs[c])
                o_bufs[c] += gB * b_bufs[c]
                hard_clip_inplace(o_bufs[c])
            self._update_meters_block(a_bufs, b_bufs)
            return

        # exclusive mode: decide from overall A/B activity across channels
        # Mixdown across channels to gauge activity (average to keep scale sane)
        mixA = np.zeros(frames, dtype=np.float32)
        mixB = np.zeros(frames, dtype=np.float32)
        for c in CHS:
            mixA += a_bufs[c]
            mixB += b_bufs[c]
        mixA *= 1.0 / len(CHS)
        mixB *= 1.0 / len(CHS)

        a_db = rms_dbfs(mixA)
        b_db = rms_dbfs(mixB)
        now = time.time()

        if a_db > self.thr_db:
            self.last_above_ts["A"] = now
        if b_db > self.thr_db:
            self.last_above_ts["B"] = now

        desired = self._decide_desired(now)

        if desired != self.active:
            self._xfade_from = self.active
            self.active = desired
            self._xfade_remaining = self.xfade_total

        # Render with optional crossfade
        if self.active == "A":
            if self._xfade_remaining > 0 and self._xfade_from == "B":
                n = min(self._xfade_remaining, frames)
                ramp = self._xfade_ramp(frames, n)
                inv = 1.0 - ramp
                for c in CHS:
                    o_bufs[c][:n] = a_bufs[c][:n] * ramp + b_bufs[c][:n] * inv
                    if n < frames:
                        o_bufs[c][n:] = a_bufs[c][n:]
            else:
                for c in CHS:
                    np.copyto(o_bufs[c], a_bufs[c])

        elif self.active == "B":
            if self._xfade_remaining > 0 and self._xfade_from == "A":
                n = min(self._xfade_remaining, frames)
                ramp = self._xfade_ramp(frames, n)
                inv = 1.0 - ramp
                for c in CHS:
                    o_bufs[c][:n] = b_bufs[c][:n] * ramp + a_bufs[c][:n] * inv
                    if n < frames:
                        o_bufs[c][n:] = b_bufs[c][n:]
            else:
                for c in CHS:
                    np.copyto(o_bufs[c], b_bufs[c])

        else:
            for c in CHS:
                o_bufs[c].fill(0.0)

        if self._xfade_remaining > 0:
            self._xfade_remaining -= min(self._xfade_remaining, frames)

        for c in CHS:
            hard_clip_inplace(o_bufs[c])

        self._update_meters_val(a_db, b_db)

    # --------------- helpers ---------------

    def _xfade_ramp(self, frames: int, n: int) -> np.ndarray:
        """Construct a 0..1 ramp slice for current crossfade stage."""
        denom = max(1, self.xfade_total)
        start = (self.xfade_total - self._xfade_remaining) / denom
        stop = (self.xfade_total - self._xfade_remaining + n) / denom
        return np.linspace(start, stop, num=n, endpoint=False, dtype=np.float32)

    def _decide_desired(self, now: float) -> str:
        """Decide desired source for exclusive mode with hold behavior."""
        idle_A = (now - self.last_above_ts["A"]) > self.hold_s
        idle_B = (now - self.last_above_ts["B"]) > self.hold_s
        if not idle_B:
            return "B"
        if not idle_A:
            return "A"
        return "none"

    def _update_meters_block(self, a_bufs: Dict[str, np.ndarray], b_bufs: Dict[str, np.ndarray]) -> None:
        # Cheap-ish metering using first channel buffers
        with self._lock:
            self._levels["A"] = rms_dbfs(a_bufs[CHS[0]])
            self._levels["B"] = rms_dbfs(b_bufs[CHS[0]])

    def _update_meters_val(self, a_db: float, b_db: float) -> None:
        with self._lock:
            self._levels["A"] = a_db
            self._levels["B"] = b_db

    def _status_loop(self) -> None:
        while True:
            with self._lock:
                a = self._levels["A"]
                b = self._levels["B"]
                act = self.active if self.mode == "exclusive" else self.mode
            print(f"[ab-matrix] mode={self.mode} active={act} A={a:6.1f} dBFS B={b:6.1f} dBFS")
            time.sleep(0.5)


def main() -> None:
    ap = argparse.ArgumentParser(description="Six-channel A/B matrix mixer for JACK")
    ap.add_argument("--mode", choices=("mix", "exclusive", "ctrl"), default="ctrl",
                    help="mix: fixed 0.5 sum; exclusive: auto B-priority; ctrl: in_switch drives blend")
    ap.add_argument("--threshold-db", type=float, default=-60.0,
                    help="RMS threshold for activity (exclusive mode)")
    ap.add_argument("--hold-ms", type=int, default=250,
                    help="Silence hold time before switching (exclusive mode)")
    ap.add_argument("--xfade-ms", type=int, default=12,
                    help="Crossfade time when switching (exclusive mode)")
    ap.add_argument("--ctrl-slew-ms", type=int, default=10,
                    help="Approx time to move control 0→1 (ctrl mode). Prevents zipper noise.")
    ap.add_argument("--verbose", action="store_true", help="Print status each 0.5s")
    ap.add_argument("--b-style", choices=("in2", "alt"), default="alt",
                    help='B-side port naming: "in2" -> in_b2/in_g2..., "alt" -> alt_in_b/alt_in_g...')
    args = ap.parse_args()

    m = ABMatrix(
        mode=args.mode,
        threshold_db=args.threshold_db,
        hold_ms=args.hold_ms,
        xfade_ms=args.xfade_ms,
        ctrl_slew_ms=args.ctrl_slew_ms,
        verbose=args.verbose,
        b_style=args.b_style,
    )
    try:
        print("ab-matrix running. Connect ports via qjackctl or jack_connect.")
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        m.close()


if __name__ == "__main__":
    main()
