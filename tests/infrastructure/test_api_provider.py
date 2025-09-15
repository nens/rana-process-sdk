# This module is a copy paste of test_api_provider.py

from http import HTTPStatus
from unittest import mock

import pytest

from rana_process_sdk.infrastructure import ApiException, ApiProvider

MODULE = "rana_process_sdk.infrastructure.api_provider"


@pytest.fixture
def response():
    response = mock.Mock()
    response.status = int(HTTPStatus.OK)
    response.headers = {"Content-Type": "application/json"}
    response.data = b'{"foo": 2}'
    return response


@pytest.fixture
def api_provider(response) -> ApiProvider:
    with mock.patch(MODULE + ".PoolManager"):
        api_provider = ApiProvider(
            url="http://testserver/foo/",
            headers_factory=lambda: {"Authorization": "Bearer tenant-2"},
        )
        api_provider._pool.request.return_value = response
        yield api_provider


def test_get(api_provider: ApiProvider, response):
    actual = api_provider.request("GET", "")

    assert api_provider._pool.request.call_count == 1
    assert api_provider._pool.request.call_args[1] == {
        "method": "GET",
        "url": "http://testserver/foo",
        "headers": {"Authorization": "Bearer tenant-2"},
        "timeout": 5.0,
    }
    assert actual == {"foo": 2}


def test_post_json(api_provider: ApiProvider, response):
    response.status == int(HTTPStatus.CREATED)
    api_provider._pool.request.return_value = response
    actual = api_provider.request("POST", "bar", json={"foo": 2})

    assert api_provider._pool.request.call_count == 1

    assert api_provider._pool.request.call_args[1] == {
        "method": "POST",
        "url": "http://testserver/foo/bar",
        "json": {"foo": 2},
        "headers": {
            "Authorization": "Bearer tenant-2",
        },
        "timeout": 5.0,
    }
    assert actual == {"foo": 2}


@pytest.mark.parametrize(
    "path,params,expected_url",
    [
        ("", None, "http://testserver/foo"),
        ("bar", None, "http://testserver/foo/bar"),
        ("bar/", None, "http://testserver/foo/bar"),
        ("", {"a": 2}, "http://testserver/foo?a=2"),
        ("bar", {"a": 2}, "http://testserver/foo/bar?a=2"),
        ("bar/", {"a": 2}, "http://testserver/foo/bar?a=2"),
        ("", {"a": [1, 2]}, "http://testserver/foo?a=1&a=2"),
        ("", {"a": 1, "b": "foo"}, "http://testserver/foo?a=1&b=foo"),
        ("", {"a": None}, "http://testserver/foo"),
        ("", {"a": ""}, "http://testserver/foo?a="),
        ("", {"a": []}, "http://testserver/foo"),
    ],
)
def test_url(api_provider: ApiProvider, path, params, expected_url):
    api_provider.request("GET", path, params=params)
    assert api_provider._pool.request.call_args[1]["url"] == expected_url


def test_timeout(api_provider: ApiProvider):
    api_provider.request("POST", "bar", timeout=2.1)
    assert api_provider._pool.request.call_args[1]["timeout"] == 2.1


@pytest.mark.parametrize(
    "status", [HTTPStatus.OK, HTTPStatus.NOT_FOUND, HTTPStatus.INTERNAL_SERVER_ERROR]
)
def test_unexpected_content_type(api_provider: ApiProvider, response, status):
    response.status = int(status)
    response.headers["Content-Type"] = "text/plain"
    with pytest.raises(ApiException) as e:
        api_provider.request("GET", "bar")

    assert e.value.status is status
    assert str(e.value) == f"{status}: Unexpected content type 'text/plain'"


def test_json_variant_content_type(api_provider: ApiProvider, response):
    response.headers["Content-Type"] = "application/something+json"
    actual = api_provider.request("GET", "bar")
    assert actual == {"foo": 2}


def test_no_content(api_provider: ApiProvider, response):
    response.status = int(HTTPStatus.NO_CONTENT)
    response.headers = {}

    actual = api_provider.request("DELETE", "bar/2")
    assert actual is None


@pytest.mark.parametrize("status", [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND])
def test_error_response(api_provider: ApiProvider, response, status):
    response.status = int(status)

    with pytest.raises(ApiException) as e:
        api_provider.request("GET", "bar")

    assert e.value.status is status
    assert str(e.value) == str(int(status)) + ": {'foo': 2}"


@mock.patch(MODULE + ".PoolManager", new=mock.Mock())
def test_no_token(response):
    api_provider = ApiProvider(url="http://testserver/foo/", headers_factory=lambda: {})
    api_provider._pool.request.return_value = response
    api_provider.request("GET", "")
    assert api_provider._pool.request.call_args[1]["headers"] == {}


@pytest.mark.parametrize(
    "path,trailing_slash,expected",
    [
        ("bar", False, "bar"),
        ("bar", True, "bar/"),
        ("bar/", False, "bar"),
        ("bar/", True, "bar/"),
    ],
)
def test_trailing_slash(api_provider: ApiProvider, path, trailing_slash, expected):
    api_provider._trailing_slash = trailing_slash
    api_provider.request("GET", path)

    assert (
        api_provider._pool.request.call_args[1]["url"]
        == "http://testserver/foo/" + expected
    )


def test_custom_header(api_provider: ApiProvider):
    api_provider.request("POST", "bar", headers={"foo": "bar"})
    assert api_provider._pool.request.call_args[1]["headers"] == {
        "foo": "bar",
        **api_provider._headers_factory(),
    }


def test_custom_header_precedes(api_provider: ApiProvider):
    api_provider.request("POST", "bar", headers={"Authorization": "bar"})
    assert api_provider._pool.request.call_args[1]["headers"]["Authorization"] == "bar"


def test_post_raw_body(api_provider: ApiProvider, response):
    response.status == int(HTTPStatus.CREATED)
    api_provider._pool.request.return_value = response
    actual = api_provider.request("POST", "bar", body=b'{"foo": 2}')

    assert api_provider._pool.request.call_count == 1

    assert api_provider._pool.request.call_args[1] == {
        "method": "POST",
        "url": "http://testserver/foo/bar",
        "body": b'{"foo": 2}',
        "headers": {
            "Authorization": "Bearer tenant-2",
        },
        "timeout": 5.0,
    }
    assert actual == {"foo": 2}


@pytest.mark.parametrize(
    "body,json,fields",
    [
        (b'{"foo": 2}', {"foo": 2}, None),
        (b'{"foo": 2}', None, {"foo": 2}),
        (None, {"foo": 2}, {"foo": 2}),
    ],
)
def test_post_multiple_data(api_provider: ApiProvider, response, body, json, fields):
    response.status == int(HTTPStatus.CREATED)
    api_provider._pool.request.return_value = response
    with pytest.raises(
        ValueError, match="Cannot specify more than one of 'body', 'json', or 'fields'"
    ):
        api_provider.request("POST", "bar", body=body, json=json, fields=fields)

    assert api_provider._pool.request.call_count == 0


def test_init_retry_settings():
    with (
        mock.patch(MODULE + ".PoolManager") as pool_manager_mock,
        mock.patch(MODULE + ".Retry") as retry_mock,
    ):
        api_provider = ApiProvider(
            url="http://testserver/foo/",
            retries=13,
            backoff_factor=0.23,
            retry_statuses={HTTPStatus.BAD_REQUEST},
            retry_methods={"GET"},
        )

    retry_mock.assert_called_once_with(
        13,
        backoff_factor=0.23,
        status_forcelist={HTTPStatus.BAD_REQUEST},
        allowed_methods={"GET"},
    )
    pool_manager_mock.assert_called_once_with(retries=retry_mock.return_value)
    api_provider._pool = pool_manager_mock.return_value
