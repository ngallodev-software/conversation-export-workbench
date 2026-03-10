"""Shared utilities: date helpers, slugify, markdown→HTML, HTML template."""

import html
import re
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Date / time helpers
# ---------------------------------------------------------------------------

def fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso


def fmt_date_full(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%A, %d %B %Y at %H:%M")
    except Exception:
        return iso


def iso_to_epoch_ms(iso: str) -> int:
    """Return milliseconds since epoch (for JS Date consumption), or 0 on error."""
    try:
        dt = datetime.fromisoformat(iso)
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")[:60]


def safe_write(path: Path, content: str, yes: bool) -> bool:
    """Write content to path. If file exists and yes=False, prompt the user.
    Returns True if the file was written, False if skipped."""
    if path.exists() and not yes:
        ans = input(f"Overwrite {path}? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print(f"Skipped: {path}")
            return False
    path.write_text(content, encoding="utf-8")
    print(f"Written: {path}")
    return True


# ---------------------------------------------------------------------------
# HTML template (shared across providers)
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%%TITLE%%</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0f1117;
    color: #e0e0e0;
    line-height: 1.7;
    padding: 2rem 1rem;
  }
  .container { max-width: 860px; margin: 0 auto; }
  h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 0.3rem;
  }
  .meta {
    font-size: 0.8rem;
    color: #666;
    margin-bottom: 2.5rem;
  }
  .message {
    margin-bottom: 1.8rem;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    position: relative;
  }
  .message.user {
    background: #1a1f2e;
    border-left: 3px solid #4a90e2;
  }
  .message.assistant {
    background: #141a14;
    border-left: 3px solid #5cb85c;
  }
  .role-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
    opacity: 0.6;
  }
  .message.user .role-label { color: #4a90e2; }
  .message.assistant .role-label { color: #5cb85c; }
  .msg-time {
    font-size: 0.72rem;
    color: #555;
    float: right;
    margin-top: 0.1rem;
  }
  .thinking {
    background: #1a1a10;
    border: 1px solid #3a3a20;
    border-radius: 6px;
    padding: 0.8rem 1.1rem;
    margin-bottom: 1rem;
    font-style: italic;
    color: #999;
    font-size: 0.88rem;
  }
  .thinking-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6a6a40;
    margin-bottom: 0.4rem;
  }
  .search-block {
    background: #111820;
    border: 1px dashed #2a3a50;
    border-radius: 6px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.8rem;
    font-size: 0.82rem;
    color: #7a9fc0;
  }
  .search-block .search-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #3a6a90;
    margin-bottom: 0.4rem;
  }
  .search-result {
    margin-top: 0.4rem;
    padding-left: 0.8rem;
    border-left: 2px solid #2a4a60;
  }
  .search-result a { color: #5a9fc0; text-decoration: none; }
  .search-result a:hover { text-decoration: underline; }
  .search-result .snippet { color: #668; font-size: 0.8rem; }
  .read-link-block {
    background: #11181a;
    border: 1px dashed #2a4040;
    border-radius: 6px;
    padding: 0.5rem 0.9rem;
    margin-bottom: 0.8rem;
    font-size: 0.8rem;
    color: #6ab;
  }
  .content p { margin-bottom: 0.8rem; }
  .content pre {
    background: #0a0a0a;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 1rem;
    overflow-x: auto;
    font-size: 0.85rem;
    margin-bottom: 0.8rem;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .content code {
    background: #1a1a1a;
    border-radius: 3px;
    padding: 0.1em 0.35em;
    font-size: 0.87em;
    font-family: "JetBrains Mono", "Fira Code", monospace;
  }
  .content pre code { background: none; padding: 0; }
  .content h1, .content h2, .content h3, .content h4 {
    color: #d0d0d0;
    margin: 1rem 0 0.5rem;
  }
  .content ul, .content ol {
    padding-left: 1.5rem;
    margin-bottom: 0.8rem;
  }
  .content li { margin-bottom: 0.3rem; }
  .content blockquote {
    border-left: 3px solid #444;
    padding-left: 1rem;
    color: #999;
    margin-bottom: 0.8rem;
  }
  .content table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 0.8rem;
    font-size: 0.88rem;
  }
  .content th, .content td {
    border: 1px solid #2a2a2a;
    padding: 0.4rem 0.7rem;
  }
  .content th { background: #1a1a1a; }
  .content hr { border: none; border-top: 1px solid #2a2a2a; margin: 1rem 0; }
  .content a { color: #4a90e2; }
  .divider {
    border: none;
    border-top: 1px solid #1e1e1e;
    margin: 2rem 0;
  }
  #index { margin-bottom: 2.5rem; }
  #index h2 { font-size: 1rem; color: #888; margin-bottom: 0.8rem; }
  #index ul { list-style: none; padding: 0; }
  #index li { margin-bottom: 0.4rem; }
  #index a { color: #4a90e2; text-decoration: none; font-size: 0.9rem; }
  #index a:hover { text-decoration: underline; }
  .conv-header { margin: 3rem 0 1rem; }
  .conv-header h2 { font-size: 1.25rem; color: #ccc; }
</style>
</head>
<body>
<div class="container">
%%BODY%%
</div>
</body>
</html>
"""


def render_template(title: str, body: str) -> str:
    safe_title = html.escape(str(title), quote=False)
    return HTML_TEMPLATE.replace("%%TITLE%%", safe_title).replace("%%BODY%%", body)


# ---------------------------------------------------------------------------
# Markdown → HTML (shared, no external deps)
# ---------------------------------------------------------------------------

def markdown_to_html(text: str) -> str:
    """Very lightweight Markdown → HTML converter."""
    def replace_code_block(m):
        lang = m.group(1) or ""
        code = m.group(2)
        code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cls = f' class="language-{lang}"' if lang else ""
        return f"<pre><code{cls}>{code}</code></pre>"

    text = re.sub(r"```(\w*)\n(.*?)```", replace_code_block, text, flags=re.DOTALL)

    lines = text.split("\n")
    html_lines = []
    in_ul = in_ol = in_table = False
    para_buf = []

    def flush_para():
        nonlocal para_buf
        if para_buf:
            joined = " ".join(para_buf).strip()
            if joined:
                html_lines.append(f"<p>{joined}</p>")
            para_buf = []

    def flush_ul():
        nonlocal in_ul
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False

    def flush_ol():
        nonlocal in_ol
        if in_ol:
            html_lines.append("</ol>")
            in_ol = False

    def flush_table():
        nonlocal in_table
        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False

    def inline(s: str) -> str:
        s = re.sub(r"\*\*\*(.*?)\*\*\*", r"<strong><em>\1</em></strong>", s)
        s = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"__(.*?)__", r"<strong>\1</strong>", s)
        s = re.sub(r"\*(.*?)\*", r"<em>\1</em>", s)
        s = re.sub(r"_((?!_).*?)_", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1).replace('<','&lt;').replace('>','&gt;')}</code>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s

    i = 0
    while i < len(lines):
        line = lines[i]

        hm = re.match(r"^(#{1,4})\s+(.*)", line)
        if hm:
            flush_para(); flush_ul(); flush_ol(); flush_table()
            level = len(hm.group(1))
            html_lines.append(f"<h{level}>{inline(hm.group(2))}</h{level}>")
            i += 1; continue

        if re.match(r"^[-*_]{3,}\s*$", line):
            flush_para(); flush_ul(); flush_ol(); flush_table()
            html_lines.append("<hr>")
            i += 1; continue

        if line.startswith("> "):
            flush_para(); flush_ul(); flush_ol(); flush_table()
            html_lines.append(f"<blockquote>{inline(line[2:])}</blockquote>")
            i += 1; continue

        ulm = re.match(r"^[-*+]\s+(.*)", line)
        if ulm:
            flush_para(); flush_ol(); flush_table()
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{inline(ulm.group(1))}</li>")
            i += 1; continue

        olm = re.match(r"^\d+\.\s+(.*)", line)
        if olm:
            flush_para(); flush_ul(); flush_table()
            if not in_ol:
                html_lines.append("<ol>")
                in_ol = True
            html_lines.append(f"<li>{inline(olm.group(1))}</li>")
            i += 1; continue

        if "|" in line and line.strip().startswith("|"):
            flush_para(); flush_ul(); flush_ol()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not in_table:
                next_line = lines[i+1] if i+1 < len(lines) else ""
                if re.match(r"^[|\s\-:]+$", next_line):
                    html_lines.append('<table><thead><tr>' +
                                      "".join(f"<th>{inline(c)}</th>" for c in cells) +
                                      "</tr></thead><tbody>")
                    in_table = True
                    i += 2; continue
                else:
                    html_lines.append('<table><tbody>')
                    in_table = True
            html_lines.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
            i += 1; continue

        if not line.strip():
            flush_para(); flush_ul(); flush_ol(); flush_table()
            i += 1; continue

        flush_ul(); flush_ol(); flush_table()
        para_buf.append(inline(line))
        i += 1

    flush_para(); flush_ul(); flush_ol(); flush_table()
    return "\n".join(html_lines)
