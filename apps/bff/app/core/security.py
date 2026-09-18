"""JWT validation against Keycloak JWKS."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx
import jwt
from jwt import PyJWKClient

from app.core.config import get_settings

_jwks_client: PyJWKClient | None = None
_jwks_client_ts: float = 0.0
_CACHE_TTL = 300.0


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client, _jwks_client_ts
    now = time.time()
    if _jwks_client is None or (now - _jwks_client_ts) > _CACHE_TTL:
        settings = get_settings()
        _jwks_client = PyJWKClient(settings.bff_jwks_url, cache_keys=True)
        _jwks_client_ts = now
    return _jwks_client


@dataclass
class Principal:
    sub: str
    email: str | None = None
    username: str | None = None
    name: str | None = None
    roles: list[str] = field(default_factory=list)
    claims: dict = field(default_factory=dict)


def decode_token(token: str) -> Principal:
    settings = get_settings()
    signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=None,
        issuer=settings.bff_token_issuer,
        options={"verify_aud": False},
    )
    realm_roles = claims.get("realm_access", {}).get("roles", [])
    return Principal(
        sub=claims.get("sub", ""),
        email=claims.get("email"),
        username=claims.get("preferred_username"),
        name=claims.get("name"),
        roles=realm_roles,
        claims=claims,
    )
