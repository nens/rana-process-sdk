from pydantic import SecretStr
from threedi_api_client import ThreediApi
from urllib3.util.retry import Retry

__all__ = ["get_threedi_api"]


def get_threedi_api(host: str, api_key: SecretStr) -> ThreediApi:
    return ThreediApi(
        config={
            "THREEDI_API_HOST": host,
            "THREEDI_API_PERSONAL_API_TOKEN": api_key.get_secret_value(),
        },
        retries=Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        ),
    )
