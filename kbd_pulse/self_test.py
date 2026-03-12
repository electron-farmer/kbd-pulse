from __future__ import annotations

import colorsys
import time
from collections.abc import Callable

from kbd_pulse.backlight import KeyboardBacklight

REGION_TEST_COLORS = ("FF0000", "00FF00", "0000FF", "FFFFFF")


def _hsv_hex(step: int, total_steps: int) -> str:
    hue = step / total_steps
    return _hue_hex(hue)


def _hue_hex(hue: float) -> str:
    red, green, blue = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return f"{int(red * 255):02X}{int(green * 255):02X}{int(blue * 255):02X}"


def run_backlight_self_test(
    backlight: KeyboardBacklight,
    *,
    brightness: int,
    hue_steps: int = 36,
    zone_dwell_sec: float = 0.2,
    sweep_dwell_sec: float = 0.03,
    sweep_mode: str = "global",
    restore_state: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    if hue_steps < 1:
        raise ValueError("hue_steps must be at least 1")
    if zone_dwell_sec < 0 or sweep_dwell_sec < 0:
        raise ValueError("dwell durations must be >= 0")
    if sweep_mode not in {"global", "independent"}:
        raise ValueError("sweep_mode must be one of: global, independent")

    zones = backlight.available_zones
    if not zones:
        raise ValueError("no zone files detected for this keyboard")

    original_brightness = backlight.get_brightness()
    original_colors = {zone: backlight.get_zone_color(zone) for zone in zones}

    try:
        backlight.set_brightness(brightness)
        backlight.set_all_zones("000000")

        for zone in zones:
            backlight.set_all_zones("000000")
            for color in REGION_TEST_COLORS:
                backlight.set_zone_color(zone, color)
                sleep(zone_dwell_sec)

        # Global mode is the most reliable on hardware that mirrors zones in firmware.
        for step in range(hue_steps):
            if sweep_mode == "global":
                backlight.set_all_zones(_hsv_hex(step, hue_steps))
            else:
                for index, zone in enumerate(zones):
                    base_hue = step / hue_steps
                    zone_hue = (base_hue + (index / len(zones))) % 1.0
                    backlight.set_zone_color(zone, _hue_hex(zone_hue))
            sleep(sweep_dwell_sec)
    finally:
        if restore_state:
            for zone, color in original_colors.items():
                backlight.set_zone_color(zone, color)
            backlight.set_brightness(original_brightness)
