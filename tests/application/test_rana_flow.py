import importlib
import re
import sys
from pathlib import Path
from typing import Annotated
from unittest.mock import MagicMock, Mock, patch

from prefect import Flow
from pydantic import Field
from pytest import fixture, mark, raises

from rana_process_sdk import (
    PrefectRanaContext,
    RanaContext,
    RanaProcessParameters,
    rana_flow,
)
from rana_process_sdk.application.local_test_rana_context import LocalTestRanaContext
from rana_process_sdk.infrastructure import SentryBlock

MODULE = "rana_process_sdk.application.rana_flow"


class Output(RanaProcessParameters):
    number: int


class Inputs(RanaProcessParameters):
    s: Annotated[str, Field(title="String", description="A string")]


def test_rana_flow():
    @rana_flow()
    def flow(context: PrefectRanaContext[Output], inputs: Inputs) -> None:
        assert inputs.s == "foo"
        return None

    assert isinstance(flow, Flow)

    assert flow.on_crashed_hooks[0] == SentryBlock.crash_handler


def test_rana_flow_param_spec():
    @rana_flow()
    def flow(context: RanaContext[Output], inputs: Inputs) -> None:
        return None

    # Prefect generates this for us, just check the result:
    assert flow.parameters.properties["context"] == {
        "$ref": "#/definitions/RanaContext_Output_",
        "position": 0,
        "title": "context",
    }
    assert flow.parameters.definitions["RanaContext_Output_"] == {
        "properties": {
            "output": {
                "anyOf": [{"$ref": "#/definitions/Output"}, {"type": "null"}],
                "default": None,
            },
            "output_paths": {
                "additionalProperties": {"type": "string"},
                "default": {},
                "title": "Output Paths",
                "type": "object",
            },
        },
        "title": "RanaContext[Output]",
        "type": "object",
    }
    assert flow.parameters.definitions["Output"] == {
        "properties": {"number": {"title": "Number", "type": "integer"}},
        "required": ["number"],
        "title": "Output",
        "type": "object",
        "order": ["number"],
    }
    assert flow.parameters.properties["inputs"] == {
        "$ref": "#/definitions/Inputs",
        "position": 1,
        "title": "inputs",
    }
    assert flow.parameters.definitions["Inputs"] == {
        "properties": {
            "s": {
                "description": "A string",
                "title": "String",
                "type": "string",
            }
        },
        "required": ["s"],
        "title": "Inputs",
        "type": "object",
        "order": ["s"],
    }


def test_param_spec_no_context():
    def f(inputs: Inputs) -> None:
        return None

    with raises(
        ValueError, match="The function must have a parameter called 'context'"
    ):
        rana_flow()(f)


def test_param_spec_generic():
    def f(context: PrefectRanaContext, inputs: Inputs) -> None:
        return None

    with raises(
        ValueError,
        match=re.escape(
            "RanaContext must be subclassed like so: RanaContext[SomeOutputClass]"
        ),
    ):
        rana_flow()(f)


def test_param_spec_context_no_rana_process_parameters():
    def f(context: PrefectRanaContext[str], inputs: Inputs) -> None:
        return None

    with raises(
        ValueError, match="The output field must be a subclass of RanaProcessParameters"
    ):
        rana_flow()(f)


def test_param_spec_no_inputs():
    def f(context: PrefectRanaContext[Output]) -> None:
        return None

    with raises(ValueError, match="The function must have a parameter called 'inputs'"):
        rana_flow()(f)


def test_param_spec_inputs_no_rana_process_parameters():
    def f(context: PrefectRanaContext[Output], inputs: str) -> None:
        return None

    with raises(
        ValueError,
        match="The inputs parameter must be a subclass of RanaProcessParameters",
    ):
        rana_flow()(f)


@mark.parametrize("rana_context_class", [PrefectRanaContext, LocalTestRanaContext])
@patch(MODULE + ".cast_rana_context")
def test_rana_flow_context(cast_rana_context: Mock, rana_context_class):
    rana_context = Mock(
        rana_context_class[Output], __enter__=MagicMock(), __exit__=MagicMock()
    )
    cast_rana_context.return_value = rana_context

    @rana_flow()
    def flow(context: RanaContext[Output], inputs: Inputs) -> None:
        context.__enter__.assert_called_once()
        assert not context.__exit__.called

    flow.fn(rana_context, None)

    rana_context.__exit__.assert_called_once()
    rana_context.setup_logger.assert_called_once()


def test_rana_flow_with_title():
    @rana_flow(title="foo")
    def flow(context: PrefectRanaContext[Output], inputs: Inputs) -> None:
        return None

    assert flow.name == "foo"


@fixture
def flow_module(tmp_path: Path):
    module_path = tmp_path / "process.py"
    module_path.write_text(Path("tests/data/example_process.py").read_text())
    return load_module(module_path)


@fixture
def flow_module_with_descripion_file(tmp_path: Path):
    module_path = tmp_path / "process.py"
    module_path.write_text(Path("tests/data/example_process.py").read_text())
    (tmp_path / "description.md").write_text("# Example Process Description")
    return load_module(module_path)


def load_module(module_path: Path):
    module_name = "example_process"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_rana_flow_description_with_pararm(flow_module):
    assert flow_module.flow_with_description.description == "This is a test flow"


def test_rana_flow_description_without_param(flow_module):
    assert flow_module.flow_without_description.description is None


def test_rana_flow_description_file_with_param(flow_module_with_descripion_file):
    assert (
        flow_module_with_descripion_file.flow_with_description.description
        == "This is a test flow"
    )


def test_rana_flow_description_file_without_param(flow_module_with_descripion_file):
    assert (
        flow_module_with_descripion_file.flow_without_description.description
        == "# Example Process Description"
    )


def test_rana_flow_description_file_not_read_without_file_in_globals():
    """Test that description file is not read when __file__ is not in globals."""
    # Use current globals but remove __file__ to simulate the scenario
    globals_without_file = globals().copy()
    globals_without_file.pop("__file__", None)

    local_namespace = {}

    exec(
        """
@rana_flow()
def flow_no_file_global(context: PrefectRanaContext[Output], inputs: Inputs) -> None:
    return None
result = flow_no_file_global
""",
        globals_without_file,
        local_namespace,
    )

    result_flow = local_namespace["result"]
    assert result_flow.description is None
