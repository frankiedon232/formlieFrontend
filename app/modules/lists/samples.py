"""Formalie's sample lists (mock: data/libraryStore.ts SAMPLE_LISTS), given to the seeded development workspaces:
use-only (`system_key`), options in every language (data/option_translations.json, copied by
scripts/sync_frontend_data.py). Neutral places on several continents.
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.lists.models import OptionList

PLACES: dict[str, dict[str, list[str]]] = {
    "Brazil": {"São Paulo": ["São Paulo", "Campinas", "Santos"], "Rio de Janeiro": ["Rio de Janeiro", "Niterói"]},
    "Canada": {"Ontario": ["Toronto", "Ottawa", "Hamilton"], "Quebec": ["Montréal", "Québec City"]},
    "Germany": {"Bavaria": ["Munich", "Nuremberg", "Augsburg"], "Hesse": ["Frankfurt", "Wiesbaden"]},
    "India": {"Maharashtra": ["Mumbai", "Pune", "Nagpur"], "Karnataka": ["Bengaluru", "Mysuru"]},
    "Japan": {"Tokyo": ["Shinjuku", "Shibuya"], "Osaka": ["Osaka", "Sakai"]},
    "Kenya": {"Nairobi": ["Nairobi", "Westlands"], "Mombasa": ["Mombasa", "Nyali"]},
}
PRODUCTS: list[tuple[str, float, str]] = [
    ("Standing desk", 420, "Furniture"), ("Office chair", 189.5, "Furniture"), ("Monitor 27 inch", 239, "Equipment"),
    ("Laptop stand", 45, "Equipment"), ("Headset", 79, "Equipment"), ("Desk lamp", 32.5, "Furniture"),
]


@lru_cache(maxsize=1)
def _translations() -> dict[str, dict[str, str]]:
    return json.loads((Path(__file__).parent / "data" / "option_translations.json").read_text(encoding="utf-8"))


def _slug(text: str) -> str:
    plain = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.sub(r"^_+|_+$", "", re.sub(r"[^a-z0-9]+", "_", plain.lower()))


def _plain(key: str, name: str, labels: list[str]) -> dict[str, Any]:
    return {"system_key": key, "name": name, "options": [
        {"value": re.sub(r"[^a-z0-9]+", "_", label.lower()), "label": label,
         **({"translations": dict(_translations()[label])} if label in _translations() else {})} for label in labels]}


def _places() -> dict[str, Any]:
    options: list[dict[str, Any]] = []
    for country, regions in PLACES.items():
        options.append({"value": _slug(country), "label": country})
        for region, cities in regions.items():
            at = f"{_slug(country)}_{_slug(region)}"
            options.append({"value": at, "label": region, "level": 1, "parent": _slug(country)})
            options.extend({"value": f"{at}_{_slug(city)}", "label": city, "level": 2, "parent": at} for city in cities)
    return {"system_key": "places", "name": "Places", "description": "Country, region and city",
            "levels": [{"key": "country", "label": "Country"}, {"key": "region", "label": "Region"},
                       {"key": "city", "label": "City"}], "options": options}


def _products() -> dict[str, Any]:
    return {"system_key": "products", "name": "Sample products",
            "description": "Products with a price and a category, to try details in formulas and logic",
            "columns": [{"key": "price", "label": "Price"}, {"key": "category", "label": "Category"}],
            "options": [{"value": _slug(label), "label": label, "attrs": {"price": price, "category": category}}
                        for label, price, category in PRODUCTS]}


def sample_lists() -> list[dict[str, Any]]:
    return [
        _plain("priority", "Priority", ["Low", "Medium", "High", "Critical"]),
        _plain("departments", "Departments", ["Finance", "Operations", "People", "Sales", "Support", "Technology"]),
        _plain("weekdays", "Days of the week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),
        _plain("satisfaction", "Satisfaction", ["Very unhappy", "Unhappy", "Neutral", "Happy", "Very happy"]),
        _places(),
        _products(),
    ]


async def seed_sample_lists(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID) -> int:
    """The sample lists the workspace doesn't have yet (by system_key, or a list of its own with the same name);
    how many were added."""
    from app.modules.lists.service import save_options

    rows = (await db.execute(select(OptionList.system_key, OptionList.name).where(
        OptionList.tenant_id == tenant_id, OptionList.deleted_at.is_(None)))).all()
    keys, names = {r.system_key for r in rows if r.system_key}, {r.name.lower() for r in rows}
    added = 0
    for sample in sample_lists():
        if sample["system_key"] in keys or sample["name"].lower() in names:
            continue
        row = OptionList(tenant_id=tenant_id, organisation_id=organisation_id, name=sample["name"],
                         description=sample.get("description"), levels=sample.get("levels"),
                         columns=sample.get("columns"), system_key=sample["system_key"])
        db.add(row)
        await db.flush()
        await save_options(db, row, sample["options"], None)  # type: ignore[arg-type]
        added += 1
    return added
