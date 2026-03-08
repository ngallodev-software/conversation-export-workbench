#!/usr/bin/env python3
"""
Conversation export formatter — supports DeepSeek and Claude (Anthropic) exports.

Usage:
  python format_conversations.py [options]

Options:
  --input FILE        Path to conversations.json (default: conversations.json)
  --output DIR        Output directory (default: output/<provider>/)
  --provider NAME     Force provider: deepseek, claude  (auto-detected if omitted)
  --format FORMAT     Output format: html, md, json (default: html)
  --id ID             Export only the conversation with this ID
  --list              List all conversations and exit
  --combined          Combine all conversations into one file (html/md only)
  --yes               Overwrite existing files without prompting
"""

import argparse
import json
import sys
from pathlib import Path

from formatters import claude, deepseek
from formatters.shared import safe_write, slugify

# Registry: ordered list of formatter modules; first match wins
_FORMATTERS = [deepseek, claude]


def detect_provider(data: list):
    """Return the matching formatter module, or None."""
    for mod in _FORMATTERS:
        if mod.detect(data):
            return mod
    return None


def load_conversations(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Format DeepSeek / Claude conversation exports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", default="conversations.json", help="Input JSON file")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: output/<provider>/)")
    parser.add_argument("--provider", choices=["deepseek", "claude"],
                        help="Force provider (auto-detected if omitted)")
    parser.add_argument("--format", default="html", choices=["html", "md", "json"],
                        help="Output format")
    parser.add_argument("--id", dest="conv_id", help="Export only conversation with this ID")
    parser.add_argument("--list", action="store_true", help="List conversations and exit")
    parser.add_argument("--combined", action="store_true",
                        help="Combine all conversations into one file (html/md only)")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Overwrite existing files without prompting")
    args = parser.parse_args()

    data = load_conversations(args.input)

    # --- Resolve formatter module ---
    forced_mod = {"deepseek": deepseek, "claude": claude}.get(args.provider)
    detected_mod = detect_provider(data)

    if forced_mod:
        fmt_mod = forced_mod
        if detected_mod and detected_mod is not forced_mod:
            print(f"Warning: file looks like '{detected_mod.PROVIDER}' "
                  f"but --provider={fmt_mod.PROVIDER} was forced.")
    elif detected_mod:
        fmt_mod = detected_mod
        print(f"Detected provider: {fmt_mod.PROVIDER}")
    else:
        print("Could not auto-detect provider from file structure.")
        ans = input("Enter provider [deepseek/claude]: ").strip().lower()
        fmt_mod = {"deepseek": deepseek, "claude": claude}.get(ans)
        if not fmt_mod:
            print("Unknown provider. Aborting.", file=sys.stderr)
            sys.exit(1)

    # --- Resolve output directory ---
    out_dir = Path(args.output) if args.output else Path("output") / fmt_mod.PROVIDER
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- List ---
    if args.list:
        print(f"Provider: {fmt_mod.PROVIDER}")
        print(f"{'#':<4} {'ID':<40} {'Title'}")
        print("-" * 80)
        for i, c in enumerate(data, 1):
            conv_id    = c.get(fmt_mod.ID_FIELD, "")
            conv_title = c.get(fmt_mod.TITLE_FIELD, "")
            print(f"{i:<4} {conv_id:<40} {conv_title[:50]}")
        return

    # --- Select target conversations ---
    fmt = args.format
    ext = fmt

    if args.conv_id:
        target = next((c for c in data if c.get(fmt_mod.ID_FIELD) == args.conv_id), None)
        if not target:
            print(f"Error: no conversation found with id '{args.conv_id}'", file=sys.stderr)
            sys.exit(1)
        targets = [target]
    else:
        targets = data

    # --- Combined output ---
    if args.combined and fmt in ("html", "md"):
        if fmt == "html":
            content = fmt_mod.build_html_all(targets)
            fname = "all_conversations.html"
        else:
            content = "\n\n---\n\n".join(fmt_mod.conv_to_md(c) for c in targets)
            fname = "all_conversations.md"
        safe_write(out_dir / fname, content, args.yes)
        return

    # --- One file per conversation ---
    for conv in targets:
        title = conv.get(fmt_mod.TITLE_FIELD, conv.get(fmt_mod.ID_FIELD, "untitled"))
        slug = slugify(title)
        out_path = out_dir / f"{slug}.{ext}"

        if fmt == "html":
            content = fmt_mod.build_html_single(conv)
        elif fmt == "md":
            content = fmt_mod.conv_to_md(conv)
        else:
            content = fmt_mod.build_json_single(conv)

        safe_write(out_path, content, args.yes)


if __name__ == "__main__":
    main()
