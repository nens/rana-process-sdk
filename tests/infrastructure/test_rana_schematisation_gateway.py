from unittest.mock import Mock

from pytest import fixture

from rana_process_sdk import RanaApiProvider
from rana_process_sdk.domain import FileUpload
from rana_process_sdk.infrastructure import (
    PrefectRanaSchematisationGateway,
    RanaSchematisationGateway,
)


@fixture
def provider() -> Mock:
    return Mock(RanaApiProvider)


@fixture
def gateway(provider: Mock) -> PrefectRanaSchematisationGateway:
    return PrefectRanaSchematisationGateway(provider)


def test_create(gateway: RanaSchematisationGateway, provider: Mock):
    file_json = {
        "id": "path",
        "ref": "abc123",
        "last_modified": "2021-01-01T00:00:00Z",
        "schematisation_id": 123,
        "revision_id": None,
    }
    provider.job_request.return_value = file_json

    result = gateway.create("path")

    assert result == (FileUpload.model_validate(file_json), 123)
    provider.job_request.assert_called_once_with(
        "POST",
        "model-schematisations",
        params={"path": "path"},
    )
