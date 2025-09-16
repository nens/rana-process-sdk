from typing import Annotated

from pydantic import BaseModel, TypeAdapter
from pytest import fixture

from rana_process_sdk import UsingWidget, Widget


@fixture
def widget() -> Widget:
    return Widget(id="some_id")


def test_using_widget():
    SomeType = Annotated[str, UsingWidget(Widget(id="some_id"))]

    # NB Using WithJsonSchema would not show the "type": "string"
    assert TypeAdapter(SomeType).json_schema() == {
        "type": "string",
        "rana_widget": {"id": "some_id"},
    }


def test_using_widget_override():
    SomeType = Annotated[str, UsingWidget(Widget(id="some_id"))]
    SomeDerivedType = Annotated[SomeType, UsingWidget(Widget(id="some_other_id"))]

    assert TypeAdapter(SomeDerivedType).json_schema() == {
        "type": "string",
        "rana_widget": {"id": "some_other_id"},
    }


def test_using_widget_in_model_field(widget: Widget):
    class SomeModel(BaseModel):
        a: Annotated[int, UsingWidget(widget)]

    assert SomeModel.model_json_schema()["properties"]["a"]["type"] == "integer"
    assert SomeModel.model_json_schema()["properties"]["a"]["rana_widget"] == {
        "id": widget.id
    }
