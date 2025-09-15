import inspect
import typing

from prefect import Flow
from pydantic._internal._model_construction import ModelMetaclass

from rana_process_sdk.domain.rana_process_parameters import RanaProcessParameters

from .. import LocalTestRanaContext
from ..infrastructure import LocalTestRanaRuntime

__all__ = ["run_local_test"]


def run_local_test(
    rana_flow: Flow, runtime: LocalTestRanaRuntime, inputs: dict, output_paths: dict
) -> None:
    rana_process_output_type: ModelMetaclass = typing.get_args(
        inspect.signature(rana_flow.fn)
        .parameters["context"]
        .annotation.model_fields["output"]
        .annotation
    )[0]
    inputs_class: type[RanaProcessParameters] = (
        inspect.signature(rana_flow.fn).parameters["inputs"].annotation
    )
    LocalTestRanaContext.runtime_override = runtime
    local_test_rana_context = LocalTestRanaContext[rana_process_output_type](
        output_paths=output_paths
    )  # type: ignore
    rana_flow.fn(local_test_rana_context, inputs_class(**inputs))
