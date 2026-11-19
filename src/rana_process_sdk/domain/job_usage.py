from enum import StrEnum

from clean_python import ValueObject
from pydantic import Field

__all__ = ["JobUsageStatus", "JobUsageReport"]


class JobUsageStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobUsageReport(ValueObject):
    status: JobUsageStatus
    elapsed_seconds: int = Field(
        ge=0, description="Cumulative seconds since the job started running"
    )
