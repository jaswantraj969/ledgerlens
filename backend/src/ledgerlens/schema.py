"""Extraction schemas loaded from YAML."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

FieldType = Literal["text", "identifier", "date", "currency", "amount"]

SCHEMA_DIR = Path(__file__).parent / "schemas"


class FieldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: FieldType
    labels: list[str] = []
    take: Literal["first", "last"] = "first"
    position: Literal["first_line"] | None = None
    scan: bool = False


class LineItemSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    header_labels: list[str]
    end_labels: list[str]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    fields: list[FieldSpec]
    line_items: LineItemSpec | None = None

    def field(self, name: str) -> FieldSpec | None:
        return next((spec for spec in self.fields if spec.name == name), None)


def load_schema(name_or_path: str | Path) -> Schema:
    """Load a bundled schema by name, or any schema file by path."""
    path = Path(name_or_path)
    if not path.suffix:
        path = SCHEMA_DIR / f"{name_or_path}.yaml"
    return Schema.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
