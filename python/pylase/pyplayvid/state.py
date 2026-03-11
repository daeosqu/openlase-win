"""Playback state helpers shared by the qplayvid2 pipeline."""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

LOGGER = logging.getLogger("openlase.pyplayvid.state")


class PlaybackState:
    """Thread-safe coordination of playback mode, stop state, and seek IDs."""

    def __init__(
        self,
        initial_mode: Any,
        *,
        initial_seek_id: int = 1,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        self._mode = initial_mode
        self._seek_id = initial_seek_id
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._stop_event = stop_event or threading.Event()

    @property
    def stop_event(self) -> threading.Event:
        return self._stop_event

    @property
    def seek_id(self) -> int:
        with self._lock:
            return self._seek_id

    def advance_seek(self) -> int:
        with self._lock:
            self._seek_id += 1
            LOGGER.debug("Seek ID advanced to %s", self._seek_id)
            return self._seek_id

    def get_mode(self) -> Any:
        with self._lock:
            return self._mode

    def set_mode(self, mode: Any) -> None:
        with self._condition:
            LOGGER.debug("Playback mode transition %s -> %s", self._mode, mode)
            self._mode = mode
            self._condition.notify_all()

    def wait_for_play(self, pause_value: Any) -> Any:
        with self._condition:
            while self._mode == pause_value and not self._stop_event.is_set():
                self._condition.wait()
            return self._mode

    def request_stop(self, stop_value: Any) -> None:
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        with self._condition:
            self._mode = stop_value
            self._condition.notify_all()

    def should_stop(self) -> bool:
        return self._stop_event.is_set()


class FrameSync:
    """Maintain the frame/audio relationship during playback."""

    def __init__(self) -> None:
        self._current: Optional[Any] = None
        self._pending: Optional[Any] = None
        self.audio_clock: float = 0.0

    @property
    def current(self) -> Optional[Any]:
        return self._current

    def clear_current(self) -> None:
        self._current = None

    def ensure_frame(self, video_queue, state: PlaybackState, *, stop_value: Any) -> Optional[Any]:
        if self._current is not None:
            return self._current
        while True:
            item = video_queue.popleft(block=False)
            if item is None:
                return None
            if not hasattr(item, "seekid") or not hasattr(item, "pts"):
                continue
            if getattr(item, "eof", False):
                LOGGER.debug("Video EOF detected via ensure_frame")
                state.request_stop(stop_value)
                return None
            if getattr(item, "seekid", state.seek_id) != state.seek_id:
                continue
            self._current = item
            return item

    def next_frame_for_audio(
        self,
        video_queue,
        state: PlaybackState,
        *,
        stop_value: Any,
        video_rate: float,
    ) -> None:
        tolerance = 1.5 / max(video_rate, 1.0)
        while True:
            candidate = self._pending
            if candidate is None:
                fetched = video_queue.popleft(block=False)
                if fetched is None:
                    break
                if not hasattr(fetched, "seekid") or not hasattr(fetched, "pts"):
                    continue
                if getattr(fetched, "eof", False):
                    LOGGER.debug("Video EOF detected via next_frame_for_audio")
                    state.request_stop(stop_value)
                    break
                if getattr(fetched, "seekid", state.seek_id) != state.seek_id:
                    continue
                candidate = fetched
            if getattr(candidate, "pts", float("inf")) <= self.audio_clock + tolerance:
                self._current = candidate
                self._pending = None
            else:
                self._pending = candidate
                break

    def pending(self) -> Optional[Any]:
        return self._pending
