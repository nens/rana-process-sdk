from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from prefect.client.schemas import FlowRun
from prefect.context import EngineContext, SettingsContext
from prefect.settings import Settings
from pytest import fixture

from rana_process_sdk.infrastructure import PrefectRanaRuntime

MODULE = "rana_process_sdk.infrastructure.prefect_rana_runtime"


@fixture
def engine_context() -> Iterator[EngineContext]:
    with patch(f"{MODULE}.EngineContext") as m:
        m.get.return_value = Mock(
            EngineContext,
            flow_run=FlowRun(
                id=UUID("7d991ce4-9025-47dc-b715-bc7c08761190"),
                name="my job",
                parameters={"foo": "bar"},
                flow_id=UUID("87373e6b-69bc-4159-9f6c-a87825069ee8"),
                deployment_id=UUID("55d186b3-36ee-400e-9289-ad7140b795ba"),
                job_variables={"job_secret": "supersecret", "tenant_id": "Tenant"},
            ),
        )
        yield m.get.return_value


@fixture
def settings_context(tmp_path) -> Iterator[SettingsContext]:
    with patch(f"{MODULE}.SettingsContext") as m:
        m.get.return_value = Mock(
            SettingsContext, settings=Mock(Settings, home=Path(tmp_path))
        )
        yield m.get.return_value


@fixture
def runtime(
    engine_context: Iterator[EngineContext], settings_context: Iterator[SettingsContext]
) -> PrefectRanaRuntime:
    return PrefectRanaRuntime()


def test_job_id(runtime: PrefectRanaRuntime):
    assert runtime.job_id == UUID("7d991ce4-9025-47dc-b715-bc7c08761190")


def test_job_secret(runtime: PrefectRanaRuntime):
    assert runtime.job_secret.get_secret_value() == "supersecret"


def test_job_name(runtime: PrefectRanaRuntime):
    assert runtime.job_name == "my job"


def test_job_parameters(runtime: PrefectRanaRuntime):
    assert runtime.job_parameters == {"foo": "bar"}


def test_tenant_id(runtime: PrefectRanaRuntime):
    assert runtime.tenant_id == "Tenant"


def test_process_id(runtime: PrefectRanaRuntime):
    assert runtime.process_id == UUID("55d186b3-36ee-400e-9289-ad7140b795ba")


def test_working_dir(runtime: PrefectRanaRuntime, settings_context: SettingsContext):
    assert (
        runtime.job_working_dir
        == settings_context.settings.home / "7d991ce4-9025-47dc-b715-bc7c08761190"
    )


@patch(f"{MODULE}.get_run_logger")
def test_logger(get_run_logger: Mock, runtime: PrefectRanaRuntime):
    assert runtime.logger is get_run_logger.return_value
    get_run_logger.assert_called_once_with()


@patch(f"{MODULE}.create_table_artifact")
def test_set_result(create_table_artifact: Mock, runtime: PrefectRanaRuntime):
    runtime.set_result({"foo": "bar"})
    create_table_artifact.assert_called_once_with([{"foo": "bar"}], key="results")


@patch(f"{MODULE}.get_run_logger")
@patch(f"{MODULE}.update_progress_artifact")
def test_set_progress(
    update_progress_artifact: Mock, get_run_logger: Mock, runtime: PrefectRanaRuntime
):
    runtime._progress_artifact_id = "123ABC"

    runtime.set_progress(progress=100, description="Job Done!", log=True)

    get_run_logger.assert_called_once_with()
    get_run_logger.return_value.info.assert_called_once_with("Job Done!")
    update_progress_artifact.assert_called_once_with("123ABC", 100, "Job Done!")


@patch(f"{MODULE}.get_run_logger")
@patch(f"{MODULE}.update_progress_artifact")
def test_set_progress_no_log(
    update_progress_artifact: Mock, get_run_logger: Mock, runtime: PrefectRanaRuntime
):
    runtime._progress_artifact_id = "123ABC"

    runtime.set_progress(progress=100, description="Job Done!", log=False)

    get_run_logger.return_value.info.assert_not_called()
    update_progress_artifact.assert_called_once_with("123ABC", 100, "Job Done!")


@patch(f"{MODULE}.create_progress_artifact")
def test_create_progress(create_progress_artifact: Mock, runtime: PrefectRanaRuntime):
    create_progress_artifact.return_value = uuid4()

    runtime.create_progress()

    create_progress_artifact.assert_called_once_with(0.0, "progress", "Job started")
    assert runtime._progress_artifact_id == create_progress_artifact.return_value
