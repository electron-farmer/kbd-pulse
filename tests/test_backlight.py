import tempfile
import unittest
from pathlib import Path

from kbd_pulse.backlight import KeyboardBacklight, Zone


class KeyboardBacklightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.sysfs_path = Path(self.tmp_dir.name)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _write(self, name: str, value: str) -> None:
        (self.sysfs_path / name).write_text(value)

    def test_detects_available_zones(self) -> None:
        self._write("color_left", "FFFFFF\n")
        self._write("color_right", "000000\n")

        backlight = KeyboardBacklight(self.sysfs_path)

        self.assertEqual(backlight.available_zones, (Zone.LEFT, Zone.RIGHT))
        self.assertTrue(backlight.has_zone(Zone.LEFT))
        self.assertFalse(backlight.has_zone(Zone.CENTER))

    def test_reads_and_writes_brightness(self) -> None:
        self._write("brightness", "120\n")
        backlight = KeyboardBacklight(self.sysfs_path)

        self.assertEqual(backlight.get_brightness(), 120)
        backlight.set_brightness(200)
        self.assertEqual((self.sysfs_path / "brightness").read_text(), "200\n")

    def test_brightness_range_validation(self) -> None:
        self._write("brightness", "0\n")
        backlight = KeyboardBacklight(self.sysfs_path)

        with self.assertRaises(ValueError):
            backlight.set_brightness(-1)
        with self.assertRaises(ValueError):
            backlight.set_brightness(256)

    def test_reads_and_writes_zone_color(self) -> None:
        self._write("color_center", "00ff00\n")
        backlight = KeyboardBacklight(self.sysfs_path)

        self.assertEqual(backlight.get_zone_color(Zone.CENTER), "00FF00")
        backlight.set_zone_color(Zone.CENTER, "#aa11cc")
        self.assertEqual((self.sysfs_path / "color_center").read_text(), "AA11CC\n")

    def test_setting_missing_zone_raises(self) -> None:
        self._write("color_left", "FFFFFF\n")
        backlight = KeyboardBacklight(self.sysfs_path)

        with self.assertRaises(ValueError):
            backlight.set_zone_color(Zone.EXTRA, "112233")

    def test_set_all_zones_writes_only_detected_files(self) -> None:
        self._write("color_left", "000000\n")
        self._write("color_extra", "000000\n")
        backlight = KeyboardBacklight(self.sysfs_path)

        backlight.set_all_zones("123456")

        self.assertEqual((self.sysfs_path / "color_left").read_text(), "123456\n")
        self.assertEqual((self.sysfs_path / "color_extra").read_text(), "123456\n")
        self.assertFalse((self.sysfs_path / "color_center").exists())

    def test_set_all_zones_is_noop_when_no_zone_files_exist(self) -> None:
        backlight = KeyboardBacklight(self.sysfs_path)
        backlight.set_all_zones("ABCDEF")
        self.assertEqual(backlight.available_zones, ())

    def test_color_validation(self) -> None:
        self._write("color_left", "000000\n")
        backlight = KeyboardBacklight(self.sysfs_path)

        with self.assertRaises(ValueError):
            backlight.set_zone_color(Zone.LEFT, "ZZ0000")
        with self.assertRaises(ValueError):
            backlight.set_zone_color(Zone.LEFT, "12345")


if __name__ == "__main__":
    unittest.main()
