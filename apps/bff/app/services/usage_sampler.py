"""Background usage sampler: records CPU/memory usage for active sandboxes."""
from __future__ import annotations

import asyncio
import logging

import httpx
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import SandboxRecord, UsageSnapshot
from app.services.execd import normalize_endpoint
from app.services.upstream import OpenSandboxClient

logger = logging.getLogger("sandboxhub.usage")
INTERVAL = 60  # seconds
ACTIVE = {"Running"}

# cost rates (configurable via settings in a later iteration)
RATE_CPU_PER_HOUR = 0.5   # currency per CPU-hour
RATE_MEM_PER_GB_HOUR = 0.1


async def sample_once() -> int:
    osb = OpenSandboxClient()
    count = 0
    async with SessionLocal() as db:
        records = (
            await db.execute(select(SandboxRecord).where(SandboxRecord.status.in_(ACTIVE)))
        ).scalars().all()
        for rec in records:
            try:
                ep = await osb.get_endpoint(rec.osb_sandbox_id, 44772)
                endpoint = ep.get("endpoint") if isinstance(ep, dict) else ep
                base = normalize_endpoint(endpoint)
                async with httpx.AsyncClient(timeout=8) as client:
                    r = await client.get(f"{base}/metrics")
                m = r.json()
                cpu_pct = float(m.get("cpu_used_pct") or 0)
                mem_mib = float(m.get("mem_used_mib") or 0)
                db.add(
                    UsageSnapshot(
                        tenant_id=rec.tenant_id,
                        sandbox_id=rec.osb_sandbox_id,
                        cpu_seconds=(cpu_pct / 100.0) * INTERVAL,
                        mem_gb_seconds=(mem_mib / 1024.0) * INTERVAL,
                    )
                )
                count += 1
            except Exception:  # noqa: BLE001
                continue
        await db.commit()
    return count


async def run_sampler() -> None:
    while True:
        try:
            n = await sample_once()
            if n:
                logger.info("usage sampled for %d sandboxes", n)
        except Exception as exc:  # noqa: BLE001
            logger.warning("usage sampler error: %s", exc)
        await asyncio.sleep(INTERVAL)


def cost(cpu_seconds: float, mem_gb_seconds: float) -> float:
    return (cpu_seconds / 3600.0) * RATE_CPU_PER_HOUR + (mem_gb_seconds / 3600.0) * RATE_MEM_PER_GB_HOUR
