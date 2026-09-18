from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, get_principal
from app.core.security import Principal
from app.models import Membership, Tenant, User

router = APIRouter()


def _tenant_dict(t: Tenant, role: str) -> dict:
    return {
        "id": str(t.id),
        "slug": t.slug,
        "name": t.name,
        "status": t.status,
        "role": role,
        "quota": {
            "cpu": t.quota_cpu,
            "memory": t.quota_memory,
            "sandboxes": t.quota_sandboxes,
        },
    }


@router.get("/me")
async def get_me(
    principal: Principal = Depends(get_principal),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    is_platform_admin = "platform-admin" in principal.roles
    rows = (
        await db.execute(
            select(Tenant, Membership.role)
            .join(Membership, Membership.tenant_id == Tenant.id)
            .where(Membership.user_id == user.id)
        )
    ).all()
    tenants = [_tenant_dict(t, role) for t, role in rows]
    if is_platform_admin:
        all_rows = (await db.execute(select(Tenant))).scalars().all()
        have = {t["id"] for t in tenants}
        for t in all_rows:
            if str(t.id) not in have:
                tenants.append(_tenant_dict(t, "platform-admin"))
    return {
        "user": {
            "id": str(user.id),
            "username": principal.username or user.display_name,
            "email": user.email,
            "display_name": user.display_name,
        },
        "roles": principal.roles,
        "is_platform_admin": is_platform_admin,
        "tenants": tenants,
    }
