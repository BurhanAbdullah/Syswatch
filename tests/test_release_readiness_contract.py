from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE = WORKFLOWS / "release.yml"
WINDOWS = WORKFLOWS / "windows.yml"
SECURITY = WORKFLOWS / "security.yml"
WINDOWS_BUILD_REQUIREMENTS = ROOT / "requirements-windows-build.txt"
README = ROOT / "README.md"
INSTALLER = ROOT / "install.sh"
BUILDER = ROOT / "packaging" / "build_deb.sh"


def test_all_workflow_actions_are_immutable():
    pattern = re.compile(r"^\s*-?\s*uses:\s*[^@\s]+@([^\s#]+)")
    bad = []
    for path in WORKFLOWS.rglob("*.yml"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = pattern.match(line)
            if match and not re.fullmatch(r"[0-9a-fA-F]{40}", match.group(1)):
                bad.append(f"{path}:{lineno}: {match.group(1)}")
    assert not bad, "Unpinned GitHub Actions: " + ", ".join(bad)


def test_release_cannot_publish_before_all_artifact_gates():
    text = RELEASE.read_text(encoding="utf-8")
    lifecycle = text.index("name: Verify packaged install lifecycle")
    debian_attest = text.index("name: Attest Debian package provenance")
    windows_rebuild = text.index("name: Rebuild and verify byte-identical Windows executable")
    windows_smoke = text.index("name: Smoke-test released executable")
    windows_attest = text.index("name: Attest Windows executable provenance")
    publish_job = text.index("\n  publish:\n")
    publish = text.index("name: Create verified release")

    assert lifecycle < debian_attest < publish_job < publish
    assert windows_rebuild < windows_smoke < windows_attest < publish_job < publish
    assert "needs: [package, windows-package]" in text
    assert "tests/test_debian_lifecycle.sh" in text
    assert "name: syswatch-linux-release" in text
    assert "name: syswatch-windows-release" in text
    assert "sha256sum --check SHA256SUMS" in text
    assert "sha256sum --check SHA256SUMS-WINDOWS" in text


def test_release_contract_is_versioned_reproducible_and_identity_bound():
    text = RELEASE.read_text(encoding="utf-8")
    required = (
        "workflow_dispatch:",
        "release_tag:",
        'REF_NAME="${{ inputs.release_tag }}"',
        'REF_NAME="${GITHUB_REF_NAME}"',
        '[[ "$REF_NAME" =~ ^v[0-9]+\\.[0-9]+\\.[0-9]+$ ]]',
        'git show-ref --verify --quiet "refs/tags/${{ steps.release.outputs.ref_name }}"',
        'test "$RELEASE_SHA" = "$(git rev-parse HEAD)"',
        'grep -Fxq "Version: $VERSION" control/control',
        "grep -Fxq 'Architecture: amd64' control/control",
        'EXPECTED_SUM="$(sha256sum "$PACKAGE")"',
        'test "$(cat SHA256SUMS)" = "$EXPECTED_SUM"',
        "sha256sum --check SHA256SUMS",
        'grep -Fxq "SYSWATCH $VERSION" RELEASE-METADATA.txt',
        'grep -Fxq "Commit $RELEASE_SHA" RELEASE-METADATA.txt',
        'grep -Fxq "Source-Date-Epoch $SOURCE_EPOCH" RELEASE-METADATA.txt',
        'cmp --silent first-build.deb "$PACKAGE"',
        'test "$(cat SHA256SUMS)" = "$(sha256sum "$PACKAGE")"',
        "requirements-windows-build.txt",
        "SOURCE_DATE_EPOCH=$sourceEpoch",
        "PYTHONHASHSEED=1",
        "Rebuild and verify byte-identical Windows executable",
        "$firstHash -ne $secondHash",
        "SHA256SUMS-WINDOWS",
        "Smoke-test released executable and native Windows telemetry API",
    )
    for invariant in required:
        assert invariant in text


def test_windows_build_dependency_is_pinned_audited_and_preserved_as_sbom():
    requirements = WINDOWS_BUILD_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    assert requirements == ["pyinstaller==6.15.0"]

    security = SECURITY.read_text(encoding="utf-8")
    required = (
        "requirements-windows-build.txt",
        "windows-build-dependency-sbom.cdx.json",
        "python -m pip_audit -r requirements-windows-build.txt",
        "name: Preserve supply-chain SBOM evidence",
        "syswatch-sboms-${{ github.sha }}",
    )
    for invariant in required:
        assert invariant in security


def test_windows_executable_gates_are_reproducible_and_prove_native_read_only_telemetry_path():
    reproducibility = (
        "requirements-windows-build.txt",
        "SOURCE_DATE_EPOCH=$sourceEpoch",
        "PYTHONHASHSEED=1",
        "first-build.exe",
        "$firstHash -ne $secondHash",
    )
    telemetry = (
        "$health.agent -eq 'online'",
        "$metrics.platform -notmatch 'Windows'",
        "$metrics.firewall.backend -ne 'windows-defender-firewall'",
        "$metrics.cpu -lt 0 -or $metrics.cpu -gt 100",
        "$metrics.memory -lt 0 -or $metrics.memory -gt 100",
        "@($processes.processes).Count -lt 1",
        "$null -eq $sample.pid -or !$sample.name",
    )
    for path in (WINDOWS, RELEASE):
        text = path.read_text(encoding="utf-8")
        for invariant in reproducibility + telemetry:
            assert invariant in text, f"{path.name} missing Windows release gate: {invariant}"


def test_service_release_boundary_is_non_privileged():
    builder = BUILDER.read_text(encoding="utf-8")
    required = (
        "User=syswatch",
        "Group=syswatch",
        "NoNewPrivileges=true",
        "PrivateDevices=true",
        "ProtectSystem=strict",
        "ProtectHome=read-only",
        "CapabilityBoundingSet=",
        "AmbientCapabilities=",
        "ReadWritePaths=/var/lib/syswatch",
    )
    for invariant in required:
        assert invariant in builder


def test_installer_and_package_share_the_same_service_boundary():
    installer = INSTALLER.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")

    shared_directives = (
        "NoNewPrivileges=true",
        "PrivateDevices=true",
        "ProtectSystem=strict",
        "ProtectHome=read-only",
        "CapabilityBoundingSet=",
        "AmbientCapabilities=",
        "StateDirectory=syswatch",
        "StateDirectoryMode=0750",
    )
    for invariant in shared_directives:
        assert invariant in installer
        assert invariant in builder

    assert 'SERVICE_USER="syswatch"' in installer
    assert 'SERVICE_GROUP="syswatch"' in installer
    assert 'User=$SERVICE_USER' in installer
    assert 'Group=$SERVICE_GROUP' in installer
    assert "User=syswatch" in builder
    assert "Group=syswatch" in builder

    assert 'STATE_DIR="/var/lib/syswatch"' in installer
    assert 'Environment=SYSWATCH_STATE_DIR=$STATE_DIR' in installer
    assert 'ReadWritePaths=$STATE_DIR' in installer
    assert "Environment=SYSWATCH_STATE_DIR=/var/lib/syswatch" in builder
    assert "ReadWritePaths=/var/lib/syswatch" in builder

    assert 'export SYSWATCH_STATE_DIR="${SYSWATCH_STATE_DIR:-/var/lib/syswatch}"' in installer
    assert 'url = "http://127.0.0.1:8080/api/health"' in installer


def test_public_documentation_keeps_platform_security_and_release_claims_bounded():
    text = README.read_text(encoding="utf-8")
    required_claims = (
        "local-first endpoint-security project",
        "Ubuntu 24.04 LTS / Linux amd64",
        "No verified public SYSWATCH release is published yet",
        "main` is a development branch",
        "does **not** claim 99.99% detection accuracy",
        "does not execute containment",
        "Cross-platform agents are not currently supported or verified",
        "RHEL-family packaging",
        "not declared release-ready until an actual versioned release artifact",
    )
    for claim in required_claims:
        assert claim in text

    forbidden_affirmative_claims = (
        "100% malware detection",
        "guaranteed malware detection",
        "detects all malware",
        "Windows is supported",
        "macOS is supported",
        "RHEL is supported",
        "SYSWATCH is a production EDR",
        "independently certified",
    )
    assert not any(claim in text for claim in forbidden_affirmative_claims)


def test_public_development_install_is_explicitly_not_a_release_install():
    text = README.read_text(encoding="utf-8")
    assert "sudo SYSWATCH_REF=main ./install.sh" in text
    assert "There is not yet a public versioned release install command" in text
    assert "**not** a substitute for a versioned release artifact" in text
