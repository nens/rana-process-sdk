from http import HTTPStatus

from ..domain import ThreediApiKey
from .api_exception import ApiException
from .rana_api_provider import PrefectRanaApiProvider

__all__ = ["ThreediApiKeyGateway"]


class ThreediApiKeyGateway:
    path = "3di-personal-api-keys/{prefix}"

    def __init__(self, provider_override: PrefectRanaApiProvider | None = None):
        self.provider_override = provider_override

    @property
    def provider(self) -> PrefectRanaApiProvider:
        return self.provider_override or PrefectRanaApiProvider()

    def add(self) -> ThreediApiKey:
        response = self.provider.job_request("POST", self.path.format(prefix=""))
        assert response is not None
        return ThreediApiKey(**response)

    def remove(self, prefix: str) -> bool:
        try:
            self.provider.job_request("DELETE", self.path.format(prefix=prefix))
        except ApiException as e:
            if e.status == HTTPStatus.NOT_FOUND:
                return False
            raise e
        return True
