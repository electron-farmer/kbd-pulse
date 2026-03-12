import unittest

from kbd_pulse.animator import DefaultProfile, ProfileRuntimeConfig, run_default_profile


class FakeBacklight:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int | str]] = []

    def set_brightness(self, value: int) -> None:
        self.calls.append(("brightness", value))

    def set_all_zones(self, color: str) -> None:
        self.calls.append(("color", color))


class AnimatorTests(unittest.TestCase):
    def test_default_profile_boost_then_fade(self) -> None:
        profile = DefaultProfile(
            base_brightness=80,
            keypress_boost=100,
            fade_seconds=2.0,
            hue_speed_degrees_per_second=10.0,
            start_time=0.0,
        )
        profile.register_keypress(10.0)

        immediate, _ = profile.state_at(10.0)
        later, _ = profile.state_at(12.0)
        long_after, _ = profile.state_at(30.0)

        self.assertGreater(immediate, later)
        self.assertGreater(later, long_after)
        self.assertEqual(long_after, 80)

    def test_default_profile_color_changes_over_time(self) -> None:
        profile = DefaultProfile(
            base_brightness=90,
            keypress_boost=0,
            fade_seconds=2.0,
            hue_speed_degrees_per_second=30.0,
            start_time=0.0,
        )
        _, color_a = profile.state_at(0.0)
        _, color_b = profile.state_at(5.0)
        self.assertNotEqual(color_a, color_b)

    def test_run_default_profile_applies_frames(self) -> None:
        backlight = FakeBacklight()
        profile = DefaultProfile(
            base_brightness=50,
            keypress_boost=50,
            fade_seconds=1.0,
            hue_speed_degrees_per_second=10.0,
            start_time=0.0,
        )
        times = iter([0.0, 0.1, 0.2, 0.3])

        code = run_default_profile(
            backlight,
            iter([0.05]),
            profile,
            runtime=ProfileRuntimeConfig(frame_interval_sec=0.001, max_frames=4),
            sleep=lambda _: None,
            monotonic=lambda: next(times),
        )

        self.assertEqual(code, 0)
        self.assertTrue(any(call[0] == "brightness" for call in backlight.calls))
        self.assertTrue(any(call[0] == "color" for call in backlight.calls))

    def test_run_default_profile_rejects_bad_interval(self) -> None:
        with self.assertRaises(ValueError):
            run_default_profile(
                FakeBacklight(),
                iter([]),
                DefaultProfile(),
                runtime=ProfileRuntimeConfig(frame_interval_sec=0),
            )


if __name__ == "__main__":
    unittest.main()
