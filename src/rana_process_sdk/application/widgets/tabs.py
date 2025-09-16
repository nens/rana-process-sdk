from typing import Literal

from pydantic import Field

from .base import Widget

__all__ = ["TabsWidget"]


class TabsWidget(Widget):
    # to be used with an Union / Optional / anyOf
    id: Literal["tabs"] = "tabs"
    # titles should be the same length as the number of tabs
    titles: list[str] = Field(..., min_length=2)
