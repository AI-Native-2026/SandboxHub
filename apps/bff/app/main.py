"""SandboxHub BFF application entrypoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.db import init_db
from app.core.errors import AppError, app_error_handler
from app.seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("sandboxhub.bff")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("starting SandboxHub BFF")
    await init_db()
    if settings.bff_seed_on_start:
        try:
            await seed()
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed failed: %s", exc)
    from app.services.usage_sampler import run_sampler

    sampler = asyncio.create_task(run_sampler())
    from app.services.cleanup import run_cleanup

    cleaner = asyncio.create_task(run_cleanup())
    yield
    sampler.cancel()
    cleaner.cancel()
    logger.info("stopping SandboxHub BFF")


app = FastAPI(title="SandboxHub BFF", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)
app.include_router(health_router, tags=["health"])
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root() -> dict:
    return {"service": "sandboxhub-bff", "docs": "/docs", "health": "/healthz"}
