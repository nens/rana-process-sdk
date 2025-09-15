from typing import Any

from pytest import mark

from rana_process_sdk import FilePickerWidget
from rana_process_sdk.domain import Json


@mark.parametrize(
    "data_type_filter,expected",
    [
        (None, None),
        ([], None),
        (["raster"], "raster"),
        (["vector"], "vector"),
        (["raster", "vector"], None),
    ],
)
def test_output_datatype(data_type_filter: list[str] | None, expected: str | None):
    widget = FilePickerWidget(data_type_filter=data_type_filter)
    assert widget.output_datatype == expected


@mark.parametrize(
    "meta_filters,expected",
    [
        ({}, {}),
        ({"key": ["value"]}, {"key": "value"}),
        ({"key": ["value1", "value2"]}, {}),
        (
            {"key1": ["value1"], "key2": ["value2"]},
            {"key1": "value1", "key2": "value2"},
        ),
        ({"key1": ["value1"], "key2": []}, {"key1": "value1"}),
    ],
)
def test_output_meta_values(meta_filters: dict[str, list[Any]], expected: Json):
    widget = FilePickerWidget(meta_filters=meta_filters)
    assert widget.output_meta_values == expected
