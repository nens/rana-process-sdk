from collections.abc import Iterator
from unittest.mock import Mock, patch
from uuid import uuid4

from pydantic import SecretStr
from pydantic_core import Url
from pytest import fixture, mark

from rana_process_sdk import PrefectRanaApiProvider
from rana_process_sdk.infrastructure import ApiProvider, RanaRuntime
from rana_process_sdk.infrastructure.rana_api_provider import (
    _get_headers,
    _get_job_path,
)
from rana_process_sdk.settings.settings import Settings

MODULE = "rana_process_sdk.infrastructure.rana_api_provider"


@fixture
def runtime() -> RanaRuntime:
    return Mock(RanaRuntime)


@fixture
def get_settings() -> Iterator[Mock]:
    result = Mock(Settings)
    result.rana_api_url = Url("http://rana-api/")
    with patch(f"{MODULE}.get_settings", return_value=result) as get_settings:
        yield get_settings


def test_get_headers(runtime: Mock):
    runtime.job_secret = SecretStr("supersecret")

    actual = _get_headers(runtime)

    assert actual == {"X-Job-Secret": "supersecret"}


def test_get_job_path():
    job_id = uuid4()
    context = Mock(RanaRuntime, tenant_id="tenantId", job_id=job_id)
    actual = _get_job_path(context)
    assert actual == f"v1-alpha/tenants/tenantId/jobs/{job_id}"


def test_init(get_settings: Mock, runtime: Mock):
    provider = PrefectRanaApiProvider(runtime)
    assert provider._url == "http://rana-api/"

    get_settings.assert_called_once_with()


@mark.parametrize("path", ["/files/ls", "files/ls"])
@patch.object(ApiProvider, "request")
@patch(f"{MODULE}._get_headers", return_value={"header": "value"})
@patch(f"{MODULE}._get_job_path", return_value="path/to/job")
def test_job_request(
    _get_job_path: Mock,
    _get_headers: Mock,
    request_m: Mock,
    runtime: Mock,
    path: str,
    get_settings: Mock,
):
    actual = PrefectRanaApiProvider(runtime).job_request(
        "GET", path, {"param": "value"}, {"json": "value"}
    )

    assert actual is request_m.return_value

    request_m.assert_called_once_with(
        "GET",
        "path/to/job/files/ls",
        params={"param": "value"},
        json={"json": "value"},
        headers={"header": "value"},
    )
    _get_headers.assert_called_once_with(runtime)
    _get_job_path.assert_called_once_with(runtime)
