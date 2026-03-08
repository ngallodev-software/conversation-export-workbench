"""Claude (Anthropic) conversation export formatter."""

import json

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
    """Return the inner HTML body for a single conversation (no full-page wrapper)."""
    title = conv.get("name", "Untitled")
    created_iso = conv.get("created_at", "")
    updated_iso = conv.get("updated_at", "")
    created_epoch = iso_to_epoch_ms(created_iso)
    updated_epoch = iso_to_epoch_ms(updated_iso)
    messages = conv.get("chat_messages", [])

    parts = [
        f'<h1>{title}</h1>',
        f'<div class="meta"'
        f' data-started-ts="{created_epoch}"'
        f' data-updated-ts="{updated_epoch}"'
        f' data-started-iso="{created_iso}"'
        f' data-updated-iso="{updated_iso}">'
        f'Started <span class="ts-display">{fmt_date(created_iso)}</span>'
        f' &nbsp;·&nbsp; '
        f'Last updated <span class="ts-display">{fmt_date(updated_iso)}</span>'
        f'</div>',
    ]

    for msg in messages:
        sender = msg.get("sender", "")
        msg_iso   = msg.get("created_at", "")
        msg_epoch = iso_to_epoch_ms(msg_iso)
        timestamp = fmt_date(msg_iso)
        content_blocks = _get_content_blocks(msg)

        if sender == "human":
            html_parts = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    html_parts.append(markdown_to_html(block.get("text", "")))
            html_content = "\n".join(html_parts) or "<em>(empty)</em>"
            parts.append(
                f'<div class="message user" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">'
                f'<div class="role-label">You'
                f' <span class="msg-time ts-display" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">{timestamp}</span>'
                f'</div>'
                f'<div class="content">{html_content}</div>'
                f"</div>"
            )
        elif sender == "assistant":
            inner_parts = []
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type", "")
                if btype == "thinking":
                    raw = block.get("thinking", "")
                    escaped = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    lines_html = "<br>".join(escaped.splitlines())
                    inner_parts.append(
                        '<div class="thinking">'
                        '<div class="thinking-label">Thinking</div>'
                        f"{lines_html}"
                        "</div>"
                    )
                elif btype == "text":
                    html = markdown_to_html(block.get("text", ""))
                    inner_parts.append(f'<div class="content">{html}</div>')
                # tool_use / tool_result blocks silently skipped
            inner = "\n".join(inner_parts) or "<em>(empty)</em>"
            parts.append(
                f'<div class="message assistant" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">'
                f'<div class="role-label">Claude'
                f' <span class="msg-time ts-display" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">{timestamp}</span>'
                f'</div>'
                f"{inner}"
                f"</div>"
            )

    return "\n".join(parts)


def build_html_single(conv: dict) -> str:
    body = conv_to_html_body(conv)
    return render_template(conv.get("name", "Conversation"), body)


def build_html_all(convs: list) -> str:
    index_items = "".join(
        f'<li><a href="#conv-{c["uuid"]}">{c.get("name","Untitled")}</a></li>'
        for c in convs
    )
    index_html = (
        '<div id="index"><h2>Conversations</h2><ul>'
        f"{index_items}"
        "</ul></div>"
    )
    sections = []
    for conv in convs:
        anchor = f'<div id="conv-{conv["uuid"]}" class="conv-header"></div>'
        sections.append(anchor + conv_to_html_body(conv))
        sections.append('<hr class="divider">')
    body = index_html + "\n".join(sections)
    return render_template("Claude Conversations", body)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def conv_to_md(conv: dict) -> str:
    title = conv.get("name", "Untitled")
    created = fmt_date(conv.get("created_at", ""))
    updated = fmt_date(conv.get("updated_at", ""))
    messages = conv.get("chat_messages", [])

    lines = [f"# {title}", "", f"*Started: {created} | Last updated: {updated}*", "", "---", ""]
    for msg in messages:
        sender = msg.get("sender", "")
        timestamp = fmt_date(msg.get("created_at", ""))
        label = "You" if sender == "human" else "Claude"
        lines.append(f"## {label}  _{timestamp}_")
        lines.append("")
        for block in _get_content_blocks(msg):
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "thinking":
                raw = block.get("thinking", "")
                block_lines = raw.splitlines()
                formatted = "\n".join(f"> *{l}*" if l.strip() else ">" for l in block_lines)
                lines.append(f"**Thinking:**\n\n{formatted}\n")
            elif btype == "text":
                lines.append(block.get("text", ""))
        lines += ["", "---", ""]
    return "\n".join(lines)


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
        clean_messages.append({
            "role": role,
            "timestamp": msg.get("created_at", ""),
            "parts": parts,
        })
    return {
        "id": conv["uuid"],
        "title": conv.get("name", ""),
        "started_at": conv.get("created_at", ""),
        "updated_at": conv.get("updated_at", ""),
        "messages": clean_messages,
    }


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
