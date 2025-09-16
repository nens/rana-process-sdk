import json as json_lib
import re
from collections.abc import Callable
from http import HTTPStatus
from urllib.parse import quote, urlencode, urljoin

from pydantic import AnyHttpUrl, BaseModel, ConfigDict
from urllib3 import HTTPResponse, PoolManager, Retry

from ..domain import Json
from .api_exception import ApiException

__all__ = ["ApiProvider", "Response"]


# Retry on 429 and all 5xx errors (because they are mostly temporary)
RETRY_STATUSES = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    }
)
# PATCH is strictly not idempotent, because you could do advanced
# JSON operations like 'add an array element'. mostly idempotent.
# However we never do that and we always make PATCH idempotent.
RETRY_METHODS = frozenset(["HEAD", "GET", "PATCH", "PUT", "DELETE", "OPTIONS", "TRACE"])


class Response(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: HTTPStatus
    data: bytes
    content_type: str | None


def join(url: str, path: str, trailing_slash: bool = False) -> str:
    """Results in a full url without trailing slash"""
    assert url.endswith("/")
    assert not path.startswith("/")
    result = urljoin(url, path)
    if trailing_slash and not result.endswith("/"):
        result = result + "/"
    elif not trailing_slash and result.endswith("/"):
        result = result[:-1]
    return result


def is_success(status: HTTPStatus) -> bool:
    """Returns True on 2xx status"""
    return (int(status) // 100) == 2


def check_exception(status: HTTPStatus, body: Json) -> None:
    if not is_success(status):
        raise ApiException(body, status=status)


def add_query_params(url: str, params: Json | None) -> str:
    # explicitly filter out None values
    if params is None:
        return url
    params = {k: v for k, v in params.items() if v is not None}
    query_str = urlencode(params, doseq=True)
    return url + "?" + query_str if query_str else url


JSON_CONTENT_TYPE_REGEX = re.compile(r"^application\/[^+]*[+]?(json);?.*$")


def is_json_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    return bool(JSON_CONTENT_TYPE_REGEX.match(content_type))


class ApiProvider:
    """Basic JSON API provider with retry policy and bearer tokens.

    The default retry policy has 3 retries with 1, 2, 4 second intervals.

    Args:
        url: The url of the API (with trailing slash)
        headers_factory: Callable that returns headers (for e.g. authorization)
        retries: Total number of retries per request
        backoff_factor: Multiplier for retry delay times (1, 2, 4, ...)
        trailing_slash: Wether to automatically add or remove trailing slashes.
    """

    def __init__(
        self,
        url: AnyHttpUrl,
        *,
        headers_factory: Callable[[], dict[str, str]] | None = None,
        retries: int = 3,
        backoff_factor: float = 1.0,
        retry_statuses: frozenset[HTTPStatus] = RETRY_STATUSES,
        retry_methods: frozenset[str] = RETRY_METHODS,
        trailing_slash: bool = False,
    ):
        self._url = str(url)
        if not self._url.endswith("/"):
            self._url += "/"
        self._headers_factory = headers_factory
        self._pool = PoolManager(
            retries=Retry(
                retries,
                backoff_factor=backoff_factor,
                status_forcelist=retry_statuses,
                allowed_methods=retry_methods,
            )
        )
        self._trailing_slash = trailing_slash

    def _request(
        self,
        method: str,
        path: str,
        params: Json | None,
        body: bytes | None,
        json: Json | None,
        fields: Json | None,
        headers: dict[str, str] | None,
        timeout: float,
    ) -> HTTPResponse:
        actual_headers = {}
        if self._headers_factory is not None:
            actual_headers.update(self._headers_factory())
        if headers:
            actual_headers.update(headers)
        request_kwargs = {
            "method": method,
            "url": add_query_params(
                join(self._url, quote(path), self._trailing_slash), params
            ),
            "timeout": timeout,
        }
        if sum(x is not None for x in (body, json, fields)) > 1:
            raise ValueError(
                "Cannot specify more than one of 'body', 'json', or 'fields'"
            )
        if body is not None:
            request_kwargs["body"] = body
        elif json is not None:
            request_kwargs["json"] = json
        elif fields is not None:
            request_kwargs["fields"] = fields
            request_kwargs["encode_multipart"] = False

        return self._pool.request(headers=actual_headers, **request_kwargs)  # type: ignore

    def request(
        self,
        method: str,
        path: str,
        params: Json | None = None,
        *,
        body: bytes | None = None,
        json: Json | None = None,
        fields: Json | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
    ) -> Json | None:
        response = self._request(
            method, path, params, body, json, fields, headers, timeout
        )
        status = HTTPStatus(response.status)
        content_type = response.headers.get("Content-Type")
        if status is HTTPStatus.NO_CONTENT:
            return None
        if not is_json_content_type(content_type):
            raise ApiException(
                f"Unexpected content type '{content_type}'", status=status
            )
        response_body = json_lib.loads(response.data.decode())
        check_exception(status, response_body)
        return response_body

    def request_raw(
        self,
        method: str,
        path: str,
        params: Json | None = None,
        *,
        body: bytes | None = None,
        json: Json | None = None,
        fields: Json | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
    ) -> Response:
        response = self._request(
            method, path, params, body, json, fields, headers, timeout
        )
        return Response(
            status=HTTPStatus(response.status),
            data=response.data,
            content_type=response.headers.get("Content-Type"),
        )
