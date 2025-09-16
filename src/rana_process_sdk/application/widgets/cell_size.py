from typing import Literal

from .base import Widget

__all__ = ["CellSizeWidget"]


class CellSizeWidget(Widget):
    id: Literal["cell_size"] = "cell_size"
    # refers to a dataset or raster typed field that has a resolution:
    data_source: str | None = None
    # refers to a Vector typed field name that has an extent.bbox:
    extent_source: str
    # compute the resulting raster(s) size: (extent / cell_size^2 * bytes_per_cell)
    bytes_per_cell: float = 4.0
