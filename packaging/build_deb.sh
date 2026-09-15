#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?version required, e.g. 1.0.0}"
SOURCE_REF="${2:-HEAD}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]

SOURCE_DATE_EPOCH="$(git show -s --format=%ct "$SOURCE_REF")"
ROOT="$(mktemp -d "${TMPDIR:-/tmp}/syswatch-deb.XXXXXX")"
trap 'rm -rf "$ROOT"' EXIT
mkdir -p "$ROOT/DEBIAN" "$ROOT/opt/syswatch" "$ROOT/usr/local/bin"
git archive --format=tar --prefix=syswatch/ "$SOURCE_REF" | tar -x -C "$ROOT/opt/syswatch" --strip-components=1

find "$ROOT/opt/syswatch" -print0 | xargs -0 touch --date="@$SOURCE_DATE_EPOCH"

cat > "$ROOT/DEBIAN/control" <<EOF
Package: syswatch
Version: ${VERSION}
Section: admin
Priority: optional
Architecture: amd64
Depends: python3, systemd, passwd
Maintainer: Burhan Abdullah
Description: SYSWATCH PRO host security monitoring
 Local-first host security monitoring and intrusion detection dashboard.
EOF
cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if ! getent group syswatch >/dev/null; then groupadd --system syswatch; fi
if ! getent passwd syswatch >/dev/null; then
  useradd --system --gid syswatch --home-dir /var/lib/syswatch --no-create-home --shell /usr/sbin/nologin syswatch
fi
install -d -m 0750 -o syswatch -g syswatch /var/lib/syswatch
chown -R root:root /opt/syswatch
install -m 0755 /opt/syswatch/bin/syswatch /usr/local/bin/syswatch
cat > /etc/systemd/system/syswatch.service <<SERVICE
[Unit]
Description=SYSWATCH Pro Host Security Monitor
After=network.target
[Service]
Type=simple
User=syswatch
Group=syswatch
WorkingDirectory=/opt/syswatch
Environment=SYSWATCH_STATE_DIR=/var/lib/syswatch
ExecStart=/usr/bin/python3 /opt/syswatch/syswatch/api/server.py
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=read-only
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
RestrictRealtime=true
CapabilityBoundingSet=
AmbientCapabilities=
ReadWritePaths=/var/lib/syswatch
StateDirectory=syswatch
StateDirectoryMode=0750
[Install]
WantedBy=multi-user.target
SERVICE
cat > /usr/local/bin/syswatch-signal <<'SIGNAL'
#!/bin/sh
set -e
export SYSWATCH_STATE_DIR="${SYSWATCH_STATE_DIR:-/var/lib/syswatch}"
exec /opt/syswatch/syswatch/agents/feed_signal.sh "$@"
SIGNAL
chmod 0755 /usr/local/bin/syswatch-signal
systemctl daemon-reload
systemctl enable syswatch.service
systemctl restart syswatch.service || systemctl start syswatch.service
EOF
chmod 755 "$ROOT/DEBIAN/postinst"
cat > "$ROOT/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
case "${1:-}" in
  remove)
    systemctl disable --now syswatch.service 2>/dev/null || true
    rm -f /etc/systemd/system/syswatch.service /usr/local/bin/syswatch /usr/local/bin/syswatch-signal
    systemctl daemon-reload 2>/dev/null || true
    ;;
  purge)
    systemctl disable --now syswatch.service 2>/dev/null || true
    rm -f /etc/systemd/system/syswatch.service /usr/local/bin/syswatch /usr/local/bin/syswatch-signal
    rm -rf /var/lib/syswatch
    if getent passwd syswatch >/dev/null; then userdel syswatch 2>/dev/null || true; fi
    if getent group syswatch >/dev/null; then groupdel syswatch 2>/dev/null || true; fi
    systemctl daemon-reload 2>/dev/null || true
    ;;
esac
EOF
chmod 755 "$ROOT/DEBIAN/postrm"

OUTPUT="syswatch_${VERSION}_amd64.deb"
SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" dpkg-deb --build --root-owner-group "$ROOT" "$OUTPUT" >/dev/null
printf 'SYSWATCH %s\nCommit %s\nSource-Date-Epoch %s\n' "$VERSION" "$(git rev-parse "$SOURCE_REF")" > RELEASE-METADATA.txt
sha256sum "$OUTPUT" > SHA256SUMS
