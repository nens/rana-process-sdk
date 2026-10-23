from asyncio import CancelledError
from unittest.mock import Mock

from rana_process_sdk.application import ProcessTimeReporter
from rana_process_sdk.infrastructure import ProcessTimeOutcome


def test_stop_reports_succeeded():
    gateway = Mock()
    reporter = ProcessTimeReporter(gateway)
    reporter.start()
    reporter.stop(failed=False)

    gateway.report.assert_called_once_with(ProcessTimeOutcome.SUCCEEDED, 0)


def test_stop_reports_failed():
    gateway = Mock()
    reporter = ProcessTimeReporter(gateway)
    reporter.start()
    reporter.stop(failed=True)

    gateway.report.assert_called_once_with(ProcessTimeOutcome.FAILED, 0)


def test_heartbeat_reports_running_until_stopped():
    gateway = Mock()
    reporter = ProcessTimeReporter(gateway, interval_seconds=0.01)
    reporter.start()
    # Wait until at least two heartbeats were sent
    while gateway.report.call_count < 2:
        pass
    reporter.stop(failed=False)

    calls = gateway.report.call_args_list
    assert all(call.args[0] is ProcessTimeOutcome.RUNNING for call in calls[:-1])
    assert calls[-1].args[0] is ProcessTimeOutcome.SUCCEEDED
    count = gateway.report.call_count
    assert count >= 3
    # No heartbeat after the final report
    assert gateway.report.call_count == count


def test_report_failure_does_not_raise():
    gateway = Mock()
    gateway.report.side_effect = RuntimeError("API down")
    reporter = ProcessTimeReporter(gateway)
    reporter.start()
    reporter.stop(failed=False)

    gateway.report.assert_called_once_with(ProcessTimeOutcome.SUCCEEDED, 0)


def test_report_base_exception_does_not_raise():
    gateway = Mock()
    gateway.report.side_effect = CancelledError()
    reporter = ProcessTimeReporter(gateway)
    reporter.start()
    reporter.stop(failed=False)

    gateway.report.assert_called_once_with(ProcessTimeOutcome.SUCCEEDED, 0)


def test_report_failure_is_logged_to_the_given_logger():
    gateway = Mock()
    gateway.report.side_effect = RuntimeError("API down")
    logger = Mock()
    reporter = ProcessTimeReporter(gateway, logger=logger)
    reporter.start()
    reporter.stop(failed=True)

    logger.warning.assert_called_once()
    assert logger.warning.call_args.args[1] == "failed"
    assert logger.warning.call_args.kwargs == {"exc_info": True}
