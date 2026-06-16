from unittest.mock import ANY, Mock, patch

from pydantic import SecretStr
from urllib3 import Retry

from rana_process_sdk.infrastructure import get_threedi_api

MODULE = "rana_process_sdk.infrastructure.threedi_api_provider"


@patch(f"{MODULE}.ThreediApi")
def test_get_threedi_api(
    threedi_api: Mock,
):
    assert (
        get_threedi_api("https://custom-3di-host", SecretStr("supersecret"))
        is threedi_api.return_value
    )

    threedi_api.assert_called_once_with(
        config={
            "THREEDI_API_HOST": "https://custom-3di-host",
            "THREEDI_API_PERSONAL_API_TOKEN": "supersecret",
        },
        retries=ANY,
    )
    retry_policy = threedi_api.call_args.kwargs["retries"]
    assert isinstance(retry_policy, Retry)
    assert retry_policy.total == 5
    assert retry_policy.backoff_factor == 1.0
    assert retry_policy.status_forcelist == [429, 500, 502, 503, 504]
