from pathlib import Path
from unittest.mock import Mock, call, patch
from zipfile import ZipFile

from pytest import fixture, raises
from threedi_api_client.openapi import (
    FileReadOnly,
    Revision,
    RevisionRaster,
    Upload,
    V3Api,
)

from rana_process_sdk.application.upload_schematisation import (
    UPLOAD_TIMEOUT,
    commit_revision,
    md5,
    upload_raster,
    upload_schematisation,
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
        _request_timeout=60,
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
        _request_timeout=60,
    )
    threedi_api.schematisations_revisions_rasters_upload.assert_called_once_with(
        threedi_api.schematisations_revisions_rasters_create.return_value.id,
        100,
        1,
        {"filename": "test_file.txt"},
        _request_timeout=60,
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
        _request_timeout=60,
    )
    threedi_api.schematisations_revisions_rasters_upload.assert_not_called()
    md5.assert_called_once_with(local_file)


def test_commit_no_wait(threedi_api: Mock):
    # Simulate that all files are already uploaded
    mock_revision = Mock(
        Revision,
        sqlite=Mock(file=Mock(state="uploaded")),
        rasters=[Mock(file=Mock(state="uploaded"))],
    )
    threedi_api.schematisations_revisions_read.return_value = mock_revision

    commit_revision(threedi_api, 100, 1, "Commit message")

    threedi_api.schematisations_revisions_read.assert_called_once_with(
        100, 1, _request_timeout=60
    )
    threedi_api.schematisations_revisions_commit.assert_called_once_with(
        100, 1, {"commit_message": "Commit message"}, _request_timeout=60
    )


@patch(f"{MODULE}.time.sleep")
def test_commit_wait_once(mock_sleep: Mock, threedi_api: Mock):
    # Simulate that the first call returns 'created' and the second call returns 'uploaded'
    mock_revision_created = Mock(
        Revision,
        sqlite=Mock(file=Mock(state="uploaded")),
        rasters=[Mock(file=Mock(state="created"))],
    )
    mock_revision_uploaded = Mock(
        Revision,
        sqlite=Mock(file=Mock(state="uploaded")),
        rasters=[Mock(file=Mock(state="uploaded"))],
    )
    threedi_api.schematisations_revisions_read.side_effect = [
        mock_revision_created,
        mock_revision_uploaded,
    ]

    commit_revision(threedi_api, 100, 1, "Commit message")

    assert threedi_api.schematisations_revisions_read.call_count == 2
    mock_sleep.assert_called_once_with(0.5)
    threedi_api.schematisations_revisions_commit.assert_called_once()


@patch(f"{MODULE}.time.sleep")
def test_commit_timeout(mock_sleep: Mock, threedi_api: Mock):
    mock_revision_created = Mock(
        Revision,
        sqlite=Mock(file=Mock(state="created")),
        rasters=[Mock(file=Mock(state="created"))],
    )
    threedi_api.schematisations_revisions_read.return_value = mock_revision_created

    with raises(RuntimeError):
        commit_revision(threedi_api, 100, 1, "Commit message")

    assert threedi_api.schematisations_revisions_read.call_count == 8
    assert mock_sleep.call_count == 8
    threedi_api.schematisations_revisions_commit.assert_not_called()


def test_commit_unexpected_state(threedi_api: Mock):
    mock_revision_unexpected = Mock(
        Revision,
        sqlite=Mock(file=Mock(state="uploaded")),
        rasters=[Mock(file=Mock(state="failed"))],
    )
    threedi_api.schematisations_revisions_read.return_value = mock_revision_unexpected

    with raises(RuntimeError):
        commit_revision(threedi_api, 100, 1, "Commit message")

    threedi_api.schematisations_revisions_commit.assert_not_called()


@patch(f"{MODULE}.upload_sqlite")
@patch(f"{MODULE}.upload_raster")
@patch(f"{MODULE}.commit_revision")
def test_upload_schematisation(
    commit_revision_mock: Mock,
    upload_raster_mock: Mock,
    upload_sqlite_mock: Mock,
    threedi_api: Mock,
    tmp_path: Path,
):
    sqlite_file = tmp_path / "test_schematisation.gpkg"
    sqlite_file.write_text("This is a test schematisation.")
    dem_file = tmp_path / "dem.tif"  # with a 'regular' name, type is "dem_file"
    dem_file.write_text("This is a test dem.")
    friction_file = (
        tmp_path / "friction.tif"
    )  # irregular name, type is "frict_coef_file"
    friction_file.write_text("This is a test friction.")

    # Mock the API responses
    threedi_api.schematisations_revisions_create.return_value = Mock(Revision, id=100)

    upload_schematisation(threedi_api, 1, tmp_path, "Commit message")

    threedi_api.schematisations_revisions_create.assert_called_once_with(
        1, data={"empty": True}, _request_timeout=60
    )

    upload_sqlite_mock.assert_called_once_with(
        threedi_api=threedi_api,
        schematisation_id=1,
        revision_id=100,
        sqlite_path=sqlite_file,
    )

    assert upload_raster_mock.call_count == 2
    upload_raster_mock.assert_has_calls(
        [
            call(
                threedi_api=threedi_api,
                schematisation_id=1,
                revision_id=100,
                raster_type="dem_file",
                raster_path=dem_file,
            ),
            call(
                threedi_api=threedi_api,
                schematisation_id=1,
                revision_id=100,
                raster_type="frict_coef_file",
                raster_path=friction_file,
            ),
        ]
    )

    commit_revision_mock.assert_called_once_with(
        threedi_api=threedi_api,
        revision_id=100,
        schematisation_id=1,
        commit_message="Commit message",
    )


def test_upload_schematisation_no_sqlite(tmp_path: Path, threedi_api: Mock):
    # Create a directory without a .gpkg file
    (tmp_path / "dem.tif").write_text("This is a test dem.")

    with raises(RuntimeError, match="The geopackage failed to generate"):
        upload_schematisation(threedi_api, 1, tmp_path, "Commit message")
