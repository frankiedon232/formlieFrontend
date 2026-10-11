"""The PDF of a response export (port of the mock's core/pdfDoc.ts and data/responseReport.ts, and
shared/utils/settings/appearance-ink.ts, readableOn): a designed report in the application's own look, held to the
frontend's bytes by tests/parity/test_report_rules.py.

A cover band with the organisation, the form and who exported what and when; status tiles; one card per response
with its questions and answers in two columns; cards never start at the foot of a page; "Page x of y" on every page.
Helvetica with WinAnsi encoding: text outside Latin-1 shows as "?" for now (embedding fonts for every script is an
open item, PROGRESS.md).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable

PAGE_W, PAGE_H = 595.28, 841.89
APP_INK = "#18181b"
SHADE_600 = {"indigo": "#4f46e5", "blue": "#2563eb", "sky": "#0284c7", "teal": "#0d9488", "emerald": "#059669",
             "green": "#16a34a", "amber": "#d97706", "orange": "#ea580c", "red": "#dc2626", "rose": "#e11d48",
             "pink": "#db2777", "violet": "#7c3aed", "purple": "#9333ea"}

_WIDTHS = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556,
    556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722,
    778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278,
    556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]
_WIN_ANSI = {"€": 0x80, "‚": 0x82, "„": 0x84, "…": 0x85, "‘": 0x91, "’": 0x92, "“": 0x93, "”": 0x94, "•": 0x95,
             "–": 0x96, "—": 0x97, "™": 0x99}
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sept", "Oct", "Nov", "Dec"]  # en-GB short months


# ── Colours ─────────────────────────────────────────────────────────────────────

def appearance_ink(appearance: dict[str, Any] | None, brand_color: str | None = None) -> str:
    """The workspace's main colour for files made outside the browser."""
    if not appearance or appearance.get("primary") == "mono":
        return APP_INK
    if appearance.get("primary") == "brand":
        return brand_color if brand_color and re.fullmatch(r"#[0-9a-fA-F]{6}", brand_color) else APP_INK
    return SHADE_600.get(appearance.get("primary") or "", APP_INK)


def _luminance(color: str) -> float:
    def channel(i: int) -> float:
        try:
            c = int(color[i:i + 2], 16) / 255
        except ValueError:
            c = float("nan")
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5)


def _contrast(a: str, b: str) -> float:
    x, y = sorted([_luminance(a), _luminance(b)], reverse=True)
    return (x + 0.05) / (y + 0.05)


def readable_on(color: str) -> str:
    """Black or white, whichever reads better on `color`."""
    return "#ffffff" if _contrast(color, "#ffffff") >= _contrast(color, "#18181b") else "#18181b"


# ── The PDF writer (pdfDoc.ts) ──────────────────────────────────────────────────

def _fixed(value: float, digits: int = 2) -> str:
    """Number.prototype.toFixed: the exact value rounded half up."""
    if value == 0:
        return f"{0:.{digits}f}"  # -0 too
    return str(Decimal(value).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def _units(text: str) -> list[str]:
    """JavaScript's view of a string as UTF-16 code units (astral characters count twice)."""
    out = []
    for ch in text:
        if ord(ch) > 0xFFFF:
            code = ord(ch) - 0x10000
            out += [chr(0xD800 + (code >> 10)), chr(0xDC00 + (code & 0x3FF))]
        else:
            out.append(ch)
    return out


def text_width(text: str, size: float, bold: bool = False) -> float:
    units = 0
    for ch in text:  # for…of walks code points
        code = ord(ch)
        units += _WIDTHS[code - 32] if 32 <= code <= 126 else 556
    return (units / 1000) * size * (1.06 if bold else 1)


def wrap_text(text: str, size: float, width: float, bold: bool = False) -> list[str]:
    """Lines that fit `width` (words kept whole unless a single word is too long)."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in [w for w in re.split(r"[\t\n\v\f\r    -     　﻿]+",
                                          paragraph) if w]:
            nxt = f"{line} {word}" if line else word
            if text_width(nxt, size, bold) <= width:
                line = nxt
            else:
                if line:
                    lines.append(line)
                rest = _units(word)
                while text_width("".join(rest), size, bold) > width and len(rest) > 1:
                    cut = len(rest) - 1
                    while cut > 1 and text_width("".join(rest[:cut]), size, bold) > width:
                        cut -= 1
                    lines.append(_join(rest[:cut]))
                    rest = rest[cut:]
                line = _join(rest)
        lines.append(line)
    return lines


def _join(units: list[str]) -> str:
    return "".join(units).encode("utf-16", "surrogatepass").decode("utf-16", "replace")


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = "".join(chr(_WIN_ANSI[c]) if c in _WIN_ANSI else c for c in text)
    text = "".join("?" * len(_units(c)) if not (" " <= c <= "ÿ") else c for c in text)
    return re.sub(r"[()\\]", lambda m: f"\\{m.group(0)}", text)


def _rgb(color: str) -> str:
    found = re.fullmatch(r"#?([0-9a-fA-F]{6})", color)
    value = found.group(1) if found else "18181b"
    return " ".join(_fixed(int(value[i:i + 2], 16) / 255, 3) for i in (0, 2, 4))


@dataclass
class PdfDoc:
    pages: list[list[str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.add_page()

    def add_page(self) -> None:
        self.current: list[str] = []
        self.pages.append(self.current)

    def rect(self, x: float, y: float, width: float, height: float, fill: str, radius: float = 0) -> None:
        n = _fixed
        top = PAGE_H - y
        if not radius:
            self.current.append(f"{_rgb(fill)} rg {n(x)} {n(top - height)} {n(width)} {n(height)} re f")
            return
        r = min(radius, width / 2, height / 2)
        k = r * 0.5523
        left, right, bottom = x, x + width, top - height
        self.current.append(
            f"{_rgb(fill)} rg {n(left + r)} {n(top)} m {n(right - r)} {n(top)} l {n(right - r + k)} {n(top)} {n(right)} "
            f"{n(top - r + k)} {n(right)} {n(top - r)} c "
            f"{n(right)} {n(bottom + r)} l {n(right)} {n(bottom + r - k)} {n(right - r + k)} {n(bottom)} {n(right - r)} "
            f"{n(bottom)} c "
            f"{n(left + r)} {n(bottom)} l {n(left + r - k)} {n(bottom)} {n(left)} {n(bottom + r - k)} {n(left)} "
            f"{n(bottom + r)} c "
            f"{n(left)} {n(top - r)} l {n(left)} {n(top - r + k)} {n(left + r - k)} {n(top)} {n(left + r)} {n(top)} c f")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 0.6) -> None:
        n = _fixed
        self.current.append(f"{_rgb(color)} RG {n(width)} w {n(x1)} {n(PAGE_H - y1)} m {n(x2)} {n(PAGE_H - y2)} l S")

    def text(self, x: float, y: float, value: str, *, size: float = 10, bold: bool = False, color: str = "#18181b",
             right: bool = False) -> None:
        left = x - text_width(value, size, bold) if right else x
        self.current.append(f"BT {_rgb(color)} rg /F{2 if bold else 1} {_fixed(size)} Tf {_fixed(left)} "
                            f"{_fixed(PAGE_H - y)} Td ({_clean(value)}) Tj ET")

    def render(self, footer: Callable[[PdfDoc, int, int], None] | None = None) -> bytes:
        if footer:
            for index, commands in enumerate(self.pages):
                self.current = commands
                footer(self, index + 1, len(self.pages))
        objects = ["<< /Type /Catalog /Pages 2 0 R >>", "",
                   "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
                   "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
        kids = []
        for commands in self.pages:
            stream = "\n".join(commands)
            objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
            contents = len(objects)
            objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_fixed(PAGE_W)} {_fixed(PAGE_H)}] /Contents "
                           f"{contents} 0 R /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>")
            kids.append(len(objects))
        objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
        pdf = "%PDF-1.4\n"
        offsets = []
        for i, obj in enumerate(objects):
            offsets.append(len(pdf))
            pdf += f"{i + 1} 0 obj\n{obj}\nendobj\n"
        xref = len(pdf)
        pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(f"{str(at).zfill(10)} 00000 n \n" for at in offsets)
        pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
        return bytes(ord(c) & 0xFF for c in pdf)


# ── The report (responseReport.ts) ──────────────────────────────────────────────

INK, MUTED, LINE, SOFT = "#18181b", "#71717a", "#e4e4e7", "#f4f4f5"
STATUS = {"new": ("New", "#18181b", "#e4e4e7"), "reviewed": ("Reviewed", "#b45309", "#fef3c7"),
          "approved": ("Approved", "#15803d", "#dcfce7"), "rejected": ("Rejected", "#b91c1c", "#fee2e2")}
CHANNEL = {"link": "Form link", "embed": "Embedded", "api": "API"}
M = 40
RIGHT = PAGE_W - M
BOTTOM = PAGE_H - 56
Q_X = M + 12
Q_W = 168
A_X = Q_X + Q_W + 14
A_W = RIGHT - 12 - A_X


def _when(moment: datetime) -> str:
    return f"{moment.day} {_MONTHS[moment.month - 1]} {moment.year}, {moment.hour:02d}:{moment.minute:02d} UTC"


def _initials(name: str) -> str:
    words = [w for w in re.split(r"\s+", name) if w][:2]
    return "".join(_units(w)[0].upper() for w in words) or "F"


def _thousands(value: int) -> str:
    return f"{value:,}"


def response_report(org: str, form: str, brand: str, exported_by: str, exported_at: datetime, scope: str,
                    counts: dict[str, int], responses: list[dict[str, Any]]) -> bytes:
    """`responses`: [{number, name, email, submitted, status, channel, tags, answers: [{question, answer}]}];
    `exported_at` in UTC."""
    doc = PdfDoc()
    on_brand = readable_on(brand)

    doc.rect(0, 0, PAGE_W, 132, brand)
    doc.rect(M, 28, 30, 30, on_brand, 6)
    doc.text(M + 15 - text_width(_initials(org), 11, True) / 2, 47, _initials(org), size=11, bold=True, color=brand)
    doc.text(M + 40, 47, org, size=12, bold=True, color=on_brand)
    doc.text(RIGHT, 47, "Responses export", size=9, color=on_brand, right=True)
    wrapped = wrap_text(form, 22, RIGHT - M, True)
    title = wrapped[0] if wrapped else form
    doc.text(M, 92, title, size=22, bold=True, color=on_brand)
    doc.text(M, 113, f"Exported {_when(exported_at)} by {exported_by}  ·  {len(responses)} responses  ·  {scope}",
             size=9.5, color=on_brand)

    tiles = [("Responses", len(responses), brand)] + [(STATUS[k][0], counts.get(k, 0), STATUS[k][1]) for k in STATUS]
    tile_w = (RIGHT - M - 8 * (len(tiles) - 1)) / len(tiles)
    for i, (label, value, color) in enumerate(tiles):
        x = M + i * (tile_w + 8)
        doc.rect(x, 150, tile_w, 54, SOFT, 6)
        doc.rect(x + 10, 162, 7, 7, color, 1.5)
        doc.text(x + 22, 169, label, size=8.5, color=MUTED)
        doc.text(x + 10, 193, _thousands(value), size=16, bold=True, color=INK)
    state = {"y": 226.0}

    def new_page() -> None:
        doc.add_page()
        doc.rect(0, 0, PAGE_W, 6, brand)
        doc.text(M, 30, form, size=9, bold=True, color=INK)
        doc.text(RIGHT, 30, org, size=9, color=MUTED, right=True)
        doc.line(M, 40, RIGHT, 40, LINE)
        state["y"] = 58

    for response in responses:
        rows = []
        for item in response["answers"]:
            q = wrap_text(item["question"], 8.5, Q_W)
            a = wrap_text(item["answer"], 10, A_W) if item["answer"] else ["–"]
            rows.append({"q": q, "a": a, "empty": not item["answer"], "height": max(len(q) * 11, len(a) * 13) + 10})
        header = 46
        if state["y"] + header + (rows[0]["height"] if rows else 0) > BOTTOM:
            new_page()

        def draw_header(continued: bool) -> None:
            y = state["y"]
            doc.rect(M, y, RIGHT - M, header, SOFT, 6)
            doc.rect(M, y, 4, header, brand, 2)
            number = f"#{response['number']}"
            doc.text(Q_X, y + 19, number, size=11, bold=True, color=brand)
            name_x = Q_X + text_width(number, 11, True) + 8
            name = response["name"] or response["email"] or number
            doc.text(name_x, y + 19, f"{name}{'  (continued)' if continued else ''}", size=11, bold=True, color=INK)
            label, color, fill = STATUS[response["status"]]
            pill_w = text_width(label, 8, True) + 16
            doc.rect(RIGHT - 12 - pill_w, y + 9, pill_w, 15, fill, 7.5)
            doc.text(RIGHT - 12 - pill_w / 2 - text_width(label, 8, True) / 2, y + 19.5, label, size=8, bold=True, color=color)
            parts = [response["email"], response["submitted"], CHANNEL.get(response["channel"], response["channel"]),
                     f"Tags: {', '.join(response['tags'])}" if response["tags"] else ""]
            meta = "   ·   ".join(p for p in parts if p)
            first = wrap_text(meta, 8.5, RIGHT - 24 - Q_X)
            doc.text(Q_X, y + 35, first[0] if first else "", size=8.5, color=MUTED)
            state["y"] = y + header + 6
        draw_header(False)
        for row in rows:
            if state["y"] + row["height"] > BOTTOM:
                new_page()
                draw_header(True)
            y = state["y"]
            for i, line in enumerate(row["q"]):
                doc.text(Q_X, y + 12 + i * 11, line, size=8.5, color=MUTED)
            for i, line in enumerate(row["a"]):
                doc.text(A_X, y + 12 + i * 13, line, size=10, color="#a1a1aa" if row["empty"] else INK)
            state["y"] = y + row["height"]
            doc.line(Q_X, state["y"] - 3, RIGHT - 12, state["y"] - 3, LINE, 0.5)
        state["y"] += 18

    def footer(page: PdfDoc, number: int, pages: int) -> None:
        page.line(M, PAGE_H - 40, RIGHT, PAGE_H - 40, LINE)
        page.text(M, PAGE_H - 26, f"{org}  ·  {form}  ·  {_when(exported_at)}", size=8, color=MUTED)
        page.text(RIGHT, PAGE_H - 26, f"Page {number} of {pages}", size=8, bold=True, color=INK, right=True)
    return doc.render(footer)
