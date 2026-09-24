"""DeepSeek conversation export formatter."""

import html
import json

from canonical import canonical_conversation, canonical_message
from canonical_render import render_canonical_html_body, render_canonical_markdown
from .shared import (
    fmt_date, iso_to_epoch_ms, markdown_to_html, render_template, sanitize_href
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
    visited: set[str] = set()
    max_nodes = max(len(mapping) + 1, 1)
    while node_id:
        if node_id in visited or len(visited) >= max_nodes:
            break
        visited.add(node_id)
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
            url = str(r.get("url", ""))
            title = str(r.get("title", url))
            snippet = str(r.get("snippet", ""))
            safe_url = sanitize_href(url)
            title_html = html.escape(title, quote=False)
            snippet_html = html.escape(snippet[:160], quote=False)
            link_html = title_html
            if safe_url:
                url_attr = html.escape(safe_url, quote=True)
                link_html = f'<a href="{url_attr}" target="_blank" rel="noopener noreferrer">{title_html}</a>'
            items += (
                f'<div class="search-result">'
                f'{link_html}'
                + (f'<div class="snippet">{snippet_html}</div>' if snippet else "")
                + "</div>"
            )
        return (
            '<div class="search-block">'
            '<div class="search-label">Web Search</div>'
            f"{items}"
            "</div>"
        )

    if ftype == "READ_LINK":
        url = str(frag.get("url", ""))
        safe_url = sanitize_href(url)
        url_html = html.escape(url, quote=False)
        if not safe_url:
            return f'<div class="read-link-block">Read page: {url_html}</div>'
        url_attr = html.escape(safe_url, quote=True)
        return f'<div class="read-link-block">Read page: <a href="{url_attr}" target="_blank" rel="noopener noreferrer">{url_html}</a></div>'

    if ftype == "RESPONSE":
        content = frag.get("content", "")
        rendered_html = markdown_to_html(content)
        return f'<div class="content">{rendered_html}</div>'

    return ""


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
    """Normalize provider input, then render the canonical model."""
    return render_canonical_markdown(conv_to_json_clean(conv))


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
        clean_messages.append(
            canonical_message(
                role,
                msg.get("inserted_at", ""),
                parts,
                model=str(msg.get("model", "") or ""),
            )
        )
    return canonical_conversation(
        PROVIDER,
        conv.get("id", ""),
        conv.get("title", ""),
        conv.get("inserted_at", ""),
        conv.get("updated_at", ""),
        clean_messages,
    )


def build_json_single(conv: dict) -> str:
    return json.dumps(conv_to_json_clean(conv), indent=2, ensure_ascii=False)
