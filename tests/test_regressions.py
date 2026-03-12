import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import format_conversations
from formatters import deepseek


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


def test_main_zero_args_non_interactive_exits_cleanly(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(sys, "argv", ["format_conversations.py"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    with pytest.raises(SystemExit) as exc:
        format_conversations.main()

    assert exc.value.code == 2
    stderr = capsys.readouterr().err
    assert "No arguments provided and no interactive input is available." in stderr


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
