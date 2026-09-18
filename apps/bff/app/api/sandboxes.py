from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import TenantContext, get_current_user, get_tenant_context, require_writer
from app.models import User
from app.services import sandbox_service as svc
from app.services.upstream import OpenSandboxClient, osb_client

router = APIRouter()


class CreateSandboxBody(BaseModel):
    template_id: str | None = None
    image: str | None = None
    name: str | None = None
    entrypoint: list[str] | None = None
    env: dict[str, str] | None = None
    cpu: str | None = None
    memory: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=60, le=86400)
    network_policy: dict | None = None
    policy_template_id: str | None = None


class RenewBody(BaseModel):
    timeout_seconds: int = Field(ge=60, le=86400)


class MetadataBody(BaseModel):
    metadata: dict


class PolicyBody(BaseModel):
    defaultAction: str = "deny"
    egress: list[dict] | None = None


class SnapshotBody(BaseModel):
    name: str | None = None


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/sandboxes")
async def list_sandboxes(
    state: str | None = Query(None, description="逗号分隔的多个状态"),
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    states = [s.strip() for s in state.split(",") if s.strip()] if state else None
    return await svc.list_sandboxes(db, osb, tenant=ctx.tenant, states=states, q=q, page=page, size=size)


@router.post("/sandboxes", status_code=201)
async def create_sandbox(
    body: CreateSandboxBody,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return await svc.create_sandbox(
        db, osb, tenant=ctx.tenant, user=user, body=body.model_dump(exclude_none=True),
        ip=_client_ip(request), user_agent=request.headers.get("user-agent"),
    )


@router.get("/sandboxes/{sandbox_id}")
async def get_sandbox(
    sandbox_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return await svc.get_sandbox(db, osb, tenant=ctx.tenant, sandbox_id=sandbox_id)


@router.delete("/sandboxes/{sandbox_id}", status_code=204)
async def delete_sandbox(
    sandbox_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osb: OpenSandboxClient = Depends(osb_client),
) -> None:
    await svc.delete_sandbox(db, osb, tenant=ctx.tenant, user=user, sandbox_id=sandbox_id,
                             ip=_client_ip(request), user_agent=request.headers.get("user-agent"))


@router.get("/sandboxes/{sandbox_id}/events")
async def sandbox_events(
    sandbox_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    osb: OpenSandboxClient = Depends(osb_client),
) -> StreamingResponse:
    await svc.get_record(db, ctx.tenant, sandbox_id)

    async def gen():
        last = None
        for _ in range(900):  # ~30 min at 2s
            try:
                up = await osb.get_sandbox(sandbox_id)
                st = up.get("status", {})
                key = (st.get("state"), st.get("reason"))
                if key != last:
                    last = key
                    payload = {
                        "type": "status",
                        "state": st.get("state"),
                        "reason": st.get("reason"),
                        "message": st.get("message"),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(2)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/sandboxes/{sandbox_id}/pause")
async def pause_sandbox(
    sandbox_id: str, request: Request,
    ctx: TenantContext = Depends(require_writer), user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db), osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return await svc.pause_sandbox(db, osb, tenant=ctx.tenant, user=user, sandbox_id=sandbox_id,
                                   ip=_client_ip(request), user_agent=request.headers.get("user-agent"))


@router.post("/sandboxes/{sandbox_id}/resume")
async def resume_sandbox(
    sandbox_id: str, request: Request,
    ctx: TenantContext = Depends(require_writer), user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db), osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return await svc.resume_sandbox(db, osb, tenant=ctx.tenant, user=user, sandbox_id=sandbox_id,
                                    ip=_client_ip(request), user_agent=request.headers.get("user-agent"))


@router.post("/sandboxes/{sandbox_id}/renew")
async def renew_sandbox(
    sandbox_id: str, body: RenewBody, request: Request,
    ctx: TenantContext = Depends(require_writer), user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db), osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return await svc.renew_sandbox(db, osb, tenant=ctx.tenant, user=user, sandbox_id=sandbox_id,
                                   timeout_seconds=body.timeout_seconds,
                                   ip=_client_ip(request), user_agent=request.headers.get("user-agent"))


@router.patch("/sandboxes/{sandbox_id}/metadata")
async def patch_metadata(
    sandbox_id: str, body: MetadataBody, request: Request,
    ctx: TenantContext = Depends(require_writer), user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db), osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return await svc.patch_metadata(db, osb, tenant=ctx.tenant, user=user, sandbox_id=sandbox_id,
                                    metadata=body.metadata,
                                    ip=_client_ip(request), user_agent=request.headers.get("user-agent"))


@router.get("/sandboxes/{sandbox_id}/endpoints/{port}")
async def get_endpoint(
    sandbox_id: str, port: int,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db), osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return await svc.get_endpoint(db, osb, tenant=ctx.tenant, sandbox_id=sandbox_id, port=port)


@router.get("/sandboxes/{sandbox_id}/networkpolicy")
async def get_policy(
    sandbox_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db), osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    try:
        policy = await svc.get_network_policy(db, osb, tenant=ctx.tenant, sandbox_id=sandbox_id)
    except Exception:  # noqa: BLE001  (upstream 404 when no policy set)
        policy = {"defaultAction": "deny", "egress": []}
    return {"policy": policy}


@router.put("/sandboxes/{sandbox_id}/networkpolicy")
async def put_policy(
    sandbox_id: str, body: PolicyBody, request: Request,
    ctx: TenantContext = Depends(require_writer), user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db), osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return {"result": await svc.put_network_policy(db, osb, tenant=ctx.tenant, user=user, sandbox_id=sandbox_id,
                                                    policy=body.model_dump(exclude_none=True),
                                                    ip=_client_ip(request), user_agent=request.headers.get("user-agent"))}


@router.post("/sandboxes/{sandbox_id}/snapshots", status_code=201)
async def create_snapshot(
    sandbox_id: str, body: SnapshotBody, request: Request,
    ctx: TenantContext = Depends(require_writer), user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db), osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    return await svc.create_snapshot(db, osb, tenant=ctx.tenant, user=user, sandbox_id=sandbox_id,
                                     name=body.name, ip=_client_ip(request), user_agent=request.headers.get("user-agent"))
