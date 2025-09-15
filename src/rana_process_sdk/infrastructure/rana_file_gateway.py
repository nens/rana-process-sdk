__all__ = ["RanaFileGateway"]
from http import HTTPStatus

from rana_process_sdk.domain.files import History

from ..domain import DoesNotExist, FileStat, FileUpload, Json
from .api_exception import ApiException
from .rana_api_provider import PrefectRanaApiProvider


class RanaFileGateway:
    ls_subpath = "files/ls"
    stat_subpath = "files/stat"
    download_subpath = "files/download"
    history_subpath = "files/history"
    upload_subpath = "files/upload"

    def __init__(self, provider_override: PrefectRanaApiProvider | None = None):
        self.provider_override = provider_override

    @property
    def provider(self) -> PrefectRanaApiProvider:
        return self.provider_override or PrefectRanaApiProvider()

    def stat(self, path: str, ref: str) -> FileStat:
        try:
            response = self.provider.job_request(
                "GET", self.stat_subpath, params={"path": path, "ref": ref}
            )
        except ApiException as e:
            if e.status == HTTPStatus.NOT_FOUND:
                raise DoesNotExist("file", path)
            raise
        assert response is not None
        return FileStat(**response)

    def get_download_url(self, path: str, ref: str) -> str:
        response = self.provider.job_request(
            "GET", self.download_subpath, params={"path": path, "ref": ref}
        )
        if response is None:
            raise DoesNotExist("file", path)
        return response["url"]

    def history(self, path: str, ref: str, limit: int = 10) -> list[History]:
        response = self.provider.job_request(
            "GET",
            self.history_subpath,
            params={"path": path, "ref": ref, "limit": limit},
        )
        assert response is not None
        return [History.model_construct(**x) for x in response["items"]]

    def upload_start(self, path: str) -> Json:
        response = self.provider.job_request(
            "POST", self.upload_subpath, params={"path": path}
        )
        assert response is not None
        return response

    def upload_complete(
        self,
        upload: Json,
        data_type: str | None = None,
        description: str = "",
        meta: Json | None = None,
    ) -> FileUpload:
        body = upload.copy()
        if data_type or description:  # usage of meta implies data_type
            body["descriptor"] = {}
        if data_type:
            body["descriptor"]["data_type"] = data_type
        if description:
            body["descriptor"]["description"] = description
        if meta:
            body["descriptor"]["meta"] = meta
        response = self.provider.job_request("PUT", self.upload_subpath, json=body)
        assert response is not None
        return FileUpload(**response)
