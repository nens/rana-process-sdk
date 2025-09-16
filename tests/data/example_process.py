from typing import Annotated

from pydantic import Field

from rana_process_sdk import RanaContext, RanaProcessParameters, rana_flow


class Output(RanaProcessParameters):
    number: int


class Inputs(RanaProcessParameters):
    s: Annotated[str, Field(title="String", description="A string")]


@rana_flow(title="foo", description="This is a test flow")
def flow_with_description(context: RanaContext[Output], inputs: Inputs) -> None:
    return None


@rana_flow(title="foo")
def flow_without_description(context: RanaContext[Output], inputs: Inputs) -> None:
    return None
