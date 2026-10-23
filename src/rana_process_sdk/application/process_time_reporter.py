import logging
import threading
import time
from typing import Protocol

from ..infrastructure.rana_process_time_gateway import ProcessTimeOutcome

__all__ = ["ProcessTimeReporter"]

module_logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 60


class ProcessTimeGateway(Protocol):
    def report(self, outcome: ProcessTimeOutcome, elapsed_seconds: int) -> None: ...


class ProcessTimeReporter:
    """Reports the process time of a job while it runs and when it ends.

    Reporting never raises: the process result must not depend on usage tracking.
    """

    def __init__(
        self,
        gateway: ProcessTimeGateway,
        interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
        logger: logging.Logger | None = None,
    ) -> None:
        self._gateway = gateway
        self._interval_seconds = interval_seconds
        # Pass the Prefect run logger: Prefect only forwards logs of its own loggers to the run.
        self._logger = logger or module_logger
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at = 0.0

    def _elapsed_seconds(self) -> int:
        return int(time.monotonic() - self._started_at)

    def _report(self, outcome: ProcessTimeOutcome) -> None:
        try:
            self._gateway.report(outcome, self._elapsed_seconds())
        except BaseException:
            # BaseException too: a cancellation or interrupt during the report must not fail the run.
            self._logger.warning("Could not report process time (%s)", outcome.value, exc_info=True)

    def _heartbeat(self) -> None:
        while not self._stop_event.wait(self._interval_seconds):
            self._report(ProcessTimeOutcome.RUNNING)

    def start(self) -> None:
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._heartbeat, daemon=True)
        self._thread.start()

    def stop(self, failed: bool) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
        self._report(ProcessTimeOutcome.FAILED if failed else ProcessTimeOutcome.SUCCEEDED)
