from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.db import get_db
from app.core.deps import require_platform_admin
from app.core.errors import NotFound
from app.core.security import Principal
from app.models import AuditLog, Membership, SandboxRecord, Setting, Tenant, User

router = APIRouter()


def _tenant(t: Tenant, sandbox_count: int = 0, member_count: int = 0) -> dict:
    return {
        "id": str(t.id),
        "slug": t.slug,
        "name": t.name,
        "status": t.status,
        "quota": {"cpu": t.quota_cpu, "memory": t.quota_memory, "sandboxes": t.quota_sandboxes},
        "sandbox_count": sandbox_count,
        "member_count": member_count,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


class TenantBody(BaseModel):
    slug: str
    name: str
    quota_cpu: str | None = "16"
    quota_memory: str | None = "32Gi"
    quota_sandboxes: int | None = 20


class TenantPatch(BaseModel):
    name: str | None = None
    status: str | None = None
    quota_cpu: str | None = None
    quota_memory: str | None = None
    quota_sandboxes: int | None = None


class MemberBody(BaseModel):
    email: str
    role: str = "developer"


class SettingsBody(BaseModel):
    key: str
    value: dict


@router.get("/admin/tenants")
async def list_tenants(
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    tenants = (await db.execute(select(Tenant))).scalars().all()
    result = []
    for t in tenants:
        sc = (await db.execute(select(func.count()).select_from(SandboxRecord).where(SandboxRecord.tenant_id == t.id))).scalar_one()
        mc = (await db.execute(select(func.count()).select_from(Membership).where(Membership.tenant_id == t.id))).scalar_one()
        result.append(_tenant(t, sc, mc))
    return result


@router.post("/admin/tenants", status_code=201)
async def create_tenant(
    body: TenantBody,
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = Tenant(**body.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    await record_audit(db, action="tenant.create", tenant_id=t.id, resource_type="tenant", resource_id=str(t.id))
    return _tenant(t)


@router.patch("/admin/tenants/{tenant_id}")
async def patch_tenant(
    tenant_id: str,
    body: TenantPatch,
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = (await db.execute(select(Tenant).where(Tenant.id == UUID(tenant_id)))).scalar_one_or_none()
    if t is None:
        raise NotFound("租户不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    await db.commit()
    await db.refresh(t)
    await record_audit(db, action="tenant.update", tenant_id=t.id, resource_type="tenant", resource_id=str(t.id))
    return _tenant(t)


@router.get("/admin/tenants/{tenant_id}/members")
async def list_members(
    tenant_id: str,
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.tenant_id == UUID(tenant_id))
        )
    ).all()
    return [
        {"user_id": str(u.id), "email": u.email, "display_name": u.display_name, "role": m.role}
        for m, u in rows
    ]


@router.post("/admin/tenants/{tenant_id}/members", status_code=201)
async def add_member(
    tenant_id: str,
    body: MemberBody,
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user is None:
        raise NotFound("用户不存在（需先登录过一次）")
    existing = (
        await db.execute(
            select(Membership).where(Membership.user_id == user.id, Membership.tenant_id == UUID(tenant_id))
        )
    ).scalar_one_or_none()
    if existing:
        existing.role = body.role
    else:
        db.add(Membership(user_id=user.id, tenant_id=UUID(tenant_id), role=body.role))
    await db.commit()
    return {"user_id": str(user.id), "email": user.email, "role": body.role}


@router.delete("/admin/tenants/{tenant_id}/members/{user_id}", status_code=204)
async def remove_member(
    tenant_id: str,
    user_id: str,
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    m = (
        await db.execute(
            select(Membership).where(Membership.tenant_id == UUID(tenant_id), Membership.user_id == UUID(user_id))
        )
    ).scalar_one_or_none()
    if m:
        await db.delete(m)
        await db.commit()


@router.get("/admin/audit")
async def list_audit(
    tenant: str | None = None,
    action: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    if tenant:
        stmt = stmt.where(AuditLog.tenant_id == UUID(tenant))
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "ts": a.ts.isoformat() if a.ts else None,
            "actor_user_id": str(a.actor_user_id) if a.actor_user_id else None,
            "tenant_id": str(a.tenant_id) if a.tenant_id else None,
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "result": a.result,
            "ip": a.ip,
            "detail": a.detail,
        }
        for a in rows
    ]


@router.get("/admin/audit/export")
async def export_audit(
    tenant: str | None = None,
    action: str | None = None,
    limit: int = Query(5000, ge=1, le=20000),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    import csv
    import io

    from fastapi.responses import Response

    stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    if tenant:
        stmt = stmt.where(AuditLog.tenant_id == UUID(tenant))
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    rows = (await db.execute(stmt)).scalars().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ts", "actor_user_id", "tenant_id", "action", "resource_type", "resource_id", "result", "ip"])
    for a in rows:
        w.writerow([
            a.ts.isoformat() if a.ts else "", a.actor_user_id or "", a.tenant_id or "",
            a.action, a.resource_type or "", a.resource_id or "", a.result, a.ip or "",
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sandboxhub-audit.csv"},
    )


@router.post("/admin/cleanup")
async def run_cleanup_now(
    principal: Principal = Depends(require_platform_admin),
) -> dict:
    from app.services.cleanup import reconcile_and_purge

    return await reconcile_and_purge()


@router.get("/admin/settings")
async def get_settings_all(
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (await db.execute(select(Setting))).scalars().all()
    return [{"key": s.key, "value": s.value} for s in rows]


@router.patch("/admin/settings")
async def patch_setting(
    body: SettingsBody,
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    s = (await db.execute(select(Setting).where(Setting.key == body.key))).scalar_one_or_none()
    if s is None:
        s = Setting(key=body.key, value=body.value)
        db.add(s)
    else:
        s.value = body.value
    await db.commit()
    await record_audit(db, action="settings.update", resource_type="setting", resource_id=body.key)
    return {"key": s.key, "value": s.value}


@router.get("/admin/metrics")
async def admin_metrics(
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenants = (await db.execute(select(func.count()).select_from(Tenant))).scalar_one()
    sandboxes = (await db.execute(select(func.count()).select_from(SandboxRecord))).scalar_one()
    active = (
        await db.execute(
            select(func.count()).select_from(SandboxRecord).where(SandboxRecord.status == "Running")
        )
    ).scalar_one()
    users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    return {"tenants": tenants, "sandboxes": sandboxes, "active_sandboxes": active, "users": users}
