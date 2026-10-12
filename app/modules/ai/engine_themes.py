"""The stand-in's designer: port of the mock's server/mock/ai/themeEngine.ts. Three designs from one brand colour,
each a full set of theme tokens over the workspace default. Buttons get a shade dark enough for white text (WCAG
contrast 4.5 : 1), backgrounds only a light tint. A mood word (calm, bold, formal, friendly, playful, minimal) picks
the order. The model's designs are checked against the same rules (app/modules/ai/checks.py)."""

from __future__ import annotations

import re
from typing import Any

from app.core import js
from app.modules.design.theme import apply_patch, default_theme
from app.modules.ai.engine_forms import I, rx


def _rgb(hex_: str) -> list[int]:
    return [int(hex_[at:at + 2], 16) for at in (1, 3, 5)]


def _hex_of(values: list[float]) -> str:
    return "#" + "".join(f"{int(js.math_round(min(255.0, max(0.0, v)))):02x}" for v in values)


def mix(a: str, b: str, share: float) -> str:
    x, y = _rgb(a), _rgb(b)
    return _hex_of([v * share + y[i] * (1 - share) for i, v in enumerate(x)])


def _luminance(hex_: str) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in _rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    l1, l2 = sorted([_luminance(a), _luminance(b)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def readable(hex_: str) -> str:
    """The brand colour, darkened just enough for white text on it."""
    colour = hex_.lower()
    for _ in range(20):
        if contrast(colour, "#ffffff") >= 4.5:
            break
        colour = mix(colour, "#000000", 0.9)
    return colour


MOODS = {
    "calm": rx(r"\b(calm|soft|gentle|friendly|warm|care|health)\b", I),
    "bold": rx(r"\b(bold|strong|vivid|playful|fun|bright|energetic|event)\b", I),
    "minimal": rx(r"\b(minimal|clean|simple|formal|serious|corporate|legal|official)\b", I),
}
NAMES = {"calm": "Calm", "bold": "Bold", "minimal": "Minimal"}
DESCRIPTIONS = {
    "calm": "Soft tinted page, rounded fields and the brand colour on buttons and headings.",
    "bold": "A brand-coloured band at the top, a gradient page and full-width buttons.",
    "minimal": "A clean white page, serif headings and underlined fields with a brand accent.",
}


def brand_of(colour: str) -> str:
    return colour.lower() if re.match(r"^#[0-9a-f]{6}$", colour, I) else "#18181b"


def patches(brand: str, primary: str) -> dict[str, dict[str, Any]]:
    ink = "#18181b"
    return {
        "calm": {
            "page": {"bg_type": "color", "bg": mix(brand, "#ffffff", 0.07)},
            "container": {"radius": "xl", "shadow": "sm", "border": False},
            "colors": {"primary": primary, "input_border": mix(brand, "#d4d4d8", 0.18)},
            "inputs": {"radius": "md", "style": "outline"},
            "buttons": {"radius": "md", "variant": "solid"},
            "typography": {"font": "rounded"},
            "blocks": {"section": "plain", "section_color": "primary", "divider": "space"},
        },
        "bold": {
            "page": {"bg_type": "gradient", "bg": mix(brand, "#ffffff", 0.16), "bg_to": mix(brand, "#ffffff", 0.04),
                     "gradient_angle": 160},
            "container": {"radius": "lg", "shadow": "md", "border": False},
            "colors": {"primary": primary, "input_border": mix(brand, "#d4d4d8", 0.25)},
            "header": {"band": "gradient", "band_bg": primary, "band_to": mix(primary, "#000000", 0.7)},
            "buttons": {"radius": "full", "variant": "solid", "full_width": True},
            "inputs": {"radius": "md", "style": "soft"},
            "blocks": {"section": "band", "section_color": "primary", "divider": "line"},
        },
        "minimal": {
            "layout": "plain",
            "page": {"bg_type": "color", "bg": "#ffffff"},
            "container": {"radius": "none", "shadow": "none", "border": False},
            "colors": {"primary": primary, "text": ink},
            "typography": {"font": "serif", "heading_weight": "bold"},
            "inputs": {"radius": "none", "style": "underline"},
            "buttons": {"radius": "none", "variant": "solid"},
            "header": {"band": "accent", "band_bg": primary},
            "blocks": {"section": "underline", "section_color": "text", "section_caps": True, "divider": "line"},
        },
    }


def order_for(mood: str) -> list[str]:
    return sorted(MOODS, key=lambda key: -int(bool(MOODS[key].search(mood))))


def base_theme(colour: str, logo_url: str | None) -> dict[str, Any]:
    return default_theme(logo_url, readable(brand_of(colour)))


def themes_from_colour(colour: str, mood: str = "", logo_url: str | None = None) -> list[dict[str, Any]]:
    """Three designs for a brand colour, the one that fits the mood first: [{key, name, description, tokens}]."""
    brand = brand_of(colour)
    primary = readable(brand)
    base = default_theme(logo_url, primary)
    made = patches(brand, primary)
    return [{"key": key, "name": NAMES[key], "description": DESCRIPTIONS[key], "tokens": apply_patch(base, made[key])}
            for key in order_for(mood)]
