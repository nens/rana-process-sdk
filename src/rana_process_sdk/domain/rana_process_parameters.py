from pydantic import BaseModel, ConfigDict
from pydantic.config import JsonDict

__all__ = ["RanaProcessParameters"]


def add_order_to_objects(a: JsonDict, b: type[BaseModel]) -> None:
    a["order"] = list(b.model_fields)


class RanaProcessParameters(BaseModel):
    model_config = ConfigDict(json_schema_extra=add_order_to_objects)
