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
