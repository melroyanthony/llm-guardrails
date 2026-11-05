"""The site ships Libre Baskerville and an open sans stack."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "docs" / "assets" / "fonts" / "libre-baskerville"
CSS = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")
WORDMARK = (ROOT / "docs" / "assets" / "brand" / "wordmark-light.svg").read_text(encoding="utf-8")


def test_libre_baskerville_keeps_its_licence_notice():
    notice = (FONT_DIR / "OFL.txt").read_text(encoding="utf-8")
    font = FONT_DIR / "LibreBaskerville[wght].ttf"
    assert font.is_file()
    assert "SIL OPEN FONT LICENSE" in notice
    assert "Reserved Font Name Libre Baskerville" in notice
    assert "Libre Baskerville" in CSS
    assert "Libre Baskerville" in WORDMARK


def test_body_uses_the_open_sans_stack():
    shipped = [
        path.name.lower()
        for path in (ROOT / "docs").rglob("*")
        if path.suffix.lower() in {".ttf", ".otf", ".woff", ".woff2"}
    ]
    readme = (ROOT / "brand" / "README.md").read_text(encoding="utf-8")
    assert shipped == ["librebaskerville[wght].ttf"]
    assert "RM Neue" not in CSS
    assert "RM Neue" not in readme
    assert "font-weight: 600" not in CSS
    assert '"DejaVu Sans", "Liberation Sans", system-ui, sans-serif' in CSS
    assert "DejaVu Sans Mono" in CSS
    assert "font-display: swap" in CSS
