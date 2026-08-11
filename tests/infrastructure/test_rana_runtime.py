from pathlib import Path
from unittest.mock import Mock

from pytest import fixture

from rana_process_sdk.infrastructure import LocalTestRanaRuntime
from rana_process_sdk.settings import LocalTestSettings


@fixture
def runtime(tmp_path: Path) -> LocalTestRanaRuntime:
    project_dir = tmp_path / "project_dir"
    project_dir.mkdir()
    return LocalTestRanaRuntime(
        working_dir=tmp_path / "working_dir",
        project_dir=project_dir,
        settings=Mock(LocalTestSettings, threedi=None),
    )


def test_get_progress_initial_value(runtime: LocalTestRanaRuntime):
    assert runtime.get_progress() == 0


def test_set_progress_stores_value(runtime: LocalTestRanaRuntime):
    runtime.set_progress(50, "Halfway there", log=False)
    assert runtime.get_progress() == 50


def test_set_progress_updates_on_multiple_calls(runtime: LocalTestRanaRuntime):
    runtime.set_progress(25, "Quarter done", log=False)
    assert runtime.get_progress() == 25

    runtime.set_progress(75, "Nearly done", log=False)
    assert runtime.get_progress() == 75

    runtime.set_progress(100, "Complete", log=False)
    assert runtime.get_progress() == 100
