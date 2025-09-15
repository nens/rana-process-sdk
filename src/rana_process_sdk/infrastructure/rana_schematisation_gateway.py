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
    def upload(self, path: str, schematisation_id: str) -> FileUpload:
        pass


class PrefectRanaSchematisationGateway(RanaSchematisationGateway):
    add_subpath = "threedi-schematisations"
    provider_override: RanaApiProvider | None = None

    def __init__(self, provider_override: RanaApiProvider | None = None):
        self.provider_override = provider_override

    @property
    def provider(self) -> RanaApiProvider:
        return self.provider_override or PrefectRanaApiProvider()

    def upload(self, path: str, schematisation_id: str) -> FileUpload:
        params = {
            "path": path,
            "schematisation_id": schematisation_id,
            "branch": "main",
        }
        response = self.provider.job_request("POST", self.add_subpath, params=params)
        assert response is not None
        return FileUpload(**response)


class LocalTestRanaSchematisationGateway(RanaSchematisationGateway):
    def __init__(self, provider_override: LocalTestRanaApiProvider):
        self.provider_override = provider_override

    @property
    def provider(self) -> LocalTestRanaApiProvider:
        return self.provider_override

    def upload(self, path: str, schematisation_id: str) -> FileUpload:
        project_dir = self.provider.rana_runtime.project_dir
        with open(os.path.join(project_dir, path), "w") as f:
            f.write(schematisation_id)
        return FileUpload(
            id=path, ref="local_test", last_modified=datetime.datetime.now()
        )
