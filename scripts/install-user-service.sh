#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_TEMPLATE="${ROOT_DIR}/systemd/kbd-pulse.service"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_PATH="${UNIT_DIR}/kbd-pulse.service"

if [[ ! -f "${UNIT_TEMPLATE}" ]]; then
  echo "missing template: ${UNIT_TEMPLATE}"
  exit 1
fi

UV_BIN="${UV_BIN:-${HOME}/.local/bin/uv}"
if [[ ! -x "${UV_BIN}" ]]; then
  echo "uv binary not found or not executable: ${UV_BIN}"
  echo "set UV_BIN=/path/to/uv and rerun"
  exit 1
fi

mkdir -p "${UNIT_DIR}"
cp "${UNIT_TEMPLATE}" "${UNIT_PATH}"

sed -i "s|^WorkingDirectory=.*$|WorkingDirectory=${ROOT_DIR}|" "${UNIT_PATH}"
sed -i "s|^ExecStart=.*$|ExecStart=${UV_BIN} run kbd-pulse|" "${UNIT_PATH}"

systemctl --user daemon-reload
systemctl --user enable --now kbd-pulse.service

echo "installed: ${UNIT_PATH}"
echo "status: systemctl --user status kbd-pulse.service"
echo "logs:   journalctl --user -u kbd-pulse.service -f"
