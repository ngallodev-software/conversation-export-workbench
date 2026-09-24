import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import format_conversations
import serve_spa
from formatters import chatgpt, deepseek
from formatters.shared import markdown_to_html, sanitize_href
from formatters.spa import build_spa


def test_markdown_escapes_raw_html_and_event_handlers():
    rendered = markdown_to_html('<img src=x onerror="alert(1)">')
    assert "<img" not in rendered
    assert "onerror=" in rendered
    assert "&lt;img" in rendered


def test_markdown_rejects_javascript_links():
    rendered = markdown_to_html("[click](javascript:alert(1))")
    assert "javascript:" not in rendered
    assert "<a " not in rendered
    assert "click" in rendered


def test_markdown_allows_https_links_with_safe_rel():
    rendered = markdown_to_html("[example](https://example.com/path)")
    assert 'href="https://example.com/path"' in rendered
    assert 'rel="noopener noreferrer"' in rendered


@pytest.mark.parametrize(
    "value, expected",
    [
        ("https://example.com", "https://example.com"),
        ("http://example.com", "http://example.com"),
        ("#section", "#section"),
        ("javascript:alert(1)", None),
        ("data:text/html,boom", None),
        ("file:///tmp/private", None),
        ("relative/path", None),
    ],
)
def test_sanitize_href_policy(value, expected):
    assert sanitize_href(value) == expected


def test_deepseek_search_does_not_link_unsafe_scheme():
    rendered = deepseek._render_fragment_html(
        {
            "type": "SEARCH",
            "results": [
                {
                    "url": "javascript:alert(1)",
                    "title": "unsafe",
                    "snippet": "example",
                }
            ],
        }
    )
    assert "javascript:" not in rendered
    assert "<a " not in rendered
    assert "unsafe" in rendered


def test_deepseek_cycle_terminates():
    mapping = {
        "root": {"message": None, "children": ["a"]},
        "a": {"message": {"fragments": []}, "children": ["root"]},
    }
    assert len(deepseek.walk_tree(mapping)) <= len(mapping)


def test_chatgpt_cycle_terminates():
    mapping = {
        "a": {"parent": "b", "message": None},
        "b": {"parent": "a", "message": None},
    }
    assert chatgpt.walk_tree(mapping, "a") == []


def test_zip_member_rejects_suspicious_compression_ratio():
    info = zipfile.ZipInfo("conversations.json")
    info.file_size = 10_000
    info.compress_size = 1
    with pytest.raises(ValueError, match="compression ratio"):
        format_conversations._validate_zip_info(info)


def test_server_refuses_network_bind_without_explicit_opt_in(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "serve_spa.py",
            "--output",
            str(tmp_path),
            "--host",
            "0.0.0.0",
        ],
    )
    assert serve_spa.main() == 1


def test_generated_spa_has_no_remote_tailwind_runtime(tmp_path):
    provider_dir = tmp_path / "chatgpt"
    provider_dir.mkdir(parents=True)
    provider_dir.joinpath("sample.html").write_text(
        '<html><body><div class="container"><h1>Sample</h1>'
        '<div class="message user">hello</div></div></body></html>',
        encoding="utf-8",
    )
    html = build_spa(tmp_path)
    assert "cdn.tailwindcss.com" not in html
    assert "Content-Security-Policy" in html
    assert "sanitizeConversationRoot" in html
