from unittest.mock import Mock

from pytest import fixture

from rana_process_sdk.infrastructure import (
    ProcessTimeOutcome,
    RanaApiProvider,
    RanaProcessTimeGateway,
)


@fixture
def provider() -> Mock:
    return Mock(RanaApiProvider)


@fixture
def gateway(provider: Mock) -> RanaProcessTimeGateway:
    return RanaProcessTimeGateway(provider)


def test_report(gateway: RanaProcessTimeGateway, provider: Mock):
    gateway.report(ProcessTimeOutcome.RUNNING, 60)

    provider.job_request.assert_called_once_with(
        "PUT",
        "process-time",
        json={"outcome": "running", "elapsed_seconds": 60},
    )
