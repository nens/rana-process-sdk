import logging
import threading
import time

from ..domain import JobUsageReport, JobUsageStatus
from ..infrastructure import RanaJobUsageGateway

__all__ = ["JobUsageHeartbeat"]

HEARTBEAT_INTERVAL_SECONDS = 60
STOP_TIMEOUT_SECONDS = 5


class JobUsageHeartbeat:
    """Reports job usage while the job runs, and its final outcome when it stops."""

    gateway: RanaJobUsageGateway
    logger: logging.Logger
    started_at: float = 0.0
    thread: threading.Thread | None = None
    stop_event: threading.Event

    def __init__(
        self,
        logger: logging.Logger,
        gateway: RanaJobUsageGateway | None = None,
    ) -> None:
        self.logger = logger
        self.gateway = gateway or RanaJobUsageGateway()
        self.stop_event = threading.Event()

    def start(self) -> None:
        self.started_at = time.monotonic()
        thread = threading.Thread(target=self.beat, daemon=True)
        try:
            thread.start()
        except Exception:
            self.logger.warning("Could not start job usage heartbeat", exc_info=True)
            return
        self.thread = thread

    def beat(self) -> None:
        self.send(JobUsageStatus.RUNNING)
        while not self.stop_event.wait(HEARTBEAT_INTERVAL_SECONDS):
            self.send(JobUsageStatus.RUNNING)

    def stop(self, failed: bool) -> None:
        self.stop_event.set()
        if self.thread is not None:
            # A heartbeat in flight may be retrying; do not hold up the end of the run for it.
            self.thread.join(STOP_TIMEOUT_SECONDS)
        self.send(JobUsageStatus.FAILED if failed else JobUsageStatus.SUCCEEDED)

    def send(self, status: JobUsageStatus) -> None:
        try:
            report = JobUsageReport(
                status=status, elapsed_seconds=int(time.monotonic() - self.started_at)
            )
            self.gateway.report(report)
        except BaseException:
            self.logger.warning(
                "Could not report job usage (%s)", status.value, exc_info=True
            )
