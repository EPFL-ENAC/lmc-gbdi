from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_session

# Everything lives under /api, so Traefik (compose) and the k8s Ingress route
# by plain path prefix: no prefix stripping, no controller-specific rewrites.
app = FastAPI(
    title="GBDI API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the process is up. Never touches the database."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Readiness: the database answers."""
    await session.exec(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(router)
