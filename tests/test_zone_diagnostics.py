import unittest

from kbd_pulse.backlight import Zone
from kbd_pulse.zone_diagnostics import detect_linked_zones, run_slow_zone_diagnostics


class FakeBacklight:
    def __init__(self, linked_groups: tuple[tuple[Zone, ...], ...]) -> None:
        self.available_zones = (Zone.LEFT, Zone.CENTER, Zone.RIGHT, Zone.EXTRA)
        self._brightness = 10
        self._colors = {
            Zone.LEFT: "111111",
            Zone.CENTER: "222222",
            Zone.RIGHT: "333333",
            Zone.EXTRA: "444444",
        }
        self._linked_groups = linked_groups

    def get_brightness(self) -> int:
        return self._brightness

    def set_brightness(self, brightness: int) -> None:
        self._brightness = brightness

    def get_zone_color(self, zone: Zone) -> str:
        return self._colors[zone]

    def set_zone_color(self, zone: Zone, color: str) -> None:
        for group in self._linked_groups:
            if zone in group:
                for member in group:
                    self._colors[member] = color
                return
        self._colors[zone] = color

    def set_all_zones(self, color: str) -> None:
        for zone in self.available_zones:
            self._colors[zone] = color


class ZoneDiagnosticsTests(unittest.TestCase):
    def test_detect_linked_zones(self) -> None:
        backlight = FakeBacklight(
            linked_groups=((Zone.LEFT, Zone.RIGHT), (Zone.CENTER,), (Zone.EXTRA,))
        )
        groups = detect_linked_zones(backlight)
        self.assertEqual(
            groups,
            [(Zone.CENTER,), (Zone.EXTRA,), (Zone.LEFT, Zone.RIGHT)],
        )

    def test_slow_zone_diagnostics_restores_state(self) -> None:
        backlight = FakeBacklight(
            linked_groups=((Zone.LEFT,), (Zone.CENTER,), (Zone.RIGHT,), (Zone.EXTRA,))
        )

        groups = run_slow_zone_diagnostics(
            backlight,
            brightness=200,
            zone_dwell_sec=0,
            sweep_steps=4,
            sweep_dwell_sec=0,
            restore_state=True,
            sleep=lambda _: None,
        )

        self.assertEqual(
            groups,
            [(Zone.CENTER,), (Zone.EXTRA,), (Zone.LEFT,), (Zone.RIGHT,)],
        )
        self.assertEqual(backlight.get_brightness(), 10)
        self.assertEqual(backlight.get_zone_color(Zone.LEFT), "111111")


if __name__ == "__main__":
    unittest.main()
