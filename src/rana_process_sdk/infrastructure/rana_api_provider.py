from abc import abstractmethod

from ..domain import Json
from ..settings import get_settings
from .api_provider import ApiProvider
from .local_test_rana_runtime import LocalTestRanaRuntime
from .prefect_rana_runtime import PrefectRanaRuntime
from .rana_runtime import RanaRuntime

__all__ = ["RanaApiProvider", "PrefectRanaApiProvider", "LocalTestRanaApiProvider"]


def _get_headers(runtime: RanaRuntime) -> Json:
    return {"X-Job-Secret": runtime.job_secret.get_secret_value()}


def _get_job_path(runtime: RanaRuntime) -> str:
    return f"v1-alpha/tenants/{runtime.tenant_id}/jobs/{runtime.job_id}"


class RanaApiProvider(ApiProvider):
    def __init__(self) -> None:
        super().__init__(url=get_settings().rana_api_url)

    @abstractmethod
    def job_request(
        self,
        method: str,
        path: str,
        params: Json | None = None,
        json: Json | None = None,
    ) -> Json | None:
        pass


class PrefectRanaApiProvider(RanaApiProvider):
    rana_runtime: PrefectRanaRuntime

    def __init__(self, rana_runtiem: PrefectRanaRuntime | None = None) -> None:
        self.rana_runtime = rana_runtiem or PrefectRanaRuntime()
        super().__init__()

    def job_request(
        self,
        method: str,
        path: str,
        params: Json | None = None,
        json: Json | None = None,
    ) -> Json | None:
        path = _get_job_path(self.rana_runtime) + (
            path if path.startswith("/") else "/" + path
        )
        return super().request(
            method,
            path,
            params=params,
            json=json,
            headers=_get_headers(self.rana_runtime),
        )


class LocalTestRanaApiProvider(RanaApiProvider):
    rana_runtime: LocalTestRanaRuntime

    def __init__(self, rana_runtime: LocalTestRanaRuntime) -> None:
        self.rana_runtime = rana_runtime

    def job_request(
        self,
        method: str,
        path: str,
        params: Json | None = None,
        json: Json | None = None,
    ) -> Json | None:
        raise NotImplementedError("Do not use job request in local test runtime")
