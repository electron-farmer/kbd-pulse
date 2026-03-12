from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Protocol

from evdev import InputDevice, ecodes, list_devices

DEFAULT_KEYBOARD_NAME = "AT Translated Set 2 keyboard"


class _ReadableDevice(Protocol):
    def read_loop(self) -> Iterator[object]: ...

    def close(self) -> None: ...


@dataclass(slots=True)
class InputWatcher:
    device_name: str = DEFAULT_KEYBOARD_NAME
    scan_interval_sec: float = 1.0
    reconnect_interval_sec: float = 1.0
    list_device_paths: Callable[[], list[str]] = list_devices
    get_device_name: Callable[[str], str | None] | None = None
    open_device: Callable[[str], _ReadableDevice] = InputDevice
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if self.get_device_name is None:
            self.get_device_name = self._default_get_device_name

    def _default_get_device_name(self, path: str) -> str | None:
        device = InputDevice(path)
        try:
            return device.name
        finally:
            device.close()

    def find_device_path(self) -> str | None:
        for path in self.list_device_paths():
            name = self.get_device_name(path) if self.get_device_name else None
            if name == self.device_name:
                return path
        return None

    def keypress_timestamps(self, max_events: int | None = None) -> Iterator[float]:
        emitted = 0
        while max_events is None or emitted < max_events:
            device_path = self.find_device_path()
            if device_path is None:
                self.sleep(self.scan_interval_sec)
                continue

            device = self.open_device(device_path)
            try:
                for event in device.read_loop():
                    if (
                        getattr(event, "type", None) == ecodes.EV_KEY
                        and getattr(event, "value", None) == 1
                    ):
                        emitted += 1
                        yield self.clock()
                        if max_events is not None and emitted >= max_events:
                            return
            except OSError:
                self.sleep(self.reconnect_interval_sec)
            finally:
                device.close()
