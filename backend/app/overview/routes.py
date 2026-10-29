from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.overview.schemas import Overview
from app.overview.service import project_overview

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("")
def get_overview(settings: Annotated[Settings, Depends(get_settings)]) -> Overview:
    """Building carbon overview of the OpenBDF project in OPENBDF_DATA_DIR."""
    if settings.OPENBDF_DATA_DIR is None:
        raise HTTPException(503, "No OpenBDF project configured (OPENBDF_DATA_DIR)")
    return project_overview(settings.OPENBDF_DATA_DIR)
