from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from ...domain import Json
from ..widgets import (
    DirectoryPickerWidget,
    FilePickerWidget,
    PathPickerWidget,
    UsingWidget,
)

__all__ = [
    "File",
    "Directory",
    "Raster",
    "Vector",
    "Scenario",
    "RanaPath",
    "StudyArea",
    "ThreediSchematisation",
    "path_picker_from_json_prop",
    "OGC3DTiles",
]


class RanaPath(BaseModel):
    variable_type: Literal["rana_path"] = "rana_path"
    id: str
    ref: str = "main"

    @model_validator(mode="before")
    @classmethod
    def _convert_str_to_path(cls, values: Any) -> Any:
        if isinstance(values, str):
            return {"id": values}
        if isinstance(values, Path):
            return {"id": str(values)}
        return values


class RanaFile(RanaPath):
    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema))
        json_schema["format"] = "rana_file"
        return json_schema


class RanaDirectory(RanaPath):
    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler.resolve_ref_schema(handler(core_schema))
        json_schema["format"] = "rana_directory"
        return json_schema


File = Annotated[RanaFile, UsingWidget(FilePickerWidget())]
Directory = Annotated[RanaDirectory, UsingWidget(DirectoryPickerWidget())]
Raster = Annotated[
    RanaFile,
    UsingWidget(FilePickerWidget(data_type_filter=["raster"])),
]
Vector = Annotated[
    RanaFile,
    UsingWidget(FilePickerWidget(data_type_filter=["vector"])),
]
StudyArea = Annotated[
    RanaFile,
    UsingWidget(
        FilePickerWidget(
            data_type_filter=["vector"],
            meta_filters={"feature_type_definition": ["study_area"]},
        )
    ),
]
Scenario = Annotated[
    RanaFile,
    UsingWidget(FilePickerWidget(data_type_filter=["scenario"])),
]
ThreediSchematisation = Annotated[
    RanaFile,
    UsingWidget(FilePickerWidget(data_type_filter=["threedi_schematisation"])),
]
OGC3DTiles = Annotated[
    RanaFile,
    UsingWidget(FilePickerWidget(data_type_filter=["ogc_3d_tiles"])),
]


def path_picker_from_json_prop(prop: Json | None) -> PathPickerWidget | None:
    if prop is None or "rana_widget" not in prop:
        return None
    if prop["rana_widget"]["id"] == "file_picker":
        return FilePickerWidget.model_validate(prop["rana_widget"])
    if prop["rana_widget"]["id"] == "directory_picker":
        return DirectoryPickerWidget.model_validate(prop["rana_widget"])
    return None
