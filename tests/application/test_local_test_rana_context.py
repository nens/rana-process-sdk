from pathlib import Path
from unittest.mock import Mock

from pytest import fixture

from rana_process_sdk import (
    LocalTestRanaContext,
    LocalTestRanaRuntime,
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
