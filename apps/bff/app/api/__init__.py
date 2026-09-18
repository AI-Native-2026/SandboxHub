from fastapi import APIRouter

from app.api import admin as admin_api
from app.api import api_keys as api_keys_api
from app.api import exec as exec_api
from app.api import governance as governance_api
from app.api import intelligence as intelligence_api
from app.api import me, overview, sandboxes, snapshots, templates, tenants
from app.api import platform as platform_api
from app.api import security as security_api

api_router = APIRouter()
api_router.include_router(me.router, prefix="/v1", tags=["identity"])
api_router.include_router(tenants.router, prefix="/v1", tags=["identity"])
api_router.include_router(overview.router, prefix="/v1", tags=["overview"])
api_router.include_router(sandboxes.router, prefix="/v1", tags=["sandboxes"])
api_router.include_router(exec_api.router, prefix="/v1", tags=["exec"])
api_router.include_router(templates.router, prefix="/v1", tags=["templates"])
api_router.include_router(snapshots.router, prefix="/v1", tags=["snapshots"])
api_router.include_router(api_keys_api.router, prefix="/v1", tags=["api-keys"])
api_router.include_router(admin_api.router, prefix="/v1", tags=["admin"])
api_router.include_router(governance_api.router, prefix="/v1", tags=["governance"])
api_router.include_router(security_api.router, prefix="/v1", tags=["security"])
api_router.include_router(platform_api.router, prefix="/v1", tags=["platform"])
api_router.include_router(intelligence_api.router, prefix="/v1", tags=["intelligence"])
