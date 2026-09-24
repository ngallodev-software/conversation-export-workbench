"""Render provider-neutral canonical conversations to HTML and Markdown."""

from __future__ import annotations

import html
import json
from typing import Any

from canonical import validate_conversation
from formatters.shared import fmt_date, iso_to_epoch_ms, markdown_to_html, sanitize_href

_PROVIDER_LABELS = {
    "chatgpt": "ChatGPT",
    "claude": "Claude",
    "deepseek": "DeepSeek",
}


def _label(record: dict[str, Any], role: str) -> str:
    if role == "user":
        return "You"
    if role == "tool":
        return "Tool"
    if role == "system":
        return "System"
    return _PROVIDER_LABELS.get(str(record.get("provider", "")), "Assistant")


def _json_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)


def _render_search_html(part: dict[str, Any]) -> str:
    items = []
    for result in part.get("results", []):
        if not isinstance(result, dict):
            continue
        title = html.escape(str(result.get("title") or result.get("url") or "Result"), quote=False)
        snippet = html.escape(str(result.get("snippet", "")), quote=False)
        raw_url = str(result.get("url", ""))
        href = sanitize_href(raw_url)
        if href:
            title_html = (
                f'<a href="{html.escape(href, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">{title}</a>'
            )
        else:
            title_html = title
        items.append(
            '<div class="search-result">'
            f"{title_html}"
            + (f'<div class="snippet">{snippet}</div>' if snippet else "")
            + "</div>"
        )
    return (
        '<div class="search-block">'
        '<div class="search-label">Search results</div>'
        + "".join(items)
        + "</div>"
    )


def _render_part_html(part: dict[str, Any]) -> str:
    part_type = part.get("type")
    if part_type == "text":
        return f'<div class="content">{markdown_to_html(str(part.get("content", "")))}</div>'
    if part_type == "thinking":
        content = html.escape(str(part.get("content", "")), quote=False).replace("\n", "<br>")
        return (
            '<div class="thinking">'
            '<div class="thinking-label">Thinking</div>'
            f"{content}</div>"
        )
    if part_type == "search":
        return _render_search_html(part)
    if part_type == "read_link":
        raw_url = str(part.get("url", ""))
        label = html.escape(raw_url, quote=False)
        href = sanitize_href(raw_url)
        if href:
            link = (
                f'<a href="{html.escape(href, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">{label}</a>'
            )
        else:
            link = label
        return f'<div class="read-link-block">Read page: {link}</div>'
    if part_type == "tool_use":
        name = html.escape(str(part.get("name", "tool")), quote=False)
        payload = html.escape(_json_text(part.get("input", {})), quote=False)
        return (
            '<div class="search-block">'
            f'<div class="search-label">Tool use · {name}</div>'
            f'<div class="content"><pre><code>{payload}</code></pre></div>'
            "</div>"
        )
    if part_type == "tool_result":
        payload = html.escape(_json_text(part.get("content", "")), quote=False)
        return (
            '<div class="search-block">'
            '<div class="search-label">Tool result</div>'
            f'<div class="content"><pre><code>{payload}</code></pre></div>'
            "</div>"
        )
    if part_type == "attachment":
        name = html.escape(str(part.get("name", "attachment")), quote=False)
        mime = html.escape(str(part.get("mime_type", "")), quote=False)
        suffix = f" · {mime}" if mime else ""
        return f'<div class="read-link-block">Attachment: {name}{suffix}</div>'
    return ""


def render_canonical_html_body(record: dict[str, Any]) -> str:
    """Render one validated canonical conversation body."""
    validate_conversation(record)
    title = html.escape(str(record.get("title") or "Untitled"), quote=False)
    started = str(record.get("started_at", ""))
    updated = str(record.get("updated_at", ""))
    started_attr = html.escape(started, quote=True)
    updated_attr = html.escape(updated, quote=True)

    out = [
        f"<h1>{title}</h1>",
        (
            '<div class="meta"'
            f' data-started-ts="{iso_to_epoch_ms(started)}"'
            f' data-updated-ts="{iso_to_epoch_ms(updated)}"'
            f' data-started-iso="{started_attr}"'
            f' data-updated-iso="{updated_attr}">'
            f'Started <span class="ts-display">{html.escape(fmt_date(started), quote=False)}</span>'
            " &nbsp;·&nbsp; "
            f'Last updated <span class="ts-display">{html.escape(fmt_date(updated), quote=False)}</span>'
            "</div>"
        ),
    ]

    for message in record.get("messages", []):
        role = str(message.get("role", "assistant"))
        timestamp = str(message.get("timestamp", ""))
        ts_attr = html.escape(timestamp, quote=True)
        label = html.escape(_label(record, role), quote=False)
        rendered_parts = "".join(
            _render_part_html(part)
            for part in message.get("parts", [])
            if isinstance(part, dict)
        )
        if not rendered_parts:
            rendered_parts = "<em>(empty)</em>"
        css_role = "user" if role == "user" else "assistant"
        out.append(
            f'<div class="message {css_role}" data-ts="{iso_to_epoch_ms(timestamp)}" data-ts-iso="{ts_attr}">'
            f'<div class="role-label">{label}'
            f' <span class="msg-time ts-display" data-ts="{iso_to_epoch_ms(timestamp)}" '
            f'data-ts-iso="{ts_attr}">{html.escape(fmt_date(timestamp), quote=False)}</span>'
            "</div>"
            f"{rendered_parts}</div>"
        )
    return "\n".join(out)


def _render_part_markdown(part: dict[str, Any]) -> str:
    part_type = part.get("type")
    if part_type == "text":
        return str(part.get("content", ""))
    if part_type == "thinking":
        raw = str(part.get("content", ""))
        quoted = "\n".join(f"> *{line}*" if line.strip() else ">" for line in raw.splitlines())
        return f"**Thinking:**\n\n{quoted}"
    if part_type == "search":
        lines = ["**Search results:**"]
        for result in part.get("results", []):
            if not isinstance(result, dict):
                continue
            title = str(result.get("title") or result.get("url") or "Result")
            url = str(result.get("url", ""))
            snippet = str(result.get("snippet", ""))
            if sanitize_href(url):
                lines.append(f"- [{title}]({url})")
            else:
                lines.append(f"- {title}")
            if snippet:
                lines.append(f"  {snippet}")
        return "\n".join(lines)
    if part_type == "read_link":
        url = str(part.get("url", ""))
        return f"**Read page:** {url}"
    if part_type == "tool_use":
        return (
            f"**Tool use: {part.get('name', 'tool')}**\n\n"
            f"~~~json\n{_json_text(part.get('input', {}))}\n~~~"
        )
    if part_type == "tool_result":
        return f"**Tool result:**\n\n~~~json\n{_json_text(part.get('content', ''))}\n~~~"
    if part_type == "attachment":
        mime = str(part.get("mime_type", ""))
        suffix = f" ({mime})" if mime else ""
        return f"**Attachment:** {part.get('name', 'attachment')}{suffix}"
    return ""


def render_canonical_markdown(record: dict[str, Any]) -> str:
    """Render one validated canonical conversation to Markdown."""
    validate_conversation(record)
    lines = [
        f"# {record.get('title') or 'Untitled'}",
        "",
        f"*Started: {fmt_date(str(record.get('started_at', '')))} | "
        f"Last updated: {fmt_date(str(record.get('updated_at', '')))}*",
        "",
        "---",
        "",
    ]
    for message in record.get("messages", []):
        role = str(message.get("role", "assistant"))
        lines += [
            f"## {_label(record, role)}  _{fmt_date(str(message.get('timestamp', '')))}_",
            "",
        ]
        for part in message.get("parts", []):
            if not isinstance(part, dict):
                continue
            rendered = _render_part_markdown(part)
            if rendered:
                lines += [rendered, ""]
        lines += ["---", ""]
    return "\n".join(lines)
