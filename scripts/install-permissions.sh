#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULE_SRC="${ROOT_DIR}/udev/99-kbd-pulse.rules"
RULE_DST="/etc/udev/rules.d/99-kbd-pulse.rules"

if [[ ! -f "${RULE_SRC}" ]]; then
  echo "missing udev rule file: ${RULE_SRC}"
  exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required to install udev rules"
  exit 1
fi

echo "installing udev rule -> ${RULE_DST}"
sudo install -D -m 0644 "${RULE_SRC}" "${RULE_DST}"

echo "ensuring user '${USER}' is in 'input' group"
sudo usermod -aG input "${USER}"

echo "reloading and triggering udev rules"
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add --subsystem-match=leds

# Apply immediately for current session even if udev event timing is delayed.
if [[ -d "/sys/class/leds/system76::kbd_backlight" ]]; then
  sudo chgrp input /sys/class/leds/system76::kbd_backlight/brightness \
    /sys/class/leds/system76::kbd_backlight/color_* || true
  sudo chmod g+w /sys/class/leds/system76::kbd_backlight/brightness \
    /sys/class/leds/system76::kbd_backlight/color_* || true
fi

if id -nG "${USER}" | tr ' ' '\n' | grep -qx "input"; then
  echo "group membership already active for this session"
else
  echo "IMPORTANT: log out and back in so 'input' group membership takes effect."
fi

echo "permission setup complete"
