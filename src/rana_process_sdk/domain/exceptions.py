__all__ = [
    "ProcessUserError",
    "ProcessInternalError",
    "FormattedException",
    "DoesNotExist",
]

import traceback
from typing import Literal

from pydantic import BaseModel, ConfigDict


class FormattedException(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    traceback: str
    error_type: Literal["user", "internal"]
    description: str | None = None


class ProcessUserError(Exception):
    """Exception should raised for user-facing errors.

    This exception should be used when an error occurs that needs to be
    communicated to the end user in a clear and understandable way.
    """

    def __init__(self, title: str, description: str | None = None):
        self.title = title
        self.description = description

    def format(self) -> FormattedException:
        return FormattedException(
            title=f"Process execution encountered an exception: {self.__class__.__name__}: {self.title}",
            traceback=traceback.format_exc(),
            error_type="user",
            description=self.description,
        )


class ProcessInternalError(Exception):
    """Exception should raised for internal errors.

    This exception should be used when an error occurs that is not
    expected to be communicated to the end user.
    """

    def __init__(self, exception: Exception):
        self.exception = exception

    def format(self) -> FormattedException:
        return FormattedException(
            title=f"Process execution encountered an exception: {self.__class__.__name__}({self.exception.__class__.__name__}): {self.exception}",
            traceback=traceback.format_exc(),
            error_type="internal",
            description="During process execution an internal exception occured. This should have not have happened and our support has been notified. When you want to reference this problem, please provide the ID of this job, or the project ID.",
        )


class DoesNotExist(Exception):
    """Raised when an entity does not exist."""

    pass
