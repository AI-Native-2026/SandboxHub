"""Application configuration (env-driven)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # database / cache
    bff_database_url: str = "postgresql+asyncpg://sandboxhub:sandboxhub@localhost:5433/sandboxhub"
    bff_redis_url: str = "redis://localhost:6380/0"

    # auth
    bff_jwks_url: str = "http://localhost:8180/realms/sandboxhub/protocol/openid-connect/certs"
    bff_token_issuer: str = "http://43.135.120.107:8081/realms/sandboxhub"
    bff_cors_origins: str = "http://localhost:8081"
    bff_auth_disabled: bool = False

    # upstream OpenSandbox (BFF-internal only)
    osb_base_url: str = "http://localhost:8090"
    osb_api_key: str = ""
    osb_request_timeout: float = 60.0
    osb_endpoint_host: str = "host.docker.internal"

    # misc
    bff_seed_on_start: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.bff_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
