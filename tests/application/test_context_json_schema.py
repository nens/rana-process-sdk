"""Verify the public JSON schema of PrefectRanaContext to match RanaContext

These tests detects regression introduced by properties required to track internal state.
"""

from pytest import mark

from rana_process_sdk import (
    File,
    PrefectRanaContext,
    RanaContext,
    RanaProcessParameters,
    rana_flow,
)


class Output(RanaProcessParameters):
    number: int


class FileOutput(RanaProcessParameters):
    x: File


class Inputs(RanaProcessParameters):
    s: str


PREFECT_CONTEXT_SCHEMA = {
    "$defs": {
        "Output": {
            "order": ["number"],
            "properties": {"number": {"title": "Number", "type": "integer"}},
            "required": ["number"],
            "title": "Output",
            "type": "object",
        }
    },
    "properties": {
        "output": {
            "anyOf": [{"$ref": "#/$defs/Output"}, {"type": "null"}],
            "default": None,
        },
        "output_paths": {
            "additionalProperties": {"type": "string"},
            "default": {},
            "title": "Output Paths",
            "type": "object",
        },
    },
    "title": "PrefectRanaContext[Output]",
    "type": "object",
}


@mark.parametrize("output_type", [Output, FileOutput])
@mark.parametrize("mode", ["validation", "serialization"])
def test_prefect_context_schema_matches_rana_context(output_type, mode):
    prefect_schema = PrefectRanaContext[output_type].model_json_schema(mode=mode)
    rana_schema = RanaContext[output_type].model_json_schema(mode=mode)

    assert prefect_schema["properties"] == rana_schema["properties"]
    assert prefect_schema.get("$defs") == rana_schema.get("$defs")


def test_prefect_context_schema_is_unchanged():
    assert PrefectRanaContext[Output].model_json_schema() == PREFECT_CONTEXT_SCHEMA


def test_prefect_context_model_fields_match_rana_context():
    assert list(PrefectRanaContext[Output].model_fields) == list(
        RanaContext[Output].model_fields
    )


@mark.parametrize("context_type", [RanaContext, PrefectRanaContext])
def test_flow_parameter_context_publishes_public_fields_only(context_type):
    @rana_flow()
    def flow(context: context_type[Output], inputs: Inputs) -> None:  # type: ignore
        return None

    schema = flow.parameters.model_dump_for_openapi()
    context_name = schema["properties"]["context"]["$ref"].split("/")[-1]

    assert list(schema["definitions"][context_name]["properties"]) == [
        "output",
        "output_paths",
    ]


def test_flow_parameter_context_prefect_matches_rana_context():
    @rana_flow()
    def rana_context_flow(context: RanaContext[Output], inputs: Inputs) -> None:
        return None

    @rana_flow()
    def prefect_context_flow(
        context: PrefectRanaContext[Output], inputs: Inputs
    ) -> None:
        return None

    rana_schema = rana_context_flow.parameters.model_dump_for_openapi()
    prefect_schema = prefect_context_flow.parameters.model_dump_for_openapi()
    rana_context = rana_schema["definitions"][
        rana_schema["properties"]["context"]["$ref"].split("/")[-1]
    ]
    prefect_context = prefect_schema["definitions"][
        prefect_schema["properties"]["context"]["$ref"].split("/")[-1]
    ]

    assert prefect_context["properties"] == rana_context["properties"]
