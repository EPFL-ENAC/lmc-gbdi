"""Load OpenBDF workbooks into the database, the way the upload endpoint does.

    make load-buildings FILES="~/Downloads/Output/*.xlsx"   (from the repo root)

A workbook whose file name is already loaded is skipped, so a rerun adds only the
new ones. A rejected workbook prints its first findings and loads nothing.
"""

import asyncio
import sys
import time
from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings.ingest import RejectedWorkbook, parse, store
from app.buildings.models import Upload
from app.db import engine


async def load(path: Path) -> None:
    async with AsyncSession(engine) as session:
        loaded = await session.exec(
            select(Upload.id).where(Upload.file_name == path.name)
        )
        if loaded.first() is not None:
            print(f"{path.name}: already loaded")
            return
        start = time.perf_counter()
        try:
            project, findings = await asyncio.to_thread(parse, path.read_bytes())
        except RejectedWorkbook as rejected:
            print(f"{path.name}: rejected")
            for f in rejected.findings[:5]:
                print(
                    f"  {f.severity} {f.code} {f.sheet or ''} {f.row or ''} {f.message}"
                )
            return
        parsed = time.perf_counter()
        lines = len(project.bill_of_materials)
        project_id = await store(session, project, path.name, findings)
        await session.commit()
        print(
            f"{path.name}: project {project_id}, {lines} lines, "
            f"{len(findings)} findings, parsed in {parsed - start:.0f} s, "
            f"stored in {time.perf_counter() - parsed:.0f} s"
        )


async def main(paths: list[Path]) -> None:
    for path in paths:
        await load(path)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main([Path(p) for p in sys.argv[1:]]))
