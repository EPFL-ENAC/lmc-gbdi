"""What the names the app prints mean, from lmc-openbdf's own model.

Every OpenBDF enum value carries a display name and often a description; every field a
description. The glossary keys them by the label the app prints, so the frontend looks
up exactly what it shows. Only the enums the app displays are included, so a generic
word ("Other", "Unknown") never picks up a meaning from an unrelated list.
"""

import enum
import typing
from functools import lru_cache

from fastapi import APIRouter
from openbdf.model.enums.element_classifications import (
    OpenBDFBuildingElementClassification,
)
from openbdf.model.enums.lca import LCAStageOrModuleOrSubModule
from openbdf.model.enums.materials import (
    MaterialDataType,
    OpenBDFMaterialClassification,
)
from openbdf.model.tables import ProjectRecord
from pydantic import BaseModel

from app.overview.service import DATA_TYPES, PROJECT_FIELDS

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


class Glossary(BaseModel):
    fields: dict[str, str]  # field code → description
    terms: dict[str, str]  # printed label, dashes as "-" → what it means


def key(label: str) -> str:
    """The app prints "A1–A3" (en dash); OpenBDF writes "A1-A3"."""
    return label.replace("–", "-").replace("—", "-").strip()


def field_enum(code: str) -> type[enum.Enum] | None:
    annotation = ProjectRecord.model_fields[code].annotation
    for arg in typing.get_args(annotation) or (annotation,):
        if isinstance(arg, type) and issubclass(arg, enum.Enum):
            return arg
    return None


@lru_cache
def glossary() -> Glossary:
    shown = [
        OpenBDFMaterialClassification,
        OpenBDFBuildingElementClassification,
        LCAStageOrModuleOrSubModule,
        MaterialDataType,
        *(e for _, code, _ in PROJECT_FIELDS if (e := field_enum(code))),
    ]
    terms: dict[str, str] = {}
    for kind in shown:
        for item in kind:
            # The description, or the long name when the app prints the short code.
            for label in (item.display_name, item.value):
                meaning = item.description or (
                    item.display_name if key(item.display_name) != key(label) else None
                )
                if meaning:
                    terms.setdefault(key(label), meaning)
    # The overview labels its data types in its own words; the keys are OpenBDF's.
    for code, label in DATA_TYPES:
        if description := MaterialDataType(code).description:
            terms[key(label)] = description
    fields = {
        code: info.description
        for code, info in ProjectRecord.model_fields.items()
        if info.description
    }
    return Glossary(fields=fields, terms=terms)


@router.get("")
def get_glossary() -> Glossary:
    """Field and term meanings for tooltips; fixed for a given lmc-openbdf version."""
    return glossary()
