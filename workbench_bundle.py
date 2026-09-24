"""Portable Conversation Export Workbench (.cew) bundle support."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from canonical import CONVERSATION_SCHEMA, searchable_text, validate_conversation
from format_conversations import detect_provider, load_conversations
from formatters import chatgpt, claude, deepseek

BUNDLE_SCHEMA_V1 = "cew.bundle/v1"
BUNDLE_SCHEMA = "cew.bundle/v2"
SUPPORTED_BUNDLE_SCHEMAS = {BUNDLE_SCHEMA_V1, BUNDLE_SCHEMA}
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


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_bundle_member(info: zipfile.ZipInfo) -> None:
    if info.file_size > MAX_BUNDLE_MEMBER_BYTES:
        raise ValueError(
            f"bundle member {info.filename!r} exceeds {MAX_BUNDLE_MEMBER_BYTES} bytes"
        )
    if info.file_size and info.compress_size == 0:
        raise ValueError(f"bundle member {info.filename!r} has suspicious compression metadata")
    if info.compress_size and info.file_size / info.compress_size > MAX_BUNDLE_COMPRESSION_RATIO:
        raise ValueError(f"bundle member {info.filename!r} has suspicious compression ratio")


def _record_key(record: dict[str, Any]) -> tuple[str, str]:
    return str(record.get("provider", "")), str(record.get("id", ""))


def _record_rank(record: dict[str, Any]) -> tuple[str, str, bytes]:
    return (
        str(record.get("updated_at", "")),
        str(record.get("started_at", "")),
        _json_bytes(record),
    )


def merge_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Deterministically de-duplicate canonical conversations.

    Provider + source conversation ID forms the identity. The newest updated_at
    record wins; ties are broken deterministically from canonical JSON bytes.
    """
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_count = 0
    for record in records:
        validate_conversation(record)
        key = _record_key(record)
        if not key[0] or not key[1]:
            raise ValueError("canonical conversations require provider and id for bundle merge")
        existing = selected.get(key)
        if existing is None:
            selected[key] = record
            continue
        duplicate_count += 1
        if _record_rank(record) > _record_rank(existing):
            selected[key] = record

    merged = sorted(
        selected.values(),
        key=lambda record: (
            str(record.get("provider", "")),
            str(record.get("updated_at", "")),
            str(record.get("id", "")),
        ),
    )
    return merged, duplicate_count


def normalize_export(input_path: str | Path, provider: str | None = None) -> list[dict[str, Any]]:
    data = load_conversations(str(input_path))
    formatter = _FORMATTER_BY_NAME.get(provider) if provider else detect_provider(data)
    if formatter is None:
        raise ValueError(
            "Could not auto-detect provider; pass one of: chatgpt, claude, deepseek"
        )

    records = [formatter.conv_to_json_clean(conv) for conv in data]
    records, _ = merge_records(records)
    return records


def _search_index(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": record["id"],
            "provider": record["provider"],
            "title": record["title"],
            "text": searchable_text(record),
        }
        for record in records
    ]


def _bundle_id(records: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_json_bytes(records)).hexdigest()


def _write_bundle(
    destination: str | Path,
    records: list[dict[str, Any]],
    *,
    sources: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
    duplicate_count: int = 0,
) -> dict[str, Any]:
    records, internal_duplicates = merge_records(records)
    duplicate_count += internal_duplicates
    providers = sorted({record["provider"] for record in records})
    search_index = _search_index(records)
    manifest = {
        "schema_version": BUNDLE_SCHEMA,
        "conversation_schema": CONVERSATION_SCHEMA,
        "bundle_id": _bundle_id(records),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "conversation_count": len(records),
        "providers": providers,
        "duplicate_records_resolved": duplicate_count,
        "sources": sources,
        "history": list(history or []),
        "files": {
            "conversations": BUNDLE_CONVERSATIONS,
            "search": BUNDLE_SEARCH,
        },
    }

    output = Path(destination)
    if output.suffix.lower() != ".cew":
        output = output.with_suffix(".cew")
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(BUNDLE_MANIFEST, _json_bytes(manifest))
        zf.writestr(BUNDLE_CONVERSATIONS, _json_bytes(records))
        zf.writestr(BUNDLE_SEARCH, _json_bytes(search_index))

    return {**manifest, "path": str(output)}


def build_bundle(
    input_path: str | Path,
    output_path: str | Path,
    provider: str | None = None,
) -> dict[str, Any]:
    source = Path(input_path)
    records = normalize_export(source, provider=provider)
    detected_provider = records[0]["provider"] if records else (provider or "unknown")
    source_info = {
        "kind": "provider-export",
        "filename": source.name,
        "sha256": _sha256_file(source),
        "provider": detected_provider,
    }
    return _write_bundle(output_path, records, sources=[source_info])


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

    schema = manifest.get("schema_version")
    if schema not in SUPPORTED_BUNDLE_SCHEMAS:
        raise ValueError(f"unsupported bundle schema: {schema!r}")
    if manifest.get("conversation_schema") != CONVERSATION_SCHEMA:
        raise ValueError("bundle canonical-conversation schema does not match this reader")
    if not isinstance(conversations, list) or not isinstance(search_index, list):
        raise ValueError("bundle payloads must be JSON arrays")
    if manifest.get("conversation_count") != len(conversations):
        raise ValueError("bundle manifest conversation_count does not match payload")
    for record in conversations:
        validate_conversation(record)

    if schema == BUNDLE_SCHEMA:
        expected_id = _bundle_id(conversations)
        if manifest.get("bundle_id") != expected_id:
            raise ValueError("bundle_id does not match canonical conversation payload")
        if not isinstance(manifest.get("sources", []), list):
            raise ValueError("bundle sources must be a list")

    return manifest, conversations, search_index


def merge_bundles(
    input_paths: Iterable[str | Path],
    output_path: str | Path,
) -> dict[str, Any]:
    all_records: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []

    for raw_path in input_paths:
        path = Path(raw_path)
        manifest, conversations, _ = read_bundle(path)
        all_records.extend(conversations)
        schema = str(manifest.get("schema_version", ""))
        history.append(
            {
                "kind": "bundle-merge",
                "filename": path.name,
                "sha256": _sha256_file(path),
                "schema_version": schema,
                "bundle_id": manifest.get("bundle_id", ""),
            }
        )
        manifest_sources = manifest.get("sources")
        if isinstance(manifest_sources, list):
            for source in manifest_sources:
                if isinstance(source, dict):
                    sources.append(source)
        else:
            sources.append(
                {
                    "kind": "legacy-bundle",
                    "filename": path.name,
                    "sha256": _sha256_file(path),
                }
            )

    merged_records, duplicates = merge_records(all_records)

    unique_sources: dict[tuple[str, str], dict[str, Any]] = {}
    for source in sources:
        key = (str(source.get("kind", "")), str(source.get("sha256", "")))
        unique_sources[key] = source

    return _write_bundle(
        output_path,
        merged_records,
        sources=list(unique_sources.values()),
        history=history,
        duplicate_count=duplicates,
    )
