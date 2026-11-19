from ..domain import JobUsageReport, Json
from .rana_api_provider import PrefectRanaApiProvider

__all__ = ["RanaJobUsageGateway"]


class JobUsageMapper:
    def to_external(self, internal: Json) -> Json:
        return {
            "status": internal["status"],
            "elapsed_seconds": internal["elapsed_seconds"],
        }


class RanaJobUsageGateway:
    mapper = JobUsageMapper()
    subpath = "usage"

    def __init__(self, provider_override: PrefectRanaApiProvider | None = None):
        self.provider = provider_override or PrefectRanaApiProvider()

    def report(self, report: JobUsageReport) -> None:
        self.provider.job_request(
            "PUT", self.subpath, json=self.mapper.to_external(report.model_dump())
        )
