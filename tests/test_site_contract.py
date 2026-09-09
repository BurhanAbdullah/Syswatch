from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "index.html"


def test_product_site_has_required_sections():
    text = SITE.read_text(encoding="utf-8")
    required = (
        'id="product"',
        'id="architecture"',
        'id="install"',
        'id="security"',
        "SYSWATCH",
        "Local-first",
        "Least privilege",
        "No destructive default",
        "other platforms are not promoted as released support",
        "No published release is represented here",
    )
    for marker in required:
        assert marker in text


def test_product_site_is_static_and_does_not_load_remote_scripts():
    text = SITE.read_text(encoding="utf-8")
    assert "<script" not in text.lower()
    assert "javascript:" not in text.lower()
    assert "iframe" not in text.lower()


def test_product_site_uses_secure_scope_and_bounded_claims():
    text = SITE.read_text(encoding="utf-8")
    assert "127.0.0.1:8080" in text
    assert "does not execute containment" in text.lower() or "does not execute containment" in SITE.read_text(encoding="utf-8").lower()
    assert "universal real-world malware-detection accuracy" in text
