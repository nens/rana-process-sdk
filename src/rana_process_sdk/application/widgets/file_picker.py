from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from ...domain import Json
from .base import Widget

__all__ = [
    "PathPickerWidget",
    "FilePickerWidget",
    "DirectoryPickerWidget",
    "ExpectedFile",
]


class PathPickerWidget(Widget):
    id: str = "file_picker"
    data_type_filter: list[str] | None = None
    meta_filters: dict[str, list[Any]] = {}

    def __hash__(self) -> int:
        return hash(
            (
                self.__class__,
                tuple(self.data_type_filter) if self.data_type_filter else None,
                frozenset((k, tuple(v)) for (k, v) in self.meta_filters.items()),
            )
        )

    @property
    def output_datatype(self) -> str | None:
        """Returns the data type (if any) intended for assigning it to a newly created file."""
        if self.data_type_filter and len(self.data_type_filter) == 1:
            return self.data_type_filter[0]
        return None

    @property
    def output_meta_values(self) -> Json:
        raise NotImplementedError(
            "Subclasses must implement output_meta_values to return metadata values for the selected file or directory."
        )


class FilePickerWidget(PathPickerWidget):
    id: Literal["file_picker"] = "file_picker"

    @property
    def output_meta_values(self) -> Json:
        """Returns metadata values intended for assigning it to a newly created file."""
        return (
            {k: v[0] for (k, v) in self.meta_filters.items() if len(v) == 1}
            if self.meta_filters
            else {}
        )


class ExpectedFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_type: str | None = None
    meta: Json = {}

    def __hash__(self) -> int:
        return hash((self.data_type, frozenset(self.meta.items())))


class DirectoryPickerWidget(PathPickerWidget):
    id: Literal["directory_picker"] = "directory_picker"
    data_type_filter: list[str] | None = ["directory"]
    expected_files: dict[str, ExpectedFile | None] = {}

    def __hash__(self) -> int:
        return hash(
            (
                self.__class__,
                tuple(self.data_type_filter) if self.data_type_filter else None,
                frozenset(
                    (k, v.__hash__()) for (k, v) in self.expected_files.items() if v
                ),
            )
        )

    @property
    def output_meta_values(self) -> Json:
        """Returns paths arnd metadata values intended for assigning to files in the newly created directory."""
        return {k: v for (k, v) in self.expected_files.items() if v is not None}
