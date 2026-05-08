import json
from pathlib import Path

from mitmproxy import http

from mock_engine import DEFAULT_ALLOW_METHODS, MockStore, match_mock, match_preflight_mock


MOCKS_PATH = Path(__file__).resolve().parent / "mocks.json"
STORE = MockStore(MOCKS_PATH)


def _apply_cors_headers(flow: http.HTTPFlow, response: http.Response) -> None:
    origin = flow.request.headers.get("Origin")
    request_headers = flow.request.headers.get("Access-Control-Request-Headers")
    response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = DEFAULT_ALLOW_METHODS
    response.headers["Access-Control-Allow-Headers"] = (
        request_headers
        if request_headers
        else "Authorization, Content-Type, Accept, Origin, X-Requested-With"
    )


def _build_response_headers(mock: dict) -> dict:
    headers = mock.get("headers", {})
    if not isinstance(headers, dict):
        headers = {}
    headers = {str(k): str(v) for k, v in headers.items()}
    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    return headers


def request(flow: http.HTTPFlow) -> None:
    mocks = STORE.mocks()

    if flow.request.method == "OPTIONS":
        requested_method = flow.request.headers.get("Access-Control-Request-Method")
        matched = match_preflight_mock(mocks, flow.request.url, requested_method)
        if matched:
            flow.response = http.Response.make(200, b"", {"Content-Type": "application/json"})
            _apply_cors_headers(flow, flow.response)
        return

    matched = match_mock(mocks, flow.request.method, flow.request.url)
    if not matched:
        return

    status = int(matched.get("status", 200))
    body = matched.get("body", {})
    content = json.dumps(body, ensure_ascii=False).encode("utf-8")
    flow.response = http.Response.make(status, content, _build_response_headers(matched))
    _apply_cors_headers(flow, flow.response)
