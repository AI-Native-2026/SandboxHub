from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import TenantContext, get_tenant_context
from app.models import AuditLog, SandboxRecord, Template

router = APIRouter()


@router.get("/overview")
async def overview(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenant_id = ctx.tenant.id

    rows = (
        await db.execute(
            select(SandboxRecord.status, func.count())
            .where(SandboxRecord.tenant_id == tenant_id)
            .group_by(SandboxRecord.status)
        )
    ).all()
    by_state = {state or "Unknown": count for state, count in rows}
    total = sum(by_state.values())

    template_count = (
        await db.execute(select(func.count()).select_from(Template))
    ).scalar_one()

    recent = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.ts.desc())
            .limit(10)
        )
    ).scalars().all()

    return {
        "tenant": {"id": str(tenant_id), "slug": ctx.tenant.slug, "name": ctx.tenant.name, "role": ctx.role},
        "sandboxes": {
            "total": total,
            "by_state": by_state,
            "quota": ctx.tenant.quota_sandboxes,
        },
        "templates": template_count,
        "recent_activity": [
            {
                "ts": a.ts.isoformat() if a.ts else None,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "result": a.result,
            }
            for a in recent
        ],
    }
