"""Colour maths for the adaptive theme: OKLCH -> sRGB conversion and WCAG 2.x contrast.

OKLCH (Ottosson's Oklab in polar form) is used because equal lightness steps look roughly equal
across hues, so every archetype palette gets comparable visual weight. Contrast is then checked
with the WCAG relative-luminance formula and lightness is adjusted until the target ratio holds.
"""

from __future__ import annotations

import math


def _linear_to_srgb(x: float) -> float:
    return 12.92 * x if x <= 0.0031308 else 1.055 * (x ** (1 / 2.4)) - 0.055


def _oklch_to_linear_rgb(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    a = chroma * math.cos(math.radians(hue))
    b = chroma * math.sin(math.radians(hue))
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_**3, m_**3, s_**3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def _in_gamut(rgb: tuple[float, float, float]) -> bool:
    return all(-1e-4 <= c <= 1 + 1e-4 for c in rgb)


def oklch_to_hex(lightness: float, chroma: float, hue: float) -> str:
    """Convert to sRGB hex, reducing chroma until the colour fits the sRGB gamut."""
    lightness = min(max(lightness, 0.0), 1.0)
    c = max(chroma, 0.0)
    rgb = _oklch_to_linear_rgb(lightness, c, hue)
    while not _in_gamut(rgb) and c > 0:
        c = max(c - 0.005, 0.0)
        rgb = _oklch_to_linear_rgb(lightness, c, hue)
    channels = [round(min(max(_linear_to_srgb(min(max(x, 0.0), 1.0)), 0.0), 1.0) * 255) for x in rgb]
    return "#" + "".join(f"{v:02x}" for v in channels)


def relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def darken_until(lightness: float, chroma: float, hue: float, against: str, minimum: float) -> tuple[str, float]:
    """Lower OKLCH lightness until the colour reaches `minimum` contrast against a light background."""
    current = lightness
    color = oklch_to_hex(current, chroma, hue)
    while contrast_ratio(color, against) < minimum and current > 0.05:
        current -= 0.01
        color = oklch_to_hex(current, chroma, hue)
    return color, current
