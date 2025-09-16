from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

from pydantic import ValidationError
from pytest import fixture, raises

from rana_process_sdk import (
    Directory,
    File,
    PrefectRanaContext,
    RanaContext,
    RanaProcessParameters,
    Raster,
    ThreediSchematisation,
)
from rana_process_sdk.domain import FileStat
from rana_process_sdk.infrastructure import (
    LizardRasterLayerGateway,
    RanaDatasetGateway,
    RanaFileGateway,
    RanaRuntime,
    RanaSchematisationGateway,
    ThreediApiKeyGateway,
)

MODULE = "rana_process_sdk.application.local_test_rana_context"


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
def base_rana_context() -> RanaContext[Output]:
    return RanaContext[Output]()


@fixture
def rana_runtime() -> Iterator[Mock]:
    with patch.object(
        RanaContext, "_rana_runtime", new_callable=PropertyMock(RanaRuntime)
    ) as m:
        yield m


@fixture
def rana_context() -> PrefectRanaContext[Output]:
    return PrefectRanaContext[Output]()


@fixture
def local_test_rana_runtime() -> Iterator[Mock]:
    with patch(f"{MODULE}.LocalTestRanaRuntime") as m:
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
def job_working_dir(local_test_rana_runtime: Mock, tmp_path) -> Path:
    path = Path(tmp_path)
    local_test_rana_runtime.job_working_dir = path
    return path


def fake_download_file(url: str, target: Path):
    target.write_text("foo")
    return target, 3


@fixture
def file_base_rana_context() -> RanaContext[FileOutputOptional]:
    return RanaContext[FileOutputOptional](output_paths={"x": "a/foo.txt"})


@fixture
def schematisation_base_rana_context() -> RanaContext[SchematisationOutput]:
    return RanaContext[SchematisationOutput](output_paths={"x": "a/foo.txt"})


@fixture
def raster_base_rana_context() -> RanaContext[RasterOutput]:
    return RanaContext[RasterOutput](output_paths={"x": "a/foo.tiff"})


def test_base_rana_context_set_output(
    local_test_rana_runtime: Mock,
    base_rana_context: RanaContext[Output],
    rana_runtime: Mock,
):
    base_rana_context.set_output(Output(number=3))

    rana_runtime.set_result.assert_called_once_with({"number": 3})


def test_base_rana_context_set_output_with_dict(
    local_test_rana_runtime: Mock,
    base_rana_context: RanaContext[Output],
    rana_runtime: Mock,
):
    base_rana_context.set_output({"number": 3})

    rana_runtime.set_result.assert_called_once_with({"number": 3})


def test_base_rana_context_set_output_bad_dict(
    local_test_rana_runtime: Mock, base_rana_context: RanaContext[Output]
):
    with raises(ValidationError):
        base_rana_context.set_output({})


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


def test_download(
    file_gateway: Mock,
    job_working_dir: Path,
    rana_context: PrefectRanaContext,
    local_test_rana_runtime: Mock,
    file_stat: FileStat,
):
    pass


def test_download_with_ref(
    file_gateway: Mock,
    job_working_dir: Path,
    rana_context: PrefectRanaContext,
    local_test_rana_runtime: Mock,
    file_stat: FileStat,
):
    pass


def test_download_already_exists(
    job_working_dir: Path,
    file_gateway: RanaFileGateway,
    rana_context: PrefectRanaContext,
):
    pass


def test_upload(
    file_gateway: Mock,
    job_working_dir: Path,
    rana_context: PrefectRanaContext,
):
    pass


def test_upload_does_not_exist(rana_context: PrefectRanaContext, job_working_dir: Path):
    pass


def test_upload_directory(rana_context: PrefectRanaContext, job_working_dir: Path):
    pass
