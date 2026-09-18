FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install \
    "fastapi>=0.115" "uvicorn[standard]>=0.30" "sqlalchemy>=2.0.30" "asyncpg>=0.29" \
    "pydantic>=2.7" "pydantic-settings>=2.3" "PyJWT[crypto]>=2.8" "httpx>=0.27" \
    "python-multipart>=0.0.9" "redis>=5.0" "websockets>=12.0"

COPY app ./app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
