import contextlib
import inspect
import typing
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, cast

from prefect import Flow, flow

from ..application import LocalTestRanaContext, RanaContext
from ..domain import RanaProcessParameters
from ..infrastructure import SentryBlock

__all__ = ["rana_flow"]

DESCRIPTION_FILENAME = "description.md"
P = ParamSpec("P")


def validate_call_signature(func: Callable[P, Any]) -> None:
    s = inspect.signature(func)
    if "context" not in s.parameters:
        raise ValueError("The function must have a parameter called 'context'")
    if not issubclass(s.parameters["context"].annotation, RanaContext):
        raise ValueError("The context parameter must be a subclass of RanaContext")
    output_field = s.parameters["context"].annotation.model_fields["output"]
    if (
        typing.get_origin(output_field.annotation) is not typing.Union
        or len(typing.get_args(output_field.annotation)) != 2
        or typing.get_args(output_field.annotation)[1] is not type(None)
    ):
        raise ValueError("The context's output field must be nullable")
    try:
        if not issubclass(
            typing.get_args(output_field.annotation)[0], RanaProcessParameters
        ):
            raise ValueError(
                "The output field must be a subclass of RanaProcessParameters"
            )
    except TypeError:
        raise ValueError(
            "RanaContext must be subclassed like so: RanaContext[SomeOutputClass]"
        )

    if "inputs" not in s.parameters:
        raise ValueError("The function must have a parameter called 'inputs'")
    if not issubclass(s.parameters["inputs"].annotation, RanaProcessParameters):
        raise ValueError(
            "The inputs parameter must be a subclass of RanaProcessParameters"
        )


def cast_rana_context(context: RanaContext) -> RanaContext:
    if not isinstance(context, LocalTestRanaContext):
        context = context.to_prefect_context()
    return context


def rana_flow(
    title: str | None = None, description: str | None = None
) -> Callable[[Callable[P, None]], Flow[P, None]]:
    def rana_flow_wrapper(func: Callable[P, None]) -> Flow[P, None]:
        validate_call_signature(func)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
            context = cast_rana_context(cast(RanaContext, args[0]))
            new_args = (context,) + args[1:]
            with context:
                context.setup_logger()
                try:
                    return func(*new_args, **kwargs)  # type: ignore
                except Exception as exception:
                    context.log_exception(exception)
                    raise exception

        description_override = description
        if "__file__" in func.__globals__:
            description_path = (
                Path(func.__globals__["__file__"]).parent / DESCRIPTION_FILENAME
            )
            if not description and description_path.exists():
                with (
                    contextlib.suppress(OSError),
                    open(description_path) as description_file,
                ):
                    description_override = description_file.read()

        return flow(
            persist_result=False,
            log_prints=True,
            description=description_override,
            name=title,
            on_crashed=[SentryBlock.crash_handler],
        )(wrapper)

    return rana_flow_wrapper
