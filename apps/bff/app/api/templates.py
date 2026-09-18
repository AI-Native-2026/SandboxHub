from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import TenantContext, get_tenant_context, require_platform_admin
from app.core.security import Principal
from app.models import Template

router = APIRouter()


class TemplateBody(BaseModel):
    name: str
    description: str | None = None
    image: str
    entrypoint: list[str] | None = None
    env: dict | None = None
    default_cpu: str | None = "1"
    default_memory: str | None = "1Gi"
    default_timeout_seconds: int | None = 1800
    network_policy: dict | None = None
    icon: str | None = None
    tags: list[str] | None = None
    visibility: str = "public"



def _tpl(t: Template) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "description": t.description,
        "image": t.image,
        "entrypoint": t.entrypoint,
        "env": t.env,
        "default_cpu": t.default_cpu,
        "default_memory": t.default_memory,
        "default_timeout_seconds": t.default_timeout_seconds,
        "network_policy": t.network_policy,
        "icon": t.icon,
        "tags": t.tags or [],
        "visibility": t.visibility,
    }


@router.get("/templates")
async def list_templates(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(
            select(Template).where(
                Template.status == "active",
                or_(Template.tenant_id.is_(None), Template.tenant_id == ctx.tenant.id),
            )
        )
    ).scalars().all()
    return [_tpl(t) for t in rows]


@router.post("/templates", status_code=201)
async def create_template(
    body: TemplateBody,
    principal: Principal = Depends(require_platform_admin),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = Template(**body.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _tpl(t)


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    body: TemplateBody,
    principal: Principal = Depends(require_platform_admin),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from uuid import UUID

    t = (await db.execute(select(Template).where(Template.id == UUID(template_id)))).scalar_one_or_none()
    if t is None:
        from app.core.errors import NotFound

        raise NotFound("模板不存在")
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    await db.commit()
    await db.refresh(t)
    return _tpl(t)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    principal: Principal = Depends(require_platform_admin),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    from uuid import UUID

    t = (await db.execute(select(Template).where(Template.id == UUID(template_id)))).scalar_one_or_none()
    if t:
        t.status = "deleted"
        await db.commit()

