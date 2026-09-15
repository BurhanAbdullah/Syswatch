#!/usr/bin/env bash
set -euo pipefail

# Prepare a clean Ubuntu 24.04 host/VM for SYSWATCH systemd validation.
# This script does not register a GitHub self-hosted runner and does not
# require GitHub credentials. Run it as root on the target host.

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash scripts/bootstrap_ubuntu24_systemd_host.sh" >&2
  exit 1
fi

OS_ID="$(. /etc/os-release && printf '%s' "$ID")"
OS_VERSION="$(. /etc/os-release && printf '%s' "$VERSION_ID")"
[[ "$OS_ID" == "ubuntu" && "$OS_VERSION" == "24.04" ]] || {
  echo "SYSWATCH requires Ubuntu 24.04 for release host validation; detected $OS_ID $OS_VERSION" >&2
  exit 1
}

PID1="$(cat /proc/1/comm 2>/dev/null || true)"
[[ "$PID1" == "systemd" ]] || {
  echo "systemd must be PID 1; detected '$PID1'. Do not use a container for this host test." >&2
  exit 1
}

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git python3 systemd passwd dpkg

systemctl daemon-reload
systemctl reset-failed

printf '\nSYSWATCH Ubuntu host ready\n'
printf '  OS: %s %s\n' "$OS_ID" "$OS_VERSION"
printf '  PID 1: %s\n' "$PID1"
printf '  systemd: %s\n' "$(systemctl --version | head -n1)"
printf '  python3: %s\n' "$(python3 --version)"
printf '  curl: %s\n' "$(curl --version | head -n1)"
printf '\nNext: copy the SYSWATCH .deb to this host and run:\n'
printf '  sudo bash tests/test_ubuntu_systemd_host.sh /path/to/syswatch_VERSION_amd64.deb\n'
printf '\nOptional upgrade validation:\n'
printf '  sudo SYSWATCH_UPGRADE_DEB=/path/to/syswatch_NEXT_VERSION_amd64.deb \\\n'
printf '    bash tests/test_ubuntu_systemd_host.sh /path/to/syswatch_VERSION_amd64.deb\n'
