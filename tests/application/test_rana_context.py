from collections.abc import Iterator
from pathlib import Path
from typing import Annotated
from unittest.mock import Mock, PropertyMock, call, patch
from uuid import UUID

from pydantic import BaseModel, SecretStr, ValidationError
from pytest import fixture, mark, raises

from rana_process_sdk import (
    Directory,
    DirectoryPickerWidget,
    File,
    RanaContext,
    RanaPath,
    RanaProcessParameters,
    Raster,
    StudyArea,
    ThreediSchematisation,
    UsingWidget,
    transfer_extension,
)
from rana_process_sdk.application.rana_context import (
    DirectoryOutput,
    FileOutput,
    expected_files,
)
from rana_process_sdk.application.widgets.file_picker import ExpectedFile
from rana_process_sdk.domain import FileStat, ProcessUserError, ThreediApiKey
from rana_process_sdk.infrastructure import (
    LizardRasterLayerGateway,
    RanaDatasetGateway,
    RanaRuntime,
    RanaSchematisationGateway,
    ThreediApiKeyGateway,
)

MODULE = "rana_process_sdk.application.rana_context"


class Output(RanaProcessParameters):
    number: int


class TestFileOutput(RanaProcessParameters):
    x: File


class FileOutputOptional(RanaProcessParameters):
    x: File | None = None


class TestDirectoryOutput(RanaProcessParameters):
    x: Directory


class TestDirectoryOutputWithExpectedFiles(RanaProcessParameters):
    x: Annotated[
        Directory,
        UsingWidget(
            DirectoryPickerWidget(
                expected_files={
                    "elevation.tif": ExpectedFile(
                        data_type="raster",
                        meta={"physical_quantity": "digital_elevation"},
                    ),
                }
            )
        ),
    ]


class DirectoryOutputOptional(RanaProcessParameters):
    x: Directory | None = None


class FileOutputOptionalNoDefault(RanaProcessParameters):
    x: File | None


class SchematisationOutput(RanaProcessParameters):
    x: ThreediSchematisation


class RasterOutput(RanaProcessParameters):
    x: Raster


class StudyAreaOutput(RanaProcessParameters):
    x: StudyArea


class MultipleFileOutput(RanaProcessParameters):
    x: File
    y: File


@fixture
def threedi_api_key_gateway() -> Iterator[Mock]:
    with patch.object(
        RanaContext,
        "_threedi_api_key_gateway",
        new_callable=PropertyMock(ThreediApiKeyGateway),
    ) as m:
        yield m


@fixture
def rana_schematisation_gateway() -> Iterator[Mock]:
    with patch.object(
        RanaContext,
        "_rana_schematisation_gateway",
        new_callable=PropertyMock(RanaSchematisationGateway),
    ) as m:
        yield m


@fixture
def rana_dataset_gateway() -> Iterator[Mock]:
    with patch.object(
        RanaContext,
        "_rana_dataset_gateway",
        new_callable=PropertyMock(RanaDatasetGateway),
    ) as m:
        yield m


@fixture
def lizard_raster_layer_gateway() -> Iterator[Mock]:
    with patch.object(
        RanaContext,
        "lizard_raster_layer_gateway",
        new_callable=PropertyMock(LizardRasterLayerGateway),
    ) as m:
        yield m


@fixture
def base_rana_context() -> RanaContext[Output]:
    return RanaContext[Output]()


@fixture
def rana_runtime() -> Iterator[Mock]:
    with patch.object(
        RanaContext, "_rana_runtime", new_callable=PropertyMock(RanaRuntime)
    ) as m:
        yield m


@fixture
def file_stat() -> FileStat:
    return FileStat.model_validate(
        {
            "id": "foo",
            "last_modified": "2021-01-01T00:00:00Z",
            "url": "http://example.com",
            "descriptor_id": "abc123",
        }
    )


@fixture
def job_working_dir(rana_runtime: Mock, tmp_path: Path) -> Path:
    rana_runtime.job_working_dir = tmp_path
    return tmp_path


@fixture
def file_base_rana_context() -> RanaContext[FileOutputOptional]:
    return RanaContext[FileOutputOptional](output_paths={"x": "a/foo.txt"})


@fixture
def schematisation_base_rana_context() -> RanaContext[SchematisationOutput]:
    return RanaContext[SchematisationOutput](output_paths={"x": "a/foo.txt"})


@fixture
def raster_base_rana_context() -> RanaContext[RasterOutput]:
    return RanaContext[RasterOutput](output_paths={"x": "a/foo.tiff"})


@fixture
def threedi_api_key() -> ThreediApiKey:
    return ThreediApiKey(
        prefix="Prefix",
        key=SecretStr("supersecret"),
        organisations=[UUID("8a831188-f7fa-4d04-90d0-7a104cd09963")],
    )


def test_base_rana_context_set_output(
    rana_runtime: Mock, base_rana_context: RanaContext[Output]
):
    base_rana_context.set_output(Output(number=3))

    rana_runtime.set_result.assert_called_once_with({"number": 3})


def test_base_rana_context_set_output_with_dict(
    rana_runtime: Mock, base_rana_context: RanaContext[Output]
):
    base_rana_context.set_output({"number": 3})

    rana_runtime.set_result.assert_called_once_with({"number": 3})


def test_base_rana_context_set_output_bad_dict(
    rana_runtime: Mock, base_rana_context: RanaContext[Output]
):
    with raises(ValidationError):
        base_rana_context.set_output({})


@fixture
def schematisation_rana_context() -> RanaContext[SchematisationOutput]:
    return RanaContext[SchematisationOutput](output_paths={"x": "a/foo.txt"})


def test_init_with_output_paths():
    actual = RanaContext[TestFileOutput](output_paths={"x": "foo"})
    assert actual.output_paths == {"x": "foo"}


def test_init_with_missing_output_path():
    with raises(ValidationError, match=".*output_paths must contain.*"):
        RanaContext[TestFileOutput](output_paths={})


def test_init_with_empty_output_path():
    with raises(ValidationError, match=".*output_paths must contain.*"):
        RanaContext[TestFileOutput](output_paths={"x": ""})


def test_init_with_extra_output_path():
    with raises(ValidationError, match=".*received unexpected output paths.*"):
        RanaContext[TestFileOutput](output_paths={"x": "bar", "y": "foo"})


def test_init_with_duplicate_output_paths():
    with raises(ValueError, match="Output paths parameters should be unique"):
        RanaContext[MultipleFileOutput](output_paths={"x": "dem.tif", "y": "dem.tif"})


def test_init_with_directory_path():
    with raises(ValidationError, match=".*is not a file.*"):
        RanaContext[TestFileOutput](output_paths={"x": "foo/"})


def test_init_directory_with_file_path():
    with raises(ValidationError, match=".*is not a directory.*"):
        RanaContext[TestDirectoryOutput](output_paths={"x": "foo"})


def test_init_with_missing_optional_output_path():
    actual = RanaContext[FileOutputOptional](output_paths={})
    assert actual.output_paths == {}


def test_init_with_empty_optional_output_path():
    actual = RanaContext[FileOutputOptional](output_paths={"x": ""})
    assert actual.output_paths == {}


@patch.object(
    RanaContext, "upload", return_value=RanaPath(id="a/foo.txt", ref="abc123")
)
def test_base_rana_context_set_output_with_file(
    upload: Mock,
    file_base_rana_context: RanaContext[FileOutputOptional],
    rana_runtime: Mock,
    tmp_path: Path,
):
    path = tmp_path / "local.txt"
    open(path, "a").close()

    file_base_rana_context.set_output({"x": path})

    upload.assert_called_once_with(path, "a/foo.txt", data_type=None, meta={})
    # the result contains the rana path (not the local one)
    rana_runtime.set_result.assert_called_once_with(
        {"x": {"variable_type": "rana_path", "id": "a/foo.txt", "ref": "abc123"}}
    )


def test_base_rana_context_set_output_with_file_does_not_exist(
    file_base_rana_context: RanaContext[FileOutputOptional],
):
    # the file was queried (it is in output_paths), but not created by the process:
    with raises(ValidationError):
        file_base_rana_context.set_output({"x": None})


@patch.object(RanaContext, "upload")
def test_base_rana_context_set_output_with_file_ignored(
    upload: Mock, rana_runtime: Mock
):
    # the file was not queried (it is not in output paths), but created by the process:

    file_context = RanaContext[FileOutputOptional]()
    file_context.set_output({"x": "a/foo.txt"})

    assert not upload.called
    # the result contains no path
    rana_runtime.set_result.assert_called_once_with({"x": None})


@patch.object(
    RanaContext,
    "upload_schematisation",
    return_value=RanaPath(id="a/foo.txt", ref="abc123"),
)
def test_base_rana_context_set_output_with_schematisation(
    upload_schematisation: Mock,
    schematisation_base_rana_context: RanaContext[SchematisationOutput],
    rana_runtime: Mock,
):
    schematisation_base_rana_context.set_output({"x": "schematisation_id"})

    upload_schematisation.assert_called_once_with("schematisation_id", "a/foo.txt")
    # the result contains the rana path (not the local one)
    rana_runtime.set_result.assert_called_once_with(
        {"x": {"variable_type": "rana_path", "id": "a/foo.txt", "ref": "abc123"}}
    )


@patch.object(
    RanaContext, "upload", return_value=RanaPath(id="a/foo.tiff", ref="abc123")
)
def test_base_rana_context_set_output_with_raster(
    upload: Mock,
    raster_base_rana_context: RanaContext[RasterOutput],
    rana_runtime: Mock,
    tmp_path: Path,
):
    path = tmp_path / "local.tiff"
    open(path, "a").close()
    raster_base_rana_context.set_output({"x": path})

    # the data_type should be set to "raster"
    upload.assert_called_once_with(path, "a/foo.tiff", data_type="raster", meta={})
    rana_runtime.set_result.assert_called_once()


@patch.object(
    RanaContext, "upload", return_value=RanaPath(id="a/foo.tiff", ref="abc123")
)
def test_base_rana_context_set_output_with_raster_override_meta(
    upload: Mock,
    raster_base_rana_context: RanaContext[RasterOutput],
    rana_runtime: Mock,
    tmp_path: Path,
):
    path = tmp_path / "local.tiff"
    open(path, "a").close()
    raster_base_rana_context.set_output(
        {"x": path}, meta_override={"x": {"physical_quantity": "digital_elevation"}}
    )

    # the data_type should be set to "raster"
    upload.assert_called_once_with(
        path,
        "a/foo.tiff",
        data_type="raster",
        meta={"physical_quantity": "digital_elevation"},
    )
    rana_runtime.set_result.assert_called_once()


@patch.object(
    RanaContext, "upload", return_value=RanaPath(id="a/foo.tiff", ref="abc123")
)
def test_base_rana_context_set_output_with_raster_override_data_type(
    upload: Mock,
    raster_base_rana_context: RanaContext[RasterOutput],
    rana_runtime: Mock,
    tmp_path: Path,
):
    path = tmp_path / "local.tiff"
    open(path, "a").close()
    raster_base_rana_context.set_output({"x": path}, data_type_override={"x": "vector"})

    # the data_type should be set to "raster"
    upload.assert_called_once_with(
        path,
        "a/foo.tiff",
        data_type="vector",
        meta={},
    )
    rana_runtime.set_result.assert_called_once()


@mark.parametrize(
    "model,expected",
    [
        (TestFileOutput, {"x": FileOutput(is_optional=False)}),
        (FileOutputOptional, {"x": FileOutput(is_optional=True)}),
        (TestDirectoryOutput, {"x": DirectoryOutput(is_optional=False)}),
        (DirectoryOutputOptional, {"x": DirectoryOutput(is_optional=True)}),
        (RasterOutput, {"x": FileOutput(is_optional=False, data_type="raster")}),
        (
            StudyAreaOutput,
            {
                "x": FileOutput(
                    is_optional=False,
                    data_type="vector",
                    meta_values={"feature_type_definition": "study_area"},
                )
            },
        ),
        (
            TestDirectoryOutputWithExpectedFiles,
            {
                "x": DirectoryOutput(
                    is_optional=False,
                    expected_files={
                        "elevation.tif": FileOutput(
                            is_optional=True,
                            data_type="raster",
                            meta_values={"physical_quantity": "digital_elevation"},
                        )
                    },
                ),
            },
        ),
    ],
)
def test_base_rana_context_expected_output_paths(
    model: type[BaseModel], expected: dict[str, TestFileOutput]
):
    assert RanaContext[model].expected_output_paths() == expected


def test_expected_files():
    path_picker = DirectoryPickerWidget(
        expected_files={
            "elevation.tif": ExpectedFile(
                data_type="raster", meta={"physical_quantity": "digital_elevation"}
            ),
            "study_area.gpkg": ExpectedFile(
                data_type="vector", meta={"feature_type_definition": ["study_area"]}
            ),
            "readme.md": ExpectedFile(),
            "other.tif": None,
        }
    )

    actual = expected_files(path_picker)

    assert actual == {
        "elevation.tif": FileOutput(
            is_optional=True,
            data_type="raster",
            meta_values={"physical_quantity": "digital_elevation"},
        ),
        "study_area.gpkg": FileOutput(
            is_optional=True,
            data_type="vector",
            meta_values={"feature_type_definition": ["study_area"]},
        ),
        "readme.md": FileOutput(is_optional=True, data_type=None, meta_values={}),
        "other.tif": FileOutput(is_optional=True, data_type=None, meta_values={}),
    }


def test_upload_schematisation(
    schematisation_rana_context: RanaContext[SchematisationOutput],
    rana_runtime: Mock,
    rana_schematisation_gateway: Mock,
):
    rana_path = "a/foo"
    schematisation_id = "schematisation_id"
    file = File(**{"id": "a/foo.txt", "last_modified": "2021-01-01T00:00:00Z"})
    rana_schematisation_gateway.upload.return_value = file

    actual = schematisation_rana_context.upload_schematisation(
        schematisation_id, rana_path
    )

    assert actual == RanaPath(id=rana_path, ref="main")
    rana_runtime.logger.info.assert_called_once_with(
        f"Writing schematisation to '{rana_path}'..."
    )
    rana_schematisation_gateway.upload.assert_called_once_with(
        rana_path, schematisation_id
    )


@patch.object(
    RanaContext, "upload_dir", return_value=RanaPath(id="a/foo/", ref="abc123")
)
def test_base_rana_context_set_output_directory(upload_dir: Mock, rana_runtime: Mock):
    file_base_rana_context = RanaContext[TestDirectoryOutput](
        output_paths={"x": "a/foo/"}
    )

    file_base_rana_context.set_output({"x": "local"})

    upload_dir.assert_called_once_with(Path("local"), "a/foo/", {})

    # the result contains the rana path (not the local one)
    rana_runtime.set_result.assert_called_once_with(
        {"x": {"variable_type": "rana_path", "id": "a/foo/", "ref": "abc123"}}
    )


@patch.object(
    RanaContext, "upload_dir", return_value=RanaPath(id="a/foo/", ref="abc123")
)
def test_base_rana_context_set_output_directory_with_expected_files(
    upload_dir: Mock, rana_runtime: Mock
):
    file_base_rana_context = RanaContext[TestDirectoryOutputWithExpectedFiles](
        output_paths={"x": "a/foo/"}
    )

    file_base_rana_context.set_output({"x": "local"})

    upload_dir.assert_called_once_with(
        Path("local"),
        "a/foo/",
        {
            "elevation.tif": FileOutput(
                is_optional=True,
                data_type="raster",
                meta_values={"physical_quantity": "digital_elevation"},
            )
        },
    )

    # the result contains the rana path (not the local one)
    rana_runtime.set_result.assert_called_once_with(
        {"x": {"variable_type": "rana_path", "id": "a/foo/", "ref": "abc123"}}
    )


@patch.object(RanaContext, "upload")
def test_base_rana_context_upload_dir(
    upload: Mock, job_working_dir: Path, base_rana_context: RanaContext
):
    local_path = job_working_dir / "dir"
    local_path.mkdir()
    (local_path / "foo.txt").touch()
    (local_path / "foo").mkdir()
    (local_path / "foo" / "bar.txt").touch()

    rana_path = "a/"

    actual = base_rana_context.upload_dir(local_path, rana_path)

    upload.assert_has_calls(
        [
            call(
                local_path=local_path / "foo.txt",
                rana_path="a/foo.txt",
                data_type=None,
                meta={},
            ),
            call(
                local_path=local_path / "foo" / "bar.txt",
                rana_path="a/foo/bar.txt",
                data_type=None,
                meta={},
            ),
        ]
    )

    assert actual == RanaPath(id="a/")


@patch.object(RanaContext, "upload")
def test_base_rana_context_upload_dir_with_expected_files(
    upload: Mock, rana_runtime: Mock, job_working_dir: Path, tmp_path: Path
):
    base_rana_context = RanaContext[TestDirectoryOutputWithExpectedFiles]()
    rana_runtime.job_working_dir = tmp_path
    local_path = job_working_dir / "dir"
    local_path.mkdir()
    (local_path / "foo.txt").touch()
    (local_path / "foo").mkdir()
    (local_path / "foo" / "bar.txt").touch()

    rana_path = "a/"

    expected_files: dict[str, FileOutput] = {
        "foo.txt": FileOutput(
            is_optional=True,
            data_type="raster",
            meta_values={"physical_quantity": "digital_elevation"},
        ),
    }

    actual = base_rana_context.upload_dir(local_path, rana_path, expected_files)

    upload.assert_has_calls(
        [
            call(
                local_path=local_path / "foo.txt",
                rana_path="a/foo.txt",
                data_type="raster",
                meta={"physical_quantity": "digital_elevation"},
            ),
            call(
                local_path=local_path / "foo" / "bar.txt",
                rana_path="a/foo/bar.txt",
                data_type=None,
                meta={},
            ),
        ]
    )

    assert actual == RanaPath(id="a/")


def test_file_output_optional_no_default_err():
    with raises(ValidationError, match=".*must have a default value*"):
        RanaContext[FileOutputOptionalNoDefault](output_paths={})


@mark.parametrize(
    "local_path,rana_path,expected",
    [
        # If not in ('rana_path'), extension is transferred from 'local_path'
        ("/tmp/foo.tif", "/some/dir/bar", "/some/dir/bar.tif"),
        # If same extension already present, nothing changes (case insensitive)
        ("/tmp/foo.tif", "/some/dir/bar.tif", "/some/dir/bar.tif"),
        ("/tmp/foo.tif", "/some/dir/bar.TIF", "/some/dir/bar.TIF"),
        # If another extension-like suffix is present, the extension is appended
        ("/tmp/foo.tif", "/some/dir/some.name", "/some/dir/some.name.tif"),
        # If the local path has no extension, nothing is done
        ("/tmp/foo", "/some/dir/bar.tif", "/some/dir/bar.tif"),
    ],
)
def test_transfer_extension(local_path: str, rana_path: str, expected: str):
    assert transfer_extension(Path(local_path), rana_path) == expected


def test_log_exception_process_user_error(
    base_rana_context: RanaContext, rana_runtime: Mock
):
    exception = ProcessUserError(title="Test exception", description="Test description")

    base_rana_context.log_exception(exception)

    rana_runtime.logger.error.assert_called_once_with(
        '{"title":"Process execution encountered an exception: ProcessUserError: Test exception","traceback":"NoneType: None\\n","error_type":"user","description":"Test description"}'
    )


def test_log_exception_process_internal_error(
    base_rana_context: RanaContext, rana_runtime: Mock
):
    exception = ValueError("Test exception")

    base_rana_context.log_exception(exception)

    rana_runtime.logger.error.assert_called_once_with(
        '{"title":"Process execution encountered an exception: ProcessInternalError(ValueError): Test exception","traceback":"NoneType: None\\n","error_type":"internal","description":"During process execution an internal exception occured. This should have not have happened and our support has been notified. When you want to reference this problem, please provide the ID of this job, or the project ID."}'
    )


def test_get_lizard_raster(
    base_rana_context: RanaContext, lizard_raster_layer_gateway: Mock
):
    actual = base_rana_context.get_lizard_raster("RasterId")

    assert actual is lizard_raster_layer_gateway.get.return_value

    lizard_raster_layer_gateway.get.assert_called_once_with("RasterId")


@patch(f"{MODULE}.get_settings")
@patch.object(
    RanaContext,
    "threedi_api_key",
    return_value=ThreediApiKey(
        prefix="a", key=SecretStr("supersecret"), organisations=[]
    ),
)
@patch(f"{MODULE}.ThreediApi")
def test_get_threedi_api(
    threedi_api: Mock,
    threedi_api_key: Mock,
    get_settings: Mock,
    base_rana_context: RanaContext,
):
    get_settings.return_value.threedi.host = "https://custom-3di-host"

    assert base_rana_context.threedi_api() is threedi_api.return_value

    get_settings.assert_called_once_with()
    threedi_api_key.assert_called_once_with()
    threedi_api.assert_called_once_with(
        config={
            "THREEDI_API_HOST": "https://custom-3di-host",
            "THREEDI_API_PERSONAL_API_TOKEN": "supersecret",
        }
    )
