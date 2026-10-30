import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings import repo, service
from app.buildings.ingest import RejectedWorkbook, parse, store
from app.buildings.schemas import BuildingSummary, Comparison, Rejection
from app.db import get_session
from app.overview.schemas import Overview

router = APIRouter(prefix="/api/buildings", tags=["buildings"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("")
async def list_buildings(session: Session) -> list[BuildingSummary]:
    """Every stored building, with its whole-life carbon per m²."""
    return await service.summaries(session)


@router.post(
    "",
    status_code=201,
    responses={
        422: {"model": Rejection, "description": "openbdf rejected the workbook"}
    },
)
async def upload_building(file: UploadFile, session: Session) -> BuildingSummary:
    """Read an OpenBDF workbook with lmc-openbdf and store it. Rejects store nothing."""
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(415, "Upload an OpenBDF workbook (.xlsx)")
    workbook = await file.read()
    try:
        project, findings = await asyncio.to_thread(parse, workbook)
    except RejectedWorkbook as rejected:
        body = Rejection(
            message=f"openbdf rejected {file.filename}: nothing was stored.",
            findings=[f.__dict__ for f in rejected.findings],
        )
        return JSONResponse(body.model_dump(), status_code=422)
    project_id = await store(session, project, file.filename or "", findings)
    try:
        # Compute before committing: a project the overview cannot read is refused,
        # never stored to break the list for everyone.
        summary = await service.building_summary(session, project_id)
    except ValueError as unreadable:
        await session.rollback()
        service.forget(project_id)
        raise HTTPException(422, f"{file.filename}: {unreadable}") from None
    await session.commit()
    return summary


@router.get("/compare")
async def compare(a: int, b: int, session: Session) -> Comparison:
    """Two buildings side by side, per m² of gross floor area."""
    try:
        return await service.compare(session, a, b)
    except repo.ProjectNotFound as missing:
        raise HTTPException(404, f"No building {missing}") from None


@router.get("/{project_id}")
async def get_building(project_id: int, session: Session) -> BuildingSummary:
    try:
        return await service.building_summary(session, project_id)
    except repo.ProjectNotFound:
        raise HTTPException(404, f"No building {project_id}") from None


@router.get("/{project_id}/overview")
async def get_overview(project_id: int, session: Session) -> Overview:
    """The building carbon overview sheet, computed from the stored project."""
    try:
        return await service.overview(session, project_id)
    except repo.ProjectNotFound:
        raise HTTPException(404, f"No building {project_id}") from None


@router.delete("/{project_id}", status_code=204)
async def delete_building(project_id: int, session: Session) -> None:
    try:
        await repo.delete_project(session, project_id)
    except repo.ProjectNotFound:
        raise HTTPException(404, f"No building {project_id}") from None
    await session.commit()
    service.forget(project_id)
