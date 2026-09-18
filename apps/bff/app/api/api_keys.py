from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, get_principal
from app.core.security import Principal
from app.models import ApiKey, User

router = APIRouter()


class KeyCreate(BaseModel):
    name: str
    # optional validity in days; None => never expires
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


def _key_dict(k: ApiKey) -> dict:
    return {
        "id": str(k.id),
        "name": k.name,
        "prefix": k.prefix,
        "status": k.status,
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        "expires_at": k.expires_at.isoformat() if k.expires_at else None,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }


@router.get("/api-keys")
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (await db.execute(select(ApiKey).where(ApiKey.user_id == user.id))).scalars().all()
    return [_key_dict(k) for k in rows]


@router.post("/api-keys", status_code=201)
async def create_key(
    body: KeyCreate,
    principal: Principal = Depends(get_principal),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = "sh_" + secrets.token_urlsafe(32)
    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
    key = ApiKey(
        user_id=user.id,
        name=body.name,
        prefix=raw[:10],
        key_hash=hashlib.sha256(raw.encode()).hexdigest(),
        scopes={"roles": principal.roles, "keycloak_sub": principal.sub},
        status="active",
        expires_at=expires_at,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return {**_key_dict(key), "api_key": raw}


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    from uuid import UUID

    key = (
        await db.execute(select(ApiKey).where(ApiKey.id == UUID(key_id), ApiKey.user_id == user.id))
    ).scalar_one_or_none()
    if key:
        key.status = "revoked"
        await db.commit()
