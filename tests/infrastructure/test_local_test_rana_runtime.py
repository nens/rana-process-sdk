from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

from pydantic import SecretStr
from pytest import LogCaptureFixture, fixture

from rana_process_sdk.infrastructure import LocalTestRanaRuntime
from rana_process_sdk.settings import LocalTestSettings


@fixture
def local_test_settings() -> Mock:
    return Mock(LocalTestSettings, threedi=None)


@fixture
def runtime(tmp_path: Path, local_test_settings: Mock) -> LocalTestRanaRuntime:
    working_dir = tmp_path / "working_dir"
    project_dir = tmp_path / "project_dir"
    project_dir.mkdir(parents=True, exist_ok=True)
    return LocalTestRanaRuntime(
        working_dir=str(working_dir),
        project_dir=str(project_dir),
        settings=local_test_settings,
        cleanup_workdir=False,
    )


def test_working_dir(runtime: LocalTestRanaRuntime, tmp_path: Path):
    assert runtime.job_working_dir == tmp_path / "working_dir"


def test_set_progress(runtime: LocalTestRanaRuntime, caplog: LogCaptureFixture):
    runtime.set_progress(0, "Start job", True)
    runtime.set_progress(50, "Update progress", True)
    runtime.set_progress(100, "Job Done!", True)

    assert " [          ]   0% | Start job" in caplog.text
    assert " [█████     ]  50% | Update progress" in caplog.text
    assert " [██████████] 100% | Job Done!" in caplog.text


def test_runtime_with_threedi_api_key(
    runtime: LocalTestRanaRuntime, local_test_settings: Mock
):
    local_test_settings.threedi = Mock(
        api_key=SecretStr("test_prefix.test_key"), organisation=uuid4()
    )

    runtime_with_key = LocalTestRanaRuntime(
        working_dir=str(runtime.job_working_dir),
        project_dir=str(runtime.project_dir),
        settings=local_test_settings,
        cleanup_workdir=False,
    )

    assert runtime_with_key.threedi_api_key is not None
    assert runtime_with_key.threedi_api_key.prefix == "test_prefix"
    assert (
        runtime_with_key.threedi_api_key.key.get_secret_value()
        == "test_prefix.test_key"
    )
    assert runtime_with_key.threedi_api_key.organisations == [
        local_test_settings.threedi.organisation
    ]
