"""Provider-neutral conversation model used by exports, bundles, search, and mobile clients."""

from __future__ import annotations

import json
from typing import Any

CONVERSATION_SCHEMA = "cew.conversation/v1"
ALLOWED_ROLES = {"user", "assistant", "system", "tool"}
ALLOWED_PART_TYPES = {
    "text",
    "thinking",
    "tool_use",
    "tool_result",
    "search",
    "read_link",
    "attachment",
}


def canonical_message(
    role: str,
    timestamp: str = "",
    parts: list[dict[str, Any]] | None = None,
    *,
    model: str = "",
    source_id: str = "",
) -> dict[str, Any]:
    role_value = role if role in ALLOWED_ROLES else "assistant"
    message: dict[str, Any] = {
        "role": role_value,
        "timestamp": str(timestamp or ""),
        "parts": list(parts or []),
    }
    if model:
        message["model"] = str(model)
    if source_id:
        message["source_id"] = str(source_id)
    return message


def canonical_conversation(
    provider: str,
    conversation_id: str,
    title: str,
    started_at: str,
    updated_at: str,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    record = {
        "schema_version": CONVERSATION_SCHEMA,
        "provider": str(provider),
        "id": str(conversation_id or ""),
        "title": str(title or ""),
        "started_at": str(started_at or ""),
        "updated_at": str(updated_at or ""),
        "messages": messages,
    }
    validate_conversation(record)
    return record


def validate_conversation(record: dict[str, Any]) -> None:
    if record.get("schema_version") != CONVERSATION_SCHEMA:
        raise ValueError("unsupported canonical conversation schema")
    if not isinstance(record.get("provider"), str) or not record["provider"]:
        raise ValueError("canonical conversation provider is required")
    if not isinstance(record.get("messages"), list):
        raise ValueError("canonical conversation messages must be a list")

    for index, message in enumerate(record["messages"]):
        if not isinstance(message, dict):
            raise ValueError(f"message {index} must be an object")
        if message.get("role") not in ALLOWED_ROLES:
            raise ValueError(f"message {index} has unsupported role")
        parts = message.get("parts")
        if not isinstance(parts, list):
            raise ValueError(f"message {index} parts must be a list")
        for part_index, part in enumerate(parts):
            if not isinstance(part, dict):
                raise ValueError(f"message {index} part {part_index} must be an object")
            if part.get("type") not in ALLOWED_PART_TYPES:
                raise ValueError(
                    f"message {index} part {part_index} has unsupported type {part.get('type')!r}"
                )


def searchable_text(record: dict[str, Any]) -> str:
    """Return deterministic plain text for local search indexing."""
    chunks = [str(record.get("title", ""))]
    for message in record.get("messages", []):
        for part in message.get("parts", []):
            part_type = part.get("type")
            if part_type in {"text", "thinking"}:
                chunks.append(str(part.get("content", "")))
            elif part_type == "search":
                for result in part.get("results", []):
                    if isinstance(result, dict):
                        chunks.extend(
                            str(result.get(key, ""))
                            for key in ("title", "snippet", "url")
                            if result.get(key)
                        )
            elif part_type == "read_link":
                chunks.append(str(part.get("url", "")))
            elif part_type == "tool_use":
                chunks.append(str(part.get("name", "")))
                chunks.append(json.dumps(part.get("input", {}), sort_keys=True, ensure_ascii=False))
            elif part_type == "tool_result":
                content = part.get("content", "")
                if isinstance(content, (dict, list)):
                    chunks.append(json.dumps(content, sort_keys=True, ensure_ascii=False))
                else:
                    chunks.append(str(content))
            elif part_type == "attachment":
                chunks.append(str(part.get("name", "")))
    return "\n".join(chunk for chunk in chunks if chunk)
