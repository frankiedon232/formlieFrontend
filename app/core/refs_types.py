"""`RefId`: the type for every id a route takes (path, query or body).

The envelope layer turns references into ids and remembers which ones it decoded (RequestContext.ref_ids).
A RefId field accepts only those: a raw UUID typed into a body or a query is refused (FRM-GEN-1002), and one typed
into the address never matches a route (FRM-GEN-1004), so ids can only come from what the server handed out.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from pydantic import BeforeValidator

from app.core.context import get_context


def _must_be_reference(value: Any) -> Any:
    ctx = get_context()
    text = str(value).lower()
    if ctx is None or text not in {i.lower() for i in ctx.ref_ids}:
        raise ValueError("not a valid reference")
    return value


RefId = Annotated[uuid.UUID, BeforeValidator(_must_be_reference)]
