"""Video decoding backends used by :mod:`pylase.qplayvid`.

The spec in ``docs/qplayvid_pyplayvid_spec.md`` defines a small abstraction layer for video sources.  The Python port exposes two implementations that share the :class:`VideoSource` protocol so the player can swap them transparently.  ``PyAVVideoSource`` decodes frames in-process while ``FFmpegVideoSource`` delegates to an external ``ffmpeg`` process; both attach ``seekid`` metadata and perform the housekeeping described in the specification.

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

import subprocess
import threading
from fractions import Fraction
from typing import IO, Iterator, Optional, Protocol, Tuple

import av
import numpy as np

from .utils import LOGGER

__all__ = [
    "DecodedVideoFrame",
    "VideoSource",
    "NullVideoSource",
    "PyAVVideoSource",
    "FFmpegVideoFrame",
    "FFmpegVideoSource",
    "find_media_streams",
    "open_video_source",
    "detect_frame_geometry",
]


class DecodedVideoFrame(Protocol):
    """Subset of the ``av.VideoFrame`` API required by the player."""

    pts: Optional[int]
    time: Optional[float]
    time_base: Optional[Fraction]

    def to_ndarray(self, format: str = "bgr24") -> np.ndarray:  # pragma: no cover - typing helper
        """Return the decoded frame as a ``numpy.ndarray``."""

        ...


class VideoSource(Protocol):
    """Common interface implemented by PyAV and ffmpeg-backed sources."""

    width: int
    height: int
    fps: float
    duration: float
    frame_count: int
    time_base: Fraction

    def read_frame(self) -> Optional[DecodedVideoFrame]:
        """Return the next decoded frame or ``None`` at EOF."""

        ...

    def seek(self, position: float) -> None:
        """Seek to ``position`` seconds from the start of the media."""

        ...

    def rewind(self) -> None:
        """Reset the stream to the beginning."""

        ...

    def close(self) -> None:
        """Release any resources held by the source."""

        ...


class NullVideoSource:
    """Sentinel source used when no video streams are available."""

    def __init__(self) -> None:
        """Initialise an empty placeholder source."""

        self.width = 0
        self.height = 0
        self.fps = 0.0
        self.duration = 0.0
        self.frame_count = 0
        self.time_base = Fraction(0, 1)

    def read_frame(self) -> Optional[DecodedVideoFrame]:
        """Always return ``None`` to signal the absence of video."""

        return None

    def seek(self, position: float) -> None:
        """No-op seek implementation for the null source."""

        return None

    def rewind(self) -> None:
        """No-op rewind implementation for the null source."""

        return None

    def close(self) -> None:
        """No-op cleanup for the null source."""

        return None


def find_media_streams(
    container: av.container.InputContainer,
) -> Tuple[
    Optional[av.stream.Stream],
    Optional[av.stream.Stream],
    Optional[int],
]:
    """Return the first video/audio streams and the positional audio index."""

    video_stream: Optional[av.stream.Stream] = None
    audio_stream: Optional[av.stream.Stream] = None
    audio_index: Optional[int] = None
    audio_position = 0

    for stream in container.streams:
        if stream.type == "audio":
            if audio_stream is None:
                audio_stream = stream
                audio_index = audio_position
            audio_position += 1
        elif stream.type == "video" and video_stream is None:
            video_stream = stream
        if video_stream is not None and audio_stream is not None:
            break

    LOGGER.debug(
        "Media probe results: video=%s audio=%s audio_index=%s",
        getattr(video_stream, "index", None),
        getattr(audio_stream, "index", None),
        audio_index,
    )

    return video_stream, audio_stream, audio_index


class PyAVVideoSource:
    """Thin wrapper around ``av.open`` that exposes convenience helpers."""

    def __init__(self, source: str) -> None:
        """Open ``source`` and probe stream metadata via PyAV."""

        self.source = source
        self._container: Optional[av.container.input.InputContainer] = None
        self._stream: Optional[av.stream.Stream] = None
        self._decoder: Optional[Iterator[av.VideoFrame]] = None
        self.width: int = 0
        self.height: int = 0
        self.fps: float = 0.0
        self.duration: float = 0.0
        self.frame_count: int = 0
        self.time_base: Fraction = Fraction(0, 1)
        LOGGER.info("Opening video source via PyAV: %s", source)
        self._open_container()

    def _open_container(self) -> None:
        """(Re)open the container and select the first video stream."""

        if self._container is not None:
            try:
                self._container.close()
            except av.error.FFmpegError:  # pragma: no cover - best effort cleanup
                LOGGER.warning("Failed to close existing container cleanly")
        try:
            container = av.open(self.source)
        except av.error.FFmpegError as exc:
            raise RuntimeError(f"Unable to open video source: {self.source}") from exc

        video_stream, _audio_stream, _ = find_media_streams(container)
        if video_stream is None:
            LOGGER.error("No video streams found in %s; disabling video playback", self.source)
            self._container = container
            self._stream = None
            self._decoder = iter(())
            self._update_metadata()
            return

        video_stream.thread_type = "AUTO"

        self._container = container
        self._stream = video_stream
        self._reset_decoder()
        self._update_metadata()
        LOGGER.debug(
            "PyAV container opened: stream=%s (%dx%d @ %.3f FPS)",
            getattr(video_stream, "index", None),
            self.width,
            self.height,
            self.fps,
        )

    def _reset_decoder(self) -> None:
        """Reset the decoder iterator after seeks or reopen events."""

        if self._container is None or self._stream is None:
            self._decoder = iter(())
            return
        self._decoder = iter(self._container.decode(self._stream))

    def _update_metadata(self) -> None:
        """Refresh cached geometry and timing information."""

        container = self._container
        if container is None:
            self.width = 0
            self.height = 0
            self.fps = 0.0
            self.duration = 0.0
            self.frame_count = 0
            self.time_base = Fraction(0, 1)
            return

        stream = self._stream
        if stream is None:
            self.width = 0
            self.height = 0
            self.fps = 0.0
            if container.duration:
                self.duration = float(container.duration * av.time_base)
            else:
                self.duration = 0.0
            self.frame_count = 0
            self.time_base = Fraction(0, 1)
            return

        codec_ctx = getattr(stream, "codec_context", None)
        width = int(getattr(stream, "width", 0) or (getattr(codec_ctx, "width", 0) if codec_ctx else 0))
        height = int(getattr(stream, "height", 0) or (getattr(codec_ctx, "height", 0) if codec_ctx else 0))

        if (width <= 0 or height <= 0) and self._decoder is not None:
            try:
                first_frame = next(self._decoder)
            except StopIteration:
                raise RuntimeError("Unable to decode a frame to detect geometry")
            width = int(getattr(first_frame, "width", 0))
            height = int(getattr(first_frame, "height", 0))
            # Reset decoder to the start so we do not drop the prefetched frame.
            try:
                if stream.time_base:
                    offset = 0
                    container.seek(offset, any_frame=False, stream=stream)
                else:
                    container.seek(0)
            except av.error.FFmpegError:
                LOGGER.warning("Failed to rewind container after geometry probe; reopening")
                self._open_container()
                return
            else:
                self._reset_decoder()

        self.width = max(1, width)
        self.height = max(1, height)

        fps = 0.0
        if stream.average_rate:
            try:
                fps = float(stream.average_rate)
            except ZeroDivisionError:
                fps = 0.0
        if fps <= 0 and codec_ctx and getattr(codec_ctx, "framerate", None):
            try:
                fps = float(codec_ctx.framerate)
            except ZeroDivisionError:
                fps = 0.0
        if fps <= 0 and stream.base_rate:
            try:
                fps = float(stream.base_rate)
            except ZeroDivisionError:
                fps = 0.0
        if fps <= 0:
            fps = 30.0
        self.fps = fps

        if stream.time_base:
            self.time_base = Fraction(stream.time_base)
        else:
            denominator = max(1, int(round(self.fps)))
            self.time_base = Fraction(1, denominator)

        if stream.duration and stream.time_base:
            self.duration = float(stream.duration * stream.time_base)
        elif container.duration:
            self.duration = float(container.duration * av.time_base)
        elif stream.frames and self.fps > 0:
            self.duration = float(stream.frames / self.fps)
        else:
            self.duration = 0.0

        self.frame_count = int(getattr(stream, "frames", 0) or 0)

        LOGGER.debug(
            "PyAV metadata: size=%dx%d fps=%.3f duration=%.3fs frames=%d time_base=%s",
            self.width,
            self.height,
            self.fps,
            self.duration,
            self.frame_count,
            self.time_base,
        )

    def read_frame(self) -> Optional[av.VideoFrame]:
        """Return the next decoded PyAV frame, reopening the stream if needed."""

        if self._container is None:
            self._open_container()
        if self._stream is None:
            return None
        if self._decoder is None:
            self._reset_decoder()
        if self._decoder is None:
            return None
        try:
            frame = next(self._decoder)
            LOGGER.debug2(
                "Decoded video frame pts=%s time=%s", getattr(frame, "pts", None), getattr(frame, "time", None)
            )
            return frame
        except StopIteration:
            LOGGER.debug("PyAV video decoder reached EOF")
            return None

    def seek(self, position: float) -> None:
        """Seek the PyAV container to ``position`` seconds."""

        position = max(0.0, position)
        if self._container is None:
            self._open_container()
        if self._container is None or self._stream is None:
            return

        stream = self._stream
        LOGGER.debug("Seeking PyAV container to %.3fs", position)
        try:
            if stream.time_base:
                offset = int(position / float(stream.time_base))
                self._container.seek(offset, any_frame=False, backward=True, stream=stream)
            else:
                offset = int(position / float(av.time_base))
                self._container.seek(offset, any_frame=False)
        except av.error.FFmpegError:
            LOGGER.warning("Accurate seek failed; reopening container")
            self._open_container()
            if position > 0.0:
                try:
                    self.seek(position)
                except RecursionError:
                    LOGGER.error("Recursive seek detected; ignoring further retries")
            return

        self._reset_decoder()
        LOGGER.debug("Seek completed; decoder reset")

    def rewind(self) -> None:
        """Seek to the beginning of the stream."""

        LOGGER.debug("Rewinding PyAV source")
        self.seek(0.0)

    def close(self) -> None:
        """Close the PyAV container and reset cached state."""

        if self._container is not None:
            try:
                self._container.close()
            except av.error.FFmpegError:  # pragma: no cover - best effort cleanup
                LOGGER.warning("Failed to close video container cleanly")
        self._container = None
        self._stream = None
        self._decoder = None
        LOGGER.debug("PyAV video source closed")


class FFmpegVideoFrame:
    """Minimal frame wrapper that mimics the ``av.VideoFrame`` API surface."""

    __slots__ = ("width", "height", "pts", "time", "time_base", "_buffer")

    def __init__(self, width: int, height: int, buffer: bytes, pts_seconds: float, time_base: Fraction) -> None:
        """Store the raw BGR frame along with timestamp metadata."""

        self.width = width
        self.height = height
        self.time_base: Optional[Fraction] = time_base if float(time_base) > 0 else None
        if self.time_base is not None:
            tb = float(self.time_base)
            self.pts = int(round(pts_seconds / tb)) if tb > 0 else None
        else:
            self.pts = None
        self.time = pts_seconds
        self._buffer = buffer

    def to_ndarray(self, format: str = "bgr24") -> np.ndarray:
        """Return the frame as a ``numpy.ndarray`` in ``format``."""

        if format != "bgr24":  # pragma: no cover - defensive guard
            raise ValueError(f"Unsupported pixel format: {format}")
        frame = np.frombuffer(self._buffer, dtype=np.uint8)
        return frame.reshape((self.height, self.width, 3))


class FFmpegVideoSource:
    """Video reader that shells out to ``ffmpeg`` via ``ffmpeg-python``."""

    def __init__(self, source: str) -> None:
        """Initialise the ffmpeg pipeline for ``source``."""

        try:
            import ffmpeg  # type: ignore[import]
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError("ffmpeg-python is required for the ffmpeg decoder") from exc

        self.source = source
        self._ffmpeg = ffmpeg
        self._process: Optional[subprocess.Popen] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._frame_size = 0
        self._start_pts = 0.0
        self._frame_index = 0
        self._lock = threading.Lock()

        LOGGER.info("Opening video source via ffmpeg-python: %s", source)
        probe = self._probe_source()
        stream = self._extract_video_stream(probe)
        self.width = int(stream.get("width", 0) or 0)
        self.height = int(stream.get("height", 0) or 0)
        if self.width <= 0 or self.height <= 0:
            raise RuntimeError(f"Unable to detect geometry for: {source}")
        self._frame_size = self.width * self.height * 3

        self.fps = self._extract_rate(stream)
        time_base = self._extract_time_base(stream)
        if time_base is None:
            if self.fps > 0:
                time_base = Fraction(1, int(round(self.fps)))
            else:
                time_base = Fraction(0, 1)
        self.time_base = time_base

        self.duration = self._extract_duration(stream, probe)
        self.frame_count = self._extract_frame_count(stream)
        LOGGER.debug(
            "ffmpeg metadata: size=%dx%d fps=%.3f duration=%.3fs frames=%d time_base=%s",
            self.width,
            self.height,
            self.fps,
            self.duration,
            self.frame_count,
            self.time_base,
        )

    def _probe_source(self) -> dict:
        """Run ``ffprobe`` and return the parsed metadata dictionary."""

        try:
            return self._ffmpeg.probe(self.source)
        except self._ffmpeg.Error as exc:  # pragma: no cover - diagnostic path
            raise RuntimeError(f"Unable to open video source: {self.source}") from exc

    @staticmethod
    def _extract_video_stream(probe: dict) -> dict:
        """Return the first video stream dictionary from ``probe``."""

        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video":
                return stream
        raise RuntimeError("No video streams found")

    @staticmethod
    def _parse_fraction(value: Optional[str]) -> Optional[Fraction]:
        """Parse ``num/den`` strings emitted by ffmpeg into :class:`Fraction`."""

        if not value or value in {"0/0", "N/A"}:
            return None
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError):
            parts = str(value).split("/")
            if len(parts) == 2:
                try:
                    numerator = float(parts[0])
                    denominator = float(parts[1])
                    if denominator == 0:
                        return None
                    return Fraction.from_float(numerator / denominator)
                except (ValueError, ZeroDivisionError):
                    return None
        return None

    def _extract_rate(self, stream: dict) -> float:
        """Return the nominal frame rate for ``stream``."""

        for key in ("avg_frame_rate", "r_frame_rate"):
            rate = self._parse_fraction(stream.get(key))
            if rate is not None:
                try:
                    return float(rate)
                except ZeroDivisionError:  # pragma: no cover - defensive
                    continue
        try:
            return float(stream.get("fps", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _extract_time_base(self, stream: dict) -> Optional[Fraction]:
        """Return the stream time base if available."""

        time_base = self._parse_fraction(stream.get("time_base"))
        if time_base is not None:
            return time_base
        return None

    def _extract_duration(self, stream: dict, probe: dict) -> float:
        """Compute the best-effort duration for ``stream`` in seconds."""

        value = stream.get("duration")
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                value = None
        if isinstance(value, (int, float)):
            return float(value)
        fmt = probe.get("format", {})
        duration = fmt.get("duration")
        if duration is None:
            return 0.0
        try:
            return float(duration)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _extract_frame_count(stream: dict) -> int:
        """Return the frame count reported by ``stream`` if present."""

        value = stream.get("nb_frames")
        if value is None:
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return 0

    def _spawn_process(self, start_time: float) -> None:
        """Launch ``ffmpeg`` positioned at ``start_time`` seconds."""

        self._stop_process()
        input_kwargs = {"ss": max(0.0, start_time)} if start_time > 0 else {}
        cmd = (
            self._ffmpeg.input(self.source, **input_kwargs)
            .output(
                "pipe:",
                format="rawvideo",
                pix_fmt="bgr24",
                loglevel="error",
                vsync="vfr",
            )
            .global_args("-nostdin")
            .compile()
        )
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError as exc:  # pragma: no cover - executable missing
            raise RuntimeError("ffmpeg executable not found on PATH") from exc
        self._process = process
        self._start_pts = max(0.0, start_time)
        self._frame_index = 0
        if process.stderr is not None:
            self._stderr_thread = threading.Thread(
                target=self._drain_stderr,
                args=(process.stderr,),
                name="FFmpegVideoSource.stderr",
                daemon=True,
            )
            self._stderr_thread.start()

    @staticmethod
    def _drain_stderr(stream: IO[bytes]) -> None:
        """Continuously drain stderr so the subprocess never blocks."""

        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
        except Exception:  # pragma: no cover - best effort logging suppression
            pass
        finally:
            try:
                stream.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass

    def _stop_process(self) -> None:
        """Terminate the ``ffmpeg`` process and cleanup handles."""

        process = self._process
        if not process:
            return
        if process.stdout is not None:
            try:
                process.stdout.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if self._stderr_thread and self._stderr_thread.is_alive():
            self._stderr_thread.join(timeout=0.5)
        self._stderr_thread = None
        self._process = None

    def read_frame(self) -> Optional[FFmpegVideoFrame]:
        """Read the next raw frame and wrap it in :class:`FFmpegVideoFrame`."""

        with self._lock:
            if self._process is None:
                self._spawn_process(self._start_pts)
            process = self._process
            if process is None or process.stdout is None:
                return None
            data = process.stdout.read(self._frame_size)
            if len(data) < self._frame_size:
                self._stop_process()
                return None
            if self.fps > 0:
                pts_seconds = self._start_pts + (self._frame_index / self.fps)
            else:
                pts_seconds = self._start_pts + float(self._frame_index)
            frame = FFmpegVideoFrame(self.width, self.height, data, pts_seconds, self.time_base)
            self._frame_index += 1
            return frame

    def seek(self, position: float) -> None:
        """Restart decoding from ``position`` seconds."""

        with self._lock:
            target = max(0.0, position)
            self._spawn_process(target)

    def rewind(self) -> None:
        """Restart decoding from the beginning of the stream."""

        self.seek(0.0)

    def close(self) -> None:
        """Stop the worker process and release resources."""

        with self._lock:
            self._stop_process()


def open_video_source(source: str, *, decoder: str, enable_video: bool = True) -> VideoSource:
    """Instantiate the requested decoder backend for ``source``."""

    decoder = decoder.lower()
    if not enable_video:
        LOGGER.info("Video playback disabled; operating in audio-only mode")
        return NullVideoSource()
    if decoder == "pyav":
        return PyAVVideoSource(source)
    if decoder == "ffmpeg":
        return FFmpegVideoSource(source)
    if decoder == "auto":
        try:
            return PyAVVideoSource(source)
        except RuntimeError:
            LOGGER.info("PyAV decoder unavailable; falling back to ffmpeg subprocess")
            return FFmpegVideoSource(source)
    raise ValueError(f"Unsupported decoder: {decoder}")


def detect_frame_geometry(source: VideoSource) -> Tuple[int, int, float]:
    """Return ``(width, height, fps)`` for ``source`` with lazy probing."""

    width = source.width
    height = source.height
    if width <= 0 or height <= 0:
        frame = source.read_frame()
        if frame is None:
            raise RuntimeError("Unable to decode a frame to detect geometry")
        array = frame.to_ndarray(format="bgr24")
        height, width = array.shape[:2]
        source.seek(0.0)
    fps = source.fps
    if fps <= 0 and source.frame_count > 0 and source.duration > 0:
        fps = source.frame_count / source.duration
    if fps <= 0:
        fps = 30.0
    return width, height, fps
