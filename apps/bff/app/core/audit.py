"""Audit logging helper."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_user_id=None,
    tenant_id=None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    result: str = "success",
    ip: str | None = None,
    user_agent: str | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            ip=ip,
            user_agent=user_agent,
            detail=detail or {},
        )
    )
    await db.commit()
