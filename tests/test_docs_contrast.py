"""Body colours in the docs theme meet WCAG AA for normal text."""

import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / "docs" / "stylesheets" / "extra.css").read_text(
    encoding="utf-8"
)


def _channel(value: float) -> float:
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    red = int(hex_color[1:3], 16) / 255
    green = int(hex_color[3:5], 16) / 255
    blue = int(hex_color[5:7], 16) / 255
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _contrast(foreground: str, background: str) -> float:
    lighter = max(_luminance(foreground), _luminance(background))
    darker = min(_luminance(foreground), _luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def _var(name: str) -> str:
    match = re.search(rf"{name}:\s*(#[0-9a-fA-F]{{6}})", CSS)
    assert match, name
    return match.group(1)


def test_text_colours_clear_wcag_aa():
    paper = _var("--fg-paper")
    ink = _var("--fg-ink")
    muted = _var("--fg-muted")
    copper = _var("--fg-copper")
    assert _contrast(ink, paper) >= 4.5
    assert _contrast(muted, paper) >= 4.5
    assert _contrast(copper, paper) >= 4.5
    assert _contrast("#fffaf6", "#7d4330") >= 4.5
    assert _contrast("#1c2126", "#e0a07a") >= 4.5
    assert _contrast("#f3efe8", "#171b1e") >= 4.5
    assert "#7d4330" in CSS
    assert "#e0a07a" in CSS
    assert "overflow-x: auto" in CSS
    assert "focus-visible" in CSS
