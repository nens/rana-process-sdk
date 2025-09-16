from base64 import b64encode
from unittest.mock import patch

from pydantic import SecretStr
from pydantic_core import Url
from pytest import fixture

from rana_process_sdk.infrastructure.lizard_api_provider import LizardApiProvider
from rana_process_sdk.settings import LizardSettings

MODULE = "rana_process_sdk.infrastructure.lizard_api_provider"


@fixture
def lizard_settings() -> LizardSettings:
    return LizardSettings(
        host=Url("https://lizard-api"),
        api_key=SecretStr("supersecret"),
    )


@fixture
def provider(lizard_settings: LizardSettings) -> LizardApiProvider:
    with patch(f"{MODULE}.get_settings") as m:
        m.return_value.lizard = lizard_settings
        return LizardApiProvider()


def test_url(provider: LizardApiProvider):
    assert provider._url == "https://lizard-api/"  # with trailing slash


def test_headers_factory(provider: LizardApiProvider):
    headers = provider._headers_factory()
    assert headers == {
        "authorization": "Basic " + b64encode(b"__key__:supersecret").decode("utf-8")
    }
