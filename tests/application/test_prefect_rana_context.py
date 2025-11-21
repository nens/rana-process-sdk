from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch
from uuid import UUID

from pydantic import AnyHttpUrl, SecretStr, ValidationError
from pytest import fixture, mark, raises

from rana_process_sdk import (
    Directory,
    File,
    PrefectRanaContext,
    RanaPath,
    RanaProcessParameters,
    Raster,
    ThreediSchematisation,
    transfer_extension,
)
from rana_process_sdk.domain import (
    FileStat,
    FileUpload,
    History,
    ProcessUserError,
    ThreediApiKey,
)
from rana_process_sdk.domain.dataset import (
    DatasetFile,
    DatasetLayer,
    DatasetLink,
    RanaDataset,
    RanaDatasetLizardRaster,
    ResourceIdentifier,
)
from rana_process_sdk.domain.lizard_raster import LizardRaster
from rana_process_sdk.infrastructure import (
    SENTRY_BLOCK_NAME,
    LizardRasterLayerGateway,
    PrefectRanaRuntime,
    RanaDatasetGateway,
    RanaFileGateway,
    RanaSchematisationGateway,
    SentryBlock,
    ThreediApiKeyGateway,
)

MODULE = "rana_process_sdk.application.prefect_rana_context"


class Output(RanaProcessParameters):
    number: int


class FileOutput(RanaProcessParameters):
    x: File


class FileOutputOptional(RanaProcessParameters):
    x: File | None = None


class DirectoryOutput(RanaProcessParameters):
    x: Directory


class DirectoryOutputOptional(RanaProcessParameters):
    x: Directory | None = None


class FileOutputOptionalNoDefault(RanaProcessParameters):
    x: File | None


class SchematisationOutput(RanaProcessParameters):
    x: ThreediSchematisation


class RasterOutput(RanaProcessParameters):
    x: Raster


class MultipleFileOutput(RanaProcessParameters):
    x: File
    y: File


@fixture
def threedi_api_key_gateway() -> Iterator[Mock]:
    with patch.object(
        PrefectRanaContext,
        "_threedi_api_key_gateway",
        new_callable=PropertyMock(ThreediApiKeyGateway),
    ) as m:
        yield m


@fixture
def rana_schematisation_gateway() -> Iterator[Mock]:
    with patch.object(
        PrefectRanaContext,
        "_rana_schematisation_gateway",
        new_callable=PropertyMock(RanaSchematisationGateway),
    ) as m:
        yield m


@fixture
def rana_dataset_gateway() -> Iterator[Mock]:
    with patch.object(
        PrefectRanaContext,
        "_rana_dataset_gateway",
        new_callable=PropertyMock(RanaDatasetGateway),
    ) as m:
        yield m


@fixture
def lizard_raster_layer_gateway() -> Iterator[Mock]:
    with patch.object(
        PrefectRanaContext,
        "lizard_raster_layer_gateway",
        new_callable=PropertyMock(LizardRasterLayerGateway),
    ) as m:
        yield m


@fixture
def rana_context() -> PrefectRanaContext[Output]:
    return PrefectRanaContext[Output]()


@fixture
def prefect_rana_runtime() -> Iterator[Mock]:
    with patch(f"{MODULE}.PrefectRanaRuntime") as m:
        result = m.return_value
        result.threedi_api_key = None
        yield result


@fixture
def file_gateway() -> Iterator[Mock]:
    with patch.object(
        PrefectRanaContext, "_file_gateway", new_callable=PropertyMock(RanaFileGateway)
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
def job_working_dir(prefect_rana_runtime: Mock, tmp_path) -> Path:
    path = Path(tmp_path)
    prefect_rana_runtime.job_working_dir = path
    return path


@fixture
def sentry_block_load() -> Iterator[Mock]:
    with patch.object(SentryBlock, "load") as load:
        yield load


def fake_download_file(url: str, target: Path):
    target.write_text("foo")
    return target, 3


@fixture
def schematisation_rana_context() -> PrefectRanaContext[SchematisationOutput]:
    return PrefectRanaContext[SchematisationOutput](output_paths={"x": "a/foo.txt"})


def test_init_with_output_paths():
    actual = PrefectRanaContext[FileOutput](output_paths={"x": "foo"})
    assert actual.output_paths == {"x": "foo"}


def test_init_with_missing_output_path():
    with raises(ValidationError, match=".*output_paths must contain.*"):
        PrefectRanaContext[FileOutput](output_paths={})


def test_init_with_empty_output_path():
    with raises(ValidationError, match=".*output_paths must contain.*"):
        PrefectRanaContext[FileOutput](output_paths={"x": ""})


def test_init_with_extra_output_path():
    with raises(ValidationError, match=".*received unexpected output paths.*"):
        PrefectRanaContext[FileOutput](output_paths={"x": "bar", "y": "foo"})


def test_init_with_duplicate_output_paths():
    with raises(ValueError, match="Output paths parameters should be unique"):
        PrefectRanaContext[MultipleFileOutput](
            output_paths={"x": "dem.tif", "y": "dem.tif"}
        )


def test_init_with_directory_path():
    with raises(ValidationError, match=".*is not a file.*"):
        PrefectRanaContext[FileOutput](output_paths={"x": "foo/"})


def test_init_directory_with_file_path():
    with raises(ValidationError, match=".*is not a directory.*"):
        PrefectRanaContext[DirectoryOutput](output_paths={"x": "foo"})


def test_init_with_missing_optional_output_path():
    actual = PrefectRanaContext[FileOutputOptional](output_paths={})
    assert actual.output_paths == {}


def test_init_with_empty_optional_output_path():
    actual = PrefectRanaContext[FileOutputOptional](output_paths={"x": ""})
    assert actual.output_paths == {}


@mark.parametrize(
    "attr", ["job_id", "job_secret", "tenant_id", "job_working_dir", "logger"]
)
def test_prefect_context_attrs(
    prefect_rana_runtime: Mock, rana_context: PrefectRanaContext, attr: str
):
    assert getattr(rana_context, attr) is getattr(prefect_rana_runtime, attr)


def test_get_file_stat(
    file_gateway: Mock, rana_context: PrefectRanaContext, file_stat: FileStat
):
    file_gateway.stat.return_value = file_stat

    assert rana_context.get_file_stat(File(id="foo", ref="bar")) == file_stat

    file_gateway.stat.assert_called_once_with("foo", "bar")


def test_get_file_stat_none(
    file_gateway: Mock, rana_context: PrefectRanaContext, file_stat: FileStat
):
    file_gateway.stat.return_value = None

    with raises(ValueError, match="File at foo does not exist in Rana"):
        assert rana_context.get_file_stat(File(id="foo", ref="bar")) == file_stat


@patch(f"{MODULE}.download_file", side_effect=fake_download_file)
def test_download(
    download_file: Mock,
    file_gateway: Mock,
    job_working_dir: Path,
    rana_context: PrefectRanaContext,
    prefect_rana_runtime: Mock,
):
    rana_path = RanaPath(id="a/foo.txt")
    expected_target = job_working_dir / rana_path.id
    file_gateway.history.return_value = [
        History.model_validate({"ref": "abc123", "created_at": "2021-01-01T00:00:00Z"})
    ]

    assert rana_context.download(rana_path) == expected_target

    file_gateway.history.assert_called_once_with(rana_path.id, "main", 1)
    file_gateway.get_download_url.assert_called_once_with(
        rana_path.id, file_gateway.history.return_value[0].ref
    )
    prefect_rana_runtime.logger.info.assert_called_once_with(
        f"Reading file at path '{rana_path.id}' from ref '{file_gateway.history.return_value[0].ref}'..."
    )
    with expected_target.open() as f:
        assert f.read() == "foo"
    download_file.assert_called_once_with(
        str(file_gateway.get_download_url.return_value), expected_target
    )


@patch(f"{MODULE}.download_file", side_effect=fake_download_file)
def test_download_with_ref(
    download_file: Mock,
    file_gateway: Mock,
    job_working_dir: Path,
    rana_context: PrefectRanaContext,
    prefect_rana_runtime: Mock,
    file_stat: FileStat,
):
    rana_path = RanaPath(id="a/foo.txt", ref="abc123")
    expected_target = job_working_dir / rana_path.id

    assert rana_context.download(rana_path) == expected_target

    file_gateway.history.assert_called_once_with(rana_path.id, rana_path.ref, 1)
    file_gateway.get_download_url.assert_called_once_with(
        rana_path.id, file_gateway.history.return_value[0].ref
    )
    prefect_rana_runtime.logger.info.assert_called_once_with(
        f"Reading file at path '{rana_path.id}' from ref '{file_gateway.history.return_value[0].ref}'..."
    )
    with expected_target.open() as f:
        assert f.read() == "foo"
    download_file.assert_called_once_with(
        str(file_gateway.get_download_url.return_value), expected_target
    )


def test_download_no_history(file_gateway: Mock, rana_context: PrefectRanaContext):
    rana_path = RanaPath(id="a/foo.txt")
    file_gateway.history.return_value = []
    file_gateway.stat.return_value = file_stat

    with raises(ValueError):
        rana_context.download(rana_path)

    file_gateway.history.assert_called_once_with(rana_path.id, "main", 1)
    file_gateway.stat.assert_not_called()


def test_download_already_exists(
    job_working_dir: Path,
    file_gateway: RanaFileGateway,
    rana_context: PrefectRanaContext,
):
    rana_path = File(id="foo.txt")
    file_gateway.history.return_value = [
        History.model_validate({"ref": "abc123", "created_at": "2021-01-01T00:00:00Z"})
    ]
    (job_working_dir / rana_path.id).touch()

    with raises(FileExistsError):
        rana_context.download(rana_path)


@patch(f"{MODULE}.upload_file")
@patch(f"{MODULE}.transfer_extension")
def test_upload(
    transfer_extension: Mock,
    upload_file: Mock,
    file_gateway: Mock,
    job_working_dir: Path,
    rana_context: PrefectRanaContext,
):
    local_path = job_working_dir / "local.txt"
    local_path.touch()
    rana_path = "a/foo"
    file_gateway.upload_start.return_value = {
        "urls": ["http://example.com"],
        "other": "fields",
    }
    file_gateway.upload_complete.return_value = FileUpload.model_validate(
        {"id": "a/foo.txt", "last_modified": "2021-01-01T00:00:00Z", "ref": "abc123"}
    )
    transfer_extension.return_value = "a/foo.txt"

    actual = rana_context.upload(
        local_path,
        rana_path,
        data_type="DataType",
        description="foo",
        meta={"key": "value"},
    )

    assert actual == RanaPath(id="a/foo.txt", ref="abc123")

    file_gateway.upload_start.assert_called_once_with("a/foo.txt")
    upload_file.assert_called_once_with("http://example.com", local_path)
    file_gateway.upload_complete.assert_called_once_with(
        file_gateway.upload_start.return_value,
        data_type="DataType",
        description="foo",
        meta={"key": "value"},
    )
    transfer_extension.assert_called_once_with(local_path, rana_path)


def test_upload_does_not_exist(rana_context: PrefectRanaContext, job_working_dir: Path):
    with raises(FileNotFoundError):
        rana_context.upload(job_working_dir / "local.txt", Path("a/foo.txt"))


def test_upload_directory(rana_context: PrefectRanaContext, job_working_dir: Path):
    path = job_working_dir / "foo"
    path.mkdir()
    with raises(FileNotFoundError):
        rana_context.upload(path, Path("a/foo.txt"))


def test_context_manager(
    rana_context: PrefectRanaContext,
    prefect_rana_runtime: Mock,
    threedi_api_key_gateway: Mock,
    job_working_dir: Path,
):
    with rana_context:
        assert rana_context.job_working_dir.exists()
        prefect_rana_runtime.create_progress.assert_called_once_with()
        (prefect_rana_runtime.job_working_dir / "file").touch()
        (prefect_rana_runtime.job_working_dir / "directory").mkdir()

    prefect_rana_runtime.create_progress.assert_called_once()
    prefect_rana_runtime.set_progress.assert_called_once_with(100, "Completed", True)
    threedi_api_key_gateway.remove_assert_called_once_with()
    assert not prefect_rana_runtime.job_working_dir.exists()


def test_context_manager_threedi_no_api_key(
    rana_context: PrefectRanaContext,
    prefect_rana_runtime: Mock,
    threedi_api_key_gateway: Mock,
    job_working_dir: Path,
):
    with rana_context:
        assert rana_context.job_working_dir.exists()
        prefect_rana_runtime.create_progress.assert_called_once_with()
        (prefect_rana_runtime.job_working_dir / "file").touch()
        (prefect_rana_runtime.job_working_dir / "directory").mkdir()

    prefect_rana_runtime.create_progress.assert_called_once()
    prefect_rana_runtime.set_progress.assert_called_once_with(100, "Completed", True)
    threedi_api_key_gateway.remove_assert_called_once_with()
    assert not prefect_rana_runtime.job_working_dir.exists()


def test_context_manager_workdir_deleted(
    rana_context: PrefectRanaContext,
    prefect_rana_runtime: PrefectRanaRuntime,
    job_working_dir: Path,
):
    with rana_context:
        prefect_rana_runtime.job_working_dir.rmdir()


@fixture
def threedi_api_key() -> ThreediApiKey:
    return ThreediApiKey(
        prefix="Prefix",
        key=SecretStr("supersecret"),
        organisations=[UUID("8a831188-f7fa-4d04-90d0-7a104cd09963")],
    )


def test_get_threedi_api_key(
    threedi_api_key_gateway: Mock,
    rana_context: PrefectRanaContext,
    prefect_rana_runtime: PrefectRanaRuntime,
    threedi_api_key: ThreediApiKey,
):
    threedi_api_key_gateway.add.return_value = threedi_api_key

    result = rana_context.threedi_api_key()

    assert result == threedi_api_key
    assert prefect_rana_runtime.threedi_api_key == threedi_api_key
    threedi_api_key_gateway.add.assert_called_once_with()


# def test_remove_threedi_api_key(
#     threedi_api_key_gateway: Mock,
#     context: RanaContext,
#     prefect_rana_runtime: PrefectRanaRuntime,
#     threedi_api_key: ThreediApiKey,
# ):
#     prefect_rana_runtime.threedi_api_key = threedi_api_key
#
#     assert context.remove_threedi_api_key() is threedi_api_key_gateway.remove.return_value
#
#     threedi_api_key_gateway.remove.assert_called_once_with("Prefix")
#

# def test_remove_threedi_api_key_no_key(
#     threedi_api_key_gateway: Mock, context: RanaContext, prefect_rana_runtime: PrefectRanaRuntime
# ):
#     prefect_rana_runtime.threedi_api_key = None
#
#     assert not context.remove_threedi_api_key()
#
#     assert not threedi_api_key_gateway.remove.called
#


def test_context_manager_with_threedi_api_key(
    rana_context: PrefectRanaContext,
    prefect_rana_runtime: PrefectRanaRuntime,
    job_working_dir: Path,
    threedi_api_key_gateway: Mock,
):
    with rana_context:
        rana_context.threedi_api_key()

        assert threedi_api_key_gateway.add.called

    assert threedi_api_key_gateway.remove.called


@patch(f"{MODULE}.PrefectRanaRuntime")
def test_prefect_is_cached(PrefectRanaRuntime: Mock, rana_context: PrefectRanaContext):
    assert rana_context._rana_runtime is rana_context._rana_runtime

    PrefectRanaRuntime.assert_called_once_with()


def test_set_progress(rana_context: PrefectRanaContext, prefect_rana_runtime: Mock):
    rana_context.set_progress(100, "Job Done!")

    prefect_rana_runtime.set_progress.assert_called_once_with(100, "Job Done!", True)


def test_file_output_optional_no_default_err():
    with raises(ValidationError, match=".*must have a default value*"):
        PrefectRanaContext[FileOutputOptionalNoDefault](output_paths={})


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
    rana_context: PrefectRanaContext, prefect_rana_runtime: Mock
):
    exception = ProcessUserError(title="Test exception", description="Test description")

    rana_context.log_exception(exception)

    prefect_rana_runtime.logger.error.assert_called_once_with(
        '{"title":"Process execution encountered an exception: ProcessUserError: Test exception","traceback":"NoneType: None\\n","error_type":"user","description":"Test description"}'
    )


def test_log_exception_process_internal_error(
    rana_context: PrefectRanaContext, prefect_rana_runtime: Mock
):
    exception = ValueError("Test exception")

    rana_context.log_exception(exception)

    prefect_rana_runtime.logger.error.assert_called_once_with(
        '{"title":"Process execution encountered an exception: ProcessInternalError(ValueError): Test exception","traceback":"NoneType: None\\n","error_type":"internal","description":"During process execution an internal exception occured. This should have not have happened and our support has been notified. When you want to reference this problem, please provide the ID of this job, or the project ID."}'
    )


def test_get_lizard_raster_dataset(
    rana_context: PrefectRanaContext,
    lizard_raster_layer_gateway: Mock,
    rana_dataset_gateway: Mock,
):
    lizard_raster_layer_gateway.namespace = AnyHttpUrl(
        "https://example.com/lizard_raster"
    )
    dataset = RanaDataset(
        id="DatasetId",
        title="Test Dataset",
        resource_identifier=[
            ResourceIdentifier(
                code="id-1", link=AnyHttpUrl("https://example.com/lizard_raster")
            )
        ],
    )
    rana_dataset_gateway.get.return_value = dataset
    lizard_raster_layer_gateway.get.return_value = Mock(LizardRaster)

    actual = rana_context.get_lizard_raster_dataset("DatasetId")

    assert actual == RanaDatasetLizardRaster(
        **dataset.model_dump(exclude_none=True),
        lizard_raster=lizard_raster_layer_gateway.get.return_value,
    )
    rana_dataset_gateway.get.assert_called_once_with("DatasetId")
    lizard_raster_layer_gateway.get.assert_called_once_with(
        dataset.get_id_for_namespace(lizard_raster_layer_gateway.namespace)
    )


def test_get_lizard_raster_dataset_no_lizard_raster(
    rana_context: PrefectRanaContext,
    lizard_raster_layer_gateway: Mock,
    rana_dataset_gateway: Mock,
):
    dataset = rana_dataset_gateway.get.return_value
    dataset.get_id_for_namespace.return_value = None

    with raises(ProcessUserError):
        rana_context.get_lizard_raster_dataset("DatasetId")

    assert not lizard_raster_layer_gateway.get.called


def test_get_lizard_raster(
    rana_context: PrefectRanaContext, lizard_raster_layer_gateway: Mock
):
    actual = rana_context.get_lizard_raster("RasterId")

    assert actual is lizard_raster_layer_gateway.get.return_value

    lizard_raster_layer_gateway.get.assert_called_once_with("RasterId")


def test_setup_logger(
    rana_context: PrefectRanaContext,
    sentry_block_load: Mock,
    prefect_rana_runtime: Mock,
):
    rana_context.setup_logger()

    sentry_block_load.assert_called_once_with(name=SENTRY_BLOCK_NAME)
    sentry_block_load.return_value.init.assert_called_once()
    sentry_block_load.return_value.set_tags_and_context.assert_called_once_with(
        prefect_rana_runtime._flow_run
    )


def test_setup_logger_err(rana_context: PrefectRanaContext, sentry_block_load: Mock):
    sentry_block_load.side_effect = ValueError("No Sentry configured")

    rana_context.setup_logger()

    sentry_block_load.assert_called_once_with(name=SENTRY_BLOCK_NAME)


def test_get_dataset(
    rana_context: PrefectRanaContext,
    rana_dataset_gateway: Mock,
):
    rana_dataset_gateway.get.return_value = RanaDataset(
        id="DatasetId",
        title="Test Dataset",
        resource_identifier=[],
        links=[
            DatasetLink(
                protocol="OGC:WCS",
                url=AnyHttpUrl("https://some/wcs?version=2.0.1"),
                layers=[
                    DatasetLayer(id="dtm_05m", title=None),
                ],
            ),
            DatasetLink(
                protocol="OGC:WFS",
                url=AnyHttpUrl("https://some/wfs?version=2.0.1"),
                layers=[
                    DatasetLayer(id="buildings", title=None),
                ],
            ),
        ],
    )

    rana_dataset_gateway.get_data_links.return_value = [
        DatasetLink(
            protocol="INSPIRE Atom",
            title="Download service",
            files=[
                DatasetFile(
                    href=AnyHttpUrl("https://some/file.tif"),
                    size=123456,
                )
            ],
        ),
    ]

    actual = rana_context.get_dataset("DatasetId")

    assert actual.id == "DatasetId"
    assert actual.title == "Test Dataset"
    assert len(actual.links) == 3
    assert actual.links[0].protocol == "INSPIRE Atom"
    assert actual.links[1].protocol == "OGC:WCS"
    assert actual.links[2].protocol == "OGC:WFS"

    rana_dataset_gateway.get.assert_called_once_with("DatasetId")
    rana_dataset_gateway.get_data_links.assert_called_once_with("DatasetId")
