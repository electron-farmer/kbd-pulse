from __future__ import annotations

import time
from collections.abc import Callable

from kbd_pulse.backlight import KeyboardBacklight, Zone
from kbd_pulse.self_test import REGION_TEST_COLORS, _hue_hex


def _connected_components(
    zones: tuple[Zone, ...], edges: set[tuple[Zone, Zone]]
) -> list[tuple[Zone, ...]]:
    unvisited = set(zones)
    groups: list[tuple[Zone, ...]] = []

    adjacency: dict[Zone, set[Zone]] = {zone: {zone} for zone in zones}
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)

    while unvisited:
        start = next(iter(unvisited))
        stack = [start]
        component: set[Zone] = set()
        while stack:
            zone = stack.pop()
            if zone in component:
                continue
            component.add(zone)
            stack.extend(adjacency[zone] - component)
        unvisited -= component
        groups.append(tuple(sorted(component, key=lambda z: z.value)))

    return sorted(groups, key=lambda g: g[0].value)


def detect_linked_zones(backlight: KeyboardBacklight) -> list[tuple[Zone, ...]]:
    return detect_linked_zones_with_probe(backlight, probe_dwell_sec=0, sleep=lambda _: None)


def detect_linked_zones_with_probe(
    backlight: KeyboardBacklight,
    *,
    probe_dwell_sec: float,
    sleep: Callable[[float], None],
    log: Callable[[str], None] | None = None,
) -> list[tuple[Zone, ...]]:
    zones = backlight.available_zones
    if not zones:
        return []

    unique_markers = {
        Zone.LEFT: "F10A0A",
        Zone.CENTER: "0AF10A",
        Zone.RIGHT: "0A0AF1",
        Zone.EXTRA: "F1F10A",
    }

    edges: set[tuple[Zone, Zone]] = set()
    pre_probe_colors = {zone: backlight.get_zone_color(zone) for zone in zones}
    for source in zones:
        if log:
            log(f"probe source={source.value} color={unique_markers[source]}")
        backlight.set_all_zones("000000")
        backlight.set_zone_color(source, unique_markers[source])
        if probe_dwell_sec > 0:
            sleep(probe_dwell_sec)
        after = {zone: backlight.get_zone_color(zone) for zone in zones}

        for other in zones:
            if other == source:
                continue
            if after[other] != "000000":
                edge = tuple(sorted((source, other), key=lambda z: z.value))
                edges.add(edge)

    for zone, color in pre_probe_colors.items():
        backlight.set_zone_color(zone, color)

    groups = _connected_components(zones, edges)
    if log:
        log(
            "linked groups detected: "
            + " | ".join(",".join(zone.value for zone in group) for group in groups)
        )
    return groups


def run_slow_zone_diagnostics(
    backlight: KeyboardBacklight,
    *,
    brightness: int,
    zone_dwell_sec: float = 1.0,
    sweep_steps: int = 36,
    sweep_dwell_sec: float = 0.15,
    probe_dwell_sec: float = 0.5,
    sweep_mode: str = "global",
    restore_state: bool = True,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] | None = None,
) -> list[tuple[Zone, ...]]:
    if sweep_steps < 1:
        raise ValueError("sweep_steps must be at least 1")
    if zone_dwell_sec < 0 or sweep_dwell_sec < 0:
        raise ValueError("dwell durations must be >= 0")
    if sweep_mode not in {"auto", "independent", "global"}:
        raise ValueError("sweep_mode must be one of: auto, independent, global")

    zones = backlight.available_zones
    if not zones:
        raise ValueError("no zone files detected for this keyboard")

    original_brightness = backlight.get_brightness()
    original_colors = {zone: backlight.get_zone_color(zone) for zone in zones}

    try:
        backlight.set_brightness(brightness)
        backlight.set_all_zones("000000")
        if log:
            log(f"set brightness={brightness}")

        for zone in zones:
            backlight.set_all_zones("000000")
            for color in REGION_TEST_COLORS:
                backlight.set_zone_color(zone, color)
                if log:
                    log(f"phase1 zone={zone.value} color={color}")
                sleep(zone_dwell_sec)

        pre_groups = detect_linked_zones(backlight)
        effective_mode = sweep_mode
        if sweep_mode == "auto":
            if len(pre_groups) == 1 and len(pre_groups[0]) == len(zones):
                effective_mode = "global"
            else:
                effective_mode = "independent"
        if log:
            log(f"phase2 effective_mode={effective_mode}")

        for step in range(sweep_steps):
            base_hue = step / sweep_steps
            if effective_mode == "global":
                color = _hue_hex(base_hue)
                backlight.set_all_zones(color)
                if log:
                    log(f"phase2 step={step + 1}/{sweep_steps} global={color}")
            else:
                for index, zone in enumerate(zones):
                    zone_hue = (base_hue + (index / len(zones))) % 1.0
                    color = _hue_hex(zone_hue)
                    backlight.set_zone_color(zone, color)
                    if log:
                        log(
                            f"phase2 step={step + 1}/{sweep_steps} zone={zone.value} color={color}"
                        )
            sleep(sweep_dwell_sec)

        return detect_linked_zones_with_probe(
            backlight,
            probe_dwell_sec=probe_dwell_sec,
            sleep=sleep,
            log=log,
        )
    finally:
        if restore_state:
            for zone, color in original_colors.items():
                backlight.set_zone_color(zone, color)
            backlight.set_brightness(original_brightness)
