from pathlib import Path
from unittest.mock import Mock, patch
from zipfile import ZipFile

from pytest import fixture
from threedi_api_client.openapi import FileReadOnly, RevisionRaster, Upload, V3Api

from rana_process_sdk.application.upload_schematisation import (
    UPLOAD_TIMEOUT,
    md5,
    upload_raster,
    upload_sqlite,
)

MODULE = "rana_process_sdk.application.upload_schematisation"


@fixture
def local_file(tmp_path) -> Path:
    file_path = Path(tmp_path) / "test_file.txt"
    file_path.write_text("This is a test file.")
    return file_path


@fixture
def threedi_api() -> Mock:
    return Mock(V3Api)


def test_md5(local_file: Path):
    assert md5(local_file) == "3de8f8b0dc94b8c2230fab9ec0ba0506"


def test_md5_chunking(tmp_path):
    # Create a large file to test chunking
    large_file_path = Path(tmp_path) / "large_test_file.txt"
    with large_file_path.open("wb") as f:
        f.write(b"A" * 10_000)  # 10 kB

    assert md5(large_file_path) == "0f53217fc7c8e7f89e8a8558e64a7083"


@patch(f"{MODULE}.upload_file")
def test_upload_sqlite(upload_file: Mock, threedi_api: Mock, local_file: Path):
    expected_zip_path = local_file.with_suffix(".zip")

    threedi_api.schematisations_revisions_sqlite_upload.return_value = Mock(
        Upload, put_url="http://example.com/upload"
    )

    upload_sqlite(threedi_api, 1, 100, local_file)

    # Check that the API was called with the correct parameters
    threedi_api.schematisations_revisions_sqlite_upload.assert_called_once_with(
        id=100,
        schematisation_pk=1,
        data={"filename": "test_file.zip"},
        _request_timeout=10,
    )
    upload_file.assert_called_once_with(
        "http://example.com/upload",
        expected_zip_path,
        timeout=UPLOAD_TIMEOUT,
    )

    # test the zip file was created correctly
    with ZipFile(expected_zip_path, "r") as zip_ref:
        assert zip_ref.namelist() == ["test_file.txt"]
        with zip_ref.open("test_file.txt") as f:
            assert f.read() == b"This is a test file."


@patch(f"{MODULE}.upload_file")
@patch(f"{MODULE}.md5", return_value="dummy_md5")
def test_upload_raster(
    md5: Mock, upload_file: Mock, threedi_api: Mock, local_file: Path
):
    threedi_api.schematisations_revisions_rasters_create.return_value = Mock(
        RevisionRaster, file=None
    )
    threedi_api.schematisations_revisions_rasters_upload.return_value = Mock(
        Upload, put_url="http://example.com/upload"
    )

    upload_raster(threedi_api, 100, 1, "test_raster", local_file)

    threedi_api.schematisations_revisions_rasters_create.assert_called_once_with(
        100,
        1,
        {"name": "test_file.txt", "type": "test_raster", "md5sum": "dummy_md5"},
        _request_timeout=10,
    )
    threedi_api.schematisations_revisions_rasters_upload.assert_called_once_with(
        threedi_api.schematisations_revisions_rasters_create.return_value.id,
        100,
        1,
        {"filename": "test_file.txt"},
        _request_timeout=10,
    )
    upload_file.assert_called_once_with(
        "http://example.com/upload",
        local_file,
        timeout=UPLOAD_TIMEOUT,
    )
    md5.assert_called_once_with(local_file)


@patch(f"{MODULE}.md5", return_value="dummy_md5")
def test_upload_raster_already_exists(md5: Mock, threedi_api: Mock, local_file: Path):
    threedi_api.schematisations_revisions_rasters_create.return_value = Mock(
        RevisionRaster, file=Mock(FileReadOnly, state="uploaded"), id=123
    )

    upload_raster(threedi_api, 100, 1, "test_raster", local_file)

    threedi_api.schematisations_revisions_rasters_create.assert_called_once_with(
        100,
        1,
        {"name": "test_file.txt", "type": "test_raster", "md5sum": "dummy_md5"},
        _request_timeout=10,
    )
    threedi_api.schematisations_revisions_rasters_upload.assert_not_called()
    md5.assert_called_once_with(local_file)
