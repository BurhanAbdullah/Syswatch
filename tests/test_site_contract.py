from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


def _text(name: str) -> str:
    return (SITE / name).read_text(encoding="utf-8")


def test_product_site_has_required_pages_and_bounded_claims():
    pages = (
        "index.html",
        "features.html",
        "security.html",
        "documentation.html",
        "download.html",
        "about.html",
    )
    for page in pages:
        assert (SITE / page).is_file(), page
        assert (SITE / page).stat().st_size > 0, page

    text = _text("index.html")
    required = (
        "SYSWATCH",
        "Ubuntu 24.04",
        "local-first",
        "Public release downloads will appear only after the versioned release gate passes.",
    )
    for marker in required:
        assert marker in text

    security = _text("security.html")
    assert "Least privilege" in security
    assert "does not execute containment" in security.lower()
    assert "universal malware-detection accuracy" in security.lower()


def test_product_site_is_static_and_uses_no_embedded_frames():
    for path in SITE.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "javascript:" not in text.lower(), path
        assert "iframe" not in text.lower(), path


def test_product_site_local_links_resolve():
    class LinkParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links = []

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                href = dict(attrs).get("href")
                if href:
                    self.links.append(href)

    for page in SITE.glob("*.html"):
        parser = LinkParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for href in parser.links:
            if href.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = (page.parent / href.split("#", 1)[0].split("?", 1)[0]).resolve()
            assert SITE.resolve() in target.parents or target == SITE.resolve(), href
            assert target.exists(), f"{page.name}: broken local link {href}"
