"""Audio playback helpers that mimic the behaviour of ``qplayvid.c``.

The original C implementation streams PCM data to OpenLase through a
multi-producer/multi-consumer ring buffer where the JACK audio callback acts as
the master clock.  The Python port follows the same strategy: decoded samples
are annotated with monotonically increasing ``pts`` values and a ``seekid`` so
that the callback can discard stale data and advance the video pipeline in
lockstep with the audio timeline.  The implementation details are documented in
``docs/qplayvid_pyplayvid_spec.md`` and the module level docstring mirrors the
key responsibilities:

* guard a static ``numpy``-backed playback mode for tests while defaulting to a
  streaming, threaded mode for normal playback;
* maintain per-sample ``pts`` and ``seekid`` metadata so that the player can
  recover after seeks and pause/resume cycles without introducing drift;
* expose the realtime audio callback that OpenLase invokes, ensuring that the
  logic remains lightweight and free from blocking operations.

This file is part of OpenLase - a realtime laser graphics toolkit.

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

import contextlib
import os
import threading
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple, Union

import av
import numpy as np
import pylase as ol

from .settings import AUDIO_BUF
from .utils import LOGGER

__all__ = [
    "AudioPlayer",
    "PlaybackClock",
    "audio_diagnostics_enabled",
    "set_audio_diagnostics_enabled",
]


@dataclass
class PlaybackClock:
    """Snapshot of the audio callback clock used by :class:`PlayerCtx`.

    The player polls ``PlaybackClock`` instances to decide whether decoded video
    frames are still aligned with the audio timeline.  The fields mirror the
    information that ``qplayvid.c`` pushes through ``get_audio``: the last
    ``pts`` presented to the backend, the ``next_pts`` that would be emitted if
    more samples were requested, and the ``seekid`` that marks the logical
    playback epoch.  ``started``, ``paused`` and ``finished`` are helpers to
    simplify state transitions inside the display loop.
    """

    pts: float
    next_pts: float
    seekid: int
    started: bool
    paused: bool
    finished: bool


def _env_flag(name: str, default: bool = False) -> bool:
    """Return ``True`` when the environment flag is set to a truthy value.

    A small helper that mirrors the feature toggles described in the
    specification.  It accepts classic truthy/falsey strings so that environment
    variables such as ``PYPLAYVID_AUDIO_CHECKS=1`` or ``=false`` behave as
    expected.
    """

    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"", "0", "false", "off", "no"}


#: Whether the optional, and comparatively expensive, runtime diagnostics should
#: be executed for every buffer operation. The flag is initialised from the
#: ``PYPLAYVID_AUDIO_CHECKS`` environment variable so power users can enable it
#: without touching the code base.
_AUDIO_DIAGNOSTICS_ENABLED = _env_flag("PYPLAYVID_AUDIO_CHECKS", False)
print(f"Audio diagnostics enabled: {_AUDIO_DIAGNOSTICS_ENABLED}")

#: Minimum number of seconds between successive buffer-underflow log messages.
#: Derived from the ``PYPLAYVID_AUDIO_UNDERFLOW_INTERVAL`` environment variable
#: so deployments can throttle (or disable with ``0``) the chatter produced when
#: an audio backend is unstable.
_UNDERFLOW_LOG_INTERVAL = max(
    0.0, float(os.environ.get("PYPLAYVID_AUDIO_UNDERFLOW_INTERVAL", "1.0"))
)
print(f"Audio underrflow log interval: {_UNDERFLOW_LOG_INTERVAL} seconds")

def audio_diagnostics_enabled() -> bool:
    """Return whether the optional buffer integrity checks are enabled.

    ``qplayvid.c`` offers a similar runtime toggle that emits verbose logging
    whenever the audio ring invariants are breached.  The Python port keeps the
    checks disabled by default so that realtime performance is unaffected, but
    they can be activated via the ``PYPLAYVID_AUDIO_CHECKS`` environment variable
    or :func:`set_audio_diagnostics_enabled`.
    """

    return _AUDIO_DIAGNOSTICS_ENABLED


def set_audio_diagnostics_enabled(enabled: bool) -> None:
    """Toggle the optional audio integrity checks at runtime."""

    global _AUDIO_DIAGNOSTICS_ENABLED
    _AUDIO_DIAGNOSTICS_ENABLED = bool(enabled)


class AudioPlayer:
    """Stream audio samples to OpenLase using a ring buffer.

    The player exposes the same lifecycle that ``qplayvid.c`` provides: a
    decoder thread fills a bounded buffer while the OpenLase audio callback
    consumes samples and drives the global playback clock.  Each sample carries
    the ``seekid`` so that seeks immediately invalidate stale data and the
    display loop can catch up by dropping mismatched frames.  The implementation
    mirrors the behaviour described in :mod:`docs.qplayvid_pyplayvid_spec`.

    Parameters
    ----------
    source:
        Either a path to a media file (streaming mode) or a stereo ``numpy``
        array of preloaded samples (static mode).
    sample_rate:
        The output sampling rate expected by OpenLase/JACK.
    stream_index:
        Optional positional index of the audio stream to decode.  Required when
        streaming from files so that the correct FFmpeg stream is selected.
    """

    _STATIC_MODE = "static"
    _STREAMING_MODE = "streaming"

    def __init__(
        self,
        source: Union[np.ndarray, str, Path],
        sample_rate: int,
        *,
        stream_index: Optional[int] = 0,
    ) -> None:
        """Create the audio pipeline and choose between static/streaming modes.

        ``numpy`` arrays trigger a minimal, single-threaded playback path that is
        mainly used by tests.  When a file path is provided the class spawns a
        decoder thread that closely follows ``decode_audio`` from the C
        implementation: the thread demuxes packets, resamples them and writes the
        resulting PCM frames into the ring buffer while tracking ``seekid`` and
        presentation timestamps.
        """

        self._mode = self._STATIC_MODE
        self._loop = False
        self._started = False
        self._paused = False
        self._finished = False
        self._lock = threading.Lock()
        self._cond = threading.Condition()
        self._stop_event = threading.Event()
        self._decoder_thread: Optional[threading.Thread] = None
        self._underflow_count = 0
        self._last_underflow_log = float("-inf")
        self._seekid = 0
        self._playback_pts = 0.0
        self._last_audio_pts = -1.0
        self._playback_seekid = 0
        self._last_callback_count = 0

        if isinstance(source, np.ndarray):
            self._init_static_mode(source, sample_rate)
        else:
            self._init_streaming_mode(Path(source), sample_rate, stream_index)

    # ------------------------------------------------------------------
    # Static mode (legacy behaviour, used by tests and fallbacks)
    # ------------------------------------------------------------------
    def _init_static_mode(self, samples: np.ndarray, sample_rate: int) -> None:
        """Prepare the legacy single-buffer playback path.

        Unlike the streaming path this variant simply keeps the whole track in
        memory and rewinds the cursor on loop.  It is intentionally simple so
        unit tests can run without PyAV or JACK present, but the return values of
        :meth:`_callback` still follow the same ``pts`` and ``seekid`` semantics
        as the real decoder.
        """

        self._mode = self._STATIC_MODE
        self._sample_rate = sample_rate
        self._samples = self._prepare_samples(samples)
        self._position = 0
        self._seekid = 0
        self._playback_pts = 0.0
        self._last_audio_pts = -1.0
        self._playback_seekid = 0
        self._last_callback_count = 0

    @staticmethod
    def _prepare_samples(samples: np.ndarray) -> np.ndarray:
        """Normalise arbitrary sample shapes to a contiguous stereo buffer."""

        array = np.asarray(samples, dtype=np.float32)

        if array.ndim == 0:
            array = array.reshape(1, 1)
        elif array.ndim == 1:
            array = array.reshape(-1, 1)
        elif array.ndim > 2:
            array = array.reshape(array.shape[0], -1)

        if array.size == 0:
            return np.zeros((0, 2), dtype=np.float32)

        channels = array.shape[1]
        if channels == 1:
            array = np.repeat(array, 2, axis=1)
        elif channels >= 2:
            array = array[:, :2]
        else:
            array = np.zeros((array.shape[0], 2), dtype=np.float32)

        return np.ascontiguousarray(array, dtype=np.float32)

    # ------------------------------------------------------------------
    # Streaming mode (mirrors the qplayvid.c buffering strategy)
    # ------------------------------------------------------------------
    def _init_streaming_mode(
        self, source: Path, sample_rate: int, stream_index: Optional[int]
    ) -> None:
        """Allocate ring buffer structures and probe the media source."""

        if stream_index is None:
            raise RuntimeError("Audio stream index required for streaming playback")

        self._mode = self._STREAMING_MODE
        self._source = source
        self._stream_index = int(stream_index)
        self._sample_rate = sample_rate

        self._container: Optional[av.container.InputContainer] = None
        self._audio_stream: Optional[av.stream.Stream] = None
        self._resampler: Optional[av.AudioResampler] = None
        self._demuxer: Optional[Iterator[av.packet.Packet]] = None

        self._pending_seek: Optional[float] = None
        self._seekid = 0

        self._capacity = max(AUDIO_BUF * self._sample_rate, self._sample_rate)
        self._samples = np.zeros((self._capacity, 2), dtype=np.float32)
        self._pts = np.zeros(self._capacity, dtype=np.float64)
        self._seekids = np.zeros(self._capacity, dtype=np.int64)
        self._write_index = 0
        self._read_index = 0
        self._count = 0
        self._current_pts = 0.0
        self._playback_pts = 0.0
        self._finished = False
        self._eof = False
        self._last_audio_pts = -1.0
        self._playback_seekid = self._seekid
        self._last_callback_count = 0

        pyav_major = int(av.__version__.split(".", 1)[0])
        self._need_pyav15_bug_fix = pyav_major < 16

        self._open_source()

    def _check_ring_buffer_locked(self, context: str) -> None:
        """Validate ring buffer invariants when diagnostics are enabled."""

        if not audio_diagnostics_enabled():
            return
        capacity = getattr(self, "_capacity", 0)
        if capacity <= 0:
            return
        problems = []
        if not 0 <= self._read_index < capacity:
            problems.append(f"read_index={self._read_index} outside [0,{capacity})")
        if not 0 <= self._write_index < capacity:
            problems.append(f"write_index={self._write_index} outside [0,{capacity})")
        if not 0 <= self._count <= capacity:
            problems.append(f"count={self._count} outside [0,{capacity}]")
        if hasattr(self, "_samples") and getattr(self._samples, "shape", (0,))[0] < capacity:
            problems.append("samples buffer smaller than capacity")
        if hasattr(self, "_pts") and getattr(self._pts, "shape", (0,))[0] < capacity:
            problems.append("pts buffer smaller than capacity")
        if hasattr(self, "_seekids") and getattr(self._seekids, "shape", (0,))[0] < capacity:
            problems.append("seekids buffer smaller than capacity")
        expected = (self._write_index - self._read_index) % capacity
        if expected != (self._count % capacity):
            problems.append(
                "write/read index difference does not match count"
            )
        if problems:
            message = "; ".join(problems)
            LOGGER.error(
                "Audio ring buffer invariant violation during %s: %s",
                context,
                message,
            )
            raise AssertionError(message)

    def _open_source(self) -> None:
        """Open the PyAV container and prime decoder state."""

        try:
            self._container = av.open(str(self._source))
        except av.error.FFmpegError as exc:  # pragma: no cover - diagnostic path
            raise RuntimeError(f"Unable to open audio source: {self._source}") from exc

        audio_streams = [stream for stream in self._container.streams if stream.type == "audio"]
        if not audio_streams:
            raise RuntimeError(f"No audio streams found in {self._source}")

        index = self._stream_index
        if index < 0:
            LOGGER.warning("Audio stream index %d is invalid; defaulting to the first stream", index)
            index = 0
        if index >= len(audio_streams):
            LOGGER.warning(
                "Audio stream index %d is out of range for %s; using the first stream",
                index,
                self._source,
            )
            index = 0
        self._stream_index = index

        self._audio_stream = audio_streams[index]
        self._audio_stream.thread_type = "AUTO"

        codec_ctx = getattr(self._audio_stream, "codec_context", None)
        input_rate = getattr(self._audio_stream, "rate", None) or (codec_ctx.sample_rate if codec_ctx else None)
        if not input_rate:
            input_rate = self._sample_rate

        LOGGER.info("Audio input sampling rate: %d", input_rate)
        LOGGER.info("Audio output sampling rate (JACK): %d", self._sample_rate)

        self._resampler = av.AudioResampler(
            format="s16",
            layout="stereo",
            rate=self._sample_rate,
        )
        LOGGER.info(
            "Initialised PyAV resampler: input=%s/%sHz output=%s/%dHz",
            getattr(codec_ctx, "format", "unknown"),
            input_rate,
            "s16",
            self._sample_rate,
        )

        self._demuxer = self._container.demux(self._audio_stream)

        with self._cond:
            self._reset_buffers_locked()
            self._current_pts = 0.0
            self._playback_pts = 0.0
            self._finished = False
            self._eof = False
            self._cond.notify_all()

        LOGGER.info(
            "Audio buffer size: %d samples = (AUDIO_BUF=%d) * %d",
            self._capacity,
            AUDIO_BUF,
            self._sample_rate,
        )

    def _close_source(self) -> None:
        """Dispose of PyAV resources and reset decoder handles."""

        if self._container is not None:
            with contextlib.suppress(Exception):
                self._container.close()
        self._container = None
        self._audio_stream = None
        self._demuxer = None
        self._resampler = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def attach(self) -> None:
        """Register the audio callback with OpenLase."""

        ol.setAudioCallback(self._callback)

    def detach(self) -> None:
        """Unregister the callback and stop the decoder thread if required."""

        ol.setAudioCallback(None)
        if self._mode == self._STREAMING_MODE:
            self._stop_decoder_thread()

    def start(self, loop: bool) -> None:
        """Start playback and optionally enable seamless looping."""

        if self._mode == self._STATIC_MODE:
            with self._lock:
                self._loop = loop
                if not self._started or self._finished:
                    self._position = 0
                self._started = True
                self._paused = False
                self._finished = False
            return

        with self._cond:
            self._loop = loop
            self._stop_event.clear()
            self._started = True
            self._paused = False
            self._finished = False
            if self._pending_seek is None:
                self._pending_seek = 0.0
            self._cond.notify_all()
        self._ensure_decoder_thread()

    def resume(self) -> None:
        """Resume playback after :meth:`pause` without resetting buffers."""

        if self._mode == self._STATIC_MODE:
            with self._lock:
                if self._started:
                    self._paused = False
            return

        with self._cond:
            if self._started:
                self._paused = False
                self._finished = False
                self._cond.notify_all()

    def pause(self) -> None:
        """Pause playback while keeping the buffered data intact."""

        if self._mode == self._STATIC_MODE:
            with self._lock:
                if self._started:
                    self._paused = True
            return

        with self._cond:
            if self._started:
                self._paused = True
                self._cond.notify_all()

    def stop(self) -> None:
        """Stop playback and clear buffered state."""

        if self._mode == self._STATIC_MODE:
            with self._lock:
                self._started = False
                self._paused = False
                self._finished = False
                self._position = 0
            return

        with self._cond:
            self._started = False
            self._paused = False
            self._finished = False
            self._loop = False
            self._reset_buffers_locked()
            self._cond.notify_all()

    def seek(self, position: float) -> None:
        """Seek to ``position`` seconds from the start of the track."""

        if self._mode == self._STATIC_MODE:
            with self._lock:
                if self._samples.size == 0:
                    self._position = 0
                    self._finished = False
                    return
                frame = int(max(0.0, position) * self._sample_rate)
                frame = min(frame, self._samples.shape[0])
                self._position = frame
                self._finished = False
            return

        with self._cond:
            self._pending_seek = max(0.0, position)
            self._finished = False
            self._cond.notify_all()

    def has_finished(self) -> bool:
        """Return ``True`` when playback reached EOF and buffers drained."""

        if self._mode == self._STATIC_MODE:
            with self._lock:
                return self._finished

        with self._cond:
            return self._finished and self._count == 0

    # ------------------------------------------------------------------
    # Streaming internals
    # ------------------------------------------------------------------
    def _ensure_decoder_thread(self) -> None:
        """Spawn the decoder thread if streaming mode requires it."""

        if self._mode != self._STREAMING_MODE:
            return
        if self._decoder_thread and self._decoder_thread.is_alive():
            return
        self._stop_event.clear()
        self._decoder_thread = threading.Thread(
            target=self._decoder_loop,
            name="AudioDecoder",
            daemon=True,
        )
        self._decoder_thread.start()

    def _stop_decoder_thread(self) -> None:
        """Signal the decoder thread to terminate and join it."""

        if self._mode != self._STREAMING_MODE:
            return
        if not self._decoder_thread:
            return
        self._stop_event.set()
        with self._cond:
            self._cond.notify_all()
        self._decoder_thread.join(timeout=1.0)
        self._decoder_thread = None
        self._close_source()

    def _decoder_loop(self) -> None:
        """Continuously feed the ring buffer according to playback state."""

        LOGGER.debug("Audio decoder thread started")
        try:
            while not self._stop_event.is_set():
                target_seek: Optional[float] = None
                with self._cond:
                    while not self._stop_event.is_set():
                        if self._pending_seek is not None:
                            target_seek = self._pending_seek
                            self._pending_seek = None
                            break
                        if not self._started:
                            self._cond.wait()
                            continue
                        if self._paused:
                            self._cond.wait()
                            continue
                        if self._count >= self._capacity:
                            self._cond.wait()
                            continue
                        break

                if self._stop_event.is_set():
                    break

                if target_seek is not None:
                    self._perform_seek(target_seek)
                    continue

                try:
                    chunk = self._decode_chunk()
                except Exception:  # pragma: no cover - defensive logging
                    LOGGER.exception("Audio decoder encountered an error; resetting stream")
                    with self._cond:
                        self._pending_seek = 0.0
                        self._cond.notify_all()
                    continue

                if chunk is None:
                    with self._cond:
                        self._finished = True
                        self._eof = True
                        self._cond.notify_all()
                    if self._loop and not self._stop_event.is_set():
                        with self._cond:
                            self._pending_seek = 0.0
                            self._finished = False
                            self._eof = False
                            self._cond.notify_all()
                        continue
                    with self._cond:
                        while (
                            not self._stop_event.is_set()
                            and self._pending_seek is None
                            and self._started
                            and not self._loop
                        ):
                            self._cond.wait()
                    continue

                samples, start_pts = chunk
                self._write_samples(samples, start_pts)
        finally:
            LOGGER.debug("Audio decoder thread exiting")

    def _perform_seek(self, position: float) -> None:
        """Reset the decoder and move to ``position`` seconds in the stream."""

        try:
            self._close_source()
            self._open_source()
        except RuntimeError as exc:
            LOGGER.warning("Failed to reset audio decoder: %s", exc)
            return
        if self._container and self._audio_stream:
            time_base = getattr(self._audio_stream, "time_base", None)
            if time_base is None or not time_base:
                sample_rate = getattr(self._audio_stream, "rate", None) or self._sample_rate
                seek_time_base = 1.0 / max(sample_rate, 1)
            else:
                seek_time_base = float(time_base)
            timestamp = int(max(0.0, position) / seek_time_base)
            with contextlib.suppress(av.error.FFmpegError):
                self._container.seek(timestamp, stream=self._audio_stream)
            self._demuxer = self._container.demux(self._audio_stream)

        with self._cond:
            self._reset_buffers_locked()
            self._current_pts = position
            self._playback_pts = position
            self._seekid += 1
            self._playback_seekid = self._seekid
            self._finished = False
            self._eof = False
            self._cond.notify_all()

    def _decode_chunk(self) -> Optional[Tuple[np.ndarray, float]]:
        """Decode the next block of PCM samples and return them with a PTS."""

        if not self._demuxer or not self._resampler or not self._audio_stream:
            return None
        try:
            while True:
                packet = next(self._demuxer)
                if packet.stream != self._audio_stream:
                    continue
                packet_pts = self._packet_pts(packet)
                if packet_pts is not None:
                    self._current_pts = packet_pts
                frames = packet.decode()
                if not frames:
                    continue
                for frame in frames:
                    frame_pts = self._frame_pts(frame)
                    if frame_pts is not None:
                        self._current_pts = frame_pts
                    converted = self._resampler.resample(frame)
                    for out_frame in converted:
                        data = self._convert_frame(out_frame)
                        if data.size == 0:
                            continue
                        start_pts = self._current_pts
                        self._current_pts += data.shape[0] / float(self._sample_rate)
                        return data, start_pts
        except StopIteration:
            return None

    def FIXED_decode_chunk(self) -> Optional[Tuple[np.ndarray, float]]:
        """Experimental alternative decoder that reconstructs missing PTS."""

        if not self._demuxer or not self._resampler or not self._audio_stream:
            return None
        try:
            while True:
                packet = next(self._demuxer)
                if packet.stream != self._audio_stream:
                    continue

                # パケット PTS があれば更新
                packet_pts = self._packet_pts(packet)
                if packet_pts is not None:
                    self._current_pts = packet_pts

                frames = packet.decode()
                if not frames:
                    continue

                for frame in frames:
                    # --- PCM 対応の PTS 補完 ---
                    if frame.pts is None or frame.time_base is None:
                        # PTS が無ければ自前でカウント
                        frame_pts = self._current_pts
                    else:
                        frame_pts = float(frame.pts * float(frame.time_base))

                    converted = self._resampler.resample(frame)
                    for out_frame in converted:
                        data = self._convert_frame(out_frame)
                        if data.size == 0:
                            continue
                        start_pts = frame_pts
                        # サンプル数で PTS を積算
                        self._current_pts = frame_pts + data.shape[0] / float(self._sample_rate)
                        return data, start_pts
        except StopIteration:
            return None

    @staticmethod
    def _frame_pts(frame: av.AudioFrame) -> Optional[float]:  # type: ignore[name-defined]
        """Return the presentation timestamp for a decoded frame, if available."""

        if frame.pts is None:
            return None
        time_base = getattr(frame, "time_base", None)
        if time_base is None:
            return None
        return float(frame.pts * float(time_base))

    def _packet_pts(self, packet: av.packet.Packet) -> Optional[float]:  # type: ignore[name-defined]
        """Return a best-effort PTS for ``packet``."""

        if packet.pts is None:
            return None
        time_base = getattr(packet, "time_base", None)
        if time_base is not None:
            return float(packet.pts * float(time_base))
        if self._audio_stream and self._audio_stream.time_base:
            return float(packet.pts * float(self._audio_stream.time_base))
        return None

    @staticmethod
    def _ensure_stereo(samples: np.ndarray) -> np.ndarray:
        """Guarantee that ``samples`` has two channels."""

        if samples.shape[1] == 1:
            return np.repeat(samples, 2, axis=1)
        if samples.shape[1] > 2:
            return samples[:, :2]
        return samples

    def _fix_pyav15_bug(self, data: np.ndarray) -> np.ndarray:
        """Work around PyAV 15's planar stereo flattening bug."""

        """Workaround for PyAV 15 stereo flatten bug (removed in >=16).
        [[L0, R0, L1, R1, L2, R2, ...]] -> [[L0, R0], [L1, R1], [L2, R2], ...]
        """
        if data.ndim == 2 and data.shape[0] == 1 and data.shape[1] > 2:
            ns = data.shape[1] // 2
            return data.reshape(ns, 2)
        return data

    def _convert_frame(self, frame: av.AudioFrame) -> np.ndarray:  # type: ignore[name-defined]
        """Convert a PyAV frame to a contiguous stereo float buffer."""

        data = frame.to_ndarray()
        if data.ndim == 1:
            data = data.reshape(1, -1)

        if self._need_pyav15_bug_fix:
            data = self._fix_pyav15_bug(data)

        data = self._ensure_stereo(data)
        integer_input = np.issubdtype(data.dtype, np.integer)
        data = np.ascontiguousarray(data, dtype=np.float32)
        if integer_input:
            data /= 32768.0
        return data

    def _reset_buffers_locked(self) -> None:
        """Clear buffered samples and restore ring indices."""

        self._write_index = 0
        self._read_index = 0
        self._count = 0
        self._playback_pts = 0.0
        self._current_pts = 0.0
        self._last_audio_pts = -1.0
        self._playback_seekid = self._seekid
        self._check_ring_buffer_locked("reset")

    def _write_samples(self, samples: np.ndarray, start_pts: float) -> None:
        """Copy ``samples`` into the ring buffer while updating metadata."""

        total = samples.shape[0]
        index = 0
        pts = start_pts
        self._check_ring_buffer_locked("write_start")
        while index < total and not self._stop_event.is_set():
            with self._cond:
                self._check_ring_buffer_locked("write_wait")
                while (
                    not self._stop_event.is_set()
                    and (self._count >= self._capacity or not self._started or self._paused)
                ):
                    self._cond.wait()
                if self._stop_event.is_set():
                    return
                space = self._capacity - self._count
                if space <= 0:
                    continue
                take = min(space, total - index)
                end = self._write_index + take
                pts_segment = pts + np.arange(take, dtype=np.float64) / float(self._sample_rate)
                if end <= self._capacity:
                    self._samples[self._write_index:end] = samples[index : index + take]
                    self._pts[self._write_index:end] = pts_segment
                    self._seekids[self._write_index:end] = self._seekid
                else:
                    first = self._capacity - self._write_index
                    self._samples[self._write_index:] = samples[index : index + first]
                    self._pts[self._write_index:] = pts_segment[:first]
                    self._seekids[self._write_index:] = self._seekid
                    second = take - first
                    if second > 0:
                        self._samples[:second] = samples[index + first : index + take]
                        self._pts[:second] = pts_segment[first:]
                        self._seekids[:second] = self._seekid
                self._write_index = (self._write_index + take) % self._capacity
                self._count += take
                self._current_pts = pts + take / float(self._sample_rate)
                self._finished = False
                self._eof = False
                self._cond.notify_all()
                self._check_ring_buffer_locked("write_after")
            index += take
            pts += take / float(self._sample_rate)
        self._check_ring_buffer_locked("write_end")

    def _read_samples_locked(self, count: int) -> Tuple[np.ndarray, int, Optional[float], Optional[int]]:
        """Read up to ``count`` samples from the ring while holding ``_cond``."""

        if count <= 0:
            return np.zeros((0, 2), dtype=np.float32), 0, None, None
        pieces = []
        remaining = count
        produced_total = 0
        last_pts: Optional[float] = None
        last_seekid: Optional[int] = None
        self._check_ring_buffer_locked("read_start")
        while remaining > 0 and self._count > 0:
            self._check_ring_buffer_locked("read_loop_before")
            take = min(remaining, self._count)
            end = self._read_index + take
            if end <= self._capacity:
                chunk = self._samples[self._read_index:end]
                pts_chunk = self._pts[self._read_index:end]
                seekid_chunk = self._seekids[self._read_index:end]
            else:
                first = self._capacity - self._read_index
                chunk = np.vstack(
                    (
                        self._samples[self._read_index:],
                        self._samples[: end % self._capacity],
                    )
                )
                pts_chunk = np.concatenate(
                    (
                        self._pts[self._read_index:],
                        self._pts[: end % self._capacity],
                    )
                )
                seekid_chunk = np.concatenate(
                    (
                        self._seekids[self._read_index:],
                        self._seekids[: end % self._capacity],
                    )
                )
            self._read_index = end % self._capacity
            self._count -= take
            if pts_chunk.size:
                last_pts = float(pts_chunk[-1])
                self._playback_pts = last_pts + 1.0 / float(self._sample_rate)
            if seekid_chunk.size:
                last_seekid = int(seekid_chunk[-1])
            pieces.append(chunk)
            remaining -= take
            produced_total += take
            self._check_ring_buffer_locked("read_loop_after")
        if not pieces:
            return np.zeros((0, 2), dtype=np.float32), 0, None, None
        self._cond.notify_all()
        self._check_ring_buffer_locked("read_end")
        return np.concatenate(pieces, axis=0), produced_total, last_pts, last_seekid

    def _log_buffer_underrun(self, requested: int, produced: int) -> None:
        """Emit a throttled warning when the audio callback underflows."""

        now = time.monotonic()
        self._underflow_count += 1
        if now - self._last_underflow_log < _UNDERFLOW_LOG_INTERVAL:
            return
        self._last_underflow_log = now
        LOGGER.warning(
            "Audio buffer underrun (%d total): requested=%d produced=%d count=%d paused=%s finished=%s",
            self._underflow_count,
            requested,
            produced,
            self._count,
            self._paused,
            self._finished,
        )

    # ------------------------------------------------------------------
    # Audio callback
    # ------------------------------------------------------------------
    def _callback(self, samples: int) -> List[Tuple[float, float]]:
        """Realtime audio callback registered with OpenLase."""

        if self._mode == self._STATIC_MODE:
            with self._lock:
                if not self._started or self._paused or self._samples.size == 0:
                    return []

                total = self._samples.shape[0]
                remaining = samples
                chunks: List[np.ndarray] = []

                while remaining > 0:
                    if self._position >= total:
                        if self._loop and total > 0:
                            self._position = 0
                            self._finished = False
                        else:
                            self._finished = True
                            break
                    take = min(remaining, max(0, total - self._position))
                    if take <= 0:
                        break
                    chunk = self._samples[self._position : self._position + take]
                    chunks.append(chunk)
                    self._position += take
                    remaining -= take

                if not chunks:
                    return []

                merged = np.concatenate(chunks, axis=0)
                produced = merged.shape[0]
                if produced > 0:
                    if self._sample_rate:
                        self._playback_pts = self._position / float(self._sample_rate)
                        self._last_audio_pts = (self._position - 1) / float(self._sample_rate)
                    else:
                        self._playback_pts = 0.0
                        self._last_audio_pts = -1.0
                    self._playback_seekid = self._seekid
                    self._last_callback_count = produced
                return [tuple(sample) for sample in merged.tolist()]

        with self._cond:
            if not self._started:
                return [(0.0, 0.0)] * samples
            if self._paused:
                return [(0.0, 0.0)] * samples

            while (
                not self._stop_event.is_set()
                and self._started
                and not self._paused
                and self._count == 0
                and not self._finished
            ):
                self._cond.wait()

            data, produced, last_pts, last_seekid = self._read_samples_locked(samples)
            if produced < samples:
                self._log_buffer_underrun(samples, produced)
                if produced == 0:
                    return [(0.0, 0.0)] * samples
                padding = np.zeros((samples - produced, 2), dtype=np.float32)
                data = np.concatenate([data, padding], axis=0)

            if produced > 0:
                if last_pts is not None:
                    self._last_audio_pts = last_pts
                else:
                    self._last_audio_pts = self._playback_pts - 1.0 / float(self._sample_rate)
                if last_seekid is not None:
                    self._playback_seekid = last_seekid
                self._last_callback_count = produced

            return [tuple(map(float, row)) for row in data.tolist()]

    def get_playback_clock(self) -> Optional[PlaybackClock]:
        """Expose the current audio playback position for synchronisation."""

        if self._mode == self._STATIC_MODE:
            with self._lock:
                if not self._started:
                    return None
                last_pts = self._last_audio_pts
                if self._position > 0 and last_pts < 0:
                    last_pts = (self._position - 1) / float(self._sample_rate)
                next_pts = self._position / float(self._sample_rate)
                return PlaybackClock(
                    pts=last_pts,
                    next_pts=next_pts,
                    seekid=self._seekid,
                    started=self._started,
                    paused=self._paused,
                    finished=self._finished,
                )

        with self._cond:
            if not self._started:
                return None
            return PlaybackClock(
                pts=self._last_audio_pts,
                next_pts=self._playback_pts,
                seekid=self._playback_seekid,
                started=self._started,
                paused=self._paused,
                finished=self._finished,
            )
