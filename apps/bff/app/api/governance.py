"""U1 governance routes: usage/cost, approvals, credentials, policy templates, quota."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.db import get_db
from app.core.deps import (
    TenantContext,
    get_current_user,
    get_principal,
    get_tenant_context,
    require_platform_admin,
    require_writer,
)
from app.core.errors import Forbidden, NotFound
from app.core.security import Principal
from app.models import (
    Approval,
    CredentialRef,
    PolicyTemplate,
    SandboxRecord,
    UsageSnapshot,
    User,
)
from app.services.usage_sampler import cost

router = APIRouter()


# ---------------------------------------------------------------- usage / cost

@router.get("/usage/summary")
async def usage_summary(
    days: int = Query(7, ge=1, le=90),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                func.coalesce(func.sum(UsageSnapshot.cpu_seconds), 0.0),
                func.coalesce(func.sum(UsageSnapshot.mem_gb_seconds), 0.0),
            ).where(UsageSnapshot.tenant_id == ctx.tenant.id, UsageSnapshot.ts >= since)
        )
    ).one()
    cpu_s, mem_s = float(rows[0]), float(rows[1])
    active = (
        await db.execute(
            select(func.count()).select_from(SandboxRecord).where(
                SandboxRecord.tenant_id == ctx.tenant.id, SandboxRecord.status == "Running"
            )
        )
    ).scalar_one()
    return {
        "days": days,
        "cpu_hours": round(cpu_s / 3600.0, 2),
        "mem_gb_hours": round(mem_s / 3600.0, 2),
        "cost": round(cost(cpu_s, mem_s), 2),
        "active_sandboxes": active,
    }


@router.get("/usage/timeseries")
async def usage_timeseries(
    days: int = Query(7, ge=1, le=90),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                func.date_trunc("day", UsageSnapshot.ts).label("d"),
                func.coalesce(func.sum(UsageSnapshot.cpu_seconds), 0.0),
                func.coalesce(func.sum(UsageSnapshot.mem_gb_seconds), 0.0),
            )
            .where(UsageSnapshot.tenant_id == ctx.tenant.id, UsageSnapshot.ts >= since)
            .group_by("d")
            .order_by("d")
        )
    ).all()
    return [
        {"date": d.isoformat()[:10], "cpu_hours": round(float(c) / 3600, 2),
         "mem_gb_hours": round(float(m) / 3600, 2), "cost": round(cost(float(c), float(m)), 2)}
        for d, c, m in rows
    ]


@router.get("/usage/top")
async def usage_top(
    days: int = Query(7, ge=1, le=90),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                UsageSnapshot.sandbox_id,
                func.coalesce(func.sum(UsageSnapshot.cpu_seconds), 0.0),
                func.coalesce(func.sum(UsageSnapshot.mem_gb_seconds), 0.0),
            )
            .where(UsageSnapshot.tenant_id == ctx.tenant.id, UsageSnapshot.ts >= since)
            .group_by(UsageSnapshot.sandbox_id)
            .order_by(func.sum(UsageSnapshot.cpu_seconds).desc())
            .limit(10)
        )
    ).all()
    return [
        {"sandbox_id": s, "cpu_hours": round(float(c) / 3600, 2),
         "mem_gb_hours": round(float(m) / 3600, 2), "cost": round(cost(float(c), float(m)), 2)}
        for s, c, m in rows
    ]


# ---------------------------------------------------------------- quota

@router.get("/quota")
async def get_quota(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = ctx.tenant
    running = (
        await db.execute(
            select(func.count()).select_from(SandboxRecord).where(
                SandboxRecord.tenant_id == t.id, SandboxRecord.status == "Running"
            )
        )
    ).scalar_one()
    total = (
        await db.execute(select(func.count()).select_from(SandboxRecord).where(SandboxRecord.tenant_id == t.id))
    ).scalar_one()
    return {
        "quota": {"cpu": t.quota_cpu, "memory": t.quota_memory, "sandboxes": t.quota_sandboxes},
        "usage": {"running": running, "total": total},
    }


# ---------------------------------------------------------------- approvals

class ApprovalBody(BaseModel):
    kind: str
    payload: dict | None = None
    reason: str | None = None


class DecisionBody(BaseModel):
    approve: bool
    note: str | None = None


def _approval_dict(a: Approval) -> dict:
    return {
        "id": str(a.id),
        "tenant_id": str(a.tenant_id) if a.tenant_id else None,
        "kind": a.kind,
        "payload": a.payload,
        "reason": a.reason,
        "status": a.status,
        "decision_note": a.decision_note,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
    }


@router.get("/approvals")
async def list_approvals(
    scope: str = Query("mine"),
    ctx: TenantContext = Depends(get_tenant_context),
    user: User = Depends(get_current_user),
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = select(Approval).order_by(Approval.created_at.desc())
    if scope == "pending":
        if ctx.role not in ("platform-admin", "tenant-admin"):
            raise Forbidden("需要管理员权限查看待审批")
        stmt = stmt.where(Approval.tenant_id == ctx.tenant.id, Approval.status == "pending")
    else:
        stmt = stmt.where(Approval.requester_user_id == user.id)
    rows = (await db.execute(stmt)).scalars().all()
    return [_approval_dict(a) for a in rows]


@router.post("/approvals", status_code=201)
async def create_approval(
    body: ApprovalBody,
    ctx: TenantContext = Depends(require_writer),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    a = Approval(
        tenant_id=ctx.tenant.id, requester_user_id=user.id,
        kind=body.kind, payload=body.payload or {}, reason=body.reason,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    await record_audit(db, action="approval.create", actor_user_id=user.id, tenant_id=ctx.tenant.id,
                       resource_type="approval", resource_id=str(a.id))
    return _approval_dict(a)


@router.post("/approvals/{approval_id}/decision")
async def decide_approval(
    approval_id: str,
    body: DecisionBody,
    ctx: TenantContext = Depends(get_tenant_context),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if ctx.role not in ("platform-admin", "tenant-admin"):
        raise Forbidden("需要管理员权限")
    a = (await db.execute(select(Approval).where(Approval.id == UUID(approval_id)))).scalar_one_or_none()
    if a is None:
        raise NotFound("申请不存在")
    a.status = "approved" if body.approve else "rejected"
    a.decided_by = user.id
    a.decided_at = datetime.now(timezone.utc)
    a.decision_note = body.note
    await db.commit()
    await record_audit(db, action=f"approval.{a.status}", actor_user_id=user.id, tenant_id=ctx.tenant.id,
                       resource_type="approval", resource_id=approval_id)
    return _approval_dict(a)


# ---------------------------------------------------------------- credentials

class CredentialBody(BaseModel):
    name: str
    type: str = "bearer"
    secret: str | None = None
    detail: dict | None = None


@router.get("/credentials")
async def list_credentials(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(select(CredentialRef).where(CredentialRef.tenant_id == ctx.tenant.id))
    ).scalars().all()
    return [
        {"id": str(c.id), "name": c.name, "type": c.type, "secret_ref": c.secret_ref,
         "detail": c.detail, "created_at": c.created_at.isoformat() if c.created_at else None}
        for c in rows
    ]


@router.post("/credentials", status_code=201)
async def create_credential(
    body: CredentialBody,
    ctx: TenantContext = Depends(get_tenant_context),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    import base64

    ref = "vault://" + base64.b64encode(body.secret.encode()).decode()[:16] if body.secret else None
    c = CredentialRef(tenant_id=ctx.tenant.id, name=body.name, type=body.type, secret_ref=ref, detail=body.detail)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": str(c.id), "name": c.name, "type": c.type, "secret_ref": c.secret_ref}


@router.delete("/credentials/{cred_id}", status_code=204)
async def delete_credential(
    cred_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    c = (
        await db.execute(select(CredentialRef).where(CredentialRef.id == UUID(cred_id), CredentialRef.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if c:
        await db.delete(c)
        await db.commit()


# ---------------------------------------------------------------- policy templates

class PolicyTemplateBody(BaseModel):
    name: str
    default_action: str = "deny"
    rules: list[dict] | None = None


@router.get("/policy-templates")
async def list_policy_templates(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(
            select(PolicyTemplate).where(
                (PolicyTemplate.tenant_id.is_(None)) | (PolicyTemplate.tenant_id == ctx.tenant.id)
            )
        )
    ).scalars().all()
    return [
        {"id": str(p.id), "name": p.name, "default_action": p.default_action, "rules": p.rules or []}
        for p in rows
    ]


@router.post("/policy-templates", status_code=201)
async def create_policy_template(
    body: PolicyTemplateBody,
    ctx: TenantContext = Depends(get_tenant_context),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    p = PolicyTemplate(tenant_id=ctx.tenant.id, name=body.name, default_action=body.default_action, rules=body.rules)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": str(p.id), "name": p.name, "default_action": p.default_action, "rules": p.rules or []}


@router.delete("/policy-templates/{tpl_id}", status_code=204)
async def delete_policy_template(
    tpl_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    p = (
        await db.execute(select(PolicyTemplate).where(PolicyTemplate.id == UUID(tpl_id), PolicyTemplate.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if p:
        await db.delete(p)
        await db.commit()
