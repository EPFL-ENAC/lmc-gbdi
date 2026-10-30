from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings import service as buildings_service
from app.buildings.routes import router as buildings_router
from app.config import get_settings
from app.db import engine, get_session
from app.overview.routes import router as overview_router
from app.overview.service import project_overview


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Read the OpenBDF export at boot: a broken export fails the deploy, not a request.
    data_dir = get_settings().OPENBDF_DATA_DIR
    if data_dir is not None:
        project_overview(data_dir)
    # Compute every stored building once, so the list answers from memory.
    async with AsyncSession(engine) as session:
        await buildings_service.summaries(session)
    yield


# Everything lives under /api, so Traefik (compose) and the k8s Ingress route
# by plain path prefix: no prefix stripping, no controller-specific rewrites.
app = FastAPI(
    title="GBDI API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
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
app.include_router(overview_router)
app.include_router(buildings_router)
