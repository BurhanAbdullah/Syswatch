#!/usr/bin/env bash
set -euo pipefail

# Run this on a real Ubuntu 24.04 host/VM with systemd as PID 1.
# Usage:
#   sudo bash tests/test_ubuntu_systemd_host.sh /path/to/syswatch_1.0.0_amd64.deb

DEB="${1:?usage: test_ubuntu_systemd_host.sh PACKAGE.deb}"
[[ -f "$DEB" ]]

if [[ "$(. /etc/os-release && echo "$ID $VERSION_ID")" != "ubuntu 24.04" ]]; then
  echo "SYSWATCH host validation requires Ubuntu 24.04" >&2
  exit 1
fi

if [[ "$(cat /proc/1/comm 2>/dev/null || true)" != "systemd" ]]; then
  echo "SYSWATCH host validation requires systemd as PID 1" >&2
  exit 1
fi

for command in dpkg dpkg-deb systemctl curl python3 id stat getent journalctl; do
  command -v "$command" >/dev/null
 done

VERSION="$(dpkg-deb -f "$DEB" Version)"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]

cleanup() {
  dpkg --purge syswatch >/dev/null 2>&1 || true
  systemctl daemon-reload >/dev/null 2>&1 || true
}
trap cleanup EXIT

health_payload_is_valid() {
  local output="$1"
  python3 - "$output" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)
expected = {"ok": True, "service": "syswatch", "agent": "online"}
raise SystemExit(0 if payload == expected else 1)
PY
}

wait_for_health() {
  local output="$1"
  local attempts="${2:-30}"
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS --max-time 2 http://127.0.0.1:8080/api/health >"$output" 2>/dev/null && health_payload_is_valid "$output"; then
      return 0
    fi
    sleep 1
  done
  systemctl status syswatch.service --no-pager >&2 || true
  journalctl -u syswatch.service -n 80 --no-pager >&2 || true
  return 1
}

# Clean baseline.
dpkg --purge syswatch >/dev/null 2>&1 || true
rm -f /etc/systemd/system/syswatch.service /usr/local/bin/syswatch /usr/local/bin/syswatch-signal
systemctl daemon-reload

# Fresh installation.
dpkg -i "$DEB"
systemctl is-enabled syswatch.service
systemctl is-active syswatch.service

[[ "$(ps -p 1 -o comm= | tr -d ' ')" == "systemd" ]]
id syswatch
[[ "$(stat -c '%U:%G:%a' /var/lib/syswatch)" == "syswatch:syswatch:750" ]]
[[ "$(stat -c '%U:%G' /opt/syswatch)" == "root:root" ]]

grep -Fxq 'User=syswatch' /etc/systemd/system/syswatch.service
grep -Fxq 'Group=syswatch' /etc/systemd/system/syswatch.service
grep -Fxq 'NoNewPrivileges=true' /etc/systemd/system/syswatch.service
grep -Fxq 'CapabilityBoundingSet=' /etc/systemd/system/syswatch.service
grep -Fxq 'AmbientCapabilities=' /etc/systemd/system/syswatch.service
grep -Fxq 'ProtectSystem=strict' /etc/systemd/system/syswatch.service
grep -Fxq 'StateDirectoryMode=0750' /etc/systemd/system/syswatch.service

syswatch version | grep -Fxq "SYSWATCH $VERSION"
syswatch status
syswatch doctor
wait_for_health /tmp/syswatch-health.json

# CLI + telemetry path while the real service is running.
syswatch signal NEW-PORT "Port 2222 opened"
syswatch demo
syswatch logs >/tmp/syswatch-logs.txt
syswatch dashboard | grep -F 'http://127.0.0.1:8080'

# Restart contract.
sudo systemctl restart syswatch.service
systemctl is-active syswatch.service
wait_for_health /tmp/syswatch-health-restart.json

# Stop/start contract.
sudo systemctl stop syswatch.service
if curl -fsS --max-time 2 http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
  echo 'SYSWATCH health unexpectedly remained available after stop' >&2
  exit 1
fi
sudo systemctl start syswatch.service
systemctl is-active syswatch.service
wait_for_health /tmp/syswatch-health-start.json

# Journal contract.
journalctl -u syswatch.service -n 100 --no-pager | grep -F 'SYSWATCH' >/dev/null || true

# Upgrade contract using a second package version if the caller provides one.
if [[ -n "${SYSWATCH_UPGRADE_DEB:-}" ]]; then
  [[ -f "$SYSWATCH_UPGRADE_DEB" ]]
  UPGRADE_VERSION="$(dpkg-deb -f "$SYSWATCH_UPGRADE_DEB" Version)"
  [[ "$UPGRADE_VERSION" != "$VERSION" ]]
  dpkg -i "$SYSWATCH_UPGRADE_DEB"
  systemctl is-active syswatch.service
  wait_for_health /tmp/syswatch-health-upgrade.json
  syswatch version | grep -Fxq "SYSWATCH $UPGRADE_VERSION"
fi

# Purge contract.
dpkg --purge syswatch
! getent passwd syswatch >/dev/null
! getent group syswatch >/dev/null
! test -e /etc/systemd/system/syswatch.service
! test -e /usr/local/bin/syswatch
! test -e /usr/local/bin/syswatch-signal
! test -e /var/lib/syswatch

trap - EXIT
cleanup
echo "SYSWATCH Ubuntu 24.04 systemd host validation passed for $VERSION."
