"""Sandbox orchestration service: maps platform tenancy onto OpenSandbox."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.errors import Forbidden, NotFound, QuotaExceeded, ValidationError
from app.models import PolicyTemplate, SandboxRecord, Tenant, Template, User
from app.services.upstream import OpenSandboxClient

ACTIVE_STATES = {"Pending", "Running", "Pausing", "Paused", "Resuming", "Stopping"}


def _normalize_state(raw: str | None) -> str:
    if not raw:
        return "Unknown"
    return raw


def _record_dict(rec: SandboxRecord, live_status: dict | None = None) -> dict:
    state = live_status.get("state") if live_status else rec.status
    return {
        "id": str(rec.id),
        "sandbox_id": rec.osb_sandbox_id,
        "name": rec.name,
        "image": rec.image,
        "template_id": str(rec.template_id) if rec.template_id else None,
        "state": _normalize_state(state),
        "reason": (live_status or {}).get("reason"),
        "cpu": rec.cpu,
        "memory": rec.memory,
        "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "owner_user_id": str(rec.owner_user_id) if rec.owner_user_id else None,
        "metadata": rec.meta or {},
    }


async def _quota_check(db: AsyncSession, tenant: Tenant) -> None:
    if not tenant.quota_sandboxes:
        return
    count = (
        await db.execute(
            select(func.count())
            .select_from(SandboxRecord)
            .where(SandboxRecord.tenant_id == tenant.id, SandboxRecord.status.in_(ACTIVE_STATES))
        )
    ).scalar_one()
    if count >= tenant.quota_sandboxes:
        raise QuotaExceeded(f"租户沙箱数已达上限（{tenant.quota_sandboxes}）")


async def create_sandbox(
    db: AsyncSession,
    osb: OpenSandboxClient,
    *,
    tenant: Tenant,
    user: User,
    body: dict,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    template: Template | None = None
    if body.get("template_id"):
        template = (await db.execute(select(Template).where(Template.id == UUID(body["template_id"])))).scalar_one_or_none()
        if template is None:
            raise NotFound("模板不存在")

    image = body.get("image") or (template.image if template else None)
    if not image:
        raise ValidationError("必须提供 image 或 template_id")

    entrypoint = body.get("entrypoint") or (template.entrypoint if template else None) or ["sleep", "infinity"]
    env: dict[str, str] = {}
    if template and template.env:
        env.update(template.env)
    if body.get("env"):
        env.update(body["env"])
    cpu = body.get("cpu") or (template.default_cpu if template else None) or "1"
    memory = body.get("memory") or (template.default_memory if template else None) or "1Gi"
    timeout_seconds = body.get("timeout_seconds") or (template.default_timeout_seconds if template else None) or 1800
    policy_template: PolicyTemplate | None = None
    if body.get("policy_template_id"):
        policy_template = (
            await db.execute(select(PolicyTemplate).where(PolicyTemplate.id == UUID(body["policy_template_id"])))
        ).scalar_one_or_none()
        if policy_template is None:
            raise NotFound("网络策略模板不存在")

    network_policy = body.get("network_policy") or (template.network_policy if template else None)
    if network_policy is None and policy_template is not None:
        network_policy = {"defaultAction": policy_template.default_action, "egress": policy_template.rules or []}

    await _quota_check(db, tenant)

    payload: dict = {
        "image": {"uri": image},
        "entrypoint": entrypoint,
        "timeout": timeout_seconds,
        "resourceLimits": {"cpu": str(cpu), "memory": str(memory)},
        "metadata": {
            "name": body.get("name") or "sandbox",
            "tenant": tenant.slug,
            "owner": str(user.id),
        },
    }
    if env:
        payload["env"] = env
    if network_policy:
        payload["networkPolicy"] = network_policy

    resp = await osb.create_sandbox(payload)
    osb_id = resp.get("id")
    if not osb_id:
        raise ValidationError("上游未返回 sandbox id")

    expires_at = None
    if resp.get("expiresAt"):
        try:
            expires_at = datetime.fromisoformat(resp["expiresAt"].replace("Z", "+00:00"))
        except ValueError:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)

    rec = SandboxRecord(
        tenant_id=tenant.id,
        owner_user_id=user.id,
        osb_sandbox_id=osb_id,
        name=payload["metadata"]["name"],
        image=image,
        template_id=template.id if template else None,
        status=resp.get("status", {}).get("state", "Pending"),
        cpu=str(cpu),
        memory=str(memory),
        expires_at=expires_at,
        meta={"tenant_slug": tenant.slug},
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    await record_audit(
        db, action="sandbox.create", actor_user_id=user.id, tenant_id=tenant.id,
        resource_type="sandbox", resource_id=osb_id, ip=ip, user_agent=user_agent,
        detail={"image": image, "cpu": cpu, "memory": memory, "template": template.name if template else None},
    )
    return _record_dict(rec, resp.get("status"))


async def list_sandboxes(db: AsyncSession, osb: OpenSandboxClient, *, tenant: Tenant, states: list[str] | None, q: str | None, page: int, size: int) -> dict:
    stmt = select(SandboxRecord).where(SandboxRecord.tenant_id == tenant.id)
    if q:
        stmt = stmt.where(SandboxRecord.name.ilike(f"%{q}%"))
    records = (await db.execute(stmt.order_by(SandboxRecord.created_at.desc()))).scalars().all()

    live: dict[str, dict] = {}
    upstream_ok = False
    try:
        items = await osb.list_all_sandboxes()
        for it in items:
            live[it.get("id")] = it.get("status") or {}
        upstream_ok = True
    except Exception:  # noqa: BLE001
        pass

    merged = []
    for r in records:
        status = live.get(r.osb_sandbox_id)
        # upstream no longer has this sandbox -> mark it terminated (stale record)
        if status is None and upstream_ok and r.status in ACTIVE_STATES:
            r.status = "Terminated"
            status = {"state": "Terminated", "reason": "UPSTREAM_GONE"}
        d = _record_dict(r, status)
        if d["state"] and d["state"] != r.status:
            r.status = d["state"]
        merged.append(d)
    if upstream_ok:
        await db.commit()
    if states:
        wanted = {s.lower() for s in states}
        merged = [m for m in merged if str(m["state"]).lower() in wanted]
    total = len(merged)
    start = max(0, (page - 1) * size)
    return {"items": merged[start : start + size], "total": total, "page": page, "size": size}


async def get_record(db: AsyncSession, tenant: Tenant, sandbox_id: str) -> SandboxRecord:
    rec = (
        await db.execute(
            select(SandboxRecord).where(
                SandboxRecord.tenant_id == tenant.id, SandboxRecord.osb_sandbox_id == sandbox_id
            )
        )
    ).scalar_one_or_none()
    if rec is None:
        raise NotFound("沙箱不存在或不属于该租户")
    return rec


async def get_sandbox(db: AsyncSession, osb: OpenSandboxClient, *, tenant: Tenant, sandbox_id: str) -> dict:
    rec = await get_record(db, tenant, sandbox_id)
    try:
        upstream = await osb.get_sandbox(sandbox_id)
    except Exception as exc:  # noqa: BLE001
        upstream = None
        if "404" in str(exc) and rec.status in ACTIVE_STATES:
            rec.status = "Terminated"
            await db.commit()
    data = _record_dict(rec, (upstream or {}).get("status"))
    if upstream:
        data["upstream"] = upstream
    data["lost"] = upstream is None
    return data


async def delete_sandbox(db, osb, *, tenant, user, sandbox_id, ip=None, user_agent=None) -> None:
    rec = await get_record(db, tenant, sandbox_id)
    try:
        await osb.delete_sandbox(sandbox_id)
    except Exception as exc:  # noqa: BLE001
        # upstream 404 (already gone) is treated as success (idempotent delete)
        if "404" not in str(exc):
            raise
    rec.status = "Terminated"
    await db.commit()
    await record_audit(db, action="sandbox.delete", actor_user_id=user.id, tenant_id=tenant.id,
                       resource_type="sandbox", resource_id=sandbox_id, ip=ip, user_agent=user_agent)


async def _lifecycle(db, osb, *, tenant, user, sandbox_id, action, ip=None, user_agent=None) -> dict:
    rec = await get_record(db, tenant, sandbox_id)
    if action == "pause":
        await osb.pause(sandbox_id)
    elif action == "resume":
        await osb.resume(sandbox_id)
    try:
        upstream = await osb.get_sandbox(sandbox_id)
        rec.status = upstream.get("status", {}).get("state", rec.status)
    except Exception:  # noqa: BLE001
        pass
    await db.commit()
    await record_audit(db, action=f"sandbox.{action}", actor_user_id=user.id, tenant_id=tenant.id,
                       resource_type="sandbox", resource_id=sandbox_id, ip=ip, user_agent=user_agent)
    return _record_dict(rec)


async def pause_sandbox(db, osb, **kw) -> dict:
    return await _lifecycle(db, osb, action="pause", **kw)


async def resume_sandbox(db, osb, **kw) -> dict:
    return await _lifecycle(db, osb, action="resume", **kw)


async def renew_sandbox(db, osb, *, tenant, user, sandbox_id, timeout_seconds, ip=None, user_agent=None) -> dict:
    rec = await get_record(db, tenant, sandbox_id)
    await osb.renew(sandbox_id, timeout_seconds)
    rec.expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)
    await db.commit()
    await record_audit(db, action="sandbox.renew", actor_user_id=user.id, tenant_id=tenant.id,
                       resource_type="sandbox", resource_id=sandbox_id, ip=ip, user_agent=user_agent,
                       detail={"timeout_seconds": timeout_seconds})
    return _record_dict(rec)


async def patch_metadata(db, osb, *, tenant, user, sandbox_id, metadata, ip=None, user_agent=None) -> dict:
    rec = await get_record(db, tenant, sandbox_id)
    await osb.patch_metadata(sandbox_id, metadata)
    rec.meta = {**(rec.meta or {}), **metadata}
    await db.commit()
    await record_audit(db, action="sandbox.patch_metadata", actor_user_id=user.id, tenant_id=tenant.id,
                       resource_type="sandbox", resource_id=sandbox_id, ip=ip, user_agent=user_agent)
    return _record_dict(rec)


async def get_endpoint(db, osb, *, tenant, sandbox_id, port) -> dict:
    await get_record(db, tenant, sandbox_id)
    try:
        return await osb.get_endpoint(sandbox_id, port)
    except Exception as exc:  # noqa: BLE001
        if "404" in str(exc):
            return {"endpoint": None, "available": False}
        raise


async def get_network_policy(db, osb, *, tenant, sandbox_id):
    await get_record(db, tenant, sandbox_id)
    return await osb.get_network_policy(sandbox_id)


async def put_network_policy(db, osb, *, tenant, user, sandbox_id, policy, ip=None, user_agent=None):
    await get_record(db, tenant, sandbox_id)
    result = await osb.put_network_policy(sandbox_id, policy)
    await record_audit(db, action="sandbox.set_network_policy", actor_user_id=user.id, tenant_id=tenant.id,
                       resource_type="sandbox", resource_id=sandbox_id, ip=ip, user_agent=user_agent)
    return result


async def create_snapshot(db, osb, *, tenant, user, sandbox_id, name, ip=None, user_agent=None) -> dict:
    await get_record(db, tenant, sandbox_id)
    result = await osb.create_snapshot(sandbox_id, name)
    await record_audit(db, action="sandbox.create_snapshot", actor_user_id=user.id, tenant_id=tenant.id,
                       resource_type="sandbox", resource_id=sandbox_id, ip=ip, user_agent=user_agent,
                       detail={"name": name})
    return result
