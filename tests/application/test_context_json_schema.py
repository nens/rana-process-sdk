"""The context is part of the public process interface: its JSON schema is published
with every process, and its fields are what Rana sends as the 'context' parameter.

Internal runtime state on PrefectRanaContext (such as the job usage heartbeat) must
never become part of that interface. These tests compare against RanaContext, so they
keep holding however that state is implemented.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock, patch

from pytest import fixture, mark

from rana_process_sdk import (
    File,
    PrefectRanaContext,
    RanaContext,
    RanaProcessParameters,
    rana_flow,
)
from rana_process_sdk.domain import Json

MODULE = "rana_process_sdk.application.prefect_rana_context"
HEARTBEAT_MODULE = "rana_process_sdk.application.job_usage_heartbeat"

PUBLIC_FIELDS = {"output", "output_paths"}


class Output(RanaProcessParameters):
    number: int


class FileOutput(RanaProcessParameters):
    x: File


class Inputs(RanaProcessParameters):
    s: str


def as_rana_context(schema: Json) -> Json:
    # PrefectRanaContext[X] and RanaContext[X] schemas may only differ in their names
    return json.loads(json.dumps(schema).replace("PrefectRanaContext", "RanaContext"))


def private_property_names(schema: Json) -> set[str]:
    # all property names starting with an underscore, at any depth
    result: set[str] = set()
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                result |= {name for name in value if name.startswith("_")}
            result |= private_property_names(value)
    elif isinstance(schema, list):
        for value in schema:
            result |= private_property_names(value)
    return result


@mark.parametrize("output_type", [Output, FileOutput])
@mark.parametrize("mode", ["validation", "serialization"])
def test_prefect_context_json_schema_equals_rana_context(output_type, mode):
    prefect_schema = PrefectRanaContext[output_type].model_json_schema(mode=mode)
    rana_schema = RanaContext[output_type].model_json_schema(mode=mode)

    assert set(prefect_schema["properties"]) == PUBLIC_FIELDS
    assert as_rana_context(prefect_schema) == as_rana_context(rana_schema)
    assert private_property_names(prefect_schema) == set()
    assert "job_usage" not in json.dumps(prefect_schema)


def test_prefect_context_model_fields():
    assert set(PrefectRanaContext[Output].model_fields) == PUBLIC_FIELDS
    assert set(PrefectRanaContext[Output].model_fields) == set(
        RanaContext[Output].model_fields
    )


@mark.parametrize("context_type", [RanaContext, PrefectRanaContext])
def test_flow_parameter_schema_has_no_private_attributes(context_type):
    @rana_flow()
    def flow(context: context_type[Output], inputs: Inputs) -> None:  # type: ignore
        return None

    # this is what Prefect publishes as the deployment's parameter schema
    schema = flow.parameters.model_dump_for_openapi()
    context_ref = schema["properties"]["context"]["$ref"]
    context_schema = schema["definitions"][context_ref.split("/")[-1]]

    assert set(context_schema["properties"]) == PUBLIC_FIELDS
    assert private_property_names(schema) == set()
    assert "job_usage" not in json.dumps(schema)


def test_flow_parameter_schema_prefect_context_equals_rana_context():
    @rana_flow()
    def rana_context_flow(context: RanaContext[Output], inputs: Inputs) -> None:
        return None

    @rana_flow()
    def prefect_context_flow(
        context: PrefectRanaContext[Output], inputs: Inputs
    ) -> None:
        return None

    assert as_rana_context(
        prefect_context_flow.parameters.model_dump_for_openapi()
    ) == as_rana_context(rana_context_flow.parameters.model_dump_for_openapi())


@fixture
def prefect_rana_runtime(tmp_path: Path) -> Iterator[Mock]:
    with patch(f"{MODULE}.PrefectRanaRuntime") as m:
        result = m.return_value
        result.threedi_api_key = None
        result.job_working_dir = tmp_path / "work"
        yield result


@fixture
def job_usage_gateway() -> Iterator[Mock]:
    with patch(f"{HEARTBEAT_MODULE}.RanaJobUsageGateway") as m:
        yield m


def test_entered_prefect_context_dumps_only_public_fields(
    prefect_rana_runtime: Mock, job_usage_gateway: Mock
):
    context = PrefectRanaContext[Output](output=Output(number=1))
    expected = {"output": {"number": 1}, "output_paths": {}}

    # inside the context, the job usage state (including a running thread) is set
    with context:
        assert context.model_dump(mode="json") == expected
        assert json.loads(context.model_dump_json()) == expected

    assert context.model_dump(mode="json") == expected


def test_private_state_cannot_be_set_through_input(
    prefect_rana_runtime: Mock, job_usage_gateway: Mock
):
    context = PrefectRanaContext[Output].model_validate(
        {
            "output_paths": {},
            "_job_usage_heartbeat": "injected",
            "job_usage_heartbeat": "injected",
        }
    )

    assert context.model_dump(mode="json") == {"output": None, "output_paths": {}}
    assert "_job_usage_heartbeat" not in context.__dict__
