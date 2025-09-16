from pathlib import Path
from typing import Any

from prefect.utilities.callables import parameter_schema
from pydantic import BaseModel
from pytest import mark

from rana_process_sdk import (
    Directory,
    File,
    Raster,
    Scenario,
    StudyArea,
    ThreediSchematisation,
    Vector,
    path_picker_from_json_prop,
)
from rana_process_sdk.application.types.path import FilePickerWidget
from rana_process_sdk.domain import Json


@mark.parametrize(
    "_type,data_types,meta_filters,ref_name,format,widget_kwargs",
    [
        (File, None, {}, "RanaFile", "rana_file", {"id": "file_picker"}),
        (
            Directory,
            ["directory"],
            {},
            "RanaDirectory",
            "rana_directory",
            {"id": "directory_picker", "expected_files": {}},
        ),
        (Raster, ["raster"], {}, "RanaFile", "rana_file", {"id": "file_picker"}),
        (Vector, ["vector"], {}, "RanaFile", "rana_file", {"id": "file_picker"}),
        (Scenario, ["scenario"], {}, "RanaFile", "rana_file", {"id": "file_picker"}),
        (
            ThreediSchematisation,
            ["threedi_schematisation"],
            {},
            "RanaFile",
            "rana_file",
            {"id": "file_picker"},
        ),
        (
            StudyArea,
            ["vector"],
            {"feature_type_definition": ["study_area"]},
            "RanaFile",
            "rana_file",
            {"id": "file_picker"},
        ),
    ],
)
def test_file_schema(
    _type: type[Any],
    data_types: list[str],
    meta_filters: dict[str, list[str]],
    ref_name: str,
    format: str,
    widget_kwargs: Json | None,
):
    def f(x: _type):
        pass

    schema = parameter_schema(f).model_dump(mode="json")

    assert schema["properties"]["x"]["rana_widget"] == {
        "data_type_filter": data_types,
        "meta_filters": meta_filters,
        **(widget_kwargs if widget_kwargs else {}),
    }
    assert schema["properties"]["x"]["$ref"] == f"#/definitions/{ref_name}"
    assert schema["definitions"][ref_name] == {
        "format": format,
        "properties": {
            "id": {"title": "Id", "type": "string"},
            "ref": {"default": "main", "title": "Ref", "type": "string"},
            "variable_type": {
                "const": "rana_path",
                "default": "rana_path",
                "enum": [
                    "rana_path",
                ],
                "title": "Variable Type",
                "type": "string",
            },
        },
        "required": ["id"],
        "title": ref_name,
        "type": "object",
    }


class FileModel(BaseModel):
    x: File


@mark.parametrize("value", [File(id="foo"), {"id": "foo"}, "foo", Path("foo")])
def test_init_as_field(value: Any):
    assert FileModel(x=value).x == File(id="foo")


@mark.parametrize(
    "prop",
    [None, {}, {"rana_widget": {"id": "tabs"}}],
)
def test_path_picker_from_json_prop_none(prop: Json):
    assert path_picker_from_json_prop(prop) is None


def test_path_picker_from_json_prop():
    prop = {
        "rana_widget": {
            "id": "file_picker",
            "data_type_filter": ["raster", "vector"],
            "meta_filters": {"feature_type_definition": ["study_area"]},
        }
    }
    path_picker = path_picker_from_json_prop(prop)
    assert isinstance(path_picker, FilePickerWidget)
    assert path_picker.data_type_filter == ["raster", "vector"]
    assert path_picker.meta_filters == {"feature_type_definition": ["study_area"]}
