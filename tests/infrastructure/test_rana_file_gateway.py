from unittest.mock import Mock

from pytest import fixture, mark

from rana_process_sdk.domain import FileStat, FileUpload, History
from rana_process_sdk.infrastructure import RanaApiProvider, RanaFileGateway

MODULE = "rana_process_sdk.infrastructure.rana_files_gateway"


@fixture
def provider() -> Mock:
    return Mock(RanaApiProvider)


@fixture
def gateway(provider: Mock) -> RanaFileGateway:
    return RanaFileGateway(provider)


def test_stat(gateway: RanaFileGateway, provider: Mock):
    provider.job_request.return_value = {
        "id": "path",
        "last_modified": "2021-01-01T00:00:00Z",
        "url": "http://example.com",
        "descriptor_id": "abc123",
    }

    actual = gateway.stat("path", "main")

    assert actual == FileStat(**provider.job_request.return_value)

    provider.job_request.assert_called_once_with(
        "GET", "files/stat", params={"path": "path", "ref": "main"}
    )


def test_upload_start(gateway: RanaFileGateway, provider: Mock):
    assert gateway.upload_start("path") is provider.job_request.return_value

    provider.job_request.assert_called_once_with(
        "POST", "files/upload", params={"path": "path"}
    )


@mark.parametrize(
    "kwargs,expected",
    [
        ({}, {}),
        ({"data_type": "raster"}, {"descriptor": {"data_type": "raster"}}),
        ({"data_type": "raster", "meta": {}}, {"descriptor": {"data_type": "raster"}}),
        ({"description": "foo"}, {"descriptor": {"description": "foo"}}),
        (
            {"data_type": "raster", "meta": {"key": "value"}},
            {"descriptor": {"data_type": "raster", "meta": {"key": "value"}}},
        ),
    ],
)
def test_upload_complete(
    gateway: RanaFileGateway, provider: Mock, kwargs: dict, expected: dict
):
    provider.job_request.return_value = {
        "id": "path",
        "last_modified": "2021-01-01T00:00:00Z",
        "url": None,
        "ref": "abc123",
    }

    actual = gateway.upload_complete({"foo": "bar"}, **kwargs)

    assert actual == FileUpload(**provider.job_request.return_value)

    provider.job_request.assert_called_once_with(
        "PUT", "files/upload", json={"foo": "bar", **expected}
    )


def test_history(gateway: RanaFileGateway, provider: Mock):
    history = History.model_validate(
        {"ref": "abc123", "created_at": "2021-01-01T00:00:00Z"}
    )
    provider.job_request.return_value = {
        "next": None,
        "limit": 10,
        "items": [history.model_dump()],
    }

    assert gateway.history("path", "main") == [history]

    provider.job_request.assert_called_once_with(
        "GET", "files/history", params={"path": "path", "ref": "main", "limit": 10}
    )
