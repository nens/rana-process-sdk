from http import HTTPStatus
from unittest.mock import Mock
from uuid import uuid4

from pydantic import AnyHttpUrl
from pytest import fixture, raises

from rana_process_sdk.domain import DoesNotExist
from rana_process_sdk.infrastructure import (
    ApiException,
    LizardApiProvider,
    LizardRasterLayerGateway,
)


@fixture
def provider() -> Mock:
    return Mock(LizardApiProvider)


@fixture
def gateway(provider: Mock) -> LizardRasterLayerGateway:
    return LizardRasterLayerGateway(provider)


def test_gateway_namespace(gateway: LizardRasterLayerGateway, provider: Mock):
    provider._url = "https://demo.lizard.net/"
    assert gateway.namespace == AnyHttpUrl("https://demo.lizard.net/api/v4/rasters")


def test_get_raster(gateway: LizardRasterLayerGateway, provider: Mock):
    raster_id = uuid4()
    provider.request.return_value = {
        "uuid": str(raster_id),
        "pixelsize_x": 2.0,
        "pixelsize_y": 10.0,
        "projection": "EPSG:4326",
    }

    raster = gateway.get(str(raster_id))

    assert raster.id == raster_id
    assert raster.pixelsize_x == 2.0
    assert raster.pixelsize_y == 10.0
    assert raster.projection == "EPSG:4326"
    provider.request.assert_called_once_with("GET", "api/v4/rasters/" + str(raster_id))


def test_get_raster_not_found(gateway: LizardRasterLayerGateway, provider: Mock):
    provider.request.side_effect = ApiException(obj={}, status=HTTPStatus.NOT_FOUND)
    raster_id = "test-raster"

    with raises(DoesNotExist):
        gateway.get(raster_id)


def test_get_geotiff_async(gateway: LizardRasterLayerGateway, provider: Mock):
    provider.request.return_value = {"task_id": "12345"}
    bbox = (1.0, 2.0, 3.0, 4.0)
    epsg_code = 4326
    pixel_size = 10.0
    raster_id = "test-raster"

    task_id = gateway.get_async_geotiff(raster_id, bbox, epsg_code, pixel_size)

    assert task_id == "12345"
    provider.request.assert_called_once_with(
        "GET",
        "api/v4/rasters/test-raster/data",
        params={
            "bbox": "1.0,2.0,3.0,4.0",
            "format": "geotiff",
            "projection": "EPSG:4326",
            "pixel_size": 10.0,
            "async": True,
        },
    )


def test_get_geotiff_async_not_found(gateway: LizardRasterLayerGateway, provider: Mock):
    provider.request.side_effect = ApiException(obj={}, status=HTTPStatus.NOT_FOUND)

    bbox = (1.0, 2.0, 3.0, 4.0)
    epsg_code = 4326
    pixel_size = 10.0
    raster_id = "test-raster"

    with raises(DoesNotExist):
        gateway.get_async_geotiff(raster_id, bbox, epsg_code, pixel_size)


def test_get_geotiff_async_other_exception(
    gateway: LizardRasterLayerGateway, provider: Mock
):
    provider.request.side_effect = ApiException(
        obj={}, status=HTTPStatus.INTERNAL_SERVER_ERROR
    )

    bbox = (1.0, 2.0, 3.0, 4.0)
    epsg_code = 4326
    pixel_size = 10.0
    raster_id = "test-raster"

    with raises(ApiException):
        gateway.get_async_geotiff(raster_id, bbox, epsg_code, pixel_size)


def test_get_task(gateway: LizardRasterLayerGateway, provider: Mock):
    task_id = uuid4()
    provider.request.return_value = {
        "uuid": str(task_id),
        "status": "SUCCESS",
        "result": "https://example.com/raster.tif",
        "detail": "some_detail",
    }
    task = gateway.get_task(str(task_id))
    assert task.id == task_id
    assert task.status == "SUCCESS"
    assert task.result == "https://example.com/raster.tif"
    assert task.detail == "some_detail"
