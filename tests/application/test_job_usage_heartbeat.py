import logging
from asyncio import CancelledError
from threading import Event
from time import monotonic, sleep
from unittest.mock import Mock, patch

from pytest import fixture

from rana_process_sdk.application.job_usage_heartbeat import JobUsageHeartbeat
from rana_process_sdk.domain import JobUsageReport, JobUsageStatus
from rana_process_sdk.infrastructure import RanaJobUsageGateway

MODULE = "rana_process_sdk.application.job_usage_heartbeat"


@fixture
def logger() -> Mock:
    return Mock(logging.Logger)


@fixture
def gateway() -> Mock:
    return Mock(RanaJobUsageGateway)


@fixture
def heartbeat(logger: Mock, gateway: Mock) -> JobUsageHeartbeat:
    return JobUsageHeartbeat(logger, gateway=gateway)


def reports(gateway: Mock) -> list[JobUsageReport]:
    return [call.args[0] for call in gateway.report.call_args_list]


def test_start_reports_running_immediately(heartbeat: JobUsageHeartbeat, gateway: Mock):
    heartbeat.start()
    heartbeat.stop(failed=False)

    assert reports(gateway)[0] == JobUsageReport(
        status=JobUsageStatus.RUNNING, elapsed_seconds=0
    )


def test_reports_running_periodically_until_stopped(
    heartbeat: JobUsageHeartbeat, gateway: Mock
):
    with patch(f"{MODULE}.HEARTBEAT_INTERVAL_SECONDS", 0.01):
        heartbeat.start()
        deadline = monotonic() + 5
        while gateway.report.call_count < 3 and monotonic() < deadline:
            sleep(0.001)
        heartbeat.stop(failed=False)

    statuses = [report.status for report in reports(gateway)]
    assert statuses[:-1] == [JobUsageStatus.RUNNING] * (len(statuses) - 1)
    assert statuses[-1] is JobUsageStatus.SUCCEEDED


def test_stop_reports_succeeded(heartbeat: JobUsageHeartbeat, gateway: Mock):
    heartbeat.start()
    heartbeat.stop(failed=False)

    assert reports(gateway)[-1].status is JobUsageStatus.SUCCEEDED


def test_stop_reports_failed(heartbeat: JobUsageHeartbeat, gateway: Mock):
    heartbeat.start()
    heartbeat.stop(failed=True)

    assert reports(gateway)[-1].status is JobUsageStatus.FAILED


def test_no_report_after_stop(heartbeat: JobUsageHeartbeat, gateway: Mock):
    with patch(f"{MODULE}.HEARTBEAT_INTERVAL_SECONDS", 0.01):
        heartbeat.start()
        heartbeat.stop(failed=False)
        count = gateway.report.call_count
        sleep(0.05)

    assert gateway.report.call_count == count


def test_elapsed_seconds_counts_from_start(heartbeat: JobUsageHeartbeat, gateway: Mock):
    heartbeat.started_at = 100.0
    with patch(f"{MODULE}.time.monotonic", return_value=130.0):
        heartbeat.send(JobUsageStatus.RUNNING)

    assert reports(gateway) == [
        JobUsageReport(status=JobUsageStatus.RUNNING, elapsed_seconds=30)
    ]


def test_send_failure_is_logged_with_status(
    heartbeat: JobUsageHeartbeat, gateway: Mock, logger: Mock
):
    gateway.report.side_effect = CancelledError()

    heartbeat.send(JobUsageStatus.FAILED)

    logger.warning.assert_called_once_with(
        "Could not report job usage (%s)", "failed", exc_info=True
    )


def test_start_failure_is_logged_and_does_not_raise(
    heartbeat: JobUsageHeartbeat, gateway: Mock, logger: Mock
):
    with patch(f"{MODULE}.threading.Thread.start", side_effect=RuntimeError("no")):
        heartbeat.start()
        heartbeat.stop(failed=False)

    logger.warning.assert_called_once_with(
        "Could not start job usage heartbeat", exc_info=True
    )
    assert heartbeat.thread is None
    # the final report is still sent, so the run is reported
    assert reports(gateway) == [
        JobUsageReport(status=JobUsageStatus.SUCCEEDED, elapsed_seconds=0)
    ]


def test_stop_does_not_wait_for_a_hanging_report(
    heartbeat: JobUsageHeartbeat, gateway: Mock
):
    heartbeat_started = Event()
    release = Event()

    def hanging_report(report: JobUsageReport) -> None:
        if report.status is JobUsageStatus.RUNNING and not heartbeat_started.is_set():
            heartbeat_started.set()
            release.wait()

    gateway.report.side_effect = hanging_report
    with patch(f"{MODULE}.STOP_TIMEOUT_SECONDS", 0.05):
        heartbeat.start()
        assert heartbeat_started.wait(5)
        started = monotonic()
        heartbeat.stop(failed=False)
        assert monotonic() - started < 2

    release.set()
