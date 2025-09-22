from unittest.mock import Mock, patch
from uuid import uuid4

from pytest import fixture, mark
from sentry_sdk import get_global_scope, get_isolation_scope
from sentry_sdk.types import Event

from rana_process_sdk.domain import Json
from rana_process_sdk.infrastructure import SentryBlock
from rana_process_sdk.infrastructure.sentry_prefect_integration import (
    prefect_log_filter,
)

MODULE = "rana_process_sdk.infrastructure.sentry_prefect_integration"


@fixture
def sentry_block() -> SentryBlock:
    return SentryBlock(
        dsn="https://supersecret@o00000.ingest.sentry.local/123456789",
        environment="testing",
    )


@fixture()
def event() -> Json:
    return {
        "level": "error",
        "logger": "prefect.flow_runs",
        "logentry": {
            "message": "Process execution encountered an exception: ProcessUserError: Polygon not found"
        },
    }


def test_sentry_block_init(sentry_block: SentryBlock):
    try:
        sentry_block.init()
        scope = get_isolation_scope()

        client = scope.get_client()

        assert client.dsn == sentry_block.dsn
        assert client.options["environment"] == sentry_block.environment
    finally:
        get_global_scope().set_client(None)
        get_global_scope().clear()


@mark.parametrize(
    "event",
    [
        {"foo": "bar"},
        {"logentry": None},
        {"logentry": {"message": None}},
        {"logentry": {"message": "Something else"}},
    ],
)
def test_filter_prefect_finished_logs_no_filter(event: Event):
    assert prefect_log_filter(event, {}) == event


def test_filter_process_user_error(event):
    event["logentry"]["message"] = (
        "Process execution encountered an exception: ProcessUserError: Polygon not found"
    )

    assert not prefect_log_filter(event, {})


def test_filter_process_internal_error(event):
    event["logentry"]["message"] = (
        "Process execution encountered an exception: ProcessInternalError: Polygon not found"
    )

    assert prefect_log_filter(event, {})


def test_filter_formatted_errors(event):
    event["logentry"]["message"] = (
        "Process execution encountered an exception: ProcessUserError: Polygon not found"
    )

    assert not prefect_log_filter(event, {})


def test_filter_filter_finished_in_state_failed(event):
    event["logentry"]["message"] = (
        "Finished in state Failed('Flow run encountered an exception: ValueError: S')"
    )

    assert not prefect_log_filter(event, {})


def test_filter_formatted_exception(event):
    event["logentry"]["message"] = (
        '{"title": "Process execution encountered an exception: ProcessUserError: Polygon not found", "traceback": "Traceback (most recent call last):\\n  File \\"/code/src/rana_process_sdk/application/rana_flow.py\\", line 59, in wrapper\\n    return func(*args, **kwargs)\\n           ^^^^^^^^^^^^^^^^^^^^^\\n  File \\"/code/src/rana_flows/define_study_area.py\\", line 155, in define_study_area\\n    check_connected_polygons(selected_polygons)\\n  File \\"/code/src/rana_flows/define_study_area_lib/gdal_functions.py\\", line 189, in check_connected_polygons\\n    raise ProcessUserError(\\"Polygon not found\\", \\"Polygon is empty or not found.\\")\\nrana_process_sdk.application.exceptions.ProcessUserError: (\'Polygon not found\', \'Polygon is empty or not found.\')\\n", "error_type": "user", "description": "Polygon is empty or not found."}'
    )

    assert not prefect_log_filter(event, {})


def test_filter_misformatted_exception(event):
    event["logentry"]["message"] = "{exception"

    assert prefect_log_filter(event, {})


def test_sentry_block_set_tags_and_context(sentry_block: SentryBlock):
    flow_run = Mock()
    flow_run.deployment_id = uuid4()
    flow_run.id = uuid4()
    flow_run.tags = ["foo", "tenant_id_12345", "bar", "project_id_67890"]
    flow_run.parameters = {"param1": "value1", "param2": 2}
    try:
        SentryBlock.set_tags_and_context(flow_run)
        scope = get_isolation_scope()
        assert scope._tags["rana_process_id"] == str(flow_run.deployment_id)
        assert scope._tags["rana_job_id"] == str(flow_run.id)
        assert scope._contexts["rana_job_parameters"] == flow_run.parameters
        assert scope._tags["rana_tenant"] == "12345"
        assert scope._tags["rana_project_id"] == "67890"
    finally:
        get_global_scope().set_client(None)
        get_global_scope().clear()


def test_sentry_block_set_tags_and_context_no_tags(sentry_block: SentryBlock):
    flow_run = Mock()
    flow_run.deployment_id = uuid4()
    flow_run.id = uuid4()
    flow_run.tags = []  # No tags
    flow_run.parameters = {}
    try:
        SentryBlock.set_tags_and_context(flow_run)
        scope = get_isolation_scope()
        assert scope._contexts["rana_job_parameters"] == {}
        assert scope._tags["rana_tenant"] is None
        assert scope._tags["rana_project_id"] is None
    finally:
        get_global_scope().set_client(None)
        get_global_scope().clear()


@patch(f"{MODULE}.capture_message")
def test_crash_handler(capture_message: Mock, sentry_block: SentryBlock):
    flow = Mock()
    flow_run = Mock(deployment_id=uuid4())
    state = Mock()

    with patch.object(SentryBlock, "set_tags_and_context") as set_tags_and_context:
        sentry_block.crash_handler(flow, flow_run, state)

    capture_message.assert_called_once_with(
        f"Process {flow_run.deployment_id} crashed", level="error"
    )
    set_tags_and_context.assert_called_once_with(flow_run)
