from unittest.mock import Mock

from pytest import fixture

from rana_process_sdk.domain import JobUsageReport, JobUsageStatus
from rana_process_sdk.infrastructure import RanaApiProvider, RanaJobUsageGateway

MODULE = "rana_process_sdk.infrastructure.rana_job_usage_gateway"


@fixture
def provider() -> Mock:
    return Mock(RanaApiProvider)


@fixture
def gateway(provider: Mock) -> RanaJobUsageGateway:
    return RanaJobUsageGateway(provider)


def test_report(gateway: RanaJobUsageGateway, provider: Mock):
    gateway.report(JobUsageReport(status=JobUsageStatus.RUNNING, elapsed_seconds=60))

    provider.job_request.assert_called_once_with(
        "PUT",
        "usage",
        json={"status": "running", "elapsed_seconds": 60},
    )
