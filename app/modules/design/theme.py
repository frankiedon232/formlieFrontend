"""Form themes and page designs (port of shared/utils/forms/theme.ts and page-design.ts), held to the frontend's
answers by tests/parity/test_design_rules.py.

A theme is a small set of design tokens stored on the form (`schema.theme`); a page design is the part that shapes
the page around the form on its public link (frame and page background). Formalie's own themes and page designs
are the workspace default theme (its brand colour and logo) with a preset patch over it.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from app.core import zod as z
from app.modules.design.catalogues import (
    PAGE_PRESETS, TEMPLATE_CATEGORIES, THEME_FONTS, THEME_FRAMES, THEME_LAYOUTS, THEME_PRESETS,
)

_HEX = r"^#[0-9a-f]{6}$"


def _hex() -> z.Schema:
    return z.string().regex(_HEX, flags="i")


def _image() -> z.Schema:
    return z.string().max(2000).regex(r"^(https:\/\/\S+|\/api\/v1\/files\/[\w-]+)$", flags="i").nullable()


def _href_ok(value: str) -> bool:
    """https only (or on its way to it while typing); anything else is emptied."""
    return "https://".startswith(value.lower()) or bool(re.match(r"^https://", value, re.IGNORECASE))


_frame = z.obj(style=z.enum(THEME_FRAMES), show_website=z.boolean(), show_facts=z.boolean(),
               tone=z.enum(["light", "dark", "brand"]))
_page = z.obj(bg_type=z.enum(["color", "gradient", "image"]), bg=_hex(), bg_to=_hex(),
              gradient_angle=z.number().int().min(0).max(360), bg_image=_image(), overlay=z.number().int().min(0).max(80))

theme_schema = z.obj(
    layout=z.enum(THEME_LAYOUTS),
    page=_page,
    container=z.obj(width=z.enum(["sm", "md", "lg", "xl"]), padding=z.enum(["sm", "md", "lg"]),
                    radius=z.enum(["none", "sm", "md", "lg", "xl"]), border=z.boolean(),
                    shadow=z.enum(["none", "sm", "md", "lg"]), bg=_hex()),
    typography=z.obj(font=z.enum(THEME_FONTS), size=z.enum(["sm", "md", "lg"]),
                     heading_weight=z.enum(["medium", "semibold", "bold"])),
    colors=z.obj(primary=_hex(), text=_hex(), muted=_hex(), input_bg=_hex(), input_border=_hex(), error=_hex()),
    inputs=z.obj(radius=z.enum(["none", "sm", "md", "lg", "full"]), size=z.enum(["sm", "md", "lg"]),
                 style=z.enum(["outline", "soft", "underline"])),
    buttons=z.obj(radius=z.enum(["none", "sm", "md", "lg", "full"]), variant=z.enum(["solid", "outline", "soft"]),
                  full_width=z.boolean()),
    header=z.obj(show_logo=z.boolean(), logo=_image(), cover=_image(), cover_height=z.enum(["sm", "md", "lg"]),
                 show_title=z.boolean(), subtitle=z.string().max(300), align=z.enum(["start", "center"]),
                 band=z.enum(["none", "color", "gradient", "accent"]), band_bg=_hex(), band_to=_hex()),
    split=z.obj(image=_image(), side=z.enum(["start", "end"]), panel=z.enum(["image", "color", "gradient"]),
                bg=_hex(), bg_to=_hex()),
    footer=z.obj(
        enabled=z.boolean(), text=z.string().max(500),
        links=z.array(z.obj(label=z.string().max(60).catch(""),
                            href=z.string().max(2000).refine(_href_ok).catch(""))).max(6),
        show_logo=z.boolean(), align=z.enum(["start", "center"]), style=z.enum(["plain", "band"]), bg=_hex(),
    ),
    thank_you=z.obj(show_icon=z.boolean()),
    blocks=z.obj(section=z.enum(["plain", "underline", "accent", "band"]), section_color=z.enum(["text", "primary"]),
                 section_caps=z.boolean(), divider=z.enum(["line", "accent", "gradient", "dots", "space"]),
                 divider_weight=z.enum(["thin", "thick"]), paragraph=z.enum(["plain", "muted", "callout"]),
                 image_radius=z.enum(["none", "sm", "md", "lg", "xl"]), image_shadow=z.boolean(),
                 image_border=z.boolean()),
    frame=_frame,
)

page_design_schema = z.obj(frame=_frame, page=_page)


def default_theme(logo_url: str | None = None, primary: str | None = None) -> dict[str, Any]:
    """The workspace default: what every form looks like until someone designs it."""
    return {
        "layout": "card",
        "page": {"bg_type": "color", "bg": "#f4f4f5", "bg_to": "#e4e4e7", "gradient_angle": 135, "bg_image": None,
                 "overlay": 0},
        "container": {"width": "md", "padding": "md", "radius": "lg", "border": True, "shadow": "sm", "bg": "#ffffff"},
        "typography": {"font": "sans", "size": "md", "heading_weight": "semibold"},
        "colors": {"primary": primary if primary and re.fullmatch(_HEX, primary, re.IGNORECASE) else "#18181b",
                   "text": "#18181b", "muted": "#71717a", "input_bg": "#ffffff", "input_border": "#d4d4d8",
                   "error": "#dc2626"},
        "inputs": {"radius": "sm", "size": "md", "style": "outline"},
        "buttons": {"radius": "sm", "variant": "solid", "full_width": False},
        "header": {"show_logo": bool(logo_url), "logo": None, "cover": None, "cover_height": "md", "show_title": True,
                   "subtitle": "", "align": "start", "band": "none", "band_bg": "#18181b", "band_to": "#3f3f46"},
        "split": {"image": None, "side": "start", "panel": "image", "bg": "#18181b", "bg_to": "#3f3f46"},
        "footer": {"enabled": False, "text": "", "links": [], "show_logo": False, "align": "center", "style": "plain",
                   "bg": "#18181b"},
        "thank_you": {"show_icon": True},
        "blocks": {"section": "plain", "section_color": "text", "section_caps": False, "divider": "line",
                   "divider_weight": "thin", "paragraph": "plain", "image_radius": "md", "image_shadow": False,
                   "image_border": False},
        "frame": {"style": "branded", "show_website": True, "show_facts": True, "tone": "light"},
    }


def merge(base: Any, patch: Any) -> Any:
    """Only keys the base has; objects merged into objects, anything else replaced (lists too)."""
    if not isinstance(patch, dict):
        return base
    out = dict(base)
    for key, value in patch.items():
        if key not in out:
            continue
        out[key] = merge(out[key], value) if isinstance(out[key], dict) and isinstance(value, dict) else copy.deepcopy(value)
    return out


def apply_patch(theme: dict[str, Any], patch: Any) -> dict[str, Any]:
    return merge(theme, patch)


def page_tokens(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """presetTokens(): a preset as full page tokens over a base theme."""
    return {"frame": {**base["frame"], **(patch.get("frame") or {})}, "page": {**base["page"], **(patch.get("page") or {})}}


def _capital(key: str) -> str:
    return key[:1].upper() + key[1:].replace("_", " ")


def system_themes(logo_url: str | None, primary: str | None) -> list[dict[str, Any]]:
    """Formalie's themes for this workspace: the designer's presets, then every template category design."""
    base = default_theme(logo_url, primary)
    return [
        *({"id": f"sys_preset_{p['key']}", "name": _capital(p["key"]), "tokens": apply_patch(base, p["patch"])}
          for p in THEME_PRESETS if p["key"] != "workspace"),
        *({"id": f"sys_category_{c['key']}", "name": f"{_capital(c['key'])} design",
           "tokens": apply_patch(base, c["design"])} for c in TEMPLATE_CATEGORIES),
    ]


def system_pages(logo_url: str | None, primary: str | None) -> list[dict[str, Any]]:
    base = default_theme(logo_url, primary)
    return [{"id": f"sys_page_{p['key']}", "name": _capital(p["key"]), "tokens": page_tokens(base, p["patch"])}
            for p in PAGE_PRESETS]
