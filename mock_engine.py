import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


DEFAULT_CONFIG = {"mocks": []}
DEFAULT_ALLOW_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"


def normalize_method(method: str) -> str:
    return (method or "").upper().strip()


def parse_query_string(url_or_path: str) -> Dict[str, str]:
    parsed = urlparse(url_or_path)
    query = parse_qs(parsed.query, keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in query.items()}


def parse_path(url_or_path: str) -> str:
    parsed = urlparse(url_or_path)
    return parsed.path or "/"


class MockStore:
    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self._mtime: Optional[float] = None
        self._config: Dict[str, Any] = DEFAULT_CONFIG.copy()

    def load_if_changed(self) -> None:
        if not self.config_path.exists():
            self._config = DEFAULT_CONFIG.copy()
            self._mtime = None
            return

        current_mtime = self.config_path.stat().st_mtime
        if self._mtime is not None and current_mtime == self._mtime:
            return

        with self.config_path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
        self._config = loaded if isinstance(loaded, dict) else DEFAULT_CONFIG.copy()
        self._mtime = current_mtime

    def read_config(self) -> Dict[str, Any]:
        self.load_if_changed()
        return self._config

    def write_config(self, config: Dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent=2)
        self._config = config
        self._mtime = self.config_path.stat().st_mtime

    def mocks(self) -> List[Dict[str, Any]]:
        config = self.read_config()
        mocks = config.get("mocks", [])
        return mocks if isinstance(mocks, list) else []


def path_matches(mock: Dict[str, Any], request_path: str) -> bool:
    match_type = (mock.get("path_match") or "exact").strip().lower()
    expected_path = mock.get("path") or ""
    if not isinstance(expected_path, str) or not expected_path:
        return False
    if match_type == "prefix":
        return request_path.startswith(expected_path)
    return request_path == expected_path


def query_matches(mock: Dict[str, Any], request_query: Dict[str, str]) -> bool:
    expected_query = mock.get("query", {})
    if expected_query in (None, {}):
        return True
    if not isinstance(expected_query, dict):
        return False
    for key, expected_value in expected_query.items():
        if request_query.get(key) != str(expected_value):
            return False
    return True


def method_matches(mock: Dict[str, Any], method: str) -> bool:
    return normalize_method(mock.get("method", "")) == normalize_method(method)


def build_candidate_list(
    mocks: List[Dict[str, Any]],
    method: str,
    request_path: str,
    request_query: Dict[str, str],
) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for index, mock in enumerate(mocks):
        if not isinstance(mock, dict):
            continue
        if not mock.get("enabled", True):
            continue
        if not method_matches(mock, method):
            continue
        if not path_matches(mock, request_path):
            continue
        if not query_matches(mock, request_query):
            continue
        candidates.append({"index": index, "mock": mock})
    return candidates


def select_highest_priority(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (-int(c["mock"].get("priority", 0)), int(c["index"])),
    )
    return sorted_candidates[0]["mock"]


def match_mock(
    mocks: List[Dict[str, Any]],
    method: str,
    url_or_path: str,
) -> Optional[Dict[str, Any]]:
    request_path = parse_path(url_or_path)
    request_query = parse_query_string(url_or_path)
    candidates = build_candidate_list(mocks, method, request_path, request_query)
    return select_highest_priority(candidates)


def match_preflight_mock(
    mocks: List[Dict[str, Any]],
    url_or_path: str,
    requested_method: Optional[str],
) -> Optional[Dict[str, Any]]:
    request_path = parse_path(url_or_path)
    request_query = parse_query_string(url_or_path)
    method = normalize_method(requested_method or "")
    candidates: List[Dict[str, Any]] = []

    for index, mock in enumerate(mocks):
        if not isinstance(mock, dict):
            continue
        if not mock.get("enabled", True):
            continue
        if method and not method_matches(mock, method):
            continue
        if not path_matches(mock, request_path):
            continue
        if not query_matches(mock, request_query):
            continue
        candidates.append({"index": index, "mock": mock})

    return select_highest_priority(candidates)
