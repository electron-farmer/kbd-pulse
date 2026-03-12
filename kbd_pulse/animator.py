from __future__ import annotations

import colorsys
import math
import queue
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from kbd_pulse.backlight import KeyboardBacklight


@dataclass(slots=True)
class DefaultProfile:
    base_brightness: int = 90
    keypress_boost: int = 110
    fade_seconds: float = 2.0
    hue_speed_degrees_per_second: float = 8.0
    start_time: float = 0.0
    last_keypress_time: float | None = None

    def register_keypress(self, timestamp: float) -> None:
        self.last_keypress_time = timestamp

    def state_at(self, now: float) -> tuple[int, str]:
        brightness = self.base_brightness
        if self.last_keypress_time is not None:
            delta = max(0.0, now - self.last_keypress_time)
            # Exponential falloff back toward base brightness.
            brightness += int(round(self.keypress_boost * math.exp(-delta / self.fade_seconds)))
        brightness = max(0, min(255, brightness))

        hue_turns = ((now - self.start_time) * self.hue_speed_degrees_per_second / 360.0) % 1.0
        red, green, blue = colorsys.hsv_to_rgb(hue_turns, 1.0, 1.0)
        color = f"{int(red * 255):02X}{int(green * 255):02X}{int(blue * 255):02X}"
        return brightness, color


@dataclass(slots=True)
class ProfileRuntimeConfig:
    frame_interval_sec: float = 0.05
    max_frames: int | None = None


def run_default_profile(
    backlight: KeyboardBacklight,
    keypress_stream: Iterator[float],
    profile: DefaultProfile,
    *,
    runtime: ProfileRuntimeConfig | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> int:
    runtime_cfg = runtime or ProfileRuntimeConfig()
    if runtime_cfg.frame_interval_sec <= 0:
        raise ValueError("frame_interval_sec must be > 0")

    events: queue.SimpleQueue[float | None] = queue.SimpleQueue()
    def stream_worker() -> None:
        try:
            for timestamp in keypress_stream:
                events.put(timestamp)
        finally:
            events.put(None)

    threading.Thread(target=stream_worker, name="kbd-pulse-keypress-stream", daemon=True).start()

    previous: tuple[int, str] | None = None
    frames = 0
    while True:
        while True:
            try:
                item = events.get_nowait()
            except queue.Empty:
                break
            if item is None:
                break
            profile.register_keypress(item)

        brightness, color = profile.state_at(monotonic())
        current = (brightness, color)
        if current != previous:
            backlight.set_brightness(brightness)
            backlight.set_all_zones(color)
            previous = current

        frames += 1
        if runtime_cfg.max_frames is not None and frames >= runtime_cfg.max_frames:
            return 0
        sleep(runtime_cfg.frame_interval_sec)
