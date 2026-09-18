"""U5 intelligence routes: tasks (batch), artifacts, agent launcher."""
from __future__ import annotations

import asyncio
import base64
from datetime import timedelta
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, get_db
from app.core.deps import TenantContext, get_current_user, get_tenant_context, require_writer
from app.core.errors import NotFound
from app.models import Artifact, SandboxRecord, Task, TaskItem, Tenant, User
from app.services.execd import normalize_endpoint
from app.services.upstream import OpenSandboxClient

router = APIRouter()

AGENTS = [
    {"id": "claude-code", "name": "Claude Code", "image": "opensandbox/code-interpreter:v1.1.0",
     "install": "npm install -g @anthropic-ai/claude-code", "run": "claude -p 'hello'",
     "docs": "https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/examples/claude-code.md"},
    {"id": "opencode", "name": "OpenCode", "image": "opensandbox/code-interpreter:v1.1.0",
     "install": "npm install -g opencode-ai@latest", "run": "opencode run 'Compute 1+1'",
     "docs": "https://open-sandbox.ai/examples/opencode"},
    {"id": "codex-cli", "name": "OpenAI Codex CLI", "image": "opensandbox/code-interpreter:v1.1.0",
     "install": "npm install -g @openai/codex", "run": "codex exec 'echo hi'",
     "docs": "https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/examples/codex-cli.md"},
]


@router.get("/agents")
async def list_agents() -> list[dict]:
    return AGENTS


class LaunchBody(BaseModel):
    cpu: str = "2"
    memory: str = "2Gi"
    timeout_seconds: int = 3600
    name: str | None = None


async def _install_agent(sandbox_id: str, install_cmd: str) -> None:
    osb = OpenSandboxClient()
    try:
        ep = await osb.get_endpoint(sandbox_id, 44772)
        base = normalize_endpoint(ep.get("endpoint") if isinstance(ep, dict) else ep)
        async with httpx.AsyncClient(timeout=900) as client:
            await client.post(f"{base}/command", json={"command": install_cmd})
    except Exception:  # noqa: BLE001
        pass


@router.post("/agents/{agent_id}/launch", status_code=201)
async def launch_agent(
    agent_id: str,
    body: LaunchBody,
    ctx: TenantContext = Depends(require_writer),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if agent is None:
        raise NotFound("Agent 不存在")
    osb = OpenSandboxClient()
    resp = await osb.create_sandbox({
        "image": {"uri": agent["image"]},
        "entrypoint": ["sleep", "infinity"],
        "timeout": body.timeout_seconds,
        "resourceLimits": {"cpu": body.cpu, "memory": body.memory},
        "metadata": {"tenant": ctx.tenant.slug, "owner": str(user.id), "agent": agent_id},
    })
    sid = resp.get("id")
    db.add(SandboxRecord(
        tenant_id=ctx.tenant.id, owner_user_id=user.id, osb_sandbox_id=sid,
        name=body.name or f"agent-{agent_id}", image=agent["image"],
        status="Running", cpu=body.cpu, memory=body.memory,
    ))
    await db.commit()
    # install the agent inside the sandbox (image does not include it)
    asyncio.create_task(_install_agent(sid, agent["install"]))
    return {
        "sandbox_id": sid,
        "agent": agent["name"],
        "install_command": agent["install"],
        "run_command": agent["run"],
        "note": "正在后台安装 Agent，稍候可在终端执行运行命令（安装约需 30-90 秒）",
    }


# ---------------------------------------------------------------- tasks

class TaskBody(BaseModel):
    name: str
    image: str = "python:3.12"
    command: str = "echo hello"
    replicas: int = 1


def _task(t: Task) -> dict:
    return {
        "id": str(t.id), "name": t.name, "image": t.image, "command": t.command,
        "replicas": t.replicas, "status": t.status, "succeeded": t.succeeded, "failed": t.failed,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("/tasks")
async def list_tasks(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(select(Task).where(Task.tenant_id == ctx.tenant.id).order_by(Task.created_at.desc()))
    ).scalars().all()
    return [_task(t) for t in rows]


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = (
        await db.execute(select(Task).where(Task.id == UUID(task_id), Task.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if t is None:
        raise NotFound("任务不存在")
    items = (await db.execute(select(TaskItem).where(TaskItem.task_id == t.id))).scalars().all()
    return {
        **_task(t),
        "items": [
            {"id": str(i.id), "sandbox_id": i.sandbox_id, "status": i.status,
             "exit_code": i.exit_code, "output": (i.output or "")[:2000]}
            for i in items
        ],
    }


async def _run_task(task_id: str, tenant_id: str, user_id: str, image: str, command: str, replicas: int) -> None:
    osb = OpenSandboxClient()
    ok = 0
    fail = 0
    async with SessionLocal() as db:
        task = (await db.execute(select(Task).where(Task.id == UUID(task_id)))).scalar_one()
        task.status = "running"
        await db.commit()

    for _ in range(replicas):
        sid = None
        try:
            payload = {
                "image": {"uri": image},
                "entrypoint": ["sleep", "infinity"],
                "timeout": 1800,
                "resourceLimits": {"cpu": "1", "memory": "1Gi"},
                "metadata": {"tenant": tenant_id, "task": task_id},
            }
            resp = await osb.create_sandbox(payload)
            sid = resp.get("id")
            async with SessionLocal() as db:
                db.add(SandboxRecord(
                    tenant_id=UUID(tenant_id), owner_user_id=UUID(user_id) if user_id else None,
                    osb_sandbox_id=sid, name=f"task-{task_id[:8]}", image=image,
                    status="Running", cpu="1", memory="1Gi",
                ))
                await db.commit()
            ep = await osb.get_endpoint(sid, 44772)
            base = normalize_endpoint(ep.get("endpoint") if isinstance(ep, dict) else ep)
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(f"{base}/command", json={"command": command})
                out = r.text[:4000]
            exit_code = 0 if r.status_code < 400 else r.status_code
            async with SessionLocal() as db:
                db.add(TaskItem(task_id=UUID(task_id), sandbox_id=sid,
                                status="succeeded" if exit_code == 0 else "failed",
                                exit_code=exit_code, output=out))
                await db.commit()
            ok += 1 if exit_code == 0 else 0
            fail += 0 if exit_code == 0 else 1
        except Exception as exc:  # noqa: BLE001
            async with SessionLocal() as db:
                db.add(TaskItem(task_id=UUID(task_id), sandbox_id=sid, status="failed",
                                output=f"{type(exc).__name__}: {exc}"[:1000]))
                await db.commit()
            fail += 1

    async with SessionLocal() as db:
        task = (await db.execute(select(Task).where(Task.id == UUID(task_id)))).scalar_one()
        task.status = "completed"
        task.succeeded = ok
        task.failed = fail
        await db.commit()


@router.post("/tasks", status_code=201)
async def create_task(
    body: TaskBody,
    ctx: TenantContext = Depends(require_writer),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = Task(
        tenant_id=ctx.tenant.id, owner_user_id=user.id, name=body.name,
        image=body.image, command=body.command, replicas=max(1, min(body.replicas, 20)),
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    asyncio.create_task(
        _run_task(str(t.id), str(ctx.tenant.id), str(user.id), body.image, body.command, t.replicas)
    )
    return _task(t)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    t = (
        await db.execute(select(Task).where(Task.id == UUID(task_id), Task.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if t:
        await db.delete(t)
        await db.commit()


# ---------------------------------------------------------------- artifacts

class CollectBody(BaseModel):
    sandbox_id: str
    path: str
    name: str | None = None


def _artifact(a: Artifact) -> dict:
    return {
        "id": str(a.id), "sandbox_id": a.sandbox_id, "name": a.name, "path": a.path,
        "size": a.size, "content_type": a.content_type,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/artifacts")
async def list_artifacts(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.execute(select(Artifact).where(Artifact.tenant_id == ctx.tenant.id).order_by(Artifact.created_at.desc()))
    ).scalars().all()
    return [_artifact(a) for a in rows]


@router.post("/artifacts/collect", status_code=201)
async def collect_artifact(
    body: CollectBody,
    ctx: TenantContext = Depends(require_writer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    osb = OpenSandboxClient()
    rec = (
        await db.execute(
            select(SandboxRecord).where(
                SandboxRecord.tenant_id == ctx.tenant.id, SandboxRecord.osb_sandbox_id == body.sandbox_id
            )
        )
    ).scalar_one_or_none()
    if rec is None:
        raise NotFound("沙箱不存在或不属于该租户")
    ep = await osb.get_endpoint(body.sandbox_id, 44772)
    base = normalize_endpoint(ep.get("endpoint") if isinstance(ep, dict) else ep)
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{base}/files/download", params={"path": body.path})
    if r.status_code >= 400:
        from app.core.errors import UpstreamError

        raise UpstreamError(f"读取产物失败: {r.status_code}")
    a = Artifact(
        tenant_id=ctx.tenant.id, sandbox_id=body.sandbox_id,
        name=body.name or body.path.split("/")[-1], path=body.path,
        size=len(r.content), content_type=r.headers.get("content-type", "application/octet-stream"),
        content=r.content,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return _artifact(a)


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    a = (
        await db.execute(select(Artifact).where(Artifact.id == UUID(artifact_id), Artifact.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if a is None:
        raise NotFound("产物不存在")
    return Response(
        content=a.content or b"",
        media_type=a.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{a.name}"'},
    )


@router.delete("/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(
    artifact_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    a = (
        await db.execute(select(Artifact).where(Artifact.id == UUID(artifact_id), Artifact.tenant_id == ctx.tenant.id))
    ).scalar_one_or_none()
    if a:
        await db.delete(a)
        await db.commit()
