from pathlib import Path
from unittest.mock import Mock

from pytest import fixture

from rana_process_sdk import (
    LocalTestRanaContext,
    LocalTestRanaRuntime,
    RanaPath,
)
from rana_process_sdk.domain import RanaDataset
from rana_process_sdk.settings import LocalTestSettings


@fixture
def local_test_settings() -> Mock:
    result = Mock(LocalTestSettings)
    result.datasets = {"dataset-1": Mock(RanaDataset, title="Foo")}
    return result


@fixture
def local_runtime(tmp_path: Path, local_test_settings: LocalTestSettings) -> Mock:
    result = Mock(spec=LocalTestRanaRuntime)
    result.job_working_dir = tmp_path
    result.settings = local_test_settings
    return result


@fixture
def local_test_rana_context(local_runtime: Mock) -> LocalTestRanaContext:
    LocalTestRanaContext.runtime_override = local_runtime
    result = LocalTestRanaContext()
    return result


def test_get_dataset(
    local_test_rana_context: LocalTestRanaContext,
    local_test_settings: LocalTestSettings,
) -> None:
    dataset = local_test_rana_context.get_dataset("dataset-1")
    assert dataset is local_test_settings.datasets["dataset-1"]


def test_upload_dir_preserves_local_test_ref(
    local_test_rana_context: LocalTestRanaContext,
    local_runtime: Mock,
    tmp_path: Path,
) -> None:
    local_runtime.project_dir = tmp_path / "project"
    local_path = tmp_path / "output"
    local_path.mkdir()
    (local_path / "file.txt").write_text("file contents")

    actual = local_test_rana_context.upload_dir(local_path, "results/")

    assert actual == RanaPath(id="results/", ref="local-test-ref")
    assert (
        local_runtime.project_dir / "results/file.txt"
    ).read_text() == "file contents"
