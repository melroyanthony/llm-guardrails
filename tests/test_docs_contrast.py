"""Docs colours: derivation is separate from measured contrast."""

import colorsys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "docs" / "stylesheets" / "extra.css").read_text(encoding="utf-8")
BRAND = ROOT / "docs" / "assets" / "brand"
README = (ROOT / "brand" / "README.md").read_text(encoding="utf-8")
ANGLE = 137.5


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


def _hsl(hex_color: str) -> tuple[float, float, float]:
    red = int(hex_color[1:3], 16) / 255
    green = int(hex_color[3:5], 16) / 255
    blue = int(hex_color[5:7], 16) / 255
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    return hue * 360, saturation * 100, lightness * 100


def _hex_from_hsl(hue: float, saturation: float, lightness: float) -> str:
    red, green, blue = colorsys.hls_to_rgb(
        (hue % 360) / 360,
        lightness / 100,
        saturation / 100,
    )
    red_byte, green_byte, blue_byte = (
        max(0, min(255, round(channel * 255))) for channel in (red, green, blue)
    )
    return f"#{red_byte:02x}{green_byte:02x}{blue_byte:02x}"


def _block(selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(.*?)\}}", CSS, re.S)
    assert match, selector
    return match.group(1)


def _vars(block: str) -> dict[str, str]:
    found = dict(re.findall(r"(--fg-[\w-]+):\s*(#[0-9a-fA-F]{6})", block))
    assert found, block[:40]
    return {name: value.lower() for name, value in found.items()}


def _hue_delta(left: str, right: str) -> float:
    return (_hsl(right)[0] - _hsl(left)[0]) % 360


LIGHT = _vars(_block(":root"))
DARK = {**LIGHT, **_vars(_block('[data-md-color-scheme="slate"]'))}


def test_accent_and_support_are_derived_from_the_main_colour():
    main = LIGHT["--fg-main"]
    hue, saturation, lightness = _hsl(main)
    assert LIGHT["--fg-accent"] == _hex_from_hsl(hue + ANGLE, saturation, lightness)
    assert LIGHT["--fg-support"] == _hex_from_hsl(hue, saturation * 0.4, lightness)
    assert abs(_hue_delta(main, LIGHT["--fg-accent"]) - ANGLE) < 1.5
    support_hue, support_saturation, support_lightness = _hsl(LIGHT["--fg-support"])
    assert abs(support_hue - hue) < 1.5 or abs(support_hue - hue) > 358.5
    assert abs(support_saturation - (saturation * 0.4)) < 1.5
    assert abs(support_lightness - lightness) < 1.5
    # The angle is recorded so it cannot be mistaken for a contrast ratio.
    assert "137.5" in CSS
    assert "not a contrast ratio" in CSS


def test_text_buttons_and_focus_meet_contrast_on_their_backgrounds():
    for scheme in (LIGHT, DARK):
        paper = scheme["--fg-paper"]
        assert _contrast(scheme["--fg-ink"], paper) >= 4.5
        assert _contrast(scheme["--fg-muted"], paper) >= 4.5
        assert _contrast(scheme["--fg-link"], paper) >= 4.5
        assert _contrast(scheme["--fg-link-hover"], paper) >= 4.5
        assert _contrast(scheme["--fg-button-fg"], scheme["--fg-button-bg"]) >= 4.5
        assert _contrast(scheme["--fg-button-fg-hover"], scheme["--fg-button-bg-hover"]) >= 4.5
        assert _contrast(scheme["--fg-focus"], paper) >= 3
        assert _contrast(scheme["--fg-focus"], scheme["--fg-code-bg"]) >= 3
        assert _contrast(scheme["--fg-focus-header"], scheme["--fg-header"]) >= 3
        assert _contrast(scheme["--fg-header-fg"], scheme["--fg-header"]) >= 4.5
        assert scheme["--fg-paper"] not in {
            scheme["--fg-main"],
            scheme["--fg-accent"],
            scheme["--fg-support"],
        }
    assert LIGHT["--fg-link"] == LIGHT["--fg-main"]
    assert LIGHT["--fg-focus"] == LIGHT["--fg-accent"]
    assert (
        abs(_hue_delta(LIGHT["--fg-main"], DARK["--fg-link"])) < 1.5
        or _hue_delta(LIGHT["--fg-main"], DARK["--fg-link"]) > 358.5
    )
    assert abs(_hue_delta(LIGHT["--fg-accent"], DARK["--fg-focus"])) < 2
    assert "overflow-x: auto" in CSS
    assert "focus-visible" in CSS
    assert ":hover" in CSS
    assert "fg-features" not in CSS
    assert "grid-template-columns" not in CSS
    assert "color: var(--fg-ink)" in CSS


def test_example_swatches_and_false_formula_are_not_the_brand():
    blob = "\n".join(
        [
            CSS,
            README,
            *[path.read_text(encoding="utf-8") for path in BRAND.glob("*.svg")],
        ]
    ).lower()
    for banned in ("#ffa500", "#00b2a9", "#b28e4c", "#b28e4d", "360 / 1.618", "360 ÷ 1.618"):
        assert banned not in blob
    light_icon = (BRAND / "icon.svg").read_text(encoding="utf-8").lower()
    dark_icon = (BRAND / "icon-dark.svg").read_text(encoding="utf-8").lower()
    assert LIGHT["--fg-main"] in light_icon
    assert LIGHT["--fg-support"] in light_icon
    assert DARK["--fg-link"] in dark_icon
    assert "#93adb9" in dark_icon
    assert _contrast("#93adb9", LIGHT["--fg-header"]) >= 3
    assert (
        (BRAND / "wordmark-light.svg").read_text(encoding="utf-8").lower().count(LIGHT["--fg-ink"])
    )
    assert DARK["--fg-ink"] in (BRAND / "wordmark-dark.svg").read_text(encoding="utf-8").lower()
