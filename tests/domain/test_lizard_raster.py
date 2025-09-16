from uuid import uuid4

from pytest import fixture

from rana_process_sdk.domain import LizardRaster


@fixture
def lizard_raster() -> LizardRaster:
    return LizardRaster(
        id=uuid4(), pixelsize_x=2.0, pixelsize_y=-10.0, projection="EPSG:4326"
    )


@fixture
def lizard_raster_empty() -> LizardRaster:
    return LizardRaster(id=uuid4(), pixelsize_x=None, pixelsize_y=None, projection=None)


def test_resolution(lizard_raster: LizardRaster):
    assert lizard_raster.resolution == 2.0


def test_resolution_empty(lizard_raster_empty: LizardRaster):
    assert lizard_raster_empty.resolution is None


def test_epsg_code(lizard_raster: LizardRaster):
    assert lizard_raster.epsg_code == 4326


def test_epsg_code_empty(lizard_raster_empty: LizardRaster):
    assert lizard_raster_empty.epsg_code is None
