"""ChatGPT (OpenAI) conversation export formatter."""

import html
import json
from datetime import datetime, timezone

from canonical import canonical_conversation, canonical_message
from canonical_render import render_canonical_html_body, render_canonical_markdown
from .shared import (
    fmt_date, markdown_to_html, render_template
)


PROVIDER    = "chatgpt"
ID_FIELD    = "id"
TITLE_FIELD = "title"


def detect(data: list) -> bool:
    """Return True if data looks like a ChatGPT export."""
    return (
        bool(data)
        and isinstance(data[0], dict)
        and "mapping" in data[0]
        and "current_node" in data[0]
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _epoch_to_iso(t: float | None) -> str:
    """Convert float unix seconds to ISO 8601 string, or '' on failure."""
    if not t:
        return ""
    try:
        return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


def _epoch_to_epoch_ms(t: float | None) -> int:
    """Convert float unix seconds to integer milliseconds, or 0."""
    if not t:
        return 0
    try:
        return int(t * 1000)
    except Exception:
        return 0


def _fmt_epoch(t: float | None) -> str:
    """Human-readable date from float unix seconds."""
    if not t:
        return ""
    return fmt_date(_epoch_to_iso(t))


# ---------------------------------------------------------------------------
# Tree walker
# ---------------------------------------------------------------------------

def walk_tree(mapping: dict, current_node: str) -> list:
    """
    Walk the active branch from current_node back to root, then reverse.
    Returns ordered list of message objects (skipping None and system/weight=0).
    """
    path = []
    node_id = current_node
    visited: set[str] = set()
    max_nodes = max(len(mapping) + 1, 1)
    while node_id:
        if node_id in visited or len(visited) >= max_nodes:
            break
        visited.add(node_id)
        node = mapping.get(node_id)
        if not node:
            break
        path.append(node_id)
        node_id = node.get("parent")
    path.reverse()

    messages = []
    for nid in path:
        node = mapping.get(nid, {})
        msg = node.get("message")
        if msg is None:
            continue
        role = msg.get("author", {}).get("role", "")
        if role == "system":
            continue
        weight = msg.get("weight", 1)
        if weight == 0:
            continue
        messages.append(msg)
    return messages


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _message_to_html(msg: dict) -> str:
    role = msg.get("author", {}).get("role", "")
    if role not in ("user", "assistant"):
        return ""

    content = msg.get("content", {})
    content_type = content.get("content_type", "")
    if content_type not in ("text", "multimodal_text"):
        return ""

    parts = content.get("parts", [])
    text = "\n".join(str(p) for p in parts if isinstance(p, str)).strip()
    if not text:
        return ""

    ts_float = msg.get("create_time")
    msg_epoch = _epoch_to_epoch_ms(ts_float)
    msg_iso   = _epoch_to_iso(ts_float)
    timestamp = _fmt_epoch(ts_float)

    html_content = markdown_to_html(text)

    if role == "user":
        return (
            f'<div class="message user" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">'
            f'<div class="role-label">You'
            f' <span class="msg-time ts-display" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">{timestamp}</span>'
            f'</div>'
            f'<div class="content">{html_content}</div>'
            f'</div>'
        )
    else:
        return (
            f'<div class="message assistant" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">'
            f'<div class="role-label">ChatGPT'
            f' <span class="msg-time ts-display" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">{timestamp}</span>'
            f'</div>'
            f'<div class="content">{html_content}</div>'
            f'</div>'
        )


def conv_to_html_body(conv: dict) -> str:
    """Normalize provider input, then render the canonical model."""
    return render_canonical_html_body(conv_to_json_clean(conv))

def build_html_single(conv: dict) -> str:
    body = conv_to_html_body(conv)
    return render_template(conv.get("title", "Conversation"), body)


def build_html_all(convs: list) -> str:
    index_rows = []
    for c in convs:
        conv_id = html.escape(str(c.get("id", "")), quote=True)
        conv_title = html.escape(str(c.get("title", "Untitled")), quote=False)
        index_rows.append(f'<li><a href="#conv-{conv_id}">{conv_title}</a></li>')
    index_items = "".join(index_rows)
    index_html = (
        '<div id="index"><h2>Conversations</h2><ul>'
        f"{index_items}"
        "</ul></div>"
    )
    sections = []
    for conv in convs:
        anchor_id = html.escape(str(conv.get("id", "")), quote=True)
        anchor = f'<div id="conv-{anchor_id}" class="conv-header"></div>'
        sections.append(anchor + conv_to_html_body(conv))
        sections.append('<hr class="divider">')
    body = index_html + "\n".join(sections)
    return render_template("ChatGPT Conversations", body)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def conv_to_md(conv: dict) -> str:
    """Normalize provider input, then render the canonical model."""
    return render_canonical_markdown(conv_to_json_clean(conv))


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def conv_to_json_clean(conv: dict) -> dict:
    messages = walk_tree(conv["mapping"], conv["current_node"])
    clean_messages = []
    for msg in messages:
        role = msg.get("author", {}).get("role", "")
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content", {})
        if content.get("content_type") not in ("text", "multimodal_text"):
            continue
        parts_raw = content.get("parts", [])
        text = "\n".join(str(p) for p in parts_raw if isinstance(p, str)).strip()
        if not text:
            continue
        clean_messages.append(
            canonical_message(
                role,
                _epoch_to_iso(msg.get("create_time")),
                [{"type": "text", "content": text}],
                source_id=str(msg.get("id", "")),
            )
        )
    return canonical_conversation(
        PROVIDER,
        conv.get("id", ""),
        conv.get("title", ""),
        _epoch_to_iso(conv.get("create_time")),
        _epoch_to_iso(conv.get("update_time")),
        clean_messages,
    )


def build_json_single(conv: dict) -> str:
    return json.dumps(conv_to_json_clean(conv), indent=2, ensure_ascii=False)
