import datetime
import os
from abc import ABC, abstractmethod

from ..domain import FileUpload
from .rana_api_provider import (
    LocalTestRanaApiProvider,
    PrefectRanaApiProvider,
    RanaApiProvider,
)

__all__ = [
    "RanaSchematisationGateway",
    "PrefectRanaSchematisationGateway",
    "LocalTestRanaSchematisationGateway",
]


class RanaSchematisationGateway(ABC):
    @abstractmethod
    def __init__(self, provider_override: RanaApiProvider | None = None):
        pass

    @property
    @abstractmethod
    def provider(self) -> RanaApiProvider:
        pass

    @abstractmethod
    def create(self, path: str) -> tuple[FileUpload, int]:
        pass


class PrefectRanaSchematisationGateway(RanaSchematisationGateway):
    create_subpath = "model-schematisations"
    provider_override: RanaApiProvider | None = None

    def __init__(self, provider_override: RanaApiProvider | None = None):
        self.provider_override = provider_override

    @property
    def provider(self) -> RanaApiProvider:
        return self.provider_override or PrefectRanaApiProvider()

    def create(self, path: str) -> tuple[FileUpload, int]:
        params = {"path": path}
        response = self.provider.job_request("POST", self.create_subpath, params=params)
        assert response is not None
        return FileUpload(**response), response["schematisation_id"]


class LocalTestRanaSchematisationGateway(RanaSchematisationGateway):
    def __init__(self, provider_override: LocalTestRanaApiProvider):
        self.provider_override = provider_override

    @property
    def provider(self) -> LocalTestRanaApiProvider:
        return self.provider_override

    def create(self, path: str) -> tuple[FileUpload, int]:
        project_dir = self.provider.rana_runtime.project_dir
        with open(os.path.join(project_dir, path), "w") as f:
            f.write("local_test")
        return FileUpload(
            id=path, ref="local_test", last_modified=datetime.datetime.now()
        ), 123
