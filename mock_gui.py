import json
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from mock_engine import MockStore, match_mock


CONFIG_PATH = Path(__file__).resolve().parent / "mocks.json"
STORE = MockStore(CONFIG_PATH)
METHOD_OPTIONS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }
        h1, h2, h3 {
            letter-spacing: 0.2px;
        }
        .muted-caption {
            opacity: 0.8;
            font-size: 0.9rem;
            margin-bottom: 0.6rem;
        }
        .title-row {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            margin-bottom: 0.35rem;
            flex-wrap: wrap;
        }
        .method-pill {
            display: inline-block;
            background: rgba(56, 189, 248, 0.14);
            color: #93c5fd;
            border: 1px solid rgba(56, 189, 248, 0.28);
            border-radius: 999px;
            padding: 0.1rem 0.55rem;
            font-size: 0.78rem;
            font-weight: 600;
            margin-right: 0.45rem;
            vertical-align: middle;
        }
        .path-chip {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.84rem;
            opacity: 0.92;
            display: inline-block;
            max-width: 100%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            vertical-align: middle;
        }
        .mock-name {
            font-weight: 600;
            font-size: 1rem;
            margin-right: 0.2rem;
        }
        .badge {
            display: inline-block;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.78rem;
            border-radius: 8px;
            padding: 0.18rem 0.42rem;
            border: 1px solid rgba(120, 120, 150, 0.25);
            color: #86efac;
            background: rgba(74, 222, 128, 0.08);
        }
        .path-row {
            display: flex;
            align-items: center;
            gap: 0.48rem;
            min-width: 0;
            margin-bottom: 0.35rem;
        }
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
            margin-bottom: 0.6rem;
        }
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div {
            padding-bottom: 0.9rem;
            padding-top: 0.3rem;
            padding-left: 0.25rem;
            padding-right: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def parse_json_object(raw: str, field_name: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw.strip() or "{}")
    except json.JSONDecodeError as error:
        raise ValueError(f"{field_name} is not valid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must be a JSON object.")
    return parsed


def parse_json_value(raw: str, field_name: str) -> Any:
    try:
        return json.loads(raw.strip() or "{}")
    except json.JSONDecodeError as error:
        raise ValueError(f"{field_name} is not valid JSON: {error}") from error


def update_mock_enabled(index: int, enabled: bool) -> None:
    config = STORE.read_config()
    mocks = config.get("mocks", [])
    if 0 <= index < len(mocks):
        mocks[index]["enabled"] = bool(enabled)
        STORE.write_config(config)


def save_mock(index: int, new_mock: Dict[str, Any]) -> None:
    config = STORE.read_config()
    mocks = config.get("mocks", [])
    mocks[index] = new_mock
    STORE.write_config(config)


def add_mock(new_mock: Dict[str, Any]) -> None:
    config = STORE.read_config()
    mocks = config.setdefault("mocks", [])
    mocks.append(new_mock)
    STORE.write_config(config)


def delete_mock(index: int) -> None:
    config = STORE.read_config()
    mocks = config.get("mocks", [])
    if 0 <= index < len(mocks):
        mocks.pop(index)
        STORE.write_config(config)


def mock_form(initial: Dict[str, Any], submit_label: str, key_prefix: str):
    with st.form(key=f"{key_prefix}_form"):
        name = st.text_input("Name", value=initial.get("name", ""))
        enabled = st.checkbox("Enabled", value=initial.get("enabled", True))
        method = st.selectbox(
            "Method",
            options=METHOD_OPTIONS,
            index=max(
                METHOD_OPTIONS.index(initial.get("method", "GET"))
                if initial.get("method", "GET") in METHOD_OPTIONS
                else 0,
                0,
            ),
        )
        path_match = st.selectbox(
            "Path Match",
            options=["exact", "prefix"],
            index=0 if initial.get("path_match", "exact") == "exact" else 1,
        )
        path = st.text_input("Path", value=initial.get("path", ""))
        priority = st.number_input(
            "Priority",
            value=int(initial.get("priority", 0)),
            step=1,
            format="%d",
        )
        query_raw = st.text_area(
            "Query JSON object",
            value=json.dumps(initial.get("query", {}), ensure_ascii=False, indent=2),
            height=120,
        )
        headers_raw = st.text_area(
            "Headers JSON object",
            value=json.dumps(initial.get("headers", {"Content-Type": "application/json"}), ensure_ascii=False, indent=2),
            height=140,
        )
        body_raw = st.text_area(
            "Body JSON value",
            value=json.dumps(initial.get("body", {}), ensure_ascii=False, indent=2),
            height=220,
        )

        submitted = st.form_submit_button(submit_label)
        if not submitted:
            return None

    if not path.strip():
        raise ValueError("Path is required.")

    query = parse_json_object(query_raw, "Query")
    headers = parse_json_object(headers_raw, "Headers")
    body = parse_json_value(body_raw, "Body")
    return {
        "name": name.strip() or f"{method} {path.strip()}",
        "enabled": enabled,
        "priority": int(priority),
        "method": method,
        "path_match": path_match,
        "path": path.strip(),
        "query": query,
        "status": int(initial.get("status", 200)) if "status" in initial else 200,
        "headers": headers,
        "body": body,
    }


def main() -> None:
    st.set_page_config(page_title="mitmproxy mocks", layout="wide")
    inject_styles()
    st.title("mitmproxy mock manager")
    st.markdown(f'<div class="muted-caption">Config file: <code>{CONFIG_PATH}</code></div>', unsafe_allow_html=True)

    config = STORE.read_config()
    mocks = config.get("mocks", [])
    if not isinstance(mocks, list):
        mocks = []

    stat_cols = st.columns(3)
    enabled_count = sum(1 for m in mocks if isinstance(m, dict) and m.get("enabled", True))
    stat_cols[0].metric("Total mocks", len(mocks))
    stat_cols[1].metric("Enabled", enabled_count)
    stat_cols[2].metric("Disabled", max(len(mocks) - enabled_count, 0))

    st.subheader("Mocks")
    if not mocks:
        st.info("No mocks found.")
    else:
        for index, mock in enumerate(mocks):
            with st.container(border=True):
                cols = st.columns([0.7, 8.3])
                enabled = cols[0].toggle(
                    "On",
                    value=bool(mock.get("enabled", True)),
                    key=f"enabled_{index}",
                    label_visibility="collapsed",
                )
                if enabled != bool(mock.get("enabled", True)):
                    update_mock_enabled(index, enabled)
                    st.rerun()
                cols[1].markdown(
                    (
                        "<div class='title-row'>"
                        f"<span class='mock-name'>{mock.get('name', f'Mock {index + 1}')}</span>"
                        f"<span class='badge'>P{mock.get('priority', 0)}</span>"
                        f"<span class='badge'>{mock.get('path_match', 'exact')}</span>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                cols[1].markdown(
                    (
                        "<div class='path-row'>"
                        f"<span class='method-pill'>{mock.get('method', 'GET')}</span>"
                        f"<span class='path-chip' title='{mock.get('path', '')}'>{mock.get('path', '')}</span>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

    st.divider()
    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            st.subheader("Edit mock")
            if not mocks:
                st.info("Add a mock first.")
            else:
                selected = st.selectbox(
                    "Select mock",
                    options=list(range(len(mocks))),
                    format_func=lambda idx: f"{idx + 1}. {mocks[idx].get('name', 'Unnamed')}",
                )
                selected_mock = mocks[selected]
                status_value = st.number_input(
                    "Status",
                    value=int(selected_mock.get("status", 200)),
                    step=1,
                    format="%d",
                    key=f"status_{selected}",
                )
                selected_mock_with_status = dict(selected_mock)
                selected_mock_with_status["status"] = int(status_value)
                try:
                    edited = mock_form(selected_mock_with_status, "Save changes", "edit")
                    if edited is not None:
                        edited["status"] = int(status_value)
                        save_mock(selected, edited)
                        st.success("Mock updated.")
                        st.rerun()
                except ValueError as error:
                    st.error(str(error))

                if st.button("Delete selected mock", type="secondary"):
                    delete_mock(selected)
                    st.warning("Mock deleted.")
                    st.rerun()

    with right:
        with st.container(border=True):
            st.subheader("Add mock")
            default_new = {
                "enabled": True,
                "priority": 0,
                "method": "GET",
                "path_match": "exact",
                "path": "",
                "query": {},
                "status": 200,
                "headers": {"Content-Type": "application/json"},
                "body": {},
            }
            add_status = st.number_input("Status", value=200, step=1, format="%d", key="add_status")
            default_new["status"] = int(add_status)
            try:
                created = mock_form(default_new, "Add mock", "add")
                if created is not None:
                    created["status"] = int(add_status)
                    add_mock(created)
                    st.success("Mock added.")
                    st.rerun()
            except ValueError as error:
                st.error(str(error))

    st.divider()
    with st.container(border=True):
        st.subheader("Preview match")
        preview_method = st.selectbox(
            "Method",
            options=METHOD_OPTIONS,
            key="preview_method",
        )
        preview_url = st.text_input(
            "URL or path",
            value="/api/trade-service-moh/v1/appeals/search?page=0&size=10",
            key="preview_url",
        )
        if st.button("Preview", type="primary"):
            found = match_mock(STORE.mocks(), preview_method, preview_url)
            if found:
                st.success(f"Matched: {found.get('name', 'Unnamed mock')}")
                st.json(found)
            else:
                st.info("No matching mock.")


if __name__ == "__main__":
    main()
