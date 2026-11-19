from enum import StrEnum

from pydantic import BaseModel, Field

__all__ = ["JobUsageStatus", "JobUsageReport"]


class JobUsageStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobUsageReport(BaseModel):
    status: JobUsageStatus
    elapsed_seconds: int = Field(
        ge=0, description="Cumulative seconds since the job started running"
    )
