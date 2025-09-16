from unittest.mock import Mock

from pydantic import AnyHttpUrl
from pytest import fixture, raises

from rana_process_sdk.domain import DoesNotExist, Json
from rana_process_sdk.domain.dataset import RanaDataset, ResourceIdentifier
from rana_process_sdk.infrastructure import RanaApiProvider, RanaDatasetGateway


@fixture
def provider() -> Mock:
    return Mock(RanaApiProvider)


@fixture
def gateway(provider: Mock) -> RanaDatasetGateway:
    return RanaDatasetGateway(provider)


@fixture
def rana_dataset_response() -> Json:
    return {
        "id": "DatasetId",
        "resourceTitleObject": {
            "default": "Titel",
        },
        "resourceIdentifier": [{"code": "LizardId", "link": "https://lizard/rasters"}],
    }


def test_get(gateway: RanaDatasetGateway, provider: Mock, rana_dataset_response: Json):
    provider.job_request.return_value = rana_dataset_response

    actual = gateway.get("DatasetId")

    assert actual == RanaDataset(
        id="DatasetId",
        title="Titel",
        resource_identifier=[
            ResourceIdentifier(
                code="LizardId", link=AnyHttpUrl("https://lizard/rasters")
            )
        ],
    )
    provider.job_request.assert_called_once_with("GET", "datasets/DatasetId")


def test_get_not_found(gateway: RanaDatasetGateway, provider: Mock):
    provider.job_request.return_value = None

    with raises(DoesNotExist):
        gateway.get("DatasetId")

    provider.job_request.assert_called_once_with("GET", "datasets/DatasetId")
