from typing import Any

from process_settings import get_settings
from process_settings.settings import LizardSettings
from urllib3 import make_headers

from .api_provider import ApiProvider

__all__ = ["LizardApiProvider"]


class LizardApiProvider(ApiProvider):
    def __init__(self, lizard_settings: LizardSettings | None = None, **kwargs: Any):
        lizard_settings = lizard_settings or get_settings().lizard
        assert lizard_settings.host.scheme == "https"
        auth_headers = make_headers(basic_auth=f"__key__:{lizard_settings.api_key.get_secret_value()}")
        super().__init__(lizard_settings.host, headers_factory=lambda: auth_headers, trailing_slash=True, **kwargs)
