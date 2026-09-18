"""execd endpoint normalization and HTTP/WS proxying helpers."""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.errors import UpstreamError


def normalize_endpoint(endpoint: str) -> str:
    """Convert an upstream endpoint (e.g. '172.19.0.16:58040/proxy/44772') into a
    base URL reachable from the BFF container (host replaced by osb_endpoint_host)."""
    s = get_settings()
    endpoint = endpoint.strip()
    if "://" in endpoint:
        endpoint = endpoint.split("://", 1)[1]
    if "/" in endpoint:
        hostport, _, path = endpoint.partition("/")
    else:
        hostport, path = endpoint, ""
    port = hostport.split(":")[-1] if ":" in hostport else "80"
    base = f"http://{s.osb_endpoint_host}:{port}"
    if path:
        base += "/" + path
    return base


async def execd_request(method: str, base: str, path: str, *, json=None, params=None, content=None, headers=None, timeout: float = 60.0):
    url = base.rstrip("/") + "/" + path.lstrip("/")
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.request(method, url, json=json, params=params, content=content, headers=headers)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"execd 请求失败: {exc}") from exc
    if resp.status_code >= 400:
        raise UpstreamError(f"execd 返回 {resp.status_code}: {resp.text[:300]}")
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        return resp.json()
    return resp.content
