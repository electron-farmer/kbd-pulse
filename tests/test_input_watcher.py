import unittest
from collections.abc import Iterator
from dataclasses import dataclass
from unittest.mock import patch

from kbd_pulse.input_watcher import InputWatcher, ecodes


@dataclass
class FakeEvent:
    type: int
    value: int


class FakeDevice:
    def __init__(self, events: list[object]):
        self._events = events
        self.closed = False

    def read_loop(self) -> Iterator[object]:
        for event in self._events:
            if isinstance(event, Exception):
                raise event
            yield event

    def close(self) -> None:
        self.closed = True


class InputWatcherTests(unittest.TestCase):
    def test_find_device_path_by_exact_name(self) -> None:
        names = {
            "/dev/input/event1": "Power Button",
            "/dev/input/event2": "AT Translated Set 2 keyboard",
        }
        watcher = InputWatcher(
            list_device_paths=lambda: list(names.keys()),
            get_device_name=lambda path: names[path],
        )

        self.assertEqual(watcher.find_device_path(), "/dev/input/event2")

    def test_keypress_timestamps_emits_only_key_down_events(self) -> None:
        events = [
            FakeEvent(type=ecodes.EV_KEY, value=0),
            FakeEvent(type=ecodes.EV_KEY, value=1),
            FakeEvent(type=999, value=1),
            FakeEvent(type=ecodes.EV_KEY, value=1),
        ]
        device = FakeDevice(events)
        timestamps = iter([10.0, 10.5])

        watcher = InputWatcher(
            list_device_paths=lambda: ["/dev/input/event2"],
            get_device_name=lambda _: "AT Translated Set 2 keyboard",
            open_device=lambda _: device,
            clock=lambda: next(timestamps),
        )

        out = list(watcher.keypress_timestamps(max_events=2))
        self.assertEqual(out, [10.0, 10.5])
        self.assertTrue(device.closed)

    def test_reconnects_after_device_error(self) -> None:
        first = FakeDevice(
            [
                FakeEvent(type=ecodes.EV_KEY, value=1),
                OSError("device disconnected"),
            ]
        )
        second = FakeDevice([FakeEvent(type=ecodes.EV_KEY, value=1)])
        opened: list[FakeDevice] = []
        sleeps: list[float] = []
        timestamps = iter([1.0, 2.0])

        def open_device(_: str) -> FakeDevice:
            device = first if not opened else second
            opened.append(device)
            return device

        watcher = InputWatcher(
            list_device_paths=lambda: ["/dev/input/event2"],
            get_device_name=lambda _: "AT Translated Set 2 keyboard",
            open_device=open_device,
            clock=lambda: next(timestamps),
            sleep=lambda seconds: sleeps.append(seconds),
            reconnect_interval_sec=0.25,
        )

        out = list(watcher.keypress_timestamps(max_events=2))
        self.assertEqual(out, [1.0, 2.0])
        self.assertEqual(sleeps, [0.25])
        self.assertTrue(first.closed)
        self.assertTrue(second.closed)

    def test_waits_when_device_not_found(self) -> None:
        sleeps: list[float] = []

        def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            raise RuntimeError("stop")

        watcher = InputWatcher(
            list_device_paths=lambda: [],
            sleep=fake_sleep,
            scan_interval_sec=0.75,
        )
        with self.assertRaises(RuntimeError):
            next(watcher.keypress_timestamps(max_events=1))
        self.assertEqual(sleeps, [0.75])

    def test_default_get_device_name_closes_device(self) -> None:
        class DeviceForName:
            def __init__(self, _path: str):
                self.name = "AT Translated Set 2 keyboard"
                self.closed = False

            def close(self) -> None:
                self.closed = True

        created: list[DeviceForName] = []

        def build(path: str) -> DeviceForName:
            device = DeviceForName(path)
            created.append(device)
            return device

        with patch("kbd_pulse.input_watcher.InputDevice", build):
            watcher = InputWatcher(list_device_paths=lambda: [])
            name = watcher._default_get_device_name("/dev/input/event9")

        self.assertEqual(name, "AT Translated Set 2 keyboard")
        self.assertTrue(created[0].closed)


if __name__ == "__main__":
    unittest.main()
