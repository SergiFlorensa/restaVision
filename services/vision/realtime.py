from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Lock
from typing import Generic, TypeVar

Packet = TypeVar("Packet")


class LatestItemBuffer(Generic[Packet]):
    def __init__(self) -> None:
        self._queue: Queue[Packet] = Queue(maxsize=1)
        self._lock = Lock()

    def put(self, packet: Packet) -> None:
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except Empty:
                    break
            self._queue.put_nowait(packet)

    def get_latest(self, timeout: float | None = None) -> Packet | None:
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def clear(self) -> None:
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except Empty:
                    break


@dataclass(frozen=True, slots=True)
class FrameSkippingConfig:
    base_interval: int = 1
    hot_interval: int = 3
    cpu_hot_threshold_percent: float = 90.0

    def __post_init__(self) -> None:
        if self.base_interval < 1:
            raise ValueError("base_interval must be greater than or equal to 1.")
        if self.hot_interval < self.base_interval:
            raise ValueError("hot_interval must be greater than or equal to base_interval.")
        if not 0 <= self.cpu_hot_threshold_percent <= 100:
            raise ValueError("cpu_hot_threshold_percent must be between 0 and 100.")


class FrameSkippingPolicy:
    def __init__(self, config: FrameSkippingConfig | None = None) -> None:
        self.config = config or FrameSkippingConfig()

    def should_process(self, frame_index: int, cpu_percent: float | None = None) -> bool:
        if frame_index < 0:
            raise ValueError("frame_index must be non-negative.")

        interval = self.config.base_interval
        if cpu_percent is not None and cpu_percent >= self.config.cpu_hot_threshold_percent:
            interval = self.config.hot_interval
        return frame_index % interval == 0
