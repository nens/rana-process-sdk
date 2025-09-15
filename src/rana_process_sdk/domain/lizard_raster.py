from uuid import UUID

from pydantic import BaseModel, ConfigDict

__all__ = ["LizardRaster"]


class LizardRaster(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: UUID
    pixelsize_x: float | None
    pixelsize_y: float | None
    projection: str | None
    dtype: str | None = None
    styles: str | None = None

    @property
    def resolution(self) -> float | None:
        if self.pixelsize_x is not None and self.pixelsize_y is not None:
            return min(self.pixelsize_x, abs(self.pixelsize_y))
        return None

    @property
    def epsg_code(self) -> int | None:
        if self.projection and self.projection.upper().startswith("EPSG:"):
            return int(self.projection.split(":")[1])
        return None
