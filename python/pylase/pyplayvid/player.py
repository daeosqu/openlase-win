"""Threaded media player that mirrors ``qplayvid.c``.

The module coordinates audio, video, and rendering threads similarly to the C
reference: :class:`PlayerCtx` owns the decoder and display loops, routes seek
requests, and performs synchronisation using ``seekid`` values sourced from the
audio callback.  The specification in ``docs/qplayvid_pyplayvid_spec.md``
provides the detailed behaviour that the Python implementation follows.  The
docstrings in this file summarise the control flow and highlight how the
original design maps onto Python primitives.

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

import enum
import math
import threading
import time
from collections import deque
from fractions import Fraction
from pathlib import Path
from typing import Callable, Deque, Optional

import av
import cv2
import numpy as np
import pylase as ol

from .audio import AudioPlayer
from .gui_types import PreviewFrame
from .media import detect_frame_geometry, find_media_streams, open_video_source
from .render import (
    configure_render_params,
    create_tracer,
    iter_objects,
    render_objects,
    update_threshold,
)
from .settings import PlayerEvent, PlayerSettings, VideoFrame, get_audio_rate
from .utils import DEBUG2, DEBUG3, LOGGER, PerSecondAverager, _timing_scope

__all__ = ["DisplayMode", "PlayerCtx"]


class DisplayMode(enum.Enum):
    """Playback state machine mirroring the C enum."""

    STOP = "stop"
    PAUSE = "pause"
    PLAY = "play"


class _FrameDecision(enum.Enum):
    """Internal decision used to keep the display loop audio-synchronised."""

    RENDER = "render"
    SKIP = "skip"
    WAIT = "wait"


class PlayerCtx:
    """Threaded media player roughly mirroring the C reference implementation.

    ``PlayerCtx`` owns the long-lived resources of the player: it opens the
    media source, spawns decoder/display threads, orchestrates seeks, and proxies
    rendering events back to the GUI.  The class is intentionally stateful—the
    shared fields correspond to the ``PlayerCtx`` structure documented in the C
    codebase and described extensively in ``docs/qplayvid_pyplayvid_spec.md``.
    The methods below document how each high-level responsibility is achieved in
    Python.
    """

    def __init__(
        self,
        source: str,
        settings: PlayerSettings,
        *,
        loop: bool,
        fps_override: Optional[float],
        use_color: bool,
        stats_interval: int,
        benchmark_interval: float,
        decoder: str,
        event_callback: Optional[Callable[[PlayerEvent], None]] = None,
        frame_callback: Optional[Callable[[PreviewFrame], None]] = None,
    ) -> None:
        """Initialise playback state and inspect the media source.

        The constructor mirrors ``playvid_init`` in the C implementation:

        * probe the container to discover video/audio streams and choose
          defaults;
        * configure scaling, FPS, and duration information that the display
          thread uses;
        * construct the :class:`AudioPlayer` when an audio stream is available;
        * prepare synchronisation primitives (locks, events, queues) that the
          decoder and display threads share.
        """

        self.source = source
        self.settings = settings
        self.loop = loop
        self.fps_override = fps_override
        self.use_color = use_color
        self.stats_interval = stats_interval
        self.benchmark_interval = max(0.0, float(benchmark_interval))
        self.ev_cb = event_callback
        self.frame_cb = frame_callback
        self.decoder = decoder.lower()

        video_enabled = True
        audio_stream_index: Optional[int] = None
        probe_success = False
        probe_container: Optional[av.container.InputContainer] = None
        try:
            probe_container = av.open(self.source)
        except av.error.FFmpegError as exc:
            LOGGER.warning("Unable to inspect media streams for %s: %s", self.source, exc)
        else:
            probe_success = True
            video_stream, audio_stream, audio_index = find_media_streams(probe_container)
            if video_stream is None:
                LOGGER.error("No video streams found in %s; video playback disabled", self.source)
                video_enabled = False
            if audio_stream is None:
                LOGGER.info("No audio streams found in %s", self.source)
            elif audio_index is not None:
                audio_stream_index = audio_index
        finally:
            if probe_container is not None:
                try:
                    probe_container.close()
                except av.error.FFmpegError:
                    LOGGER.debug("Failed to close probe container cleanly")

        self.video_playback_enabled = video_enabled
        self.video_source = open_video_source(source, decoder=self.decoder, enable_video=video_enabled)
        LOGGER.info("Using %s decoder", self.decoder)
        if video_enabled:
            width, height, fps = detect_frame_geometry(self.video_source)
        else:
            width = self.video_source.width
            height = self.video_source.height
            fps = self.video_source.fps
        if fps_override and fps_override > 0:
            LOGGER.info("FPS override requested: %.3f", fps_override)
            fps = fps_override
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_period = 1.0 / fps if fps > 0 else None
        self.scale_factor = settings.scale / 100.0
        self.scaled_width = max(1, int(round(width * self.scale_factor)))
        self.scaled_height = max(1, int(round(height * self.scale_factor)))
        LOGGER.info("Scaled frame size: %dx%d", self.scaled_width, self.scaled_height)
        frame_count = self.video_source.frame_count
        if frame_count > 0 and fps > 0:
            self.duration = frame_count / fps
        elif self.video_source.duration > 0:
            self.duration = self.video_source.duration
        else:
            self.duration = 0.0

        LOGGER.info("Video geometry: %dx%d @ %.3f FPS", width, height, fps)
        LOGGER.info("Tracing at %dx%d", self.scaled_width, self.scaled_height)

        self.audio_player: Optional[AudioPlayer] = None
        source_path = Path(source)
        if source_path.is_file():
            if probe_success:
                stream_index_arg: Optional[int] = audio_stream_index
            else:
                stream_index_arg = 0

            if stream_index_arg is not None:
                try:
                    audio_rate = get_audio_rate()
                    self.audio_player = AudioPlayer(
                        source_path,
                        audio_rate,
                        stream_index=stream_index_arg,
                    )
                    LOGGER.info(
                        "Initialised streaming audio from %s (stream index %d) @ %d Hz",
                        source_path,
                        stream_index_arg,
                        audio_rate,
                    )
                except RuntimeError as exc:
                    LOGGER.warning("Audio playback disabled: %s", exc)
            else:
                LOGGER.info("Audio playback disabled (no audio streams found)")
        else:
            LOGGER.debug("Audio playback disabled for non-file source: %s", source)

        self.display_mode = DisplayMode.STOP
        self.display_mode_lock = threading.Lock()
        self.display_mode_cond = threading.Condition(self.display_mode_lock)
        self.exit_event = threading.Event()
        self.seek_event = threading.Event()
        self.decoder_done = False
        self.finished_event = threading.Event()
        self.threads_started = False

        self.video_queue: Deque[VideoFrame] = deque()
        self.video_queue_cond = threading.Condition()
        self.video_buf_len = 6

        self.seek_mutex = threading.Lock()
        self.seek_pos: Optional[float] = None
        self.cur_seekid = 0

        self.player_event = PlayerEvent()
        self.event_mutex = threading.Lock()

        self.settings_mutex = threading.Lock()
        self.settings_changed = False

        self.bg_white: Optional[bool] = None
        self.cur_frame: Optional[VideoFrame] = None
        self.last_frame_pts: Optional[float] = None

        self.decoder_thread_handle: Optional[threading.Thread] = None
        self.display_thread_handle: Optional[threading.Thread] = None

        self.openlase_ready = False
        self.tracer = create_tracer(self.settings, self.scaled_width, self.scaled_height)
        self.overscan = 1.0 + settings.overscan / 100.0
        self.scale_x = self.overscan * 2.0 / self.scaled_width
        self.scale_y = self.overscan * 2.0 / self.scaled_height
        self.center_x = (self.scaled_width - 1) / 2.0
        self.center_y = (self.scaled_height - 1) / 2.0

        LOGGER.debug("Player initialised (loop=%s, color=%s)", loop, use_color)

        self.decoder_benchmark = PerSecondAverager(
            "Decoder frame timings", interval=self.benchmark_interval
        )
        self.render_benchmark = PerSecondAverager(
            "Render frame timings", interval=self.benchmark_interval
        )
        self._needs_video_reset = False
        self._audio_wait_timeout = 0.5
        self._audio_wait_interval = 0.0025

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def playvid_play(self) -> None:
        """Switch to PLAY mode and ensure background threads are running."""

        with self.display_mode_lock:
            if self.display_mode == DisplayMode.PLAY:
                LOGGER.debug("Play command ignored; already playing")
                return
            was_paused = self.display_mode == DisplayMode.PAUSE
            if not self.threads_started:
                self._start_threads()
            self.display_mode = DisplayMode.PLAY
            self.display_mode_cond.notify_all()
        LOGGER.info("Playback started")

        if self.audio_player:
            if was_paused and not self.audio_player.has_finished():
                self.audio_player.resume()
            else:
                self.audio_player.start(self.loop)

    def playvid_pause(self) -> None:
        """Pause playback while keeping decoder and display threads alive."""

        with self.display_mode_lock:
            if not self.threads_started:
                LOGGER.debug("Pause requested before initialisation; starting threads paused")
                self._start_threads()
            if self.display_mode == DisplayMode.PAUSE:
                LOGGER.debug("Pause command ignored; already paused")
                return
            self.display_mode = DisplayMode.PAUSE
            self.display_mode_cond.notify_all()
        LOGGER.info("Playback paused")

        if self.audio_player:
            self.audio_player.pause()

    def playvid_skip(self) -> None:
        """Placeholder for parity with the C API (not yet implemented)."""

        LOGGER.debug("Skip command not implemented in Python player")

    def playvid_stop(self) -> None:
        """Stop playback, tear down threads, and close the media source."""

        with self.display_mode_lock:
            if self.display_mode == DisplayMode.STOP and not self.threads_started:
                LOGGER.debug("Stop command ignored; player already idle")
                return
            LOGGER.info("Stopping playback")
            self.display_mode = DisplayMode.STOP
            self.exit_event.set()
            self.display_mode_cond.notify_all()
        with self.video_queue_cond:
            self.video_queue_cond.notify_all()
        self.seek_event.set()
        self._needs_video_reset = True
        try:
            self.video_source.close()
        except Exception:  # pragma: no cover - best effort shutdown
            LOGGER.exception("Failed to close video source during stop")
        if self.decoder_thread_handle and self.decoder_thread_handle.is_alive():
            self.decoder_thread_handle.join(timeout=2.0)
            if self.decoder_thread_handle.is_alive():
                LOGGER.warning("Decoder thread did not exit cleanly within timeout")
        if self.display_thread_handle and self.display_thread_handle.is_alive():
            self.display_thread_handle.join(timeout=2.0)
            if self.display_thread_handle.is_alive():
                LOGGER.warning("Display thread did not exit cleanly within timeout")
        self.threads_started = False
        self.finished_event.set()
        if self.audio_player:
            self.audio_player.stop()
        if self.openlase_ready:
            if self.audio_player:
                self.audio_player.detach()
            LOGGER.debug("Shutting down OpenLase")
            try:
                ol.shutdown()
            except Exception:  # pragma: no cover - best effort cleanup
                LOGGER.exception("Failed to shutdown OpenLase cleanly")
            self.openlase_ready = False

        self.video_source.close()
        self.last_frame_pts = None

        if self.decoder_thread_handle and self.decoder_thread_handle.is_alive():
            LOGGER.error("Decoder thread still running after stop")
        self.decoder_thread_handle = None
        if self.display_thread_handle and self.display_thread_handle.is_alive():
            LOGGER.error("Display thread still running after stop")
        self.display_thread_handle = None

    def playvid_seek(self, position: float) -> None:
        """Request a seek and bump ``seekid`` for both audio and video paths."""

        if position < 0:
            position = 0.0
        with self.seek_mutex:
            self.seek_pos = position
            self.cur_seekid += 1
        with self.event_mutex:
            self.player_event.time = position
            self.player_event.ftime = 0.0
            self.player_event.pts = position
        self.seek_event.set()
        with self.video_queue_cond:
            self.video_queue.clear()
            self.video_queue_cond.notify_all()
        LOGGER.info("Seek requested: %.3fs (seekid=%d)", position, self.cur_seekid)

    def playvid_update_settings(self, new_settings: PlayerSettings) -> None:
        """Update runtime settings and flag that the display loop must refresh."""

        with self.settings_mutex:
            LOGGER.info("Updating player settings")
            self.settings = new_settings
            self.settings_changed = True

    def playvid_set_eventcb(self, callback: Optional[Callable[[PlayerEvent], None]]) -> None:
        """Replace the player event callback used by the GUI."""

        self.ev_cb = callback

    def playvid_set_framecb(self, callback: Optional[Callable[[PreviewFrame], None]]) -> None:
        """Replace the preview frame callback."""

        self.frame_cb = callback

    def playvid_get_duration(self) -> float:
        """Return the detected media duration in seconds."""

        return self.duration

    def wait_until_finished(self) -> None:
        """Block until playback naturally reaches EOF or ``playvid_stop`` runs."""

        LOGGER.debug("Waiting for playback to finish")
        self.finished_event.wait()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _start_threads(self) -> None:
        """Start decoder/display threads and ensure OpenLase is ready."""

        LOGGER.debug("Starting decoder/display threads")
        if not self.openlase_ready:
            self._init_openlase()
        if self._needs_video_reset:
            LOGGER.debug("Reopening video source after stop")
            try:
                self.video_source = open_video_source(
                    self.source,
                    decoder=self.decoder,
                    enable_video=self.video_playback_enabled,
                )
            except Exception:
                LOGGER.exception("Failed to reopen video source; aborting start")
                raise
            self._needs_video_reset = False
        self.exit_event.clear()
        self.seek_event.clear()
        self.decoder_done = False
        self.finished_event.clear()
        self.player_event = PlayerEvent()
        self.video_queue.clear()
        self.decoder_thread_handle = threading.Thread(target=self._decoder_loop, name="DecoderThread", daemon=True)
        self.display_thread_handle = threading.Thread(target=self._display_loop, name="DisplayThread", daemon=True)
        self.decoder_thread_handle.start()
        self.display_thread_handle.start()
        self.threads_started = True
        self.last_frame_pts = None

    def _init_openlase(self) -> None:
        """Initialise OpenLase and attach the audio callback."""

        LOGGER.info("Initialising OpenLase")
        if ol.init(buffer_count=5, max_points=300000) < 0:
            LOGGER.error("OpenLase initialisation failed")
            raise RuntimeError("OpenLase initialisation failed")
        params = configure_render_params(self.settings, self.scaled_width, self.scaled_height)
        LOGGER.info("Render parameters: %s", params)
        ol.setRenderParams(params)
        if self.audio_player:
            self.audio_player.attach()
        self.openlase_ready = True

    def _decoder_loop(self) -> None:
        """Decode video frames and enqueue them with the current ``seekid``."""

        LOGGER.debug("Decoder thread started")
        frame_index = 0
        try:
            while not self.exit_event.is_set():
                if self.seek_event.is_set():
                    frame_index = self._handle_seek_request(frame_index)
                    continue

                with _timing_scope(f"Video decoder frame {frame_index}", level=DEBUG3) as stop_total:
                    decode_start = time.perf_counter()
                    av_frame = self.video_source.read_frame()
                    decode_elapsed = time.perf_counter() - decode_start

                    if av_frame is None:
                        if self.loop:
                            LOGGER.info("Looping video")
                            self.video_source.rewind()
                            frame_index = 0
                            continue
                        LOGGER.info("Decoder reached end of stream")
                        break

                    convert_start = time.perf_counter()
                    frame = av_frame.to_ndarray(format="bgr24")
                    convert_elapsed = time.perf_counter() - convert_start

                    pts_seconds: Optional[float]
                    if av_frame.pts is not None:
                        time_base = av_frame.time_base or float(self.video_source.time_base)
                        if isinstance(time_base, Fraction):
                            time_base = float(time_base)
                        pts_seconds = float(av_frame.pts * time_base)
                    elif av_frame.time is not None:
                        pts_seconds = float(av_frame.time)
                    else:
                        pts_seconds = None

                    if pts_seconds is None:
                        pts_seconds = frame_index / self.fps if self.fps > 0 else float(frame_index)

                    timestamp = float(av_frame.time) if av_frame.time is not None else pts_seconds
                    packet = VideoFrame(
                        index=frame_index,
                        pts=pts_seconds,
                        timestamp=timestamp,
                        seekid=self.cur_seekid,
                        image=frame,
                    )

                    queue_wait = 0.0
                    with self.video_queue_cond:
                        if len(self.video_queue) >= self.video_buf_len and not self.exit_event.is_set():
                            wait_start = time.perf_counter()
                            while (
                                len(self.video_queue) >= self.video_buf_len
                                and not self.exit_event.is_set()
                            ):
                                LOGGER.debug3("Video decoder waiting (queue full)")
                                self.video_queue_cond.wait()
                            queue_wait = time.perf_counter() - wait_start
                        if self.exit_event.is_set():
                            break
                        self.video_queue.append(packet)
                        self.video_queue_cond.notify()

                    total_elapsed = stop_total()
                    decoder_avg = self.decoder_benchmark.add(
                        read=decode_elapsed,
                        convert=convert_elapsed,
                        queue_wait=queue_wait,
                        total=total_elapsed,
                    )
                    if decoder_avg:
                        averages, count, duration = decoder_avg
                        fps = count / duration if duration > 0 else 0.0
                        LOGGER.debug2(
                            (
                                "Video decoder average over %.2fs (%d frames): read=%.3f ms "
                                "convert=%.3f ms queue_wait=%.3f ms total=%.3f ms | fps=%.2f"
                            ),
                            duration,
                            count,
                            averages.get("read", 0.0) * 1000.0,
                            averages.get("convert", 0.0) * 1000.0,
                            averages.get("queue_wait", 0.0) * 1000.0,
                            averages.get("total", 0.0) * 1000.0,
                            fps,
                        )
                    LOGGER.debug3(
                        "Video decoder frame %d timings: read=%.3f ms convert=%.3f ms queue_wait=%.3f ms total=%.3f ms",
                        frame_index,
                        decode_elapsed * 1000.0,
                        convert_elapsed * 1000.0,
                        queue_wait * 1000.0,
                        total_elapsed * 1000.0,
                    )

                    LOGGER.debug3("Video decoded frame %d (seekid=%d)", frame_index, self.cur_seekid)
                    frame_index += 1
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Decoder thread crashed")
            with self.display_mode_lock:
                self.display_mode = DisplayMode.STOP
            self.exit_event.set()
        finally:
            with self.video_queue_cond:
                self.decoder_done = True
                self.video_queue_cond.notify_all()
            LOGGER.debug("Decoder thread exiting")

    def _handle_seek_request(self, frame_index: int) -> int:
        """Handle pending seek events and return the new frame index."""

        self.seek_event.clear()
        with self.seek_mutex:
            target = self.seek_pos
            self.seek_pos = None
        if target is None:
            return frame_index
        LOGGER.info("Applying seek to %.3fs", target)
        try:
            self.video_source.seek(target)
        except RuntimeError:
            LOGGER.exception("Seek failed; reopening video source")
            self.video_source.close()
            self.video_source = open_video_source(
                self.source,
                decoder=self.decoder,
                enable_video=self.video_playback_enabled,
            )
            self.video_source.seek(target)
        with self.video_queue_cond:
            self.video_queue.clear()
            self.video_queue_cond.notify_all()
        self.decoder_done = False
        self.bg_white = None
        if self.audio_player:
            self.audio_player.seek(target)
        LOGGER.debug("Seek applied; decoder queue flushed")
        self.last_frame_pts = None
        if self.fps > 0:
            return int(max(0.0, target) * self.fps)
        return int(max(0.0, target))

    def _display_loop(self) -> None:
        """Render frames in sync with the audio clock and display mode."""

        LOGGER.debug("Display thread started")
        next_stats_report = self.stats_interval if self.stats_interval > 0 else None
        try:
            while True:
                if self.exit_event.is_set() and not self.video_queue:
                    LOGGER.debug("Stop requested and queue drained")
                    break

                packet = self._get_next_frame()

                if packet is None:
                    if self.decoder_done and not self.video_queue:
                        LOGGER.info("Display thread detected end of playback")
                        break
                    continue

                if packet.seekid != self.cur_seekid:
                    LOGGER.debug2(
                        "Dropping stale frame %d (seekid=%d, expected=%d)",
                        packet.index,
                        packet.seekid,
                        self.cur_seekid,
                    )
                    continue

                wait_started: Optional[float] = None
                pause_wait = False
                while True:
                    with self.display_mode_lock:
                        mode_snapshot = self.display_mode

                    decision = self._decide_frame_action(packet, mode_snapshot)

                    if decision is _FrameDecision.SKIP:
                        LOGGER.debug2(
                            "Skipping frame %d (pts=%.3f)",
                            packet.index,
                            packet.pts,
                        )
                        self._pump_render_tick()
                        self.last_frame_pts = packet.pts
                        break

                    if decision is _FrameDecision.WAIT:
                        if wait_started is None:
                            wait_started = time.perf_counter()
                        elif time.perf_counter() - wait_started > self._audio_wait_timeout:
                            LOGGER.warning(
                                "Audio did not catch up within %.2fs; dropping frame %d",
                                self._audio_wait_timeout,
                                packet.index,
                            )
                            self.last_frame_pts = packet.pts
                            break

                        self._pump_render_tick()
                        if self.exit_event.wait(self._audio_wait_interval):
                            break
                        continue

                    wait_started = None

                    self.cur_frame = packet

                    with self.display_mode_lock:
                        mode = self.display_mode
                        if mode == DisplayMode.PAUSE:
                            LOGGER.debug2("Display thread paused; waiting for resume")
                            self._render_frame(packet)
                            self.display_mode_cond.wait_for(
                                lambda: self.display_mode != DisplayMode.PAUSE or self.exit_event.is_set()
                            )
                            pause_wait = True
                            break
                        if mode == DisplayMode.STOP:
                            LOGGER.debug("Display thread noticed STOP mode")
                            return

                    self._render_frame(packet)
                    break

                if decision is _FrameDecision.SKIP or decision is _FrameDecision.WAIT:
                    continue
                if pause_wait:
                    continue

                with self.event_mutex:
                    self.player_event.frames += 1
                    self.player_event.pts = packet.pts
                if next_stats_report is not None and self.player_event.frames % next_stats_report == 0:
                    self._report_stats()
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Display thread crashed")
            self.exit_event.set()
        finally:
            LOGGER.debug("Display thread exiting")
            self.finished_event.set()

    def _get_next_frame(self) -> Optional[VideoFrame]:
        """Pop the next queued frame or ``None`` when none are ready."""

        with self.video_queue_cond:
            while not self.video_queue and not self.exit_event.is_set() and not self.decoder_done:
                self.video_queue_cond.wait(timeout=0.1)
            if self.video_queue:
                packet = self.video_queue.popleft()
                self.video_queue_cond.notify()
                return packet
            return None

    def _decide_frame_action(self, packet: VideoFrame, mode: DisplayMode) -> _FrameDecision:
        """Return how the display loop should treat ``packet`` given the audio clock."""

        if mode != DisplayMode.PLAY:
            return _FrameDecision.RENDER

        audio_player = self.audio_player
        if not audio_player:
            return _FrameDecision.RENDER

        clock = audio_player.get_playback_clock()
        if clock is None:
            return _FrameDecision.RENDER
        if not clock.started or clock.paused:
            return _FrameDecision.RENDER

        if packet.seekid != self.cur_seekid:
            return _FrameDecision.SKIP
        if clock.seekid != self.cur_seekid:
            return _FrameDecision.WAIT

        audio_pts = clock.pts
        next_pts = clock.next_pts
        if audio_pts is None or math.isnan(audio_pts):
            return _FrameDecision.RENDER
        if next_pts is None or math.isnan(next_pts):
            next_pts = audio_pts

        audio_time = max(audio_pts, next_pts)
        if audio_time < 0:
            return _FrameDecision.RENDER

        frame_delta = self._estimate_frame_delta(packet.pts)
        ready_threshold = packet.pts - min(frame_delta * 0.5, 0.010)
        skip_threshold = packet.pts + frame_delta

        if audio_time + 1e-6 < ready_threshold:
            LOGGER.debug3(
                "Waiting for audio: frame %d audio=%.3f ready=%.3f", packet.index, audio_time, ready_threshold
            )
            return _FrameDecision.WAIT

        if audio_time > skip_threshold:
            LOGGER.debug2(
                "Audio ahead of frame %d (audio=%.3f, threshold=%.3f)",
                packet.index,
                audio_time,
                skip_threshold,
            )
            return _FrameDecision.SKIP

        return _FrameDecision.RENDER

    def _estimate_frame_delta(self, current_pts: float) -> float:
        """Estimate the expected time until the next frame using recent history."""

        frame_delta = 0.0
        last_pts = self.last_frame_pts
        if last_pts is not None and last_pts >= 0:
            frame_delta = current_pts - last_pts

        if frame_delta <= 0 and self.frame_period:
            frame_delta = self.frame_period
        if frame_delta <= 0 and self.fps > 0:
            frame_delta = 1.0 / self.fps
        if frame_delta <= 0:
            frame_delta = 1.0 / 60.0
        return frame_delta

    def _pump_render_tick(self) -> None:
        """Tick OpenLase to keep the audio callback serviced during skips/waits."""

        try:
            ol.renderFrame(80)
        except Exception:
            LOGGER.exception("renderFrame pump failed during synchronisation wait")

    def _render_frame(self, packet: VideoFrame) -> None:
        """Render ``packet`` to the laser output and drive preview callbacks."""

        with self.settings_mutex:
            if self.settings_changed:
                LOGGER.debug("Reconfiguring tracer and render parameters")
                self.tracer = create_tracer(self.settings, self.scaled_width, self.scaled_height)
                params = configure_render_params(self.settings, self.scaled_width, self.scaled_height)
                ol.setRenderParams(params)
                self.overscan = 1.0 + self.settings.overscan / 100.0
                self.scale_x = self.overscan * 2.0 / self.scaled_width
                self.scale_y = self.overscan * 2.0 / self.scaled_height
                self.settings_changed = False

            settings = self.settings

        with _timing_scope(f"Vidoe render frame {packet.index}", level=DEBUG3) as stop_total:
            frame = packet.image
            resize_elapsed = 0.0
            resize_start = time.perf_counter()
            if self.scale_factor != 1.0:
                interpolation = cv2.INTER_AREA if self.scale_factor < 1.0 else cv2.INTER_LINEAR
                resized = cv2.resize(
                    frame,
                    (self.scaled_width, self.scaled_height),
                    interpolation=interpolation,
                )
                resize_elapsed = time.perf_counter() - resize_start
            else:
                resized = frame
                resize_elapsed = time.perf_counter() - resize_start

            gray_start = time.perf_counter()
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            gray = np.ascontiguousarray(gray)
            gray_elapsed = time.perf_counter() - gray_start

            threshold_elapsed = 0.0
            threshold_start = time.perf_counter()
            if not settings.canny:
                self.bg_white = update_threshold(
                    self.tracer,
                    settings,
                    gray,
                    min(self.scaled_width, self.scaled_height),
                    self.bg_white,
                )
            else:
                self.tracer.threshold = settings.threshold
                self.tracer.threshold2 = settings.threshold2
            threshold_elapsed = time.perf_counter() - threshold_start

            trace_start = time.perf_counter()
            traced = self.tracer.trace(gray.tobytes(), stride=gray.strides[0])
            trace_elapsed = time.perf_counter() - trace_start

            collect_start = time.perf_counter()
            objects = list(iter_objects(traced, settings.decimation))
            collect_elapsed = time.perf_counter() - collect_start

            color_elapsed = 0.0
            if self.use_color:
                color_start = time.perf_counter()
                color_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                color_elapsed = time.perf_counter() - color_start
            else:
                color_frame = None

            render_start = time.perf_counter()
            render_objects(
                objects,
                color_frame,
                self.scale_x,
                self.scale_y,
                self.center_x,
                self.center_y,
            )
            frame_time = ol.renderFrame(80)
            render_elapsed = time.perf_counter() - render_start

            if self.frame_cb:
                try:
                    laser_paths = [
                        np.asarray(obj, dtype=np.float32)
                        for obj in objects
                        if len(obj) >= 2
                    ]
                    debug_frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                    preview = PreviewFrame(
                        index=packet.index,
                        timestamp=packet.timestamp,
                        duration=self.frame_period if self.frame_period else frame_time,
                        frame_size=(resized.shape[1], resized.shape[0]),
                        video_frame=resized,
                        laser_paths=laser_paths,
                        debug_frame=debug_frame,
                        pts=packet.pts,
                    )
                    self.frame_cb(preview.copy_for_gui())
                except Exception:  # pragma: no cover - defensive logging
                    LOGGER.exception("Frame callback failed")

            total_elapsed = stop_total()
            render_avg = self.render_benchmark.add(
                resize=resize_elapsed,
                gray=gray_elapsed,
                threshold=threshold_elapsed,
                trace=trace_elapsed,
                collect=collect_elapsed,
                color=color_elapsed,
                render=render_elapsed,
                total=total_elapsed,
            )
            if render_avg:
                averages, count, duration = render_avg
                fps = count / duration if duration > 0 else 0.0
                LOGGER.debug(
                    (
                        "Render average over %.2fs (%d frames): resize=%.3f ms gray=%.3f ms "
                        "threshold=%.3f ms trace=%.3f ms collect=%.3f ms color=%.3f ms "
                        "render=%.3f ms total=%.3f ms | fps=%.2f"
                    ),
                    duration,
                    count,
                    averages.get("resize", 0.0) * 1000.0,
                    averages.get("gray", 0.0) * 1000.0,
                    averages.get("threshold", 0.0) * 1000.0,
                    averages.get("trace", 0.0) * 1000.0,
                    averages.get("collect", 0.0) * 1000.0,
                    averages.get("color", 0.0) * 1000.0,
                    averages.get("render", 0.0) * 1000.0,
                    averages.get("total", 0.0) * 1000.0,
                    fps,
                )
            LOGGER.debug3(
                (
                    "Video render frame %d timings: resize=%.3f ms gray=%.3f ms threshold=%.3f ms "
                    "trace=%.3f ms collect=%.3f ms color=%.3f ms render=%.3f ms total=%.3f ms"
                ),
                packet.index,
                resize_elapsed * 1000.0,
                gray_elapsed * 1000.0,
                threshold_elapsed * 1000.0,
                trace_elapsed * 1000.0,
                collect_elapsed * 1000.0,
                color_elapsed * 1000.0,
                render_elapsed * 1000.0,
                total_elapsed * 1000.0,
            )

        with self.event_mutex:
            self.player_event.ftime = frame_time
            self.player_event.time += frame_time

        with self.video_queue_cond:
            queue_len = len(self.video_queue)

        LOGGER.debug3(
            "Rendered frame %d (%d objects, queue=%d)",
            packet.index,
            len(objects),
            queue_len,
        )
        self.last_frame_pts = packet.pts

    def _report_stats(self) -> None:
        """Emit periodic playback statistics and invoke the event callback."""

        info = ol.getFrameInfo()
        padding_points = getattr(info, "padding_points", 0)
        with self.video_queue_cond:
            ended_flag = int(self.decoder_done and not self.video_queue)
        with self.event_mutex:
            pts = self.player_event.pts
            if pts < 0 and self.cur_frame is not None:
                pts = self.cur_frame.pts
            event = PlayerEvent(
                time=self.player_event.time,
                ftime=self.player_event.ftime,
                frames=self.player_event.frames,
                objects=info.objects,
                points=info.points,
                resampled_points=getattr(info, "resampled_points", 0),
                resampled_blacks=getattr(info, "resampled_blacks", 0),
                padding_points=padding_points,
                pts=pts,
                ended=ended_flag,
            )
        LOGGER.info(
            "Frame %d | objects=%d points=%d resampled=%d blacks=%d",
            event.frames,
            info.objects,
            info.points,
            info.resampled_points,
            info.resampled_blacks,
        )
        if self.ev_cb:
            try:
                self.ev_cb(event)
            except Exception:  # pragma: no cover - best effort logging
                LOGGER.exception("Playback event callback raised an exception")
