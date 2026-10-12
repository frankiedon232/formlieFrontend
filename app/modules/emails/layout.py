"""The one Formalie email layout (owner-approved design, 2026-10-12), for every email in every language.

An ink header with the workspace's tile (its logo, or its initial; Formalie's own emails carry the Field F mark) and
the Formalie "fields" motif, whose dot and the rule under the header take the workspace's colour; a white card with
the subject as its title; codes in a large box, answers as a table, a line that ends in a link as an ink button; a
quiet centred footer (Formalie, the tagline, why the person got the email, Privacy · formalie.com, and Unsubscribe
where the email can be turned off). Tables and inline styles only, so Gmail, Outlook and Apple Mail show it the same.
The frontend's mock draws the same page (server/mock/core/email.ts).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings

INK, PAPER, MUTED, LINE, CANVAS, BODY = "#0a0a0a", "#ffffff", "#6b6b6b", "#e7e7e5", "#f4f4f2", "#262626"
FONT = "'Manrope',-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
ANSWERS = "[[formalie:answers]]"
_VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")
# "Accept the invitation: https://…" (also the full-width colon) → a button
_LINK_LINE = re.compile(r"^(?P<lead>.*?)[:：]\s*(?P<url>https?://\S+)\s*$", re.S)
_URL = re.compile(r"(https?://[^\s<]+)")
RTL = {"ar"}


def esc(text: Any) -> str:
    return html.escape(str(text), quote=True).replace("&#x27;", "&#39;")


def fill(text: str, values: dict[str, Any]) -> str:
    return _VAR.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text)


def assets_url() -> str:
    """Where the Formalie mark images are served (the portal's public folder on manage.*)."""
    from app.modules.tenants.router import host_port

    settings = get_settings()
    base = settings.email_assets_url
    return (base or f"https://{settings.manage_subdomain}.{settings.root_domain}{host_port()}").rstrip("/")


@dataclass
class Look:
    """Who the email comes from and the words around the message (Formalie's texts in the email's language)."""

    workspace: str = "Formalie"
    logo_url: str | None = None
    brand_color: str | None = None
    formalie: bool = False  # Formalie's own email (sign-up, find workspace): the Field F mark in the tile
    footer_lines: list[str] = field(default_factory=list)
    texts: dict[str, str] = field(default_factory=dict)  # the language's `layout` texts
    language: str = "en"
    unsubscribe_url: str | None = None


def _button(label: str, url: str) -> str:
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:6px 0 10px"><tr>'
            f'<td style="border-radius:10px;background:{INK}"><a href="{esc(url)}" style="display:inline-block;'
            f'padding:13px 22px;font:600 14px/1 {FONT};color:#ffffff;text-decoration:none;border-radius:10px">'
            f'{esc(label)}</a></td></tr></table>'
            f'<p style="margin:0 0 20px;font:12px/1.5 {FONT};color:{MUTED};word-break:break-all">'
            f'<a href="{esc(url)}" style="color:{MUTED}">{esc(url)}</a></p>')


def _code(code: str) -> str:
    spaced = "&nbsp;".join(esc(c) for c in code)
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:2px 0 20px"><tr>'
            f'<td align="center" dir="ltr" style="background:{CANVAS};border:1px solid {LINE};border-radius:12px;'
            f'padding:18px 12px;font:700 30px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
            f'letter-spacing:6px;color:{INK}">{spaced}</td></tr></table>')


def _answers(answers: list[dict[str, str]], title: str) -> str:
    rows = "".join(
        f'<tr><td style="padding:10px 14px;border-top:1px solid {LINE};font:12px/1.45 {FONT};color:{MUTED};width:38%;'
        f'vertical-align:top">{esc(a["label"])}</td><td style="padding:10px 14px;border-top:1px solid {LINE};'
        f'font:500 13px/1.45 {FONT};color:{INK};white-space:pre-wrap;vertical-align:top">{esc(a["value"])}</td></tr>'
        for a in answers)
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:2px 0 20px;'
            f'border:1px solid {LINE};border-radius:12px;border-collapse:separate;overflow:hidden">'
            f'<tr><td colspan="2" style="padding:10px 14px;background:{CANVAS};font:600 11px/1 {FONT};color:{MUTED};'
            f'text-transform:uppercase;letter-spacing:.06em">{esc(title)}</td></tr>{rows}</table>')


def _paragraph(text: str) -> str:
    linked = _URL.sub(rf'<a href="\1" style="color:{INK};text-decoration:underline">\1</a>', esc(text))
    return f'<p style="margin:0 0 16px;font:15px/1.6 {FONT};color:{BODY}">{linked.replace(chr(10), "<br>")}</p>'


def _blocks(body: str, values: dict[str, Any], answers: list[dict[str, str]], look: Look) -> str:
    parts: list[str] = []
    code = str(values.get("code") or "")
    code_shown = False
    for part in re.split(r"\n{2,}", body):
        part = part.strip()
        if not part:
            continue
        if part == ANSWERS:
            if answers:
                parts.append(_answers(answers, look.texts.get("answers", "Answers")))
            continue
        found = _LINK_LINE.match(part)
        if found and ANSWERS not in part:
            lead = found.group("lead").strip()
            if lead and len(lead) <= 48 and "\n" not in lead:
                parts.append(_button(lead, found.group("url")))  # the line's own words on the button
            else:
                if lead:
                    parts.append(_paragraph(lead))
                parts.append(_button(look.texts.get("open", "Open"), found.group("url")))
            continue
        parts.append(_paragraph(part.replace(ANSWERS, "")))
        if code and not code_shown and code in part:
            parts.append(_code(code))
            code_shown = True
    return "".join(parts)


def _header(look: Look) -> str:
    dot, rule = look.brand_color or "#ffffff", look.brand_color or INK
    if look.formalie:
        inner = (f'<img src="{esc(assets_url())}/brand/formalie-glyph-512.png" alt="" width="28" height="28" '
                 f'style="display:block;margin:6px;width:28px;height:28px">')
    elif look.logo_url:
        inner = (f'<img src="{esc(look.logo_url)}" alt="" width="28" height="28" style="display:block;margin:6px;'
                 f'width:28px;height:28px;object-fit:contain;border-radius:6px">')
    else:
        inner = f'<span style="font:800 17px/40px {FONT};color:{INK}">{esc((look.workspace.strip() or "F")[:1].upper())}</span>'
    via = "" if look.formalie else (f'<div style="font:500 12px/1.4 {FONT};color:#9a9a9a">'
                                    f'{esc(look.texts.get("via", "Sent with Formalie"))}</div>')
    motif = (f'<td align="right" style="vertical-align:middle"><table role="presentation" cellpadding="0" cellspacing="0">'
             f'<tr><td style="padding:0 0 6px"><div style="width:58px;height:9px;border-radius:9px;background:#2b2b2b">'
             f'</div></td><td></td></tr><tr><td><div style="width:38px;height:9px;border-radius:9px;background:#2b2b2b">'
             f'</div></td><td style="padding:0 0 0 6px"><div style="width:9px;height:9px;border-radius:9px;'
             f'background:{esc(dot)}"></div></td></tr></table></td>')
    return (f'<tr><td style="background:{INK};border-radius:18px 18px 0 0;padding:22px 28px">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td style="width:40px;height:40px;background:#ffffff;border-radius:11px;text-align:center;'
            f'vertical-align:middle">{inner}</td>'
            f'<td style="padding-inline-start:12px;vertical-align:middle"><div style="font:700 16px/1.25 {FONT};'
            f'color:#ffffff">{esc(look.workspace)}</div>{via}</td>{motif}</tr></table></td></tr>'
            f'<tr><td style="height:3px;line-height:3px;font-size:0;background:{esc(rule)}">&nbsp;</td></tr>')


def _footer(look: Look) -> str:
    reason = "".join(f'<p style="margin:0 0 4px;font:12px/1.6 {FONT};color:{MUTED}">{esc(line)}</p>'
                     for line in look.footer_lines)
    sep = '<span style="color:#c4c4c0">&nbsp;&nbsp;·&nbsp;&nbsp;</span>'
    links = [f'<a href="https://formalie.com/privacy" style="color:{MUTED};text-decoration:underline">'
             f'{esc(look.texts.get("privacy", "Privacy"))}</a>',
             f'<a href="https://formalie.com" style="color:{MUTED};text-decoration:none">formalie.com</a>']
    if look.unsubscribe_url:
        links.append(f'<a href="{esc(look.unsubscribe_url)}" style="color:{MUTED};text-decoration:underline">'
                     f'{esc(look.texts.get("unsubscribe", "Unsubscribe"))}</a>')
    return (f'<tr><td style="padding:26px 12px 6px" align="center">'
            f'<a href="https://formalie.com" style="text-decoration:none"><table role="presentation" cellpadding="0" '
            f'cellspacing="0"><tr><td style="vertical-align:middle"><img src="{esc(assets_url())}/brand/formalie-mark-64.png" '
            f'alt="" width="22" height="22" style="display:block;border-radius:6px"></td>'
            f'<td style="padding-inline-start:8px;vertical-align:middle;font:700 14px/1 {FONT};letter-spacing:-.02em;'
            f'color:{INK}">Formalie</td></tr></table></a>'
            f'<p style="margin:10px 0 14px;font:12px/1.5 {FONT};color:{MUTED}">'
            f'{esc(look.texts.get("tagline", "Forms, data and access, under your control."))}</p>'
            f'<div style="width:40px;height:1px;background:{LINE};margin:0 auto 14px"></div>{reason}'
            f'<p style="margin:10px 0 0;font:12px/1.6 {FONT}">{sep.join(links)}</p></td></tr>')


def page(subject: str, body: str, values: dict[str, Any], look: Look,
         answers: list[dict[str, str]] | None = None) -> dict[str, str]:
    """→ {subject, html, text}. `body` is already filled in except {{answers}} (as ANSWERS)."""
    answers = answers or []
    direction = ' dir="rtl"' if look.language.split("-")[0] in RTL else ""
    html_page = (
        f'<!doctype html><html{direction}><head><meta charset="utf-8"><meta name="viewport" '
        f'content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">'
        f'<meta name="supported-color-schemes" content="light"><title>{esc(subject)}</title></head>'
        f'<body style="margin:0;padding:0;background:{CANVAS};-webkit-text-size-adjust:100%">'
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">{esc(subject)}</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CANVAS}"><tr>'
        f'<td align="center" style="padding:36px 14px 28px">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:580px"><tr><td>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};'
        f'border:1px solid {LINE};border-radius:18px;border-collapse:separate">{_header(look)}'
        f'<tr><td style="padding:30px 32px 12px"><h1 style="margin:0 0 16px;font:800 23px/1.3 {FONT};'
        f'letter-spacing:-.02em;color:{INK}">{esc(subject)}</h1>{_blocks(body, values, answers, look)}</td></tr>'
        f'</table></td></tr>{_footer(look)}</table></td></tr></table></body></html>')
    answers_text = "\n".join(f'{a["label"]}: {a["value"]}' for a in answers)
    footer_text = "\n".join(look.footer_lines)
    unsubscribe = f'\n{look.texts.get("unsubscribe", "Unsubscribe")}: {look.unsubscribe_url}' if look.unsubscribe_url else ""
    text = (f"{body.replace(ANSWERS, answers_text)}\n\n--\n{footer_text}\n\n"
            f"Formalie · https://formalie.com{unsubscribe}")
    return {"subject": subject, "html": html_page, "text": text}
