"""Portable Conversation Export Workbench (.cew) bundle support."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from canonical import CONVERSATION_SCHEMA, searchable_text, validate_conversation
from format_conversations import detect_provider, load_conversations
from formatters import chatgpt, claude, deepseek

BUNDLE_SCHEMA = "cew.bundle/v1"
BUNDLE_MANIFEST = "manifest.json"
BUNDLE_CONVERSATIONS = "conversations.json"
BUNDLE_SEARCH = "search.json"
MAX_BUNDLE_MEMBER_BYTES = 512 * 1024 * 1024
MAX_BUNDLE_COMPRESSION_RATIO = 200

_FORMATTER_BY_NAME = {
    "chatgpt": chatgpt,
    "claude": claude,
    "deepseek": deepseek,
}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _validate_bundle_member(info: zipfile.ZipInfo) -> None:
    if info.file_size > MAX_BUNDLE_MEMBER_BYTES:
        raise ValueError(
            f"bundle member {info.filename!r} exceeds {MAX_BUNDLE_MEMBER_BYTES} bytes"
        )
    if info.file_size and info.compress_size == 0:
        raise ValueError(f"bundle member {info.filename!r} has suspicious compression metadata")
    if info.compress_size and info.file_size / info.compress_size > MAX_BUNDLE_COMPRESSION_RATIO:
        raise ValueError(f"bundle member {info.filename!r} has suspicious compression ratio")


def normalize_export(input_path: str | Path, provider: str | None = None) -> list[dict[str, Any]]:
    data = load_conversations(str(input_path))
    formatter = _FORMATTER_BY_NAME.get(provider) if provider else detect_provider(data)
    if formatter is None:
        raise ValueError(
            "Could not auto-detect provider; pass one of: chatgpt, claude, deepseek"
        )

    records = [formatter.conv_to_json_clean(conv) for conv in data]
    for record in records:
        validate_conversation(record)
    return records


def build_bundle(
    input_path: str | Path,
    output_path: str | Path,
    provider: str | None = None,
) -> dict[str, Any]:
    records = normalize_export(input_path, provider=provider)
    providers = sorted({record["provider"] for record in records})
    manifest = {
        "schema_version": BUNDLE_SCHEMA,
        "conversation_schema": CONVERSATION_SCHEMA,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "conversation_count": len(records),
        "providers": providers,
        "files": {
            "conversations": BUNDLE_CONVERSATIONS,
            "search": BUNDLE_SEARCH,
        },
    }
    search_index = [
        {
            "id": record["id"],
            "provider": record["provider"],
            "title": record["title"],
            "text": searchable_text(record),
        }
        for record in records
    ]

    destination = Path(output_path)
    if destination.suffix.lower() != ".cew":
        destination = destination.with_suffix(".cew")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(BUNDLE_MANIFEST, _json_bytes(manifest))
        zf.writestr(BUNDLE_CONVERSATIONS, _json_bytes(records))
        zf.writestr(BUNDLE_SEARCH, _json_bytes(search_index))

    return {**manifest, "path": str(destination)}


def read_bundle(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    source = Path(path)
    with zipfile.ZipFile(source) as zf:
        infos = {info.filename: info for info in zf.infolist() if not info.is_dir()}
        required = {BUNDLE_MANIFEST, BUNDLE_CONVERSATIONS, BUNDLE_SEARCH}
        missing = required - infos.keys()
        if missing:
            raise ValueError(f"bundle is missing required members: {sorted(missing)}")
        unexpected = set(infos) - required
        if unexpected:
            raise ValueError(f"bundle contains unsupported members: {sorted(unexpected)}")
        for info in infos.values():
            _validate_bundle_member(info)

        manifest = json.loads(zf.read(infos[BUNDLE_MANIFEST]).decode("utf-8"))
        conversations = json.loads(zf.read(infos[BUNDLE_CONVERSATIONS]).decode("utf-8"))
        search_index = json.loads(zf.read(infos[BUNDLE_SEARCH]).decode("utf-8"))

    if manifest.get("schema_version") != BUNDLE_SCHEMA:
        raise ValueError(f"unsupported bundle schema: {manifest.get('schema_version')!r}")
    if manifest.get("conversation_schema") != CONVERSATION_SCHEMA:
        raise ValueError("bundle canonical-conversation schema does not match this reader")
    if not isinstance(conversations, list) or not isinstance(search_index, list):
        raise ValueError("bundle payloads must be JSON arrays")
    if manifest.get("conversation_count") != len(conversations):
        raise ValueError("bundle manifest conversation_count does not match payload")
    for record in conversations:
        validate_conversation(record)

    return manifest, conversations, search_index
