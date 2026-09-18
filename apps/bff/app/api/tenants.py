from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, get_principal
from app.core.security import Principal
from app.models import Membership, Tenant, User

router = APIRouter()


@router.get("/tenants")
async def list_tenants(
    principal: Principal = Depends(get_principal),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(
            select(Tenant, Membership.role)
            .join(Membership, Membership.tenant_id == Tenant.id)
            .where(Membership.user_id == user.id)
        )
    ).all()
    result = [
        {"id": str(t.id), "slug": t.slug, "name": t.name, "status": t.status, "role": role}
        for t, role in rows
    ]
    if "platform-admin" in principal.roles:
        all_tenants = (await db.execute(select(Tenant))).scalars().all()
        have = {t["id"] for t in result}
        for t in all_tenants:
            if str(t.id) not in have:
                result.append(
                    {"id": str(t.id), "slug": t.slug, "name": t.name, "status": t.status, "role": "platform-admin"}
                )
    return result
