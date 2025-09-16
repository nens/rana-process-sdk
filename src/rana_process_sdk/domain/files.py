from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict

from .types import Json

__all__ = ["File", "FileStat", "FileUpload", "History"]


class File(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    last_modified: datetime


class FileUpload(File):
    ref: str


class FileStat(File):
    url: AnyHttpUrl
    descriptor_id: str
    descriptor: Json | None = None


class History(BaseModel):
    model_config = ConfigDict(frozen=True)

    ref: str
    created_at: datetime
