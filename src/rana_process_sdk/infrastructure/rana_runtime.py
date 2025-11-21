import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, SecretStr

from ..domain import Json, ThreediApiKey

__all__ = ["RanaRuntime"]

T = TypeVar("T", bound=BaseModel)


class RanaRuntime(ABC):
    threedi_api_key: ThreediApiKey | None

    def __init__(self) -> None:
        # PrefectContext is the only place to store variables in the context
        # of a single prefect job:
        self.threedi_api_key = None

    @property
    @abstractmethod
    def job_working_dir(self) -> Path:
        pass

    @property
    @abstractmethod
    def _job_variables(self) -> Json:
        pass

    @property
    @abstractmethod
    def job_id(self) -> UUID:
        pass

    @property
    @abstractmethod
    def process_id(self) -> UUID:
        pass

    @property
    @abstractmethod
    def job_name(self) -> str:
        pass

    @property
    @abstractmethod
    def job_parameters(self) -> Json:
        pass

    @property
    @abstractmethod
    def job_secret(self) -> SecretStr:
        pass

    @property
    @abstractmethod
    def tenant_id(self) -> str:
        pass

    @property
    @abstractmethod
    def logger(self) -> logging.Logger:
        pass

    @abstractmethod
    def set_progress(self, progress: float, description: str, log: bool) -> None:
        pass

    @abstractmethod
    def set_result(self, result: Json) -> None:
        pass
