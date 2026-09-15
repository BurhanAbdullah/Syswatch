# Ubuntu 24.04 systemd validation host

SYSWATCH service lifecycle validation requires a genuine Ubuntu host/VM with `systemd` running as PID 1. GitHub Codespaces and ordinary containers commonly use a container init process instead, so `systemctl` lifecycle checks there are not release evidence.

## Prepare the host

On a fresh Ubuntu 24.04 VM/server:

```bash
sudo bash scripts/bootstrap_ubuntu24_systemd_host.sh
```

Confirm:

```bash
ps -p 1 -o comm=
# systemd
```

## Validate a package

Copy the exact release `.deb` to the host, then run:

```bash
sudo bash tests/test_ubuntu_systemd_host.sh /path/to/syswatch_1.0.0_amd64.deb
```

The validator checks the real installation contract, including:

- Ubuntu 24.04 and `systemd` as PID 1;
- package installation, service enablement and active state;
- dedicated `syswatch` account and state permissions;
- systemd least-privilege directives;
- installed CLI/version/doctor/status;
- exact `/api/health` response;
- signal and demo paths;
- restart and stop/start lifecycle;
- journal logging evidence; and
- purge cleanup.

For an explicit upgrade test, provide a second package:

```bash
sudo SYSWATCH_UPGRADE_DEB=/path/to/syswatch_1.0.1_amd64.deb \
  bash tests/test_ubuntu_systemd_host.sh /path/to/syswatch_1.0.0_amd64.deb
```

## Self-hosted GitHub Actions runner

A persistent Ubuntu host can also be registered as a GitHub Actions self-hosted runner. Registration is intentionally kept outside repository scripts because runner registration tokens are short-lived credentials and must be supplied interactively through GitHub's runner setup flow.

Recommended runner labels:

```text
self-hosted, linux, x64, ubuntu-24.04, syswatch-systemd
```

After the runner is online, a workflow job can target `runs-on: [self-hosted, linux, x64, ubuntu-24.04, syswatch-systemd]` and execute the same host validator. Do not add such a job until the host is actually registered; otherwise the workflow will remain queued.

## Release rule

A Codespace/package test can establish CLI and package behavior, but it does not establish real systemd lifecycle behavior. A production Linux release should retain both forms of evidence and must not label the systemd gate as passed until a genuine Ubuntu host reports a passing result.
