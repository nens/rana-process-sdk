from enum import Enum

from .rana_api_provider import PrefectRanaApiProvider

__all__ = ["ProcessTimeOutcome", "RanaProcessTimeGateway"]


class ProcessTimeOutcome(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RanaProcessTimeGateway:
    subpath = "process-time"

    def __init__(self, provider_override: PrefectRanaApiProvider | None = None):
        self.provider_override = provider_override

    @property
    def provider(self) -> PrefectRanaApiProvider:
        return self.provider_override or PrefectRanaApiProvider()

    def report(self, outcome: ProcessTimeOutcome, elapsed_seconds: int) -> None:
        self.provider.job_request(
            "PUT",
            self.subpath,
            json={"outcome": outcome.value, "elapsed_seconds": elapsed_seconds},
        )
