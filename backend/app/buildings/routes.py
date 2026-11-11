import asyncio
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings import repo, service
from app.buildings.ingest import RejectedWorkbook
from app.buildings.schemas import BuildingSummary, Comparison, DraftView, Rejection
from app.db import get_session
from app.overview.schemas import Basis, Overview
from app.overview.service import BasisUnavailable

router = APIRouter(prefix="/api/buildings", tags=["buildings"])
Session = Annotated[AsyncSession, Depends(get_session)]


def _new_parser() -> ProcessPoolExecutor:
    return ProcessPoolExecutor(max_workers=1, max_tasks_per_child=1)


# Each upload runs in a fresh process, one at a time: its memory (3.7 GB for a
# 107 MB workbook) is freed when it exits, and the API keeps answering probes.
_parser = _new_parser()


async def in_parser(fn: Callable[..., Any], *args: Any) -> Any:
    """Run fn in the parser process. A process killed mid-upload (out of memory)
    breaks the pool for good, so a new one takes its place for the next upload."""
    global _parser
    try:
        return await asyncio.get_running_loop().run_in_executor(_parser, fn, *args)
    except BrokenProcessPool:
        _parser = _new_parser()
        raise


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
async def upload_building(
    request: Request, file: UploadFile, session: Session, draft: bool = False
) -> BuildingSummary:
    """Read an OpenBDF workbook with lmc-openbdf and store it. Rejects store nothing,
    unless `draft`: stored as a draft, without the parts its rejects block."""
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(415, "Upload an OpenBDF workbook (.xlsx)")
    workbook = await file.read()
    try:
        summary, overview = await in_parser(
            service.ingest, workbook, file.filename or "", draft
        )
    except BrokenProcessPool:
        raise HTTPException(
            503,
            f"{file.filename}: reading it stopped the parser, most likely out of "
            "memory. Nothing was stored.",
        ) from None
    except RejectedWorkbook as rejected:
        body = Rejection(
            message=f"openbdf rejected {file.filename}: nothing was stored.",
            findings=[f.__dict__ for f in rejected.findings],
        )
        return JSONResponse(body.model_dump(), status_code=422)
    except ValueError as unreadable:
        raise HTTPException(422, f"{file.filename}: {unreadable}") from None
    # Uploads queue one at a time: a client that gave up (a proxy timeout) never
    # learns this one was stored, and would store it twice on retry.
    if await request.is_disconnected():
        await service.delete(session, summary.id)
        raise HTTPException(499, "The client left before the upload ended.")
    service.remember(summary, overview)
    return summary


@router.get("/compare")
async def compare(a: int, b: int, session: Session) -> Comparison:
    """Two buildings side by side, per m² of gross floor area."""
    try:
        return await service.compare(session, a, b)
    except repo.ProjectNotFound as missing:
        raise HTTPException(404, f"No building {missing}") from None
    except service.DraftBlocked as draft:
        raise HTTPException(
            409, f"Building {draft} is a draft: no carbon figures"
        ) from None


@router.get("/{project_id}")
async def get_building(project_id: int, session: Session) -> BuildingSummary:
    try:
        return await service.building_summary(session, project_id)
    except repo.ProjectNotFound:
        raise HTTPException(404, f"No building {project_id}") from None


@router.get("/{project_id}/overview")
async def get_overview(
    project_id: int, session: Session, basis: Basis = "total"
) -> Overview:
    """The building carbon overview sheet, computed from the stored project, with
    every absolute figure on the basis asked for."""
    try:
        return await service.overview(session, project_id, basis)
    except BasisUnavailable as why:
        raise HTTPException(422, str(why)) from None
    except repo.ProjectNotFound:
        raise HTTPException(404, f"No building {project_id}") from None
    except service.DraftBlocked:
        raise HTTPException(
            409, f"Building {project_id} is a draft: no carbon figures"
        ) from None


@router.get("/{project_id}/draft")
async def get_draft(project_id: int, session: Session) -> DraftView:
    """What a draft still shows: its rejects, project details, materials by mass."""
    try:
        return await service.draft_view(session, project_id)
    except repo.ProjectNotFound:
        raise HTTPException(404, f"No building {project_id}") from None


@router.delete("/{project_id}", status_code=204)
async def delete_building(project_id: int, session: Session) -> None:
    try:
        await service.delete(session, project_id)
    except repo.ProjectNotFound:
        raise HTTPException(404, f"No building {project_id}") from None
