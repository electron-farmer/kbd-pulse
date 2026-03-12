#!/usr/bin/env bash
set -euo pipefail

UV_BIN="$(command -v uv || true)"
if [[ -z "${UV_BIN}" ]]; then
  echo "uv not found in PATH"
  exit 1
fi

LOG_DIR="logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/slow-zone-test-$(date +%Y%m%d-%H%M%S).log"
echo "writing log: ${LOG_FILE}"

exec > >(tee -a "${LOG_FILE}") 2>&1

if [[ $# -gt 0 ]]; then
  sudo "${UV_BIN}" run kbd-pulse zone-diagnose --verbose "$@"
  exit 0
fi

sudo "${UV_BIN}" run kbd-pulse zone-diagnose \
  --brightness 200 \
  --zone-dwell 1.2 \
  --sweep-steps 30 \
  --sweep-dwell 0.25 \
  --probe-dwell 0.8 \
  --sweep-mode global \
  --verbose \
  --no-restore
