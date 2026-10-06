from rana_process_sdk.domain import ProcessUserError


def test_process_user_error_uses_title_as_exception_message():
    error = ProcessUserError(
        title="Invalid input", description="Check the selected file."
    )

    assert str(error) == "Invalid input"
    assert error.args == ("Invalid input",)
    assert error.title == "Invalid input"
    assert error.description == "Check the selected file."
