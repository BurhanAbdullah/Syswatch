#!/usr/bin/env bash
set -Eeuo pipefail

# Safe, non-privileged CLI contract checks. These intentionally avoid starting
# services, mutating the host, or executing containment actions. Real service
# lifecycle validation remains the Ubuntu 24.04/systemd release gate.
ROOT="${SYSWATCH_ROOT:-$PWD}"
export SYSWATCH_ROOT="$ROOT"

launcher="$ROOT/bin/syswatch"
test -x "$launcher"

bash -n "$launcher"

help_out="$($launcher --help)"
for command_name in start stop restart status health dashboard open logs scan demo signal version doctor uninstall help; do
  grep -Fq "  ${command_name} " <<<"$help_out"
done

[[ "$($launcher dashboard)" == "${SYSWATCH_URL:-http://127.0.0.1:8080}" ]]

version_out="$($launcher version)"
grep -Eq '^SYSWATCH (development build|[0-9]+\.[0-9]+\.[0-9]+)' <<<"$version_out"

doctor_out="$($launcher doctor)"
grep -Fq 'SYSWATCH doctor' <<<"$doctor_out"
grep -Fq 'service:' <<<"$doctor_out"

status_out="$($launcher status)"
grep -Eq 'SYSWATCH: non-systemd container|Active:|Loaded:' <<<"$status_out"

logs_out="$($launcher logs)"
grep -Eq 'SYSWATCH: non-systemd container|-- No entries --|^[A-Z][a-z]{2} ' <<<"$logs_out"

if "$launcher" __invalid__ >/dev/null 2>&1; then
  echo 'invalid command unexpectedly succeeded' >&2
  exit 1
fi

echo 'validated safe non-systemd CLI contract: help, dashboard, version, doctor, status, logs, and invalid-command handling'
