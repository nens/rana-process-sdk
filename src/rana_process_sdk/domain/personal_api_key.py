from uuid import UUID

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = ["ThreediApiKey"]


class ThreediApiKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefix: str
    key: SecretStr
    organisations: list[UUID]
