from rana_process_sdk import RanaProcessParameters
from rana_process_sdk.infrastructure import maybe_follow_ref


class Parameters(RanaProcessParameters):
    a: int
    c: int
    b: int


class NestedParameters(RanaProcessParameters):
    a: Parameters


def test_order():
    assert Parameters.model_json_schema()["order"] == ["a", "c", "b"]


def test_order_nested():
    schema = NestedParameters.model_json_schema()
    assert schema["order"] == ["a"]
    a_defn = maybe_follow_ref(schema, schema["properties"]["a"])
    assert a_defn["order"] == ["a", "c", "b"]
