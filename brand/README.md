# Ferroguard marks

Original marks for this repository. They are not the Bird, Giga, 1Password, or CruiseKube logos, and this folder does not contain those screenshots.

The SVG sources also live at `docs/assets/brand/` so the site can use them. PNG exports sit next to those SVGs.

## Files

| File | Use |
| --- | --- |
| `icon.svg` | Site mark. Muted iron uprights, iron bar, transparent background. |
| `icon-light.svg` | Same mark for light backgrounds. |
| `icon-dark.svg` | Lighter uprights and a lighter iron bar for dark backgrounds. |
| `wordmark-light.svg` | The word ferroguard for light backgrounds. Editable `<text>`. |
| `wordmark-dark.svg` | The word ferroguard for dark backgrounds. Editable `<text>`. |
| `icon-light.png`, `icon-dark.png` | 512×512 transparent PNG renders of the icons. |
| `wordmark-light.png`, `wordmark-dark.png` | Transparent PNG renders of the wordmarks. |

Edit an SVG, then export the PNG again. The transparent PNGs are the files to upload if you set PyPI project imagery.

## Provenance

The icon is geometry drawn for Ferroguard: two uprights and one crossbar. It is not a shield.

The wordmark is the word ferroguard set as SVG text in Libre Baskerville. The font file is `docs/assets/fonts/libre-baskerville/LibreBaskerville[wght].ttf`, redistributed with its SIL Open Font License notice in `OFL.txt`. Liberation Serif and DejaVu Serif are named as fallbacks. The font software was not modified, so the reserved name stays.

Body text, navigation, and buttons use DejaVu Sans, then Liberation Sans, then `system-ui`. Code stays in DejaVu Sans Mono and Liberation Mono.

## Colour

The page is mostly neutral. Three colours are derived, and they do not get equal weight.

The main colour is iron blue `#245E78`. It is the link colour on the light page and the icon bar.

The accent is that hue plus 137.5 degrees, which is about the golden angle, at the same saturation and lightness: `#782446`. On the light page it is the focus outline. A lighter variant of the same hue, `#D0628E`, is the focus outline on the dark header and in the dark scheme, because the derived accent is too dark there. The angle is not a contrast ratio.

The support colour keeps the main hue and lightness and keeps 40% of its saturation (saturation reduced by 60%): `#3D545F`. It is the icon uprights, not a page fill. On the dark mark the uprights are `#93ADB9`.

Light surfaces are paper `#F4F6F7` and ink `#1B1F24`. Dark surfaces are paper `#12161A` and ink `#F3F5F6`. The header is the same neutral ink, not a saturated field.

Text, button, and focus pairs are measured against the background they sit on. Those checks live in `tests/test_docs_contrast.py`.
