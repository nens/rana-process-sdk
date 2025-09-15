from typing import ClassVar, Literal

from pydantic import BaseModel

__all__ = ["LizardRasterDataset"]


class Dataset(BaseModel):
    filters: ClassVar[dict[str, str]] = {}
    input_type: Literal["dataset"] | None = None
    id: str


class LizardRasterDataset(Dataset):
    filters: ClassVar[dict[str, str]] = {
        "cl_spatialRepresentationType.key": "grid",
        "resourceIdentifier.link": "*lizard*",
    }
