import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical import canonical_conversation, canonical_message
from canonical_render import render_canonical_html_body, render_canonical_markdown
from workbench_bundle import BUNDLE_SCHEMA, build_bundle, extract_attachment, merge_bundles, read_bundle


def test_canonical_renderer_preserves_tool_blocks_and_safe_text():
    record = canonical_conversation(
        "claude",
        "c1",
        "Renderer",
        "2026-09-24T00:00:00Z",
        "2026-09-24T00:01:00Z",
        [
            canonical_message(
                "assistant",
                "2026-09-24T00:01:00Z",
                [
                    {"type": "text", "content": "<img src=x onerror=alert(1)>"},
                    {"type": "tool_use", "name": "lookup", "input": {"q": "x"}},
                    {"type": "tool_result", "content": {"value": 1}},
                ],
            )
        ],
    )

    html = render_canonical_html_body(record)
    markdown = render_canonical_markdown(record)

    assert "<img src=x" not in html
    assert "&lt;img" in html
    assert "Tool use · lookup" in html
    assert "Tool result" in html
    assert "Tool use: lookup" in markdown
    assert '"value": 1' in markdown


def test_cew_v2_manifest_contains_source_provenance(tmp_path):
    output = tmp_path / "archive.cew"
    manifest = build_bundle("sample_data/chatgpt-convo.json", output)

    assert manifest["schema_version"] == BUNDLE_SCHEMA
    assert manifest["bundle_id"]
    assert manifest["sources"][0]["kind"] == "provider-export"
    assert len(manifest["sources"][0]["sha256"]) == 64

    read_manifest, conversations, search_index = read_bundle(output)
    assert read_manifest["bundle_id"] == manifest["bundle_id"]
    assert len(conversations) == read_manifest["conversation_count"]
    assert len(search_index) == len(conversations)


def test_bundle_merge_is_duplicate_aware_and_records_history(tmp_path):
    first = tmp_path / "first.cew"
    second = tmp_path / "second.cew"
    merged = tmp_path / "merged.cew"

    one = build_bundle("sample_data/chatgpt-convo.json", first)
    two = build_bundle("sample_data/chatgpt-convo.json", second)
    result = merge_bundles([first, second], merged)

    manifest, conversations, _ = read_bundle(merged)

    assert result["schema_version"] == BUNDLE_SCHEMA
    assert manifest["conversation_count"] == one["conversation_count"] == two["conversation_count"]
    assert manifest["duplicate_records_resolved"] >= manifest["conversation_count"]
    assert len(manifest["history"]) == 2
    assert len(conversations) == manifest["conversation_count"]


def test_cew_v2_attachment_payload_round_trip_and_merge(tmp_path):
    attachments = tmp_path / "attachments"
    attachments.mkdir()
    attachments.joinpath("notes.txt").write_text("offline attachment", encoding="utf-8")

    first = tmp_path / "with-attachment.cew"
    second = tmp_path / "without-attachment.cew"
    merged = tmp_path / "merged-attachment.cew"

    first_manifest = build_bundle(
        "sample_data/chatgpt-convo.json",
        first,
        attachments_dir=attachments,
    )
    build_bundle("sample_data/chatgpt-convo.json", second)

    assert len(first_manifest["attachments"]) == 1
    entry = first_manifest["attachments"][0]
    assert entry["path"].startswith("attachments/")
    assert len(entry["sha256"]) == 64

    extracted = tmp_path / "extracted.txt"
    extract_attachment(first, entry["path"], extracted)
    assert extracted.read_text(encoding="utf-8") == "offline attachment"

    merge_bundles([first, second], merged)
    merged_manifest, _, _ = read_bundle(merged)
    assert len(merged_manifest["attachments"]) == 1
    assert merged_manifest["attachments"][0]["sha256"] == entry["sha256"]
