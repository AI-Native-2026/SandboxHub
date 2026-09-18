"""U3 security routes: session recordings, RBAC roles."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import TenantContext, get_tenant_context, require_platform_admin
from app.core.errors import NotFound
from app.core.security import Principal
from app.models import CustomRole, Recording

router = APIRouter()


def _rec(r: Recording) -> dict:
    return {
        "id": str(r.id),
        "sandbox_id": r.sandbox_id,
        "name": r.name,
        "size_bytes": r.size_bytes,
        "chunks": len(r.chunks or []),
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "ended_at": r.ended_at.isoformat() if r.ended_at else None,
    }


@router.get("/recordings")
async def list_recordings(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(
            select(Recording).where(Recording.tenant_id == ctx.tenant.id).order_by(Recording.started_at.desc())
        )
    ).scalars().all()
    return [_rec(r) for r in rows]


@router.get("/recordings/{recording_id}")
async def get_recording(
    recording_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    r = (
        await db.execute(select(Recording).where(Recording.id == UUID(recording_id), Recording.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if r is None:
        raise NotFound("录制不存在")
    return {**_rec(r), "data": r.chunks or []}


@router.delete("/recordings/{recording_id}", status_code=204)
async def delete_recording(
    recording_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    r = (
        await db.execute(select(Recording).where(Recording.id == UUID(recording_id), Recording.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if r:
        await db.delete(r)
        await db.commit()


# ---------------------------------------------------------------- RBAC

ROLE_MATRIX = {
    "resources": ["sandbox", "template", "credential", "policy", "tenant", "audit", "recording"],
    "actions": ["view", "create", "update", "delete"],
    "roles": {
        "platform-admin": {r: ["view", "create", "update", "delete"] for r in
                           ["sandbox", "template", "credential", "policy", "tenant", "audit", "recording"]},
        "tenant-admin": {
            "sandbox": ["view", "create", "update", "delete"],
            "template": ["view", "create", "update"],
            "credential": ["view"],
            "policy": ["view", "create", "update"],
            "tenant": ["view"],
            "audit": ["view"],
            "recording": ["view", "delete"],
        },
        "developer": {
            "sandbox": ["view", "create", "update", "delete"],
            "template": ["view"],
            "credential": [],
            "policy": ["view"],
            "tenant": [],
            "audit": [],
            "recording": ["view"],
        },
        "viewer": {r: ["view"] for r in ["sandbox", "template", "audit", "recording"]},
    },
}


@router.get("/rbac/roles")
async def list_roles(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    custom = (
        await db.execute(select(CustomRole).where(CustomRole.tenant_id == ctx.tenant.id))
    ).scalars().all()
    return {
        "matrix": ROLE_MATRIX,
        "custom": [{"id": str(c.id), "name": c.name, "permissions": c.permissions} for c in custom],
    }


class RoleBody(BaseModel):
    name: str
    permissions: list[str] | None = None


@router.post("/rbac/roles", status_code=201)
async def create_role(
    body: RoleBody,
    ctx: TenantContext = Depends(get_tenant_context),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    c = CustomRole(tenant_id=ctx.tenant.id, name=body.name, permissions=body.permissions or [])
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": str(c.id), "name": c.name, "permissions": c.permissions}


@router.delete("/rbac/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    c = (
        await db.execute(select(CustomRole).where(CustomRole.id == UUID(role_id), CustomRole.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if c:
        await db.delete(c)
        await db.commit()
