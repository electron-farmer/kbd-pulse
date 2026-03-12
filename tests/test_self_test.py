import unittest

from kbd_pulse.backlight import Zone
from kbd_pulse.self_test import REGION_TEST_COLORS, run_backlight_self_test


class FakeBacklight:
    def __init__(self) -> None:
        self.available_zones = (Zone.LEFT, Zone.CENTER, Zone.RIGHT, Zone.EXTRA)
        self._brightness = 25
        self._colors = {
            Zone.LEFT: "111111",
            Zone.CENTER: "222222",
            Zone.RIGHT: "333333",
            Zone.EXTRA: "444444",
        }
        self.calls: list[tuple[str, object]] = []

    def get_brightness(self) -> int:
        return self._brightness

    def set_brightness(self, brightness: int) -> None:
        self._brightness = brightness
        self.calls.append(("set_brightness", brightness))

    def get_zone_color(self, zone: Zone) -> str:
        return self._colors[zone]

    def set_zone_color(self, zone: Zone, color: str) -> None:
        self._colors[zone] = color
        self.calls.append(("set_zone_color", zone, color))

    def set_all_zones(self, color: str) -> None:
        for zone in self.available_zones:
            self._colors[zone] = color
        self.calls.append(("set_all_zones", color))


class SelfTestTests(unittest.TestCase):
    def test_self_test_touches_every_zone_and_restores_state(self) -> None:
        backlight = FakeBacklight()
        sleeps: list[float] = []

        run_backlight_self_test(
            backlight,
            brightness=200,
            hue_steps=6,
            zone_dwell_sec=0.01,
            sweep_dwell_sec=0.01,
            sleep=lambda seconds: sleeps.append(seconds),
        )

        for zone in backlight.available_zones:
            seen_colors = {
                call
                for call in backlight.calls
                if call[0] == "set_zone_color" and call[1] == zone and call[2] in REGION_TEST_COLORS
            }
            observed = {call[2] for call in seen_colors}
            self.assertTrue(set(REGION_TEST_COLORS).issubset(observed))

        self.assertEqual(backlight.get_brightness(), 25)
        self.assertEqual(backlight.get_zone_color(Zone.LEFT), "111111")
        self.assertEqual(backlight.get_zone_color(Zone.CENTER), "222222")
        self.assertEqual(backlight.get_zone_color(Zone.RIGHT), "333333")
        self.assertEqual(backlight.get_zone_color(Zone.EXTRA), "444444")
        self.assertEqual(sleeps.count(0.01), (4 * len(REGION_TEST_COLORS)) + 6)

    def test_self_test_requires_detected_zones(self) -> None:
        backlight = FakeBacklight()
        backlight.available_zones = ()

        with self.assertRaises(ValueError):
            run_backlight_self_test(backlight, brightness=180, sleep=lambda _: None)

    def test_no_restore_keeps_test_state(self) -> None:
        backlight = FakeBacklight()
        run_backlight_self_test(
            backlight,
            brightness=200,
            hue_steps=1,
            zone_dwell_sec=0,
            sweep_dwell_sec=0,
            restore_state=False,
            sleep=lambda _: None,
        )
        self.assertEqual(backlight.get_brightness(), 200)
        zone_colors = [backlight.get_zone_color(zone) for zone in backlight.available_zones]
        self.assertEqual(len(set(zone_colors)), 1)

    def test_independent_mode_ends_with_different_zone_colors(self) -> None:
        backlight = FakeBacklight()
        run_backlight_self_test(
            backlight,
            brightness=200,
            hue_steps=1,
            zone_dwell_sec=0,
            sweep_dwell_sec=0,
            sweep_mode="independent",
            restore_state=False,
            sleep=lambda _: None,
        )
        zone_colors = [backlight.get_zone_color(zone) for zone in backlight.available_zones]
        self.assertGreater(len(set(zone_colors)), 1)


if __name__ == "__main__":
    unittest.main()
