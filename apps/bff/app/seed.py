"""Idempotent seed data: default tenant and template catalog."""
from __future__ import annotations

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Template, Tenant

DEFAULT_TENANT = {"slug": "demo", "name": "演示租户", "quota_cpu": "16", "quota_memory": "32Gi", "quota_sandboxes": 20}

DEFAULT_TEMPLATES = [
    {
        "name": "Python 3.12",
        "description": "通用 Python 环境，适合脚本与数据处理",
        "image": "python:3.12",
        "entrypoint": ["sleep", "infinity"],
        "env": {},
        "default_cpu": "1",
        "default_memory": "1Gi",
        "default_timeout_seconds": 1800,
        "icon": "python",
        "tags": ["python", "general"],
        "visibility": "public",
    },
    {
        "name": "Code Interpreter",
        "description": "多语言代码解释器（Python/Java/Node/Go + Jupyter）",
        "image": "opensandbox/code-interpreter:v1.1.0",
        "entrypoint": ["/opt/code-interpreter/code-interpreter.sh"],
        "env": {"PYTHON_VERSION": "3.11"},
        "default_cpu": "2",
        "default_memory": "2Gi",
        "default_timeout_seconds": 1800,
        "icon": "code",
        "tags": ["python", "java", "node", "go"],
        "visibility": "public",
    },
    {
        "name": "Playwright",
        "description": "无头浏览器自动化（Chromium + Playwright）",
        "image": "sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/playwright:latest",
        "entrypoint": None,
        "env": {},
        "default_cpu": "1",
        "default_memory": "2Gi",
        "default_timeout_seconds": 1800,
        "icon": "browser",
        "tags": ["browser", "playwright"],
        "visibility": "public",
    },
]


async def seed() -> None:
    async with SessionLocal() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == DEFAULT_TENANT["slug"]))).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(**DEFAULT_TENANT)
            db.add(tenant)
            await db.flush()

        for tpl in DEFAULT_TEMPLATES:
            existing = (await db.execute(select(Template).where(Template.name == tpl["name"]))).scalar_one_or_none()
            if existing is None:
                db.add(Template(**tpl))
        await db.commit()
