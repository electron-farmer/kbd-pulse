# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`kbd-pulse` is a Python daemon that watches keyboard input events and dynamically controls the System76 keyboard RGB backlight. It reacts to typing speed and patterns, animating the per-zone backlight (left, center, right, extra) via the sysfs interface at `/sys/class/leds/system76::kbd_backlight/`.

Target platform: Pop!_OS 24.04 LTS (Ubuntu Noble), System76 hardware, Wayland session.

## Workflow

After completing any set of changes:
1. Ensure work is on a feature branch (not `main`)
2. Commit with a descriptive message
3. Push the branch and open a PR using `gh pr create` if one doesn't already exist

```bash
git checkout -b <branch-name>        # create feature branch if needed
git add <files>
git commit -m "description"
git push -u origin <branch-name>
gh pr create --title "..." --body "..."  # open PR if none exists
gh pr view                               # check existing PR status
```

## Commands

```bash
# Install dependencies (SETUPTOOLS_USE_DISTUTILS=local required for evdev on Python 3.13)
SETUPTOOLS_USE_DISTUTILS=local uv sync

# Run the daemon
uv run kbd-pulse

# Run with elevated permissions (required for /dev/input access)
sudo uv run kbd-pulse
```

## Architecture

### Package Management
Uses `uv` for dependency management. Dependencies are declared in `pyproject.toml`. Never use `pip install` directly — always `uv add <package>`.

### Key Dependencies
- **`evdev`** — reads raw keyboard events from `/dev/input/event*`

### Sysfs Interface
The System76 keyboard exposes 4 independent RGB zones:

| File | Zone |
|------|------|
| `/sys/class/leds/system76::kbd_backlight/color_left` | Left section |
| `/sys/class/leds/system76::kbd_backlight/color_center` | Center section |
| `/sys/class/leds/system76::kbd_backlight/color_right` | Right section |
| `/sys/class/leds/system76::kbd_backlight/color_extra` | Extra (e.g. numpad/touchpad) |
| `/sys/class/leds/system76::kbd_backlight/brightness` | Master brightness (0–255) |

Colors are written as hex strings (`RRGGBB`). Brightness is an integer 0–255.

### Permissions
`/dev/input/event*` requires membership in the `input` group, or root. `/sys/class/leds/system76::kbd_backlight/` requires root or udev rules to be writable by the user.

## Project Plan

### Prior Art
Two existing Python projects were reviewed for reference:

- **[keyboard-color-switcher](https://github.com/ahoneybun/keyboard-color-switcher)** — GTK GUI for setting static zone colors. Good reference for the sysfs abstraction layer (`KeyboardBacklight` class, `Position` enum, `read_file`/`write_file` helpers). Last active 2024.
- **[System76-Backlight-Manager-cli](https://github.com/JeffLabonte/System76-Backlight-Manager-cli)** — CLI with breathe/static modes and model-aware path resolution. Good reference for the `breathe()` ramp-up/ramp-down pattern and service structure.

Neither project reacts to live input — that's the gap `kbd-pulse` fills.

### Module Structure

```
kbd-pulse/
├── kbd_pulse/
│   ├── __init__.py
│   ├── __main__.py          # entrypoint, arg parsing, daemon loop
│   ├── backlight.py         # sysfs read/write, zone abstraction
│   ├── input_watcher.py     # evdev event loop, keypress detection
│   ├── animator.py          # brightness/color transitions, fade logic
│   └── config.py            # load/parse config file (TOML)
├── systemd/
│   └── kbd-pulse.service    # user systemd service unit
├── udev/
│   └── 99-kbd-pulse.rules   # udev rules for unprivileged sysfs access
├── pyproject.toml
└── CLAUDE.md
```

### Implementation Phases

#### Phase 1 — Core backlight control
- `backlight.py`: detect zones from sysfs, read/write brightness and color per zone
- Graceful fallback if a zone file doesn't exist (single-zone keyboards)
- Unit test with mocked sysfs paths (tmp dirs)

#### Phase 2 — Input watching
- `input_watcher.py`: use `evdev` to find the keyboard device by name (`AT Translated Set 2 keyboard`), listen for `EV_KEY` down events
- Emit a timestamp stream for each keypress
- Handle device disconnect/reconnect gracefully

#### Phase 3 — Reactive animation
- `animator.py`: maintain a rolling keypress rate (keypresses/sec over a sliding window)
- Map rate → brightness on a configurable curve (e.g. linear, exponential)
- Fade brightness back to idle level after configurable timeout
- Ripple effect: on keypress, briefly boost center zone then propagate outward to left/right

#### Phase 4 — Config & profiles
- `config.py`: load `~/.config/kbd-pulse/config.toml`
- Configurable: idle brightness, active brightness, idle color, active color, fade duration, decay rate, animation style
- Hot-reload config on SIGHUP

#### Phase 5 — Systemd + udev
- `systemd/kbd-pulse.service`: user-level service, `Restart=on-failure`
- `udev/99-kbd-pulse.rules`: grant the `input` group write access to `/sys/class/leds/system76::kbd_backlight/*`
- Install script or `setup_user.sh` hook in `setup_bash`

### Permissions Strategy
Rather than running as root, use a udev rule to make the sysfs backlight nodes group-writable by `input`. The user already needs to be in the `input` group for evdev access, so no new group is needed.

```
ACTION=="add", SUBSYSTEM=="leds", KERNEL=="system76::kbd_backlight", \
  RUN+="/bin/chgrp input /sys%p/brightness /sys%p/color_*", \
  RUN+="/bin/chmod g+w /sys%p/brightness /sys%p/color_*"
```
