"""OpenSandbox upstream client (BFF-internal)."""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import UpstreamError


class OpenSandboxClient:
    """Thin async client over the OpenSandbox lifecycle API."""

    def __init__(self) -> None:
        s = get_settings()
        self.base = s.osb_base_url.rstrip("/")
        self.api_key = s.osb_api_key
        self.timeout = s.osb_request_timeout

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["OPEN-SANDBOX-API-KEY"] = self.api_key
        return h

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base}/v1{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.request(method, url, headers=self._headers(), **kwargs)
            except httpx.HTTPError as exc:
                raise UpstreamError(f"OpenSandbox 请求失败: {exc}") from exc
        if resp.status_code >= 400:
            detail = resp.text[:500]
            raise UpstreamError(f"OpenSandbox 返回 {resp.status_code}: {detail}")
        if resp.content:
            try:
                return resp.json()
            except Exception:  # noqa: BLE001
                return resp.text
        return None

    # ---- lifecycle ----
    async def create_sandbox(self, payload: dict) -> dict:
        return await self._request("POST", "/sandboxes", json=payload)

    async def list_sandboxes(self, params: dict | None = None) -> dict:
        return await self._request("GET", "/sandboxes", params=params or {})

    async def list_all_sandboxes(self, max_items: int = 2000) -> list[dict]:
        """Paginate the lifecycle list (pageSize is capped at 200 upstream)."""
        items: list[dict] = []
        page = 1
        while len(items) < max_items:
            resp = await self.list_sandboxes({"page": page, "pageSize": 200})
            batch = resp.get("items") if isinstance(resp, dict) else resp
            batch = batch or []
            items.extend(batch)
            pag = resp.get("pagination") if isinstance(resp, dict) else None
            if not pag or not pag.get("hasNextPage") or not batch:
                break
            page += 1
        return items

    async def get_sandbox(self, sandbox_id: str) -> dict:
        return await self._request("GET", f"/sandboxes/{sandbox_id}")

    async def delete_sandbox(self, sandbox_id: str) -> Any:
        return await self._request("DELETE", f"/sandboxes/{sandbox_id}")

    async def pause(self, sandbox_id: str) -> Any:
        return await self._request("POST", f"/sandboxes/{sandbox_id}/pause")

    async def resume(self, sandbox_id: str) -> Any:
        return await self._request("POST", f"/sandboxes/{sandbox_id}/resume")

    async def renew(self, sandbox_id: str, timeout_seconds: int) -> Any:
        return await self._request(
            "POST", f"/sandboxes/{sandbox_id}/renew-expiration", json={"timeout": timeout_seconds}
        )

    async def patch_metadata(self, sandbox_id: str, metadata: dict) -> Any:
        return await self._request("PATCH", f"/sandboxes/{sandbox_id}/metadata", json=metadata)

    async def get_endpoint(self, sandbox_id: str, port: int) -> dict:
        return await self._request("GET", f"/sandboxes/{sandbox_id}/endpoints/{port}")

    # ---- network policy ----
    async def get_network_policy(self, sandbox_id: str) -> Any:
        return await self._request("GET", f"/sandboxes/{sandbox_id}/networkpolicy")

    async def put_network_policy(self, sandbox_id: str, policy: dict) -> Any:
        return await self._request("PUT", f"/sandboxes/{sandbox_id}/networkpolicy", json=policy)

    # ---- snapshots ----
    async def create_snapshot(self, sandbox_id: str, name: str | None = None) -> dict:
        body = {"name": name} if name else {}
        return await self._request("POST", f"/sandboxes/{sandbox_id}/snapshots", json=body)

    async def list_snapshots(self, params: dict | None = None) -> dict:
        return await self._request("GET", "/snapshots", params=params or {})

    async def delete_snapshot(self, snapshot_id: str) -> Any:
        return await self._request("DELETE", f"/snapshots/{snapshot_id}")

    # ---- diagnostics ----
    async def diagnostics_logs(self, sandbox_id: str) -> Any:
        return await self._request("GET", f"/sandboxes/{sandbox_id}/diagnostics/logs")

    async def diagnostics_events(self, sandbox_id: str) -> Any:
        return await self._request("GET", f"/sandboxes/{sandbox_id}/diagnostics/events")


def osb_client() -> OpenSandboxClient:
    return OpenSandboxClient()
