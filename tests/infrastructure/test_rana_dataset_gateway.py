from unittest.mock import Mock

from pydantic import AnyHttpUrl
from pytest import fixture, raises

from rana_process_sdk.domain import DoesNotExist, Json
from rana_process_sdk.domain.dataset import (
    DatasetLayer,
    DatasetLink,
    RanaDataset,
    ResourceIdentifier,
)
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
        "link": [
            {
                "protocol": "OGC:WCS",
                "urlObject": {"default": "https://some/wcs?version=2.0.1"},
                "nameObject": {"default": "dtm_05m"},
            },
            {
                "protocol": "INSPIRE Atom",
                "urlObject": {},
                "nameObject": {"default": "Download service"},
            },
        ],
    }


@fixture
def rana_dataset_data_links_response() -> list[Json]:
    return [
        {
            "protocol": "OGC:WCS",
            "url": "https://some/wcs?version=2.0.1",
            "layers": [{"id": "dtm_05m", "title": "AHN (DTM 0.5m)"}],
        },
        {
            "protocol": "INSPIRE Atom",
            "title": "Download service",
            "files": [
                {
                    "href": "https://some/file.tif",
                    "size": 123456,
                    "title": None,
                    "envelope": [5.0, 51.0, 6.0, 52.0],
                    "time": "2023-01-01T00:00:00Z",
                }
            ],
        },
    ]


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
        links=[
            DatasetLink(
                protocol="OGC:WCS",
                url=AnyHttpUrl("https://some/wcs?version=2.0.1"),
                layers=[DatasetLayer(id="dtm_05m", title=None)],
            ),
        ],
    )
    provider.job_request.assert_called_once_with("GET", "datasets/DatasetId")


def test_get_not_found(gateway: RanaDatasetGateway, provider: Mock):
    provider.job_request.return_value = None

    with raises(DoesNotExist):
        gateway.get("DatasetId")

    provider.job_request.assert_called_once_with("GET", "datasets/DatasetId")


def test_get_data_links(
    gateway: RanaDatasetGateway, provider: Mock, rana_dataset_data_links_response: Json
):
    provider.job_request.return_value = rana_dataset_data_links_response

    actual = gateway.get_data_links("DatasetId")

    assert actual == [
        DatasetLink(
            protocol="OGC:WCS",
            url=AnyHttpUrl("https://some/wcs?version=2.0.1"),
            layers=[DatasetLayer(id="dtm_05m", title="AHN (DTM 0.5m)")],
        ),
        DatasetLink(
            protocol="INSPIRE Atom",
            title="Download service",
            files=[
                {
                    "href": AnyHttpUrl("https://some/file.tif"),
                    "size": 123456,
                    "title": None,
                    "envelope": (5.0, 51.0, 6.0, 52.0),
                    "time": "2023-01-01T00:00:00+00:00",
                }
            ],
        ),
    ]
    provider.job_request.assert_called_once_with("GET", "datasets/DatasetId/data-links")


def test_get_data_links_not_found(gateway: RanaDatasetGateway, provider: Mock):
    provider.job_request.return_value = None

    with raises(DoesNotExist):
        gateway.get_data_links("DatasetId")

    provider.job_request.assert_called_once_with("GET", "datasets/DatasetId/data-links")
