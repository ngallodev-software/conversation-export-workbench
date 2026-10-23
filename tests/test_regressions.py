import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import format_conversations
from formatters import chatgpt, claude, deepseek
from formatters.shared import normalize_timestamp


def test_load_conversations_accepts_zip_input(tmp_path: Path):
    conversations = [{"id": "1", "title": "zip test", "mapping": {}}]
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("nested/conversations.json", json.dumps(conversations))

    loaded = format_conversations.load_conversations(str(zip_path))
    assert loaded == conversations


def test_deepseek_fragment_search_no_unboundlocalerror():
    frag = {
        "type": "SEARCH",
        "results": [{"url": "https://example.com", "title": "Example", "snippet": "snippet"}],
    }
    rendered = deepseek._render_fragment_html(frag)
    assert "search-result" in rendered
    assert "https://example.com" in rendered


def test_claude_html_body_renders_without_unboundlocalerror():
    conv = {
        "name": "Claude Test",
        "created_at": "2026-03-01T00:00:00",
        "updated_at": "2026-03-01T00:01:00",
        "chat_messages": [
            {
                "sender": "assistant",
                "created_at": "2026-03-01T00:01:00",
                "content": [{"type": "text", "text": "hello"}],
            }
        ],
    }
    body = claude.conv_to_html_body(conv)
    assert "Claude" in body
    assert "hello" in body


def test_chatgpt_html_body_renders_without_unboundlocalerror():
    conv = {
        "id": "id-1",
        "title": "ChatGPT Test",
        "create_time": 1700000000.0,
        "update_time": 1700000060.0,
        "current_node": "node-1",
        "mapping": {
            "node-1": {
                "parent": None,
                "message": {
                    "author": {"role": "assistant"},
                    "weight": 1,
                    "create_time": 1700000060.0,
                    "content": {"content_type": "text", "parts": ["hello"]},
                },
            }
        },
    }
    body = chatgpt.conv_to_html_body(conv)
    assert "ChatGPT" in body
    assert "hello" in body


def test_main_zero_args_non_interactive_dispatches_auto_mode(monkeypatch: pytest.MonkeyPatch):
    called = {"auto": False}

    def _auto():
        called["auto"] = True

    monkeypatch.setattr(format_conversations, "non_interactive_mode", _auto)
    monkeypatch.setattr(sys, "argv", ["format_conversations.py"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    format_conversations.main()
    assert called["auto"] is True


def test_main_provider_prompt_skipped_non_interactive(monkeypatch: pytest.MonkeyPatch):
    sample_path = Path("sample_data/deepseek-convo.json")
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    # Break auto-detection to force provider resolution path.
    for item in payload:
        item.pop("mapping", None)
        item.pop("chat_messages", None)

    monkeypatch.setattr(format_conversations, "load_conversations", lambda _p: payload)
    monkeypatch.setattr(sys, "argv", ["format_conversations.py", "--input", "dummy.json"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    with pytest.raises(SystemExit) as exc:
        format_conversations.main()

    assert exc.value.code == 1


def test_normalize_timestamp_uses_utc_second_precision():
    assert normalize_timestamp("2026-08-05T07:59:21.548716Z") == "2026-08-05T07:59:21Z"
    assert normalize_timestamp("2026-04-21T09:48:15.209000+08:00") == "2026-04-21T01:48:15Z"
    assert normalize_timestamp("2026-03-01T00:00:00") == "2026-03-01T00:00:00Z"


def test_provider_canonical_timestamps_are_second_precision():
    cases = [
        (Path("sample_data/chatgpt-convo.json"), chatgpt),
        (Path("sample_data/claude-convo.json"), claude),
        (Path("sample_data/deepseek-convo.json"), deepseek),
    ]
    for path, formatter in cases:
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = formatter.conv_to_json_clean(payload[0])
        timestamps = [record["started_at"], record["updated_at"]]
        timestamps.extend(message["timestamp"] for message in record["messages"])
        assert all(value.endswith("Z") and "." not in value for value in timestamps if value)
