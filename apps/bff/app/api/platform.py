"""U4 scale routes: resource pools and observability."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import TenantContext, get_tenant_context, require_platform_admin
from app.core.errors import NotFound
from app.core.security import Principal
from app.models import PoolRegistry, SandboxRecord, Tenant, UsageSnapshot, User
from app.services.usage_sampler import cost

router = APIRouter()

POOL_PROVIDERS = [
    {"value": "docker", "label": "Docker", "description": "单机 Docker 运行时，适合单机 / 小规模"},
    {"value": "kubernetes", "label": "Kubernetes", "description": "分布式调度，支持 Pool 与原生多租户"},
]


@router.get("/pools/providers")
async def list_pool_providers() -> list[dict]:
    return POOL_PROVIDERS


def _pool(p: PoolRegistry, used: int = 0) -> dict:
    cap = p.capacity or {}
    return {
        "id": str(p.id),
        "name": p.name,
        "provider": p.provider,
        "image": p.image,
        "capacity": cap,
        "used": used,
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.get("/pools")
async def list_pools(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(
            select(PoolRegistry).where(
                (PoolRegistry.tenant_id.is_(None)) | (PoolRegistry.tenant_id == ctx.tenant.id)
            )
        )
    ).scalars().all()
    # Associate pools with user sandboxes by image: a pool warms capacity for an
    # image, so running sandboxes of that image count toward the pool's usage.
    image_counts = dict(
        (
            await db.execute(
                select(SandboxRecord.image, func.count())
                .where(SandboxRecord.tenant_id == ctx.tenant.id, SandboxRecord.status == "Running")
                .group_by(SandboxRecord.image)
            )
        ).all()
    )
    return [_pool(p, int(image_counts.get(p.image, 0)) if p.image else 0) for p in rows]


class PoolBody(BaseModel):
    name: str
    provider: str = "docker"
    image: str | None = None
    capacity: dict | None = None


@router.post("/pools", status_code=201)
async def create_pool(
    body: PoolBody,
    ctx: TenantContext = Depends(get_tenant_context),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    p = PoolRegistry(
        tenant_id=ctx.tenant.id, name=body.name, provider=body.provider,
        image=body.image, capacity=body.capacity or {"min": 0, "max": 5},
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _pool(p)


@router.delete("/pools/{pool_id}", status_code=204)
async def delete_pool(
    pool_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    p = (
        await db.execute(select(PoolRegistry).where(PoolRegistry.id == UUID(pool_id), PoolRegistry.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if p:
        await db.delete(p)
        await db.commit()


@router.get("/observability")
async def observability(
    days: int = 7,
    principal: Principal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    tenants = (await db.execute(select(func.count()).select_from(Tenant))).scalar_one()
    users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total = (await db.execute(select(func.count()).select_from(SandboxRecord))).scalar_one()
    running = (
        await db.execute(select(func.count()).select_from(SandboxRecord).where(SandboxRecord.status == "Running"))
    ).scalar_one()
    failed = (
        await db.execute(select(func.count()).select_from(SandboxRecord).where(SandboxRecord.status == "Failed"))
    ).scalar_one()
    usage = (
        await db.execute(
            select(
                func.coalesce(func.sum(UsageSnapshot.cpu_seconds), 0.0),
                func.coalesce(func.sum(UsageSnapshot.mem_gb_seconds), 0.0),
            ).where(UsageSnapshot.ts >= since)
        )
    ).one()
    by_state = (
        await db.execute(select(SandboxRecord.status, func.count()).group_by(SandboxRecord.status))
    ).all()
    series = (
        await db.execute(
            select(
                func.date_trunc("day", UsageSnapshot.ts).label("d"),
                func.coalesce(func.sum(UsageSnapshot.cpu_seconds), 0.0),
                func.coalesce(func.sum(UsageSnapshot.mem_gb_seconds), 0.0),
            )
            .where(UsageSnapshot.ts >= since)
            .group_by("d")
            .order_by("d")
        )
    ).all()
    timeseries = [
        {"date": d.isoformat()[:10], "cpu_hours": round(float(c) / 3600, 2), "mem_gb_hours": round(float(m) / 3600, 2)}
        for d, c, m in series
    ]
    return {
        "tenants": tenants,
        "users": users,
        "sandboxes": {"total": total, "running": running, "failed": failed,
                      "by_state": {s or "Unknown": c for s, c in by_state}},
        "usage": {
            "cpu_hours": round(float(usage[0]) / 3600, 2),
            "mem_gb_hours": round(float(usage[1]) / 3600, 2),
            "cost": round(cost(float(usage[0]), float(usage[1])), 2),
        },
        "timeseries": timeseries,
    }
