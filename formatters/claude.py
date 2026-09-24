"""Claude (Anthropic) conversation export formatter."""

import html
import json

from canonical import canonical_conversation, canonical_message
from canonical_render import render_canonical_html_body, render_canonical_markdown
from .shared import (
    fmt_date, iso_to_epoch_ms, markdown_to_html, render_template
)


PROVIDER    = "claude"
ID_FIELD    = "uuid"
TITLE_FIELD = "name"


def detect(data: list) -> bool:
    """Return True if data looks like a Claude (Anthropic) export."""
    return (
        bool(data)
        and isinstance(data[0], dict)
        and "chat_messages" in data[0]
        and "uuid" in data[0]
    )


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def conv_to_html_body(conv: dict) -> str:
    """Normalize provider input, then render the canonical model."""
    return render_canonical_html_body(conv_to_json_clean(conv))

def build_html_single(conv: dict) -> str:
    body = conv_to_html_body(conv)
    return render_template(conv.get("name", "Conversation"), body)


def build_html_all(convs: list) -> str:
    index_rows = []
    for c in convs:
        conv_id = html.escape(str(c.get("uuid", "")), quote=True)
        conv_title = html.escape(str(c.get("name", "Untitled")), quote=False)
        index_rows.append(f'<li><a href="#conv-{conv_id}">{conv_title}</a></li>')
    index_items = "".join(index_rows)
    index_html = (
        '<div id="index"><h2>Conversations</h2><ul>'
        f"{index_items}"
        "</ul></div>"
    )
    sections = []
    for conv in convs:
        anchor_id = html.escape(str(conv.get("uuid", "")), quote=True)
        anchor = f'<div id="conv-{anchor_id}" class="conv-header"></div>'
        sections.append(anchor + conv_to_html_body(conv))
        sections.append('<hr class="divider">')
    body = index_html + "\n".join(sections)
    return render_template("Claude Conversations", body)


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
    messages = conv.get("chat_messages", [])
    clean_messages = []
    for msg in messages:
        sender = msg.get("sender", "")
        role = "user" if sender == "human" else "assistant"
        parts = []
        for block in _get_content_blocks(msg):
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                parts.append({"type": "text", "content": block.get("text", "")})
            elif btype == "thinking":
                parts.append({"type": "thinking", "content": block.get("thinking", "")})
            elif btype == "tool_use":
                parts.append({
                    "type": "tool_use",
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                })
            elif btype == "tool_result":
                parts.append({
                    "type": "tool_result",
                    "tool_use_id": block.get("tool_use_id", ""),
                    "content": block.get("content", ""),
                })
        clean_messages.append(
            canonical_message(
                role,
                msg.get("created_at", ""),
                parts,
                source_id=str(msg.get("uuid", "")),
            )
        )
    return canonical_conversation(
        PROVIDER,
        conv.get("uuid", ""),
        conv.get("name", ""),
        conv.get("created_at", ""),
        conv.get("updated_at", ""),
        clean_messages,
    )


def build_json_single(conv: dict) -> str:
    return json.dumps(conv_to_json_clean(conv), indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_content_blocks(msg: dict) -> list:
    """Return content block list, falling back to msg['text'] if empty."""
    blocks = msg.get("content", [])
    if not blocks:
        text = msg.get("text", "")
        if text:
            return [{"type": "text", "text": text}]
    return blocks
