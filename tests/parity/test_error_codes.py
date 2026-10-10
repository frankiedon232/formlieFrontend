"""codes.py must match the frontend's shared/utils/errors/codes.ts and docs/ERROR-CODES.md exactly."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors.codes import ERROR_CODES
from scripts.gen_error_codes import ROOT, parse_codes_ts, parse_levels

pytestmark = pytest.mark.parity


def test_codes_match_frontend(frontend_dir: Path) -> None:
    frontend = parse_codes_ts(frontend_dir / "shared" / "utils" / "errors" / "codes.ts")
    assert set(frontend) == set(ERROR_CODES), "regenerate: python scripts/gen_error_codes.py"
    for code, (status, message) in frontend.items():
        assert ERROR_CODES[code].status == status, code
        assert ERROR_CODES[code].message == message, code


def test_every_code_is_documented_with_its_status_and_level() -> None:
    documented = parse_levels(ROOT / "docs" / "ERROR-CODES.md")
    for code, definition in ERROR_CODES.items():
        assert code in documented, f"{code} missing from ERROR-CODES.md"
        assert documented[code] == (definition.status, definition.level), code


def test_code_format() -> None:
    for code in ERROR_CODES:
        domain, number = code.split("-")[1:]
        assert code.startswith("FRM-") and domain.isupper() and len(number) == 4
        assert 1000 <= int(number) <= 1999 or 5000 <= int(number) <= 5999
