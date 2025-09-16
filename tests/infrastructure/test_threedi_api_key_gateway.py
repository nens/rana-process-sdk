from http import HTTPStatus
from unittest.mock import Mock

from pytest import fixture

from rana_process_sdk.domain import ThreediApiKey
from rana_process_sdk.infrastructure import (
    ApiException,
    RanaApiProvider,
    ThreediApiKeyGateway,
)


@fixture
def provider() -> Mock:
    return Mock(RanaApiProvider)


@fixture
def gateway(provider: Mock) -> ThreediApiKeyGateway:
    return ThreediApiKeyGateway(provider)


def test_add(gateway: ThreediApiKeyGateway, provider: Mock):
    provider.job_request.return_value = {
        "prefix": "ahM5ohHo",
        "key": "personal_api_key_fake_secret",
        "organisations": ["8a831188-f7fa-4d04-90d0-7a104cd09963"],
    }

    actual = gateway.add()

    assert actual == ThreediApiKey(**provider.job_request.return_value)

    provider.job_request.assert_called_once_with("POST", "3di-personal-api-keys/")


def test_remove(gateway: ThreediApiKeyGateway, provider: Mock):
    assert gateway.remove("ahM5ohHo")

    provider.job_request.assert_called_once_with(
        "DELETE", "3di-personal-api-keys/ahM5ohHo"
    )


def test_remove_does_not_exist(gateway: ThreediApiKeyGateway, provider: Mock):
    provider.job_request.side_effect = ApiException({}, status=HTTPStatus.NOT_FOUND)

    assert not gateway.remove("ahM5ohHo")
