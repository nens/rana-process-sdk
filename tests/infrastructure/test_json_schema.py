from pytest import mark

from rana_process_sdk.domain import Json
from rana_process_sdk.infrastructure import (
    is_optional,
    lookup_ref,
    maybe_follow_ref,
    unpack_optional,
)


@mark.parametrize(
    "schema,expected",
    [
        ({"anyOf": [{"foo", "bar"}, {"type": "null"}]}, True),
        ({"foo": "bar"}, False),
    ],
)
def test_is_optional(schema: Json, expected: bool):
    assert is_optional(schema) == expected


@mark.parametrize(
    "schema,expected",
    [
        ({"anyOf": [{"foo", "bar"}, {"type": "null"}]}, {"foo", "bar"}),
        ({"foo": "bar"}, None),
    ],
)
def test_unpack_optional(schema: Json, expected: Json | None):
    assert unpack_optional(schema) == expected


@mark.parametrize("definitions_key", ["definitions", "$defs"])
def test_lookup_ref(definitions_key: str):
    schema = {definitions_key: {"foo": {"bar": "baz"}}}
    assert lookup_ref(schema, f"#/{definitions_key}/foo") == {"bar": "baz"}


def test_maybe_follow_ref():
    schema = {"definitions": {"foo": {"bar": "baz"}}}
    assert maybe_follow_ref(schema, {"$ref": "#/definitions/foo"}) == {"bar": "baz"}
