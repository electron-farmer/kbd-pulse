from __future__ import annotations

from enum import StrEnum
from pathlib import Path

DEFAULT_SYSFS_PATH = Path("/sys/class/leds/system76::kbd_backlight")


class Zone(StrEnum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    EXTRA = "extra"


ZONE_FILE_NAMES = {
    Zone.LEFT: "color_left",
    Zone.CENTER: "color_center",
    Zone.RIGHT: "color_right",
    Zone.EXTRA: "color_extra",
}


class KeyboardBacklight:
    def __init__(self, sysfs_path: str | Path = DEFAULT_SYSFS_PATH):
        self.sysfs_path = Path(sysfs_path)
        self._zone_files = self._detect_zone_files()

    def _detect_zone_files(self) -> dict[Zone, Path]:
        zone_files: dict[Zone, Path] = {}
        for zone, file_name in ZONE_FILE_NAMES.items():
            candidate = self.sysfs_path / file_name
            if candidate.exists():
                zone_files[zone] = candidate
        return zone_files

    @property
    def brightness_file(self) -> Path:
        return self.sysfs_path / "brightness"

    @property
    def available_zones(self) -> tuple[Zone, ...]:
        return tuple(self._zone_files.keys())

    def has_zone(self, zone: Zone) -> bool:
        return zone in self._zone_files

    def get_brightness(self) -> int:
        return int(self.brightness_file.read_text().strip())

    def set_brightness(self, brightness: int) -> None:
        if not 0 <= brightness <= 255:
            raise ValueError("brightness must be between 0 and 255")
        self.brightness_file.write_text(f"{brightness}\n")

    def get_zone_color(self, zone: Zone) -> str:
        zone_file = self._get_zone_file(zone)
        return zone_file.read_text().strip().upper()

    def set_zone_color(self, zone: Zone, color: str) -> None:
        zone_file = self._get_zone_file(zone)
        normalized = self._normalize_color(color)
        zone_file.write_text(f"{normalized}\n")

    def set_all_zones(self, color: str) -> None:
        normalized = self._normalize_color(color)
        for zone_file in self._zone_files.values():
            zone_file.write_text(f"{normalized}\n")

    def _get_zone_file(self, zone: Zone) -> Path:
        zone_file = self._zone_files.get(zone)
        if zone_file is None:
            raise ValueError(f"zone '{zone}' is not available on this keyboard")
        return zone_file

    @staticmethod
    def _normalize_color(color: str) -> str:
        normalized = color.strip().removeprefix("#").upper()
        if len(normalized) != 6:
            raise ValueError("color must be a 6-digit hex string (RRGGBB)")

        valid_chars = set("0123456789ABCDEF")
        if any(char not in valid_chars for char in normalized):
            raise ValueError("color must be a 6-digit hex string (RRGGBB)")
        return normalized
