# Builder: uv installs the locked deps into /app/.venv. Alpine on both stages
# so the venv is built against the same libc (musl) it runs on.
FROM ghcr.io/astral-sh/uv:python3.14-alpine AS builder

# git fetches lmc-openbdf, a git dependency until it is on PyPI; builder only.
RUN apk add --no-cache git

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Manifests first: the dependency layer is reused until uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic/ alembic/
COPY app/ app/

# Runtime: plain python, no uv, unprivileged numeric user so k8s
# runAsNonRoot can verify it.
FROM python:3.14-alpine

# The alpine base lags its package repo; take every fixed package now
# rather than chase CVEs one by one (same as co2-calculator).
# pip is unused at runtime (the venv comes from the builder) and its vendored
# urllib3/msgpack/setuptools trip the HIGH vulnerability gate, so drop it.
RUN apk upgrade --no-cache && pip uninstall --yes --no-cache-dir pip

WORKDIR /app
COPY --from=builder /app /app

USER 1001
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
