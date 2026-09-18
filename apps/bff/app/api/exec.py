from __future__ import annotations

import asyncio
import base64
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
import websockets
from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, get_db
from app.core.deps import TenantContext, get_tenant_context, require_writer
from app.core.errors import Forbidden, Unauthenticated
from app.core.security import decode_token
from app.models import Membership, Tenant, User
from app.services import sandbox_service as svc
from app.services.execd import normalize_endpoint
from app.services.upstream import OpenSandboxClient, osb_client

router = APIRouter()


async def _execd_base(osb: OpenSandboxClient, sandbox_id: str, port: int = 44772) -> str:
    ep = await osb.get_endpoint(sandbox_id, port)
    endpoint = ep.get("endpoint") if isinstance(ep, dict) else ep
    return normalize_endpoint(endpoint)


# ------------------------------------------------------------------ commands (SSE)

@router.post("/sandboxes/{sandbox_id}/commands")
async def run_command(
    sandbox_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> StreamingResponse:
    body = await request.json()
    base = await _execd_base(osb, sandbox_id)
    client = httpx.AsyncClient(timeout=None)
    req = client.build_request("POST", f"{base}/command", json=body)
    resp = await client.send(req, stream=True)

    async def gen():
        try:
            async for chunk in resp.aiter_raw():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(gen(), media_type=resp.headers.get("content-type", "text/event-stream"))


@router.post("/sandboxes/{sandbox_id}/code")
async def run_code(
    sandbox_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> StreamingResponse:
    body = await request.json()
    base = await _execd_base(osb, sandbox_id)
    client = httpx.AsyncClient(timeout=None)
    req = client.build_request("POST", f"{base}/code", json=body)
    resp = await client.send(req, stream=True)

    async def gen():
        try:
            async for chunk in resp.aiter_raw():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(gen(), media_type=resp.headers.get("content-type", "text/event-stream"))


# ------------------------------------------------------------------ metrics

@router.get("/sandboxes/{sandbox_id}/metrics")
async def get_metrics(
    sandbox_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    base = await _execd_base(osb, sandbox_id)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{base}/metrics")
    return r.json()


@router.get("/sandboxes/{sandbox_id}/metrics/watch")
async def watch_metrics(
    sandbox_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    osb: OpenSandboxClient = Depends(osb_client),
) -> StreamingResponse:
    base = await _execd_base(osb, sandbox_id)
    client = httpx.AsyncClient(timeout=None)
    req = client.build_request("GET", f"{base}/metrics/watch")
    resp = await client.send(req, stream=True)

    async def gen():
        try:
            async for chunk in resp.aiter_raw():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(gen(), media_type="text/event-stream")


# ------------------------------------------------------------------ files

@router.get("/sandboxes/{sandbox_id}/files/list")
async def list_dir(
    sandbox_id: str, path: str = "/", depth: int = 1,
    ctx: TenantContext = Depends(get_tenant_context),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    base = await _execd_base(osb, sandbox_id)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{base}/directories/list", params={"path": path, "depth": depth})
    return {"entries": r.json()}


@router.get("/sandboxes/{sandbox_id}/files/info")
async def file_info(
    sandbox_id: str, paths: list[str] = Query(default=[]),
    ctx: TenantContext = Depends(get_tenant_context),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    base = await _execd_base(osb, sandbox_id)
    params = [("paths", p) for p in paths]
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{base}/files/info", params=params)
    return r.json()


@router.get("/sandboxes/{sandbox_id}/files/download")
async def download_file(
    sandbox_id: str, path: str,
    ctx: TenantContext = Depends(get_tenant_context),
    osb: OpenSandboxClient = Depends(osb_client),
) -> StreamingResponse:
    base = await _execd_base(osb, sandbox_id)
    client = httpx.AsyncClient(timeout=None)
    req = client.build_request("GET", f"{base}/files/download", params={"path": path})
    resp = await client.send(req, stream=True)

    async def gen():
        try:
            async for chunk in resp.aiter_raw():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    headers = {}
    if resp.headers.get("content-disposition"):
        headers["content-disposition"] = resp.headers["content-disposition"]
    return StreamingResponse(gen(), media_type=resp.headers.get("content-type", "application/octet-stream"), headers=headers)


@router.post("/sandboxes/{sandbox_id}/files/upload")
async def upload_file(
    sandbox_id: str,
    request: Request,
    path: str = Query(...),
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    base = await _execd_base(osb, sandbox_id)
    raw = await request.body()
    metadata = json.dumps({"path": path, "mode": 644})
    files = {
        "metadata": ("metadata.json", metadata, "application/json"),
        "file": ("file", raw, "application/octet-stream"),
    }
    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.post(f"{base}/files/upload", files=files)
    return {"status": r.status_code, "ok": r.status_code < 400}


@router.post("/sandboxes/{sandbox_id}/files/write")
async def write_file(
    sandbox_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    body = await request.json()  # {path, content}
    base = await _execd_base(osb, sandbox_id)
    path = body.get("path") or "/tmp/file.txt"
    content = body.get("content") or ""
    metadata = json.dumps({"path": path, "mode": int(body.get("mode", 644))})
    files = {
        "metadata": ("metadata.json", metadata, "application/json"),
        "file": (path.split("/")[-1], content.encode("utf-8"), "text/plain"),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{base}/files/upload", files=files)
    return {"ok": r.status_code < 400, "status": r.status_code}


@router.delete("/sandboxes/{sandbox_id}/files")
async def delete_files(
    sandbox_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    body = await request.json()  # {paths: []}
    base = await _execd_base(osb, sandbox_id)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.request("DELETE", f"{base}/files", json=body)
    return {"ok": r.status_code < 400, "status": r.status_code}


@router.post("/sandboxes/{sandbox_id}/directories")
async def create_dirs(
    sandbox_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    body = await request.json()
    base = await _execd_base(osb, sandbox_id)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{base}/directories", json=body)
    return {"ok": r.status_code < 400, "status": r.status_code}


@router.post("/sandboxes/{sandbox_id}/files/mv")
async def move_files(
    sandbox_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    body = await request.json()
    base = await _execd_base(osb, sandbox_id)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{base}/files/mv", json=body)
    return {"ok": r.status_code < 400, "status": r.status_code}


@router.get("/sandboxes/{sandbox_id}/files/search")
async def search_files(
    sandbox_id: str, path: str = "/", pattern: str = "*",
    ctx: TenantContext = Depends(get_tenant_context),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    base = await _execd_base(osb, sandbox_id)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{base}/files/search", params={"path": path, "pattern": pattern})
    return {"entries": r.json()}


# ------------------------------------------------------------------ pty

@router.post("/sandboxes/{sandbox_id}/pty")
async def create_pty(
    sandbox_id: str,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    base = await _execd_base(osb, sandbox_id)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{base}/pty", json=body or {"cwd": "/tmp"})
    return r.json()


@router.delete("/sandboxes/{sandbox_id}/pty/{session_id}")
async def delete_pty(
    sandbox_id: str, session_id: str,
    ctx: TenantContext = Depends(require_writer),
    osb: OpenSandboxClient = Depends(osb_client),
) -> dict:
    base = await _execd_base(osb, sandbox_id)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.delete(f"{base}/pty/{session_id}")
    return {"ok": r.status_code < 400}


# ------------------------------------------------------------------ terminal (WS proxy)

async def _ws_principal(token: str | None):
    if not token:
        raise Unauthenticated("缺少令牌")
    return decode_token(token)


@router.websocket("/sandboxes/{sandbox_id}/terminal")
async def terminal(
    ws: WebSocket,
    sandbox_id: str,
    session_id: str = Query(...),
    mode: str = Query("holder"),
    since: int = Query(0),
    token: str | None = Query(None),
    tenant: str | None = Query(None),
    record: int = Query(0),
    name: str | None = Query(None),
):
    try:
        principal = await _ws_principal(token)
    except Exception:  # noqa: BLE001
        await ws.close(code=4401)
        return

    # authorize tenant access
    tenant_id = None
    user_id = None
    async with SessionLocal() as db:
        t = None
        if tenant:
            try:
                from uuid import UUID as _UUID

                t = (await db.execute(select(Tenant).where(Tenant.id == _UUID(tenant)))).scalar_one_or_none()
            except (ValueError, TypeError):
                t = None
            if t is None:
                t = (await db.execute(select(Tenant).where(Tenant.slug == tenant))).scalar_one_or_none()
        if t is None:
            await ws.close(code=4403)
            return
        user = (await db.execute(select(User).where(User.keycloak_sub == principal.sub))).scalar_one_or_none()
        is_admin = "platform-admin" in principal.roles
        member = None
        if user:
            member = (await db.execute(select(Membership).where(Membership.user_id == user.id, Membership.tenant_id == t.id))).scalar_one_or_none()
        if member is None and not is_admin:
            await ws.close(code=4403)
            return
        tenant_id = t.id
        user_id = user.id if user else None
        osb = OpenSandboxClient()
        try:
            base = await _execd_base(osb, sandbox_id)
        except Exception:  # noqa: BLE001
            await ws.close(code=4404)
            return

    await ws.accept()
    qs = urlencode({"since": since, **({"mode": "viewer"} if mode == "viewer" else {})})
    upstream_url = base.replace("http://", "ws://").replace("https://", "wss://") + f"/pty/{session_id}/ws?{qs}"

    rec_chunks: list[dict] = []
    rec_state = {"on": bool(record)}
    t0 = time.time()

    upstream = None
    try:
        upstream = await websockets.connect(upstream_url, max_size=None, close_timeout=1)

        async def client_to_upstream():
            try:
                while True:
                    msg = await ws.receive()
                    if msg.get("type") == "websocket.disconnect":
                        break
                    if msg.get("bytes") is not None:
                        await upstream.send(msg["bytes"])
                    elif msg.get("text") is not None:
                        text = msg["text"]
                        try:
                            ctrl = json.loads(text)
                        except Exception:  # noqa: BLE001
                            ctrl = None
                        if isinstance(ctrl, dict) and ctrl.get("type") == "record":
                            rec_state["on"] = bool(ctrl.get("on"))
                            continue
                        await upstream.send(text)
            except Exception:  # noqa: BLE001
                pass

        async def upstream_to_client():
            try:
                async for data in upstream:
                    if isinstance(data, bytes):
                        if rec_state["on"] and data and data[0] in (0x01, 0x03):
                            rec_chunks.append(
                                {"t": int((time.time() - t0) * 1000), "b": base64.b64encode(data[1:]).decode()}
                            )
                        await ws.send_bytes(data)
                    else:
                        await ws.send_text(data)
            except Exception:  # noqa: BLE001
                pass

        tasks = [asyncio.create_task(client_to_upstream()), asyncio.create_task(upstream_to_client())]
        _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    except Exception:  # noqa: BLE001
        pass
    finally:
        # persist as soon as one side ends (client closed / upstream gone) instead
        # of waiting for a graceful websocket close handshake (which can take ~10s).
        if upstream is not None:
            try:
                await upstream.close()
            except Exception:  # noqa: BLE001
                pass
        if rec_chunks and tenant_id is not None:
            try:
                from app.models import Recording

                total = sum(len(c["b"]) for c in rec_chunks)
                async with SessionLocal() as db:
                    db.add(
                        Recording(
                            tenant_id=tenant_id,
                            sandbox_id=sandbox_id,
                            user_id=user_id,
                            name=name or f"session-{int(t0)}",
                            size_bytes=total,
                            chunks=rec_chunks,
                            ended_at=datetime.now(timezone.utc),
                        )
                    )
                    await db.commit()
            except Exception:  # noqa: BLE001
                pass
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
