"""Tests for Cloudflare Pages dashboard scaffold.

Verifies:
  1. HTML structure — 4 quadrants with correct ids, video-widget present
  2. CSS grid — desktop 2×2 grid, mobile stacked, dark theme tokens
  3. JS module — exports expected orchestration functions

Run from repo root:
    python -m pytest .test/test_cloudflare_pages.py -v
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES_SRC = REPO_ROOT / "cloudflare" / "src"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _read(filename: str) -> str:
    """Read a file from cloudflare/src/ and return its content."""
    file_path = PAGES_SRC / filename
    assert file_path.is_file(), f"Missing file: {file_path}"
    return file_path.read_text(encoding="utf-8")


class QuadrantFinder(HTMLParser):
    """Parser that collects all section elements with class 'quadrant'."""

    def __init__(self):
        super().__init__()
        self.quadrants: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self._in_quadrant = False
        self._seen_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "").split()

        if tag == "section" and "quadrant" in classes:
            self._in_quadrant = True
            self.current = {
                "tag": tag,
                "id": attrs_dict.get("id", ""),
                "classes": classes,
            }

        if self._in_quadrant and tag == "div" and "video-widget" in classes:
            self.current["has_video_widget"] = True

    def handle_endtag(self, tag: str):
        if self._in_quadrant and tag == "section":
            self._in_quadrant = False
            if self.current:
                qid = self.current.get("id", "")
                if qid and qid not in self._seen_ids:
                    self._seen_ids.add(qid)
                    self.quadrants.append(self.current)
            self.current = None


# ── Test 1: HTML Structure ───────────────────────────────────────────────────


def test_html_has_four_quadrants():
    """index.html must contain exactly 4 quadrant <section> elements."""
    html = _read("index.html")
    parser = QuadrantFinder()
    parser.feed(html)
    assert len(parser.quadrants) == 4, (
        f"Expected 4 quadrants, found {len(parser.quadrants)}"
    )


def test_html_has_video_widget():
    """index.html must contain a div with class 'video-widget'."""
    html = _read("index.html")
    assert 'class="video-widget"' in html or "class='video-widget'" in html, (
        "Missing video-widget div"
    )
    # Also verify via parser
    parser = QuadrantFinder()
    parser.feed(html)
    video_quadrants = [q for q in parser.quadrants if q.get("has_video_widget")]
    assert len(video_quadrants) >= 1, "No quadrant contains a video-widget div"


def test_html_has_required_quadrant_ids():
    """Each quadrant must have a unique id matching the naming convention."""
    required_ids = {
        "quadrant-video",
        "quadrant-tokenomics",
        "quadrant-mission",
        "quadrant-browsing",
    }
    html = _read("index.html")
    parser = QuadrantFinder()
    parser.feed(html)
    found_ids = {q["id"] for q in parser.quadrants if q["id"]}
    missing = required_ids - found_ids
    assert not missing, f"Missing quadrant ids: {missing}"


def test_html_loads_module_script():
    """index.html must load app.js as type='module'."""
    html = _read("index.html")
    assert 'type="module"' in html or "type='module'" in html, (
        "Missing type='module' script tag"
    )
    assert "app.js" in html, "Missing app.js script reference"


def test_html_loads_stylesheet():
    """index.html must link style.css."""
    html = _read("index.html")
    assert "style.css" in html, "Missing style.css link"


def test_html_has_header():
    """index.html must have a sticky header."""
    html = _read("index.html")
    assert "<header" in html, "Missing <header> element"
    assert 'class="header"' in html, "Missing header class"


# ── Test 2: CSS Grid & Dark Theme ─────────────────────────────────────────────


def test_css_has_grid_layout():
    """style.css must define a 2×2 grid for desktop with grid-template-columns."""
    css = _read("style.css")
    # Desktop grid: 2 columns, 2 rows
    assert "grid-template-columns" in css, "Missing grid-template-columns"
    # Must define 2 equal columns for desktop
    col_match = re.search(
        r"grid-template-columns\s*:\s*(1fr\s+1fr|repeat\(\s*2\s*,\s*1fr\s*\))", css
    )
    assert col_match, (
        "Desktop grid must have grid-template-columns: 1fr 1fr (or repeat(2, 1fr))"
    )
    assert "grid-template-rows" in css, "Missing grid-template-rows"
    assert "grid-template-areas" in css, "Missing grid-template-areas"


def test_css_has_mobile_media_query():
    """style.css must have a mobile media query that stacks quadrants."""
    css = _read("style.css")
    # Must have at least one max-width media query
    media_matches = re.findall(r"@media\s*\(max-width:\s*\d+px\)", css)
    assert len(media_matches) >= 1, "Missing mobile/@media (max-width) query"
    # Inside a mobile query, grid should be 1 column
    # Search for single-column grid in media queries
    single_col = re.search(
        r"@media[^{]*\{[^}]*grid-template-columns\s*:\s*(1fr|100%)[^}]*\}",
        css,
        re.DOTALL,
    )
    assert single_col, "Mobile grid must have grid-template-columns: 1fr (or 100%)"


def test_css_has_dark_theme_tokens():
    """style.css must define dark theme via :root CSS custom properties."""
    css = _read("style.css")
    assert ":root" in css, "Missing :root selector (CSS custom properties block)"
    # Key dark theme tokens
    for token in [
        "--color-bg-deepest",
        "--color-bg",
        "--color-surface",
        "--color-text-primary",
        "--color-accent",
    ]:
        assert token in css, f"Missing CSS custom property: {token}"


def test_css_has_responsive_grid_areas():
    """CSS must define grid-area assignments for each quadrant."""
    css = _read("style.css")
    areas = [
        ("video", "grid-area: video"),
        ("tokenomics", "grid-area: tokenomics"),
        ("mission", "grid-area: mission"),
        ("browsing", "grid-area: browsing"),
    ]
    for name, expected in areas:
        assert expected in css, f"Missing grid-area assignment for: {name}"


def test_css_has_sheryl_accent_color():
    """style.css must use warm gold accent colors consistent with Sheryl branding."""
    css = _read("style.css")
    # Warm archival gold — #d4a853 or close variants
    assert "#d4a853" in css or "#D4A853" in css or "212, 168, 83" in css, (
        "Missing warm gold accent color (#d4a853) — Sheryl brand color"
    )
    # Secondary teal
    assert "#3da5a0" in css or "#3DA5A0" in css or "61, 165, 160" in css, (
        "Missing teal secondary color (#3da5a0)"
    )


# ── Test 3: JS Module Loading ─────────────────────────────────────────────────


def test_js_exports_toggle_quadrant():
    """app.js must export a toggleQuadrant function."""
    js = _read("app.js")
    assert "export function toggleQuadrant" in js, (
        "Missing exported toggleQuadrant function"
    )


def test_js_exports_webrtc_init():
    """app.js must export initWebRTC and disconnectWebRTC functions."""
    js = _read("app.js")
    assert "export function initWebRTC" in js, "Missing exported initWebRTC function"
    assert "export function disconnectWebRTC" in js, (
        "Missing exported disconnectWebRTC function"
    )


def test_js_exports_system_functions():
    """app.js must export setSystemStatus and tickClock functions."""
    js = _read("app.js")
    assert "export function setSystemStatus" in js, (
        "Missing exported setSystemStatus function"
    )
    assert "export function tickClock" in js, "Missing exported tickClock function"


def test_js_exports_update_stat():
    """app.js must export updateStat for mission-control telemetry."""
    js = _read("app.js")
    assert "export function updateStat" in js, "Missing exported updateStat function"


def test_js_has_no_hardcoded_keys():
    """app.js must not contain hardcoded API keys or secrets."""
    js = _read("app.js")
    # Look for common secret patterns
    patterns = [
        r'(?i)api[_-]?key\s*[:=]\s*["\'][\w-]{10,}',
        r'(?i)secret\s*[:=]\s*["\'][\w-]{10,}',
        r'(?i)token\s*[:=]\s*["\'][\w\.-]{10,}',
        r'(?i)password\s*[:=]\s*["\'][\w-]{4,}',
    ]
    for pat in patterns:
        assert not re.search(pat, js), f"Potential hardcoded secret detected: {pat}"


def test_js_has_no_hardcoded_keys_in_css():
    """style.css must not contain hardcoded API keys or secrets."""
    css = _read("style.css")
    patterns = [
        r'(?i)api[_-]?key\s*:\s*["\'][\w-]{10,}',
        r'(?i)secret\s*:\s*["\'][\w-]{10,}',
    ]
    for pat in patterns:
        assert not re.search(pat, css), f"Potential hardcoded secret in CSS: {pat}"


def test_js_domcontentloaded_handler():
    """app.js must include a DOMContentLoaded or readyState bootstrap."""
    js = _read("app.js")
    assert "DOMContentLoaded" in js or "document.readyState" in js, (
        "Missing DOM readiness check for bootstrap"
    )
