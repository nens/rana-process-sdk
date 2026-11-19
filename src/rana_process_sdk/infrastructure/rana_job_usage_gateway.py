from ..domain import JobUsageReport
from .rana_api_provider import PrefectRanaApiProvider

__all__ = ["RanaJobUsageGateway"]


class RanaJobUsageGateway:
    subpath = "usage"

    def __init__(self, provider_override: PrefectRanaApiProvider | None = None):
        self.provider = provider_override or PrefectRanaApiProvider()

    def report(self, report: JobUsageReport) -> None:
        self.provider.job_request(
            "PUT", self.subpath, json=report.model_dump(mode="json")
        )
