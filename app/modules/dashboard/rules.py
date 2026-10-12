"""The dashboard's periods, buckets and forms filter (F21), ported from the frontend with parity tests:

- shared/utils/dashboard/buckets.ts: `bucketStart`, `bucketsOf`, `groupFor` (days, weeks from Monday, months, years;
  each bucket named by its first day),
- `periodFrom` in server/mock/routes/dashboard.ts: the period asked for (default the last 30 days), the one before it
  and its buckets,
- shared/utils/dashboard/scope.ts: `scopeFrom` (`folder`: a folder id or `none`; `owner`: a person's id).

Days are whole numbers (days since 1970-01-01), so any date the browser accepts works here too. A day here is a day
in the workspace's time zone (the routes turn moments into days first); the frontend's mock counts in UTC, which is the
same for a workspace on UTC. Recorded answers: scripts/dump_dashboard_rules.py → tests/vectors/dashboard_rules.json.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from datetime import date
from typing import Any

DASHBOARD_VIEWS = ("workspace", "forms", "data", "api")
DASHBOARD_GROUPS = ("day", "week", "month", "year")
EPOCH = 719163  # date(1970, 1, 1).toordinal()
_DAY_RX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ── Days ────────────────────────────────────────────────────────────────────────

def days_from_civil(y: int, m: int, d: int) -> int:
    """Days since 1970-01-01 of a calendar date (any year; month 1 to 12, the day may run past the month's end)."""
    y -= m <= 2
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468 + d - 1


def civil_from_days(z: int) -> tuple[int, int, int]:
    z += 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return yoe + era * 400 + (m <= 2), m, d


def iso_day(day: int) -> str:
    """toISOString().slice(0, 10): YYYY-MM-DD (years outside 0 to 9999 as JavaScript writes them)."""
    y, m, d = civil_from_days(day)
    year = f"{y:04d}" if 0 <= y <= 9999 else f"{'-' if y < 0 else '+'}{abs(y):06d}"
    return f"{year}-{m:02d}-{d:02d}"[:10]


def parse_day(value: Any) -> int | None:
    """A YYYY-MM-DD text as the browser reads it (month 1 to 12, day 1 to 31, rolling into the next month), else None."""
    if not isinstance(value, str) or not _DAY_RX.match(value):
        return None
    y, m, d = int(value[:4]), int(value[5:7]), int(value[8:10])
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return None
    return days_from_civil(y, m, d)


def day_of(value: date) -> int:
    return value.toordinal() - EPOCH


def date_of(day: int) -> date:
    """The calendar date of a day number (clamped to what Python dates hold)."""
    return date.fromordinal(min(max(day + EPOCH, date.min.toordinal()), date.max.toordinal()))


# ── Buckets (shared/utils/dashboard/buckets.ts) ─────────────────────────────────

def _utc(y: int, m: int, d: int = 1) -> int:
    """Date.UTC(y, m - 1, d): years 0 to 99 mean 1900 to 1999, then months past December roll into the next year."""
    y = y + 1900 if 0 <= y <= 99 else y
    return days_from_civil(y + (m - 1) // 12, (m - 1) % 12 + 1, 1) + d - 1


def bucket_start(day: int, group: str) -> int:
    """The first day of the bucket a day falls in."""
    y, m, d = civil_from_days(day)
    if group == "day":
        return _utc(y, m, d)
    if group == "week":
        return _utc(y, m, d) - ((day + 4) % 7 + 6) % 7  # getUTCDay(): 1970-01-01 was a Thursday (4)
    return _utc(y, m) if group == "month" else _utc(y, 1)


def _next(at: int, group: str) -> int:
    if group == "day":
        return at + 1
    if group == "week":
        return at + 7
    y, m, _ = civil_from_days(at)
    return _utc(y, m + 1) if group == "month" else _utc(y + 1, 1)


def buckets_of(start: int, end: int, group: str) -> list[str]:
    """Every bucket from `start` to `end` (both days, inclusive), in order, at most 400."""
    out: list[str] = []
    at, last = bucket_start(start, group), bucket_start(end, group)
    while at <= last and len(out) < 400:
        out.append(iso_day(at))
        at = _next(at, group)
    return out


def group_for(days: int) -> str:
    """The group that fits a period best when none is chosen (about 7 to 60 points)."""
    return "day" if days <= 62 else "week" if days <= 400 else "month" if days <= 1500 else "year"


# ── The period (periodFrom) ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class Period:
    start: int  # `from`
    end: int  # `to`
    days: int
    group: str
    prev_start: int  # the same length just before
    buckets: list[str]

    @cached_property
    def index(self) -> dict[str, int]:
        return {start: i for i, start in enumerate(self.buckets)}

    def bucket_of(self, day: int) -> int | None:
        """The bucket a day of the period falls in (None outside the chart)."""
        return self.index.get(iso_day(bucket_start(day, self.group)))


def period_from(query: dict[str, Any], today: int) -> Period:
    """`from` / `to` (default the last 30 days up to today), `group` (else the one that fits)."""
    end = parse_day(query.get("to"))
    start = parse_day(query.get("from"))
    if end is None:
        end = today
    if start is None or start > end:
        start = end - 29
    days = end - start + 1
    group = query.get("group") if query.get("group") in DASHBOARD_GROUPS else group_for(days)
    return Period(start, end, days, group, start - days, buckets_of(start, end, group))


# ── The forms filter (scopeFrom) ────────────────────────────────────────────────

@dataclass(frozen=True)
class Scope:
    folder: str | None
    owner: str | None

    @property
    def filtered(self) -> bool:
        return bool(self.folder or self.owner)

    def matches(self, folder_id: str | None, owner_id: str) -> bool:
        return (not self.folder or (folder_id or "none") == self.folder) and (not self.owner or owner_id == self.owner)


def scope_from(query: dict[str, Any]) -> Scope:
    folder = query.get("folder") if isinstance(query.get("folder"), str) and query.get("folder") else None
    owner = query.get("owner") if isinstance(query.get("owner"), str) and query.get("owner") else None
    return Scope(folder, owner)
