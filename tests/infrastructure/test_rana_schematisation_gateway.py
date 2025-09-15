from unittest.mock import Mock

from pytest import fixture

from rana_process_sdk import RanaApiProvider
from rana_process_sdk.domain import FileUpload
from rana_process_sdk.infrastructure import (
    PrefectRanaSchematisationGateway,
    RanaSchematisationGateway,
)

MODULE = "rana_process_sdk.infrastructure.rana_files_gateway"


@fixture
def provider() -> Mock:
    return Mock(RanaApiProvider)


@fixture
def gateway(provider: Mock) -> PrefectRanaSchematisationGateway:
    return PrefectRanaSchematisationGateway(provider)


def test_upload(gateway: RanaSchematisationGateway, provider: Mock):
    schematisation_id = "abc123"
    file_json = {"id": "path", "ref": "abc123", "last_modified": "2021-01-01T00:00:00Z"}
    provider.job_request.return_value = file_json

    result = gateway.upload("path", schematisation_id)

    assert result == FileUpload.model_validate(file_json)
    provider.job_request.assert_called_once_with(
        "POST",
        "threedi-schematisations",
        params={"path": "path", "schematisation_id": "abc123", "branch": "main"},
    )
