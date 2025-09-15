from uuid import uuid4

from pytest import mark

from rana_process_sdk.domain import LizardTask


@mark.parametrize(
    "status, expected",
    [
        ("PENDING", True),
        ("STARTED", True),
        ("RETRY", True),
        ("SUCCESS", False),
        ("FAILURE", False),
    ],
)
def test_is_pending(status: str, expected: bool):
    assert LizardTask(id=uuid4(), status=status).is_pending() is expected


@mark.parametrize(
    "status, expected",
    [
        ("PENDING", False),
        ("STARTED", False),
        ("RETRY", False),
        ("SUCCESS", True),
        ("FAILURE", False),
    ],
)
def test_is_success(status: str, expected: bool):
    assert LizardTask(id=uuid4(), status=status).is_success() is expected


@mark.parametrize(
    "status, expected",
    [
        ("PENDING", False),
        ("STARTED", False),
        ("RETRY", False),
        ("SUCCESS", False),
        ("FAILURE", True),
        ("UNKNOWN", True),  # UNKNOWN is treated as a failure
    ],
)
def test_is_failed(status: str, expected: bool):
    assert LizardTask(id=uuid4(), status=status).is_failed() is expected
