import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical import CONVERSATION_SCHEMA, validate_conversation
from formatters import chatgpt, claude, deepseek
from formatters.spa import build_search_index
from workbench_bundle import BUNDLE_SCHEMA, build_bundle, read_bundle


def test_all_provider_samples_normalize_to_canonical_schema():
    fixtures = [
        ("sample_data/chatgpt-convo.json", chatgpt),
        ("sample_data/claude-convo.json", claude),
        ("sample_data/deepseek-convo.json", deepseek),
    ]
    for path, formatter in fixtures:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        record = formatter.conv_to_json_clean(payload[0])
        assert record["schema_version"] == CONVERSATION_SCHEMA
        assert record["provider"] == formatter.PROVIDER
        validate_conversation(record)


def test_claude_tool_blocks_are_preserved_in_canonical_json():
    conv = {
        "uuid": "conv-1",
        "name": "Tool Test",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:01:00Z",
        "chat_messages": [
            {
                "uuid": "m1",
                "sender": "assistant",
                "created_at": "2026-01-01T00:00:01Z",
                "content": [
                    {"type": "tool_use", "id": "tool-1", "name": "lookup", "input": {"q": "x"}},
                    {"type": "tool_result", "tool_use_id": "tool-1", "content": {"value": 1}},
                ],
            }
        ],
    }
    record = claude.conv_to_json_clean(conv)
    types = [part["type"] for part in record["messages"][0]["parts"]]
    assert types == ["tool_use", "tool_result"]


def test_cew_bundle_round_trip_contains_manifest_conversations_and_search(tmp_path):
    destination = tmp_path / "archive.cew"
    result = build_bundle("sample_data/chatgpt-convo.json", destination)
    assert result["schema_version"] == BUNDLE_SCHEMA
    assert destination.exists()

    manifest, conversations, search_index = read_bundle(destination)
    assert manifest["conversation_count"] == len(conversations)
    assert len(search_index) == len(conversations)
    assert all(item["provider"] == "chatgpt" for item in search_index)
    assert any(item["text"] for item in search_index)


def test_spa_search_index_covers_conversation_without_opening_it(tmp_path):
    provider_dir = tmp_path / "chatgpt"
    provider_dir.mkdir(parents=True)
    provider_dir.joinpath("one.html").write_text(
        """<!doctype html><body><div class="container">
        <h1>Indexed Conversation</h1>
        <div class="message user"><div class="content">needle-from-unopened-chat</div></div>
        </div></body></html>""",
        encoding="utf-8",
    )

    index = build_search_index(tmp_path)
    assert "needle-from-unopened-chat" in index["chatgpt:one.html"]
