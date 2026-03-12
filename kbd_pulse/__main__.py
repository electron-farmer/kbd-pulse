from __future__ import annotations

import argparse
from collections.abc import Sequence

from kbd_pulse.animator import DefaultProfile, ProfileRuntimeConfig, run_default_profile
from kbd_pulse.backlight import KeyboardBacklight, Zone
from kbd_pulse.input_watcher import DEFAULT_KEYBOARD_NAME, InputWatcher
from kbd_pulse.self_test import run_backlight_self_test
from kbd_pulse.zone_diagnostics import run_slow_zone_diagnostics

DEFAULT_BASE_BRIGHTNESS = 90
DEFAULT_KEYPRESS_BOOST = 110
DEFAULT_FADE_SECONDS = 2.0
DEFAULT_HUE_SPEED = 8.0
DEFAULT_FRAME_INTERVAL = 0.05


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kbd-pulse")
    parser.add_argument(
        "--sysfs-path",
        default=None,
        help="override keyboard backlight sysfs path for testing",
    )

    subparsers = parser.add_subparsers(dest="command", required=False)
    parser.set_defaults(command="run")

    run_parser = subparsers.add_parser(
        "run",
        help="run the default profile: keypress boost + fade + slow color drift",
    )
    run_parser.add_argument(
        "--device-name",
        default=DEFAULT_KEYBOARD_NAME,
        help="exact evdev device name to match",
    )
    run_parser.add_argument(
        "--base-brightness",
        type=int,
        default=DEFAULT_BASE_BRIGHTNESS,
        help="idle brightness level 0-255 (default: 90)",
    )
    run_parser.add_argument(
        "--keypress-boost",
        type=int,
        default=DEFAULT_KEYPRESS_BOOST,
        help="brightness boost applied on each keypress (default: 110)",
    )
    run_parser.add_argument(
        "--fade-seconds",
        type=float,
        default=DEFAULT_FADE_SECONDS,
        help="seconds for brightness to decay toward base after keypress (default: 2.0)",
    )
    run_parser.add_argument(
        "--hue-speed",
        type=float,
        default=DEFAULT_HUE_SPEED,
        help="color drift speed in hue degrees per second (default: 8.0)",
    )
    run_parser.add_argument(
        "--frame-interval",
        type=float,
        default=DEFAULT_FRAME_INTERVAL,
        help="seconds per animation frame (default: 0.05)",
    )
    subparsers.add_parser("status", help="show detected zones and current values")

    set_parser = subparsers.add_parser("set", help="set brightness and/or color")
    set_parser.add_argument("--brightness", type=int, help="brightness value 0-255")
    set_parser.add_argument("--color", help="hex RGB color (RRGGBB or #RRGGBB)")
    set_parser.add_argument(
        "--zone",
        choices=[zone.value for zone in Zone],
        help="set color for a single zone (defaults to all detected zones)",
    )

    watch_parser = subparsers.add_parser(
        "watch-input", help="print keypress timestamps from evdev"
    )
    watch_parser.add_argument(
        "--device-name",
        default=DEFAULT_KEYBOARD_NAME,
        help="exact evdev device name to match",
    )
    watch_parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="stop after N keypresses (default: run forever)",
    )

    self_test_parser = subparsers.add_parser(
        "self-test", help="run per-zone and independent-color backlight hardware test"
    )
    self_test_parser.add_argument(
        "--brightness",
        type=int,
        default=180,
        help="test brightness 0-255 (default: 180)",
    )
    self_test_parser.add_argument(
        "--hue-steps",
        type=int,
        default=36,
        help="number of steps in independent zone color sweep (default: 36)",
    )
    self_test_parser.add_argument(
        "--zone-dwell",
        type=float,
        default=0.2,
        help="seconds to hold each per-zone test color (default: 0.2)",
    )
    self_test_parser.add_argument(
        "--sweep-dwell",
        type=float,
        default=0.03,
        help="seconds per color in full sweep (default: 0.03)",
    )
    self_test_parser.add_argument(
        "--sweep-mode",
        choices=["global", "independent"],
        default="global",
        help="full sweep style: global or independent (default: global)",
    )
    self_test_parser.add_argument(
        "--no-restore",
        action="store_true",
        help="leave the final test color/brightness instead of restoring prior state",
    )

    diagnose_parser = subparsers.add_parser(
        "zone-diagnose",
        help="slow visual zone test plus linked-zone detection from sysfs behavior",
    )
    diagnose_parser.add_argument(
        "--brightness",
        type=int,
        default=200,
        help="test brightness 0-255 (default: 200)",
    )
    diagnose_parser.add_argument(
        "--zone-dwell",
        type=float,
        default=1.0,
        help="seconds to hold each zone/color test frame (default: 1.0)",
    )
    diagnose_parser.add_argument(
        "--sweep-steps",
        type=int,
        default=24,
        help="number of steps in independent zone sweep (default: 24)",
    )
    diagnose_parser.add_argument(
        "--sweep-dwell",
        type=float,
        default=0.15,
        help="seconds to hold each sweep frame (default: 0.15)",
    )
    diagnose_parser.add_argument(
        "--sweep-mode",
        choices=["auto", "independent", "global"],
        default="global",
        help="phase 2 style: auto, independent, or global (default: global)",
    )
    diagnose_parser.add_argument(
        "--probe-dwell",
        type=float,
        default=0.5,
        help="seconds to hold each linked-zone probe color (default: 0.5)",
    )
    diagnose_parser.add_argument(
        "--no-restore",
        action="store_true",
        help="leave final test colors/brightness instead of restoring prior state",
    )
    diagnose_parser.add_argument(
        "--verbose",
        action="store_true",
        help="print detailed per-step diagnostics logging",
    )

    return parser


def command_status(backlight: KeyboardBacklight) -> int:
    print(f"sysfs path: {backlight.sysfs_path}")
    print(f"brightness: {backlight.get_brightness()}")
    if not backlight.available_zones:
        print("zones: none detected")
        return 0

    print("zones:")
    for zone in backlight.available_zones:
        print(f"  - {zone.value}: {backlight.get_zone_color(zone)}")
    return 0


def command_set(backlight: KeyboardBacklight, args: argparse.Namespace) -> int:
    if args.brightness is None and args.color is None:
        raise ValueError("set requires at least one of --brightness or --color")

    if args.brightness is not None:
        backlight.set_brightness(args.brightness)
        print(f"set brightness={args.brightness}")

    if args.color is not None:
        if args.zone:
            zone = Zone(args.zone)
            backlight.set_zone_color(zone, args.color)
            print(f"set zone {zone.value} color={args.color}")
        else:
            backlight.set_all_zones(args.color)
            print(f"set all zones color={args.color}")

    return 0


def command_watch_input(args: argparse.Namespace) -> int:
    watcher = InputWatcher(device_name=args.device_name)
    for index, timestamp in enumerate(
        watcher.keypress_timestamps(max_events=args.count), start=1
    ):
        print(f"{index}: {timestamp:.6f}")
    return 0


def command_run(backlight: KeyboardBacklight, args: argparse.Namespace) -> int:
    device_name = getattr(args, "device_name", DEFAULT_KEYBOARD_NAME)
    base_brightness = getattr(args, "base_brightness", DEFAULT_BASE_BRIGHTNESS)
    keypress_boost = getattr(args, "keypress_boost", DEFAULT_KEYPRESS_BOOST)
    fade_seconds = getattr(args, "fade_seconds", DEFAULT_FADE_SECONDS)
    hue_speed = getattr(args, "hue_speed", DEFAULT_HUE_SPEED)
    frame_interval = getattr(args, "frame_interval", DEFAULT_FRAME_INTERVAL)

    watcher = InputWatcher(device_name=device_name)
    profile = DefaultProfile(
        base_brightness=base_brightness,
        keypress_boost=keypress_boost,
        fade_seconds=fade_seconds,
        hue_speed_degrees_per_second=hue_speed,
    )
    runtime = ProfileRuntimeConfig(frame_interval_sec=frame_interval)
    run_default_profile(backlight, watcher.keypress_timestamps(), profile, runtime=runtime)
    return 0


def command_self_test(backlight: KeyboardBacklight, args: argparse.Namespace) -> int:
    run_backlight_self_test(
        backlight,
        brightness=args.brightness,
        hue_steps=args.hue_steps,
        zone_dwell_sec=args.zone_dwell,
        sweep_dwell_sec=args.sweep_dwell,
        sweep_mode=args.sweep_mode,
        restore_state=not args.no_restore,
    )
    print("self-test complete")
    return 0


def command_zone_diagnose(backlight: KeyboardBacklight, args: argparse.Namespace) -> int:
    print("phase 1/3: isolated zone color holds (R/G/B/W)")
    print(f"phase 2/3: rainbow sweep ({args.sweep_mode} mode)")
    print("phase 3/3: linked-zone probes")
    log = None
    if args.verbose:
        def verbose_log(msg: str) -> None:
            print(f"[diag] {msg}")

        log = verbose_log

    groups = run_slow_zone_diagnostics(
        backlight,
        brightness=args.brightness,
        zone_dwell_sec=args.zone_dwell,
        sweep_steps=args.sweep_steps,
        sweep_dwell_sec=args.sweep_dwell,
        probe_dwell_sec=args.probe_dwell,
        sweep_mode=args.sweep_mode,
        restore_state=not args.no_restore,
        log=log,
    )

    print("zone-diagnose complete")
    print("linked groups (from sysfs readback):")
    for group in groups:
        print(f"  - {', '.join(zone.value for zone in group)}")
    print(
        "note: physical LED linkage can still exist even when sysfs files appear independent."
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "run":
            backlight = (
                KeyboardBacklight()
                if args.sysfs_path is None
                else KeyboardBacklight(sysfs_path=args.sysfs_path)
            )
            return command_run(backlight, args)
        if args.command == "status":
            backlight = (
                KeyboardBacklight()
                if args.sysfs_path is None
                else KeyboardBacklight(sysfs_path=args.sysfs_path)
            )
            return command_status(backlight)
        if args.command == "set":
            backlight = (
                KeyboardBacklight()
                if args.sysfs_path is None
                else KeyboardBacklight(sysfs_path=args.sysfs_path)
            )
            return command_set(backlight, args)
        if args.command == "watch-input":
            return command_watch_input(args)
        if args.command == "self-test":
            backlight = (
                KeyboardBacklight()
                if args.sysfs_path is None
                else KeyboardBacklight(sysfs_path=args.sysfs_path)
            )
            return command_self_test(backlight, args)
        if args.command == "zone-diagnose":
            backlight = (
                KeyboardBacklight()
                if args.sysfs_path is None
                else KeyboardBacklight(sysfs_path=args.sysfs_path)
            )
            return command_zone_diagnose(backlight, args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
