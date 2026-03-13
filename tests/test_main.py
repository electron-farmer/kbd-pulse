import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from kbd_pulse.__main__ import main
from kbd_pulse.backlight import Zone


class MainCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.sysfs_path = Path(self.tmp_dir.name)
        (self.sysfs_path / "brightness").write_text("100\n")
        (self.sysfs_path / "color_left").write_text("101010\n")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_status_command(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(["--sysfs-path", str(self.sysfs_path), "status"])

        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("brightness: 100", output)
        self.assertIn("left: 101010", output)

    def test_set_command_updates_brightness_and_color(self) -> None:
        code = main(
            [
                "--sysfs-path",
                str(self.sysfs_path),
                "set",
                "--brightness",
                "180",
                "--color",
                "A1B2C3",
            ]
        )

        self.assertEqual(code, 0)
        self.assertEqual((self.sysfs_path / "brightness").read_text(), "180\n")
        self.assertEqual((self.sysfs_path / "color_left").read_text(), "A1B2C3\n")

    def test_watch_input_command(self) -> None:
        class FakeWatcher:
            def __init__(self, device_name: str):
                self.device_name = device_name

            def keypress_timestamps(self, max_events=None):
                del max_events
                yield 1.25
                yield 2.5

        stdout = StringIO()
        with patch("kbd_pulse.__main__.InputWatcher", FakeWatcher):
            with redirect_stdout(stdout):
                code = main(["watch-input", "--count", "2"])

        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("1: 1.250000", output)
        self.assertIn("2: 2.500000", output)

    def test_run_command(self) -> None:
        called = []

        def fake_run(backlight, args):
            del backlight
            called.append(args.command)
            return 0

        with patch("kbd_pulse.__main__.command_run", fake_run):
            code = main(["--sysfs-path", str(self.sysfs_path), "run"])

        self.assertEqual(code, 0)
        self.assertEqual(called, ["run"])

    def test_default_command_is_run(self) -> None:
        called = []

        def fake_run(backlight, args):
            del backlight
            called.append(
                (
                    args.command,
                    getattr(args, "device_name", None),
                    getattr(args, "base_brightness", None),
                    getattr(args, "keypress_boost", None),
                )
            )
            return 0

        with patch("kbd_pulse.__main__.command_run", fake_run):
            code = main(["--sysfs-path", str(self.sysfs_path)])

        self.assertEqual(code, 0)
        self.assertEqual(called, [("run", None, None, None)])

    def test_default_command_executes_run_with_fallback_defaults(self) -> None:
        seen = {}

        class FakeWatcher:
            def __init__(self, device_name: str):
                seen["device_name"] = device_name

            def keypress_timestamps(self):
                return iter(())

        def fake_run_default_profile(_backlight, _keypress_stream, profile, *, runtime):
            seen["base_brightness"] = profile.base_brightness
            seen["keypress_boost"] = profile.keypress_boost
            seen["fade_seconds"] = profile.fade_seconds
            seen["hue_speed"] = profile.hue_speed_degrees_per_second
            seen["hue_boost_per_keypress"] = profile.hue_speed_boost_per_keypress
            seen["hue_boost_decay"] = profile.hue_speed_boost_decay_seconds
            seen["hue_boost_max"] = profile.hue_speed_boost_max
            seen["hue_jump"] = profile.hue_jump_per_keypress_degrees
            seen["frame_interval"] = runtime.frame_interval_sec
            return 0

        with patch("kbd_pulse.__main__.InputWatcher", FakeWatcher):
            with patch("kbd_pulse.__main__.run_default_profile", fake_run_default_profile):
                code = main(["--sysfs-path", str(self.sysfs_path)])

        self.assertEqual(code, 0)
        self.assertEqual(seen["device_name"], "AT Translated Set 2 keyboard")
        self.assertEqual(seen["base_brightness"], 70)
        self.assertEqual(seen["keypress_boost"], 170)
        self.assertEqual(seen["fade_seconds"], 2.0)
        self.assertEqual(seen["hue_speed"], 8.0)
        self.assertEqual(seen["hue_boost_per_keypress"], 40.0)
        self.assertEqual(seen["hue_boost_decay"], 3.0)
        self.assertEqual(seen["hue_boost_max"], 320.0)
        self.assertEqual(seen["hue_jump"], 18.0)
        self.assertEqual(seen["frame_interval"], 0.05)

    def test_self_test_command(self) -> None:
        called: list[tuple[int, int, float, float, str, bool]] = []

        def fake_self_test(
            backlight,
            *,
            brightness: int,
            hue_steps: int,
            zone_dwell_sec: float,
            sweep_dwell_sec: float,
            sweep_mode: str,
            restore_state: bool,
        ):
            del backlight
            called.append(
                (
                    brightness,
                    hue_steps,
                    zone_dwell_sec,
                    sweep_dwell_sec,
                    sweep_mode,
                    restore_state,
                )
            )

        with patch("kbd_pulse.__main__.run_backlight_self_test", fake_self_test):
            code = main(
                [
                    "--sysfs-path",
                    str(self.sysfs_path),
                    "self-test",
                    "--brightness",
                    "190",
                    "--hue-steps",
                    "12",
                    "--zone-dwell",
                    "0.05",
                    "--sweep-dwell",
                    "0.01",
                    "--sweep-mode",
                    "independent",
                ]
            )

        self.assertEqual(code, 0)
        self.assertEqual(called, [(190, 12, 0.05, 0.01, "independent", True)])

    def test_zone_diagnose_command(self) -> None:
        called: list[tuple[int, float, int, float, float, str, bool]] = []

        def fake_zone_diagnostics(
            backlight,
            *,
            brightness: int,
            zone_dwell_sec: float,
            sweep_steps: int,
            sweep_dwell_sec: float,
            probe_dwell_sec: float,
            sweep_mode: str,
            restore_state: bool,
            log,
        ):
            del backlight
            called.append(
                (
                    brightness,
                    zone_dwell_sec,
                    sweep_steps,
                    sweep_dwell_sec,
                    probe_dwell_sec,
                    sweep_mode,
                    restore_state,
                    log is not None,
                )
            )
            return [(Zone.LEFT,), (Zone.CENTER, Zone.RIGHT)]

        with patch("kbd_pulse.__main__.run_slow_zone_diagnostics", fake_zone_diagnostics):
            code = main(
                [
                    "--sysfs-path",
                    str(self.sysfs_path),
                    "zone-diagnose",
                    "--brightness",
                    "210",
                    "--zone-dwell",
                    "1.2",
                    "--sweep-steps",
                    "10",
                    "--sweep-dwell",
                    "0.2",
                    "--probe-dwell",
                    "0.6",
                    "--sweep-mode",
                    "global",
                    "--no-restore",
                ]
            )

        self.assertEqual(code, 0)
        self.assertEqual(called, [(210, 1.2, 10, 0.2, 0.6, "global", False, False)])

    def test_set_requires_value(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(["--sysfs-path", str(self.sysfs_path), "set"])
        self.assertEqual(code, 2)
        self.assertIn("set requires at least one", stdout.getvalue())

    def test_status_with_no_zones(self) -> None:
        empty = self.sysfs_path / "empty"
        empty.mkdir()
        (empty / "brightness").write_text("90\n")
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(["--sysfs-path", str(empty), "status"])
        self.assertEqual(code, 0)
        self.assertIn("zones: none detected", stdout.getvalue())

    def test_zone_diagnose_verbose_enables_logger(self) -> None:
        called = []

        def fake_zone_diagnostics(backlight, **kwargs):
            del backlight
            called.append(kwargs["log"] is not None)
            kwargs["log"]("verbose enabled")
            return [(Zone.LEFT,)]

        stdout = StringIO()
        with patch("kbd_pulse.__main__.run_slow_zone_diagnostics", fake_zone_diagnostics):
            with redirect_stdout(stdout):
                code = main(
                    [
                        "--sysfs-path",
                        str(self.sysfs_path),
                        "zone-diagnose",
                        "--verbose",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertEqual(called, [True])
        self.assertIn("[diag] verbose enabled", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
