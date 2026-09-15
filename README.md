# SYSWATCH

**SYSWATCH** is a local-first endpoint-security project that turns host telemetry and normalized security signals into causal attack context for a local operator console.

> Observe → Correlate → Understand → Respond

SYSWATCH is under active development. This repository deliberately separates what is implemented, what has been exercised in CI, and what is not yet a supported release claim.

## Product goal: install, then use

SYSWATCH is being productized as a **command-first local security tool**, not just a research repository. A finished supported release must let an operator install it, verify it, control the service, inspect health/logs, open the dashboard, run a safe scan, and exercise the synthetic signal bridge without editing Python files.

The intended operator experience is:

```bash
# install a verified release
sudo apt install ./syswatch_<version>_amd64.deb

# operate SYSWATCH from the shell
syswatch start
syswatch status
syswatch health
syswatch dashboard
syswatch logs
syswatch scan
syswatch signal NEW-PORT "Port 2222 opened"
syswatch uninstall
```

The repository now contains a dependency-free command launcher under `bin/syswatch` implementing this command contract. The packaged installer/DEB integration is still a release-readiness task and must be exercised in the real Ubuntu 24.04 lifecycle before the command surface is promoted as a released interface.

For development/testing, the current installer already creates `/usr/local/bin/syswatch` and `/usr/local/bin/syswatch-signal` and supports service lifecycle commands. `main` remains a development branch and is not a substitute for a versioned release.

## Current verified scope

The release-readiness path is currently validated on **Ubuntu 24.04 LTS / Linux amd64** in GitHub-hosted CI. The Python test matrix covers Python **3.10, 3.11, 3.12 and 3.13**.

The repository currently exercises:

- local host/resource telemetry and a localhost dashboard;
- network, firewall, Wi-Fi and SSH posture where the operating system exposes that information;
- process lineage, filesystem behavior, DNS/network intelligence and behavioral baselining;
- deterministic temporal correlation of normalized security signals into causal chains;
- bounded local prediction and read-only policy/evidence output;
- protected-state integrity, corruption handling, bounded resource/nesting checks, race regression and persistence soak coverage;
- a least-privilege systemd service using a dedicated `syswatch` account and `/var/lib/syswatch` state boundary;
- standalone installer first-install failure rollback and failed-upgrade rollback on Ubuntu 24.04;
- deterministic Debian package build plus install → exact application health → upgrade → exact application health → purge lifecycle validation;
- pinned GitHub Actions, dependency audit/SBOM generation and a stdlib-only application runtime dependency boundary;
- a versioned release workflow that requires lifecycle verification before provenance attestation and publication.

These are repository/CI validation statements, not claims of universal malware detection or production EDR certification.

## Release status

**No verified public SYSWATCH release is published yet.**

The release workflow requires a semantic version tag (`vX.Y.Z`) and checks that the tag points to the exact checked-out commit. It then builds the versioned Debian artifact, verifies its checksum and byte-for-byte reproducibility, runs the package lifecycle gate, creates provenance only after that lifecycle succeeds, and only then permits GitHub release publication.

Until that workflow has produced and validated a real versioned artifact, this README does not provide a release download link, checksum, provenance link, or claim that a release exists.

## Install for development/testing

There is not yet a public versioned release install command. For development or repository testing on the currently validated Linux target, clone the repository and select the development branch explicitly:

```bash
git clone https://github.com/BurhanAbdullah/Syswatch.git
cd Syswatch
sudo SYSWATCH_REF=main ./install.sh
```

The standalone installer stages the incoming tree before replacing the active installation, uses a dedicated non-login `syswatch` service account, keeps persistent state under `/var/lib/syswatch`, and requires the exact local application-health contract before committing a new install or upgrade. A failed first installation is required to leave no SYSWATCH host residue; a failed upgrade is required to restore the prior code, state, service unit, wrappers and service state.

`main` is a development branch and can change. It is **not** a substitute for a versioned release artifact.

### Local health verification

```bash
syswatch status
syswatch logs
curl -fsS http://127.0.0.1:8080/api/health
```

A healthy service currently returns the application identity contract:

```json
{"ok": true, "service": "syswatch", "agent": "online"}
```

The dashboard and API bind to loopback by default:

```text
http://127.0.0.1:8080
```

Do not expose the dashboard directly to an untrusted network without an explicit authentication and network-security design.

## Command-line product contract

The command surface is intentionally designed to be understandable without knowing the internal Python modules:

| Command | Purpose |
|---|---|
| `syswatch start` | Start the local service and verify health |
| `syswatch stop` | Stop the service |
| `syswatch restart` | Restart and verify health |
| `syswatch status` | Show systemd service state |
| `syswatch health` | Verify the exact local health contract |
| `syswatch dashboard` | Print the local dashboard URL |
| `syswatch open` | Open the dashboard when a desktop browser opener exists |
| `syswatch logs` | Show recent service logs |
| `syswatch scan` | Run the bounded safe local scan |
| `syswatch demo` | Feed synthetic demonstration signals |
| `syswatch signal ...` | Send a normalized security signal |
| `syswatch version` | Show installed release/ref information |
| `syswatch doctor` | Run local installation diagnostics |
| `syswatch uninstall` | Remove SYSWATCH |

No command in this interface enables privileged host mutation or real containment. The response/containment boundary remains fail-closed.

## Uninstall

For a standalone development installation:

```bash
sudo /opt/syswatch/uninstall.sh
```

or, through the command interface:

```bash
sudo syswatch uninstall
```

The Debian lifecycle gate separately verifies package purge behavior, including removal of the service, wrappers, state and dedicated account/group.

## Architecture

```text
Linux endpoint
    │
    ├── host / process / network / security collectors
    ▼
normalized bounded signals
    │
    ▼
temporal correlation + causal evidence
    │
    ├── protected local state
    ├── bounded prediction / policy evidence
    ▼
localhost API + operator dashboard
```

SYSWATCH is local-first: the current dashboard does not require a cloud account. Telemetry that is unavailable from the host is intended to remain unavailable rather than being fabricated.

## Security boundary

SYSWATCH is deliberately conservative about response authority and security claims.

- It does **not** claim 99.99% detection accuracy, universal malware detection, or guaranteed detection.
- Current causal detection is deterministic and depends on the normalized signals and temporal windows that are actually present.
- Synthetic adversarial tests validate controlled signal patterns; they are not independent evidence of real-world detection efficacy.
- The policy/evidence API is read-only.
- The default containment execution path **does not execute containment** when no explicitly configured adapter is present.
- Privileged host mutation and real containment remain disabled until the execution chain is separately validated end-to-end.
- The service runs under a dedicated non-login account with an empty capability bounding set in the validated service contract.
- Protected state is local and bounded; corruption and failed atomic replacement paths are tested to fail closed or preserve the prior known-good state where designed.
- No independent security evaluation has been completed or claimed.

## Platform support and non-claims

The only platform currently used for release-lifecycle claims is the tested Ubuntu 24.04 / Linux amd64 target.

**Cross-platform agents are not currently supported or verified.** macOS, Windows, other Linux distributions, RHEL-family packaging, IoT/edge targets and additional architectures must not be presented as supported until they have their own executable CI/release evidence.

Likewise, there is currently no claim of production EDR status, independent certification, signed binary distribution beyond whatever the verified release workflow eventually produces, or universal false-positive/detection performance.

## Validation

Safe synthetic and regression coverage includes, among other cases:

- signal-order variation and correlation-window expiry;
- noisy benign telemetry and multiple simultaneous chains;
- protected-state malformed/corrupted/oversized input handling;
- bounded nesting and adversarial state corpus cases;
- concurrent protected-state initialization;
- atomic replacement failure preservation;
- repeated save/load/integrity-health soak coverage;
- standalone installer first-install failure rollback;
- standalone installer failed-upgrade rollback;
- Debian install/upgrade/purge lifecycle with exact SYSWATCH health JSON;
- least-privilege service contract checks;
- immutable GitHub Action reference enforcement;
- dependency audit, SBOM and runtime dependency-boundary checks.

Run the repository tests from a development checkout with:

```bash
python3 -m pytest -q
```

The adversarial tests use synthetic telemetry and do not execute exploit or destructive payloads.

## Security event bridge

Existing modules can feed normalized signals to the local bridge, for example:

```bash
syswatch-signal NEW-PORT "Port 2222 opened"
syswatch-signal REVERSE-SHELL "unexpected shell process"
syswatch-signal FILE-INTEG "/tmp/.implant written"
syswatch-signal CRON-PERSIST "new scheduled task"
syswatch-signal C2-CONNECT "unexpected outbound endpoint"
syswatch-signal PRIVESC "new SUID executable"
```

A built-in demonstration injects synthetic telemetry only; it does not attack the host:

```bash
cd /opt/syswatch
bash syswatch/agents/feed_signal.sh --demo
```

## Release-readiness roadmap

Completed repository gates include protected-state hardening, bounded adversarial/race/soak regression coverage, deterministic Debian packaging, least-privilege service hardening, installer rollback validation, exact health-contract validation, supply-chain checks, release reproducibility checks and provenance/lifecycle ordering in the release workflow.

The remaining product/release gates are intentionally narrower:

1. Integrate the command launcher into the real standalone installer and Debian package, then exercise the full command contract on Ubuntu 24.04.
2. Create/execute a real semantic-version release tag on the supported Linux target.
3. Review the resulting versioned artifact, SHA-256 checksum, byte-for-byte rebuild evidence, lifecycle evidence and provenance attestation.
4. Perform the final security/reliability/reproducibility audit against that actual release evidence.
5. Publish and synchronize the SYSWATCH product website only after the verified release exists.
6. Add Windows as a released platform only after the versioned executable passes native telemetry/API, deterministic-build, smoke, checksum and provenance gates.
7. Add any additional platform/distribution only after equivalent executable validation exists.
8. Obtain an independent external security evaluation before making that claim.

Issue #4 tracks the security maturity/release-readiness roadmap and remains open while these gates are incomplete.

## Design principles

**Evidence over hype.** Claims should be traceable to implementation and executable validation.

**Local-first.** Core monitoring remains useful without a cloud account.

**Least privilege.** Monitoring authority must not silently become mutation authority.

**Bounded behavior.** Inputs, state, resource use and failure paths should have explicit limits.

**Transactional lifecycle.** Installation and upgrade failure should preserve or restore a known-good host state.

**Inspectable.** Detection, evidence and release behavior should remain understandable and auditable.

## Project status

SYSWATCH is an active security engineering project moving toward its first evidence-backed release. Engineering gates are substantially stronger than an ordinary development install, but the project is **not declared release-ready until an actual versioned release artifact clears the configured workflow and final audit**.

## License

See [`LICENSE`](LICENSE).
