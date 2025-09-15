from typing import Literal

from .base import Widget

__all__ = ["DatasetWidget"]


class DatasetWidget(Widget):
    id: Literal["dataset"] = "dataset"
    filters: dict[str, str] = {}
    default: dict[str, str] | None = None

    def __hash__(self) -> int:
        return hash((self.__class__, self.filters, self.default))
