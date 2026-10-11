"""Field types that accept exactly what the frontend's validation (zod) accepts, so both sides agree.

`Email`: zod 4's `z.email()` rule (zod/v4/core/regexes.js `email`), copied as it is. It allows the reserved test
domains (.test, .example) that the sample accounts use, which the email-validator package refuses.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator

ZOD_EMAIL = re.compile(
    r"^(?:[A-Za-z0-9_'+\-]+\.)*[A-Za-z0-9_'+\-]*[A-Za-z0-9_+-]@(?:[A-Za-z0-9][A-Za-z0-9\-]*\.)+[A-Za-z]{2,}$"
)


def _email(value: str) -> str:
    value = value.strip()
    if len(value) > 254 or not ZOD_EMAIL.match(value):
        raise ValueError("Invalid email address")
    return value


Email = Annotated[str, AfterValidator(_email)]
