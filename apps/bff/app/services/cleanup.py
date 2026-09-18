"""Background cleanup: reconcile sandbox status with upstream and purge terminated records.

- Every CLEANUP_INTERVAL seconds:
  1. Fetch the authoritative sandbox id set from OpenSandbox.
  2. Mark platform records that are active but missing upstream as `Terminated`.
  3. Purge (delete) all `Terminated` records so they no longer appear in listings.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import ApiKey, SandboxRecord
from app.services.upstream import OpenSandboxClient

logger = logging.getLogger("sandboxhub.cleanup")

CLEANUP_INTERVAL = 900  # 15 minutes
ACTIVE_STATES = {"Pending", "Running", "Pausing", "Paused", "Resuming", "Stopping"}


async def reconcile_and_purge() -> dict:
    osb = OpenSandboxClient()
    upstream_ids: set[str] = set()
    upstream_ok = False
    try:
        items = await osb.list_all_sandboxes()
        upstream_ids = {it.get("id") for it in items}
        upstream_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("cleanup: upstream list failed: %s", exc)

    marked = 0
    purged = 0
    async with SessionLocal() as db:
        records = (await db.execute(select(SandboxRecord))).scalars().all()
        if upstream_ok:
            for r in records:
                if r.osb_sandbox_id not in upstream_ids and r.status in ACTIVE_STATES:
                    r.status = "Terminated"
                    marked += 1
        for r in records:
            if r.status == "Terminated":
                await db.delete(r)
                purged += 1
        # expire API keys past their expiry
        now = datetime.now(timezone.utc)
        expired_keys = (
            await db.execute(
                select(ApiKey).where(
                    ApiKey.status == "active",
                    ApiKey.expires_at.isnot(None),
                    ApiKey.expires_at < now,
                )
            )
        ).scalars().all()
        for k in expired_keys:
            k.status = "expired"
        await db.commit()
    if marked or purged or expired_keys:
        logger.info("cleanup: marked=%d purged=%d expired_keys=%d", marked, purged, len(expired_keys))
    return {"marked": marked, "purged": purged, "expired_keys": len(expired_keys)}


async def run_cleanup() -> None:
    while True:
        try:
            await reconcile_and_purge()
        except Exception as exc:  # noqa: BLE001
            logger.warning("cleanup error: %s", exc)
        await asyncio.sleep(CLEANUP_INTERVAL)
