#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_ROOT="${ROOT_DIR}/logs/service-health"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="${LOG_ROOT}/${STAMP}"
COMBINED_LOG="${RUN_DIR}/combined.log"

mkdir -p "${RUN_DIR}"

run_check() {
  local name="$1"
  shift
  local out="${RUN_DIR}/${name}.log"
  local rc=0

  {
    echo "===== ${name} ====="
    echo "cmd: $*"
    echo "time: $(date --iso-8601=seconds)"
    if "$@"; then
      rc=0
    else
      rc=$?
    fi
    echo "exit_code: ${rc}"
  } >"${out}" 2>&1

  {
    echo
    echo "##### ${name} #####"
    cat "${out}"
  } | tee -a "${COMBINED_LOG}" >/dev/null

  return 0
}

run_check service_is_active systemctl --user is-active kbd-pulse.service
run_check service_status systemctl --user status kbd-pulse.service --no-pager
run_check service_journal journalctl --user -u kbd-pulse.service -n 80 --no-pager
run_check session_groups id -nG
run_check input_group_check bash -lc "id -nG | tr ' ' '\n' | grep '^input$'"
run_check sysfs_permissions ls -l \
  /sys/class/leds/system76::kbd_backlight/brightness \
  /sys/class/leds/system76::kbd_backlight/color_*

if command -v uv >/dev/null 2>&1; then
  run_check cli_status bash -lc "cd '${ROOT_DIR}' && uv run kbd-pulse status"
else
  {
    echo "===== cli_status ====="
    echo "uv not found in PATH"
    echo "exit_code: 127"
  } >"${RUN_DIR}/cli_status.log"
fi

SUMMARY="${RUN_DIR}/summary.log"
{
  echo "run_dir: ${RUN_DIR}"
  echo
  echo "key_findings:"
  rg -n "Permission denied|Failed|error:|not found|exit_code: [1-9]" "${RUN_DIR}" || true
} | tee "${SUMMARY}" >/dev/null

echo "logs written to: ${RUN_DIR}"
echo "summary: ${SUMMARY}"
