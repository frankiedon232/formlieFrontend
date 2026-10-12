"""Closing workspaces (B16): once a closing workspace's date has passed it becomes `closed`.

A soft state: nothing is deleted (owner rule, no hard deletes; purging stays a platform admin decision for later).
A closed workspace refuses sign-in and the API (FRM-TEN-1002 with `workspace: closed`) and its public forms take no
more answers (tenant.py `BLOCKED_STATUSES`). Run every 10 minutes by Beat (tasks.py).
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.core.db.session import db_session
from app.modules.audit.service import Actor, record

log = logging.getLogger("formalie.platform")


async def close_due() -> int:
    """Closes every closing workspace past its date (platform.close_due_workspaces), with an audit entry each."""
    async with db_session("write") as db:
        closed = (await db.execute(text(
            "SELECT id, organisation_id, subdomain, name, close_at FROM platform.close_due_workspaces()"))).all()
    if not closed:
        return 0
    from app.modules.forms.service import iso
    from app.modules.tenants.service import TenantDirectory

    directory = TenantDirectory()
    for row in closed:
        try:
            async with db_session("write", tenant_id=row.id, organisation_id=row.organisation_id) as db:
                await record(db, tenant_id=row.id, organisation_id=row.organisation_id, action="workspace.updated",
                             actor=Actor.system(), severity="warning",
                             resource={"type": "workspace", "id": str(row.id), "name": row.name},
                             changes=[{"field": "status", "before": "closing", "after": "closed"}],
                             metadata={"cause": "close_at_passed", "close_at": iso(row.close_at) or ""})
        except Exception:  # the status is already closed; a missing audit line must not stop the others
            log.exception("FRM-GEN-5000 workspace closed without its audit entry",
                          extra={"error_code": "FRM-GEN-5000", "tenant_id": str(row.id)})
        finally:
            await directory.forget(row.subdomain)
    log.info("closing workspaces closed", extra={"count": len(closed)})
    return len(closed)
