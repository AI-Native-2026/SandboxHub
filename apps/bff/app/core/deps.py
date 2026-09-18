"""FastAPI dependencies: auth principal, current user, tenant context, RBAC."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import Forbidden, Unauthenticated
from app.core.security import Principal, decode_token
from app.models import Membership, Tenant, User


async def get_principal(request: Request, db: AsyncSession = Depends(get_db)) -> Principal:
    settings = get_settings()
    if settings.bff_auth_disabled:
        return Principal(sub="dev-admin", username="dev-admin", email="dev@local", roles=["platform-admin"])

    api_key = request.headers.get("X-API-Key")
    if api_key:
        import hashlib
        from datetime import datetime, timezone

        from app.models import ApiKey

        h = hashlib.sha256(api_key.encode()).hexdigest()
        key = (
            await db.execute(select(ApiKey).where(ApiKey.key_hash == h, ApiKey.status == "active"))
        ).scalar_one_or_none()
        if key is None:
            raise Unauthenticated("API Key 无效")
        now = datetime.now(timezone.utc)
        if key.expires_at and key.expires_at < now:
            key.status = "expired"
            await db.commit()
            raise Unauthenticated("API Key 已过期")
        key.last_used_at = now
        await db.commit()
        scopes = key.scopes or {}
        return Principal(sub=scopes.get("keycloak_sub", ""), roles=scopes.get("roles", []))

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise Unauthenticated("缺少访问令牌")
    token = auth.split(" ", 1)[1].strip()
    try:
        return decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise Unauthenticated(f"令牌校验失败: {exc}") from exc


async def get_current_user(
    principal: Principal = Depends(get_principal),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = (await db.execute(select(User).where(User.keycloak_sub == principal.sub))).scalar_one_or_none()
    if user is None:
        user = User(
            keycloak_sub=principal.sub,
            email=principal.email,
            display_name=principal.name or principal.username or principal.sub,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    await _ensure_default_membership(db, user, principal)
    return user


_ROLE_PRIORITY = ["platform-admin", "tenant-admin", "developer", "viewer"]


async def _ensure_default_membership(db: AsyncSession, user: User, principal: Principal) -> None:
    """Auto-onboard a user with no membership into the default tenant."""
    existing = (
        await db.execute(select(Membership).where(Membership.user_id == user.id))
    ).first()
    if existing is not None:
        return
    tenant = (await db.execute(select(Tenant).where(Tenant.slug == "demo"))).scalar_one_or_none()
    if tenant is None:
        return
    role = "developer"
    for candidate in _ROLE_PRIORITY:
        if candidate in principal.roles:
            role = candidate
            break
    db.add(Membership(user_id=user.id, tenant_id=tenant.id, role=role))
    await db.commit()


@dataclass
class TenantContext:
    tenant: Tenant
    role: str  # effective role within tenant


async def get_tenant_context(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    principal: Principal = Depends(get_principal),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    if not x_tenant_id:
        raise Forbidden("缺少租户上下文（X-Tenant-Id）")
    tenant = None
    try:
        tenant = (await db.execute(select(Tenant).where(Tenant.id == UUID(x_tenant_id)))).scalar_one_or_none()
    except ValueError:
        tenant = None
    if tenant is None:
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == x_tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise Forbidden("租户不存在或无权访问")

    is_platform_admin = "platform-admin" in principal.roles
    membership = (
        await db.execute(
            select(Membership).where(Membership.user_id == user.id, Membership.tenant_id == tenant.id)
        )
    ).scalar_one_or_none()

    if membership is None and not is_platform_admin:
        raise Forbidden("不属于该租户")
    role = membership.role if membership else "platform-admin"
    return TenantContext(tenant=tenant, role=role)


def require_platform_admin(principal: Principal = Depends(get_principal)) -> Principal:
    if "platform-admin" not in principal.roles:
        raise Forbidden("需要平台管理员权限")
    return principal


def require_writer(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    if ctx.role == "viewer":
        raise Forbidden("只读角色无权执行此操作")
    return ctx
