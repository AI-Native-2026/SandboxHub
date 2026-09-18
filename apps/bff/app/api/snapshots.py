from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import TenantContext, get_current_user, get_tenant_context, require_writer
from app.models import User
from app.services import sandbox_service as svc
from app.services.upstream import OpenSandboxClient, osb_client

router = APIRouter()


@router.get("/snapshots")
async def list_snapshots(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    try:
        data = await osb.list_snapshots({"page": 1, "pageSize": 200})
    except Exception:  # noqa: BLE001
        data = {"items": []}
    return data


@router.delete("/snapshots/{snapshot_id}", status_code=204)
async def delete_snapshot(
    snapshot_id: str,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> None:
    await osb.delete_snapshot(snapshot_id)
