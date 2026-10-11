"""The audit trail's export file (registered with the exports module)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.audit import queries
from app.modules.exports.models import ExportJob
from app.modules.exports.service import register


async def build_audit_file(db: AsyncSession, job: ExportJob) -> tuple[bytes, int]:
    filters = job.params.get("filters") or {}
    organisation = job.params.get("organisation")
    rows = await queries.all_rows(db, job.tenant_id, filters, get_settings().export_max_rows)
    table = queries.rows_of([queries.view(row, organisation) for row in rows])
    content = queries.to_xlsx(table) if job.format == "xlsx" else queries.to_csv(table)
    return content, len(rows)


register("audit", build_audit_file)
