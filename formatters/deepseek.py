"""DeepSeek conversation export formatter."""

import json

from .shared import (
    fmt_date, iso_to_epoch_ms, markdown_to_html, render_template
)


PROVIDER = "deepseek"
ID_FIELD    = "id"
TITLE_FIELD = "title"


def detect(data: list) -> bool:
    """Return True if data looks like a DeepSeek export."""
    return bool(data) and isinstance(data[0], dict) and "mapping" in data[0]


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def walk_tree(mapping: dict) -> list:
    """Walk the conversation tree from root, returning messages in order."""
    messages = []
    node_id = "root"
    while node_id:
        node = mapping.get(node_id)
        if not node:
            break
        msg = node.get("message")
        if msg:
            messages.append(msg)
        children = node.get("children") or []
        node_id = children[0] if children else None
    return messages


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _render_fragment_html(frag: dict) -> str:
    ftype = frag.get("type", "")

    if ftype == "REQUEST":
        return ""

    if ftype == "THINK":
        content = frag.get("content", "")
        escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines_html = "<br>".join(escaped.splitlines())
        return (
            '<div class="thinking">'
            '<div class="thinking-label">Thinking</div>'
            f"{lines_html}"
            "</div>"
        )

    if ftype == "SEARCH":
        results = frag.get("results", [])
        items = ""
        for r in results[:5]:
            url = r.get("url", "")
            title = r.get("title", url)
            snippet = r.get("snippet", "")
            items += (
                f'<div class="search-result">'
                f'<a href="{url}" target="_blank">{title}</a>'
                + (f'<div class="snippet">{snippet[:160]}</div>' if snippet else "")
                + "</div>"
            )
        return (
            '<div class="search-block">'
            '<div class="search-label">Web Search</div>'
            f"{items}"
            "</div>"
        )

    if ftype == "READ_LINK":
        url = frag.get("url", "")
        return f'<div class="read-link-block">Read page: <a href="{url}" target="_blank">{url}</a></div>'

    if ftype == "RESPONSE":
        content = frag.get("content", "")
        html = markdown_to_html(content)
        return f'<div class="content">{html}</div>'

    return ""


def conv_to_html_body(conv: dict) -> str:
    """Return the inner HTML body for a single conversation (no full-page wrapper)."""
    title = conv.get("title", "Untitled")
    inserted_iso = conv.get("inserted_at", "")
    updated_iso  = conv.get("updated_at", "")
    inserted_epoch = iso_to_epoch_ms(inserted_iso)
    updated_epoch  = iso_to_epoch_ms(updated_iso)
    messages = walk_tree(conv["mapping"])

    parts = [
        f'<h1>{title}</h1>',
        f'<div class="meta"'
        f' data-started-ts="{inserted_epoch}"'
        f' data-updated-ts="{updated_epoch}"'
        f' data-started-iso="{inserted_iso}"'
        f' data-updated-iso="{updated_iso}">'
        f'Started <span class="ts-display">{fmt_date(inserted_iso)}</span>'
        f' &nbsp;·&nbsp; '
        f'Last updated <span class="ts-display">{fmt_date(updated_iso)}</span>'
        f'</div>',
    ]

    for msg in messages:
        frags = msg.get("fragments", [])
        if not frags:
            continue
        role = frags[0]["type"]
        msg_iso   = msg.get("inserted_at", "")
        msg_epoch = iso_to_epoch_ms(msg_iso)
        timestamp = fmt_date(msg_iso)

        if role == "REQUEST":
            content = frags[0].get("content", "")
            html_content = markdown_to_html(content)
            parts.append(
                f'<div class="message user" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">'
                f'<div class="role-label">You'
                f' <span class="msg-time ts-display" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">{timestamp}</span>'
                f'</div>'
                f'<div class="content">{html_content}</div>'
                f"</div>"
            )
        else:
            inner = "".join(_render_fragment_html(f) for f in frags)
            parts.append(
                f'<div class="message assistant" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">'
                f'<div class="role-label">DeepSeek'
                f' <span class="msg-time ts-display" data-ts="{msg_epoch}" data-ts-iso="{msg_iso}">{timestamp}</span>'
                f'</div>'
                f"{inner}"
                f"</div>"
            )

    return "\n".join(parts)


def build_html_single(conv: dict) -> str:
    body = conv_to_html_body(conv)
    return render_template(conv.get("title", "Conversation"), body)


def build_html_all(convs: list) -> str:
    index_items = "".join(
        f'<li><a href="#conv-{c["id"]}">{c.get("title","Untitled")}</a></li>'
        for c in convs
    )
    index_html = (
        '<div id="index"><h2>Conversations</h2><ul>'
        f"{index_items}"
        "</ul></div>"
    )
    sections = []
    for conv in convs:
        anchor = f'<div id="conv-{conv["id"]}" class="conv-header"></div>'
        sections.append(anchor + conv_to_html_body(conv))
        sections.append('<hr class="divider">')
    body = index_html + "\n".join(sections)
    return render_template("DeepSeek Conversations", body)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def _fragment_to_md(frag: dict) -> str:
    ftype = frag.get("type", "")
    if ftype == "THINK":
        content = frag.get("content", "")
        block_lines = content.splitlines()
        formatted = "\n".join(f"> *{l}*" if l.strip() else ">" for l in block_lines)
        return f"**Thinking:**\n\n{formatted}\n\n"
    if ftype == "SEARCH":
        results = frag.get("results", [])
        lines = ["**Web Search:**\n"]
        for r in results[:5]:
            url = r.get("url", "")
            title = r.get("title", url)
            snippet = r.get("snippet", "")
            lines.append(f"- [{title}]({url})")
            if snippet:
                lines.append(f"  *{snippet[:160]}*")
        return "\n".join(lines) + "\n\n"
    if ftype == "READ_LINK":
        url = frag.get("url", "")
        return f"**Read page:** {url}\n\n"
    if ftype == "RESPONSE":
        return frag.get("content", "") + "\n\n"
    return ""


def conv_to_md(conv: dict) -> str:
    title = conv.get("title", "Untitled")
    inserted = fmt_date(conv.get("inserted_at", ""))
    updated  = fmt_date(conv.get("updated_at", ""))
    messages = walk_tree(conv["mapping"])

    lines = [f"# {title}", "", f"*Started: {inserted} | Last updated: {updated}*", "", "---", ""]
    for msg in messages:
        frags = msg.get("fragments", [])
        if not frags:
            continue
        role = frags[0]["type"]
        timestamp = fmt_date(msg.get("inserted_at", ""))
        if role == "REQUEST":
            content = frags[0].get("content", "")
            lines += [f"## You  _{timestamp}_", "", content, "", "---", ""]
        else:
            lines.append(f"## DeepSeek  _{timestamp}_")
            lines.append("")
            for f in frags:
                lines.append(_fragment_to_md(f))
            lines += ["---", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def conv_to_json_clean(conv: dict) -> dict:
    messages = walk_tree(conv["mapping"])
    clean_messages = []
    for msg in messages:
        frags = msg.get("fragments", [])
        if not frags:
            continue
        role = "user" if frags[0]["type"] == "REQUEST" else "assistant"
        parts = []
        for f in frags:
            ftype = f.get("type")
            if ftype == "REQUEST":
                parts.append({"type": "text", "content": f.get("content", "")})
            elif ftype == "RESPONSE":
                parts.append({"type": "text", "content": f.get("content", "")})
            elif ftype == "THINK":
                parts.append({"type": "thinking", "content": f.get("content", "")})
            elif ftype == "SEARCH":
                parts.append({"type": "search", "results": f.get("results", [])})
            elif ftype == "READ_LINK":
                parts.append({"type": "read_link", "url": f.get("url", "")})
        clean_messages.append({
            "role": role,
            "timestamp": msg.get("inserted_at", ""),
            "model": msg.get("model", ""),
            "parts": parts,
        })
    return {
        "id": conv["id"],
        "title": conv.get("title", ""),
        "started_at": conv.get("inserted_at", ""),
        "updated_at": conv.get("updated_at", ""),
        "messages": clean_messages,
    }


def build_json_single(conv: dict) -> str:
    return json.dumps(conv_to_json_clean(conv), indent=2, ensure_ascii=False)
