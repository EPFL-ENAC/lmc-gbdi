"""Load OpenBDF workbooks into the database, the way the upload endpoint does.

    make load-buildings FILES="~/Downloads/Output/*.xlsx"   (from the repo root)
    make load-buildings FILES=new.xlsx REPLACE=121 DRAFT=1

A workbook whose file name is already loaded is skipped, so a rerun adds only the
new ones. A rejected workbook prints its first findings and loads nothing. With
--replace, one workbook replaces that building in the same transaction, whatever
its file name; with --draft, rejects are stored as the upload page's draft does.
"""

import argparse
import asyncio
import time
from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings import repo
from app.buildings.ingest import RejectedWorkbook, parse, store
from app.buildings.models import Upload
from app.db import engine


async def load(path: Path, draft: bool = False, replace: int | None = None) -> None:
    async with AsyncSession(engine) as session:
        if replace is not None:
            await repo.get_upload(session, replace)  # ProjectNotFound before the parse
        else:
            loaded = await session.exec(
                select(Upload.id).where(Upload.file_name == path.name)
            )
            if loaded.first() is not None:
                print(f"{path.name}: already loaded")
                return
        start = time.perf_counter()
        try:
            project, findings = await asyncio.to_thread(parse, path.read_bytes(), draft)
        except RejectedWorkbook as rejected:
            print(f"{path.name}: rejected")
            for f in rejected.findings[:5]:
                print(
                    f"  {f.severity} {f.code} {f.sheet or ''} {f.row or ''} {f.message}"
                )
            return
        parsed = time.perf_counter()
        lines = len(project.bill_of_materials)
        is_draft = any(f.severity == "Reject" for f in findings)
        project_id = await store(
            session, project, path.name, findings, is_draft, replace
        )
        await session.commit()
        replaced = f", replaces {replace}" if replace is not None else ""
        print(
            f"{path.name}: project {project_id}{replaced}, {lines} lines, "
            f"{sum(f.count for f in findings)} findings, "
            f"parsed in {parsed - start:.0f} s, "
            f"stored in {time.perf_counter() - parsed:.0f} s"
        )


async def main(paths: list[Path], draft: bool, replace: int | None) -> None:
    if replace is not None and len(paths) != 1:
        raise SystemExit("--replace takes exactly one workbook")
    for path in paths:
        await load(path, draft, replace)
    await engine.dispose()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cli.add_argument("files", nargs="+", type=Path)
    cli.add_argument("--draft", action="store_true")
    cli.add_argument("--replace", type=int, metavar="ID")
    args = cli.parse_args()
    asyncio.run(main(args.files, args.draft, args.replace))
