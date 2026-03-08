#!/usr/bin/env python3
"""
Conversation export formatter — supports DeepSeek and Claude (Anthropic) exports.

Usage:
  python format_conversations.py [options]

  Run with no arguments for interactive mode: auto-discovers zip files and
  conversations.json files in the current directory and prompts to process them.

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
import zipfile
from pathlib import Path

from formatters import claude, deepseek
from formatters.shared import safe_write, slugify

# Registry: ordered list of formatter modules; first match wins
_FORMATTERS = [deepseek, claude]


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------

def detect_provider(data: list):
    """Return the matching formatter module, or None."""
    for mod in _FORMATTERS:
        if mod.detect(data):
            return mod
    return None


def load_conversations(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Interactive (zero-args) mode
# ---------------------------------------------------------------------------

def _prompt(question: str) -> bool:
    """Ask a yes/no question; return True for yes."""
    ans = input(f"{question} [y/N] ").strip().lower()
    return ans in ("y", "yes")


def _extract_zip(zip_path: Path, cwd: Path) -> list[Path]:
    """
    Extract a zip, looking for conversations.json inside.
    Returns list of extracted conversations.json paths.
    """
    found = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        json_names = [n for n in names if Path(n).name == "conversations.json"]
        if not json_names:
            print(f"  No conversations.json found inside {zip_path.name}")
            return []
        for name in json_names:
            # Extract to a sibling path named after the zip (without extension)
            dest_dir = cwd / zip_path.stem
            dest_dir.mkdir(exist_ok=True)
            dest_path = dest_dir / "conversations.json"
            dest_path.write_bytes(zf.read(name))
            print(f"  Extracted → {dest_path}")
            found.append(dest_path)
    return found


def _process_json(json_path: Path, fmt: str, yes: bool):
    """Load, detect, and export a single conversations.json."""
    print(f"\nProcessing {json_path} …")
    data = load_conversations(str(json_path))
    fmt_mod = detect_provider(data)
    if not fmt_mod:
        print(f"  Could not auto-detect provider.")
        ans = input("  Enter provider [deepseek/claude]: ").strip().lower()
        fmt_mod = {"deepseek": deepseek, "claude": claude}.get(ans)
        if not fmt_mod:
            print("  Unknown provider — skipping.")
            return

    print(f"  Provider: {fmt_mod.PROVIDER}  ({len(data)} conversations)")
    out_dir = Path("output") / fmt_mod.PROVIDER
    out_dir.mkdir(parents=True, exist_ok=True)

    ext = fmt
    for conv in data:
        title = conv.get(fmt_mod.TITLE_FIELD, conv.get(fmt_mod.ID_FIELD, "untitled"))
        slug = slugify(title)
        out_path = out_dir / f"{slug}.{ext}"
        if fmt == "html":
            content = fmt_mod.build_html_single(conv)
        elif fmt == "md":
            content = fmt_mod.conv_to_md(conv)
        else:
            content = fmt_mod.build_json_single(conv)
        safe_write(out_path, content, yes)


def interactive_mode():
    """Zero-args interactive mode: discover zips and json files, prompt to process."""
    cwd = Path(".")
    print("No arguments given — scanning current directory…\n")

    # 1. Discover zip files (exclude already-gitignored data zips we know about)
    zips = sorted(cwd.glob("*.zip"))
    json_candidates: list[Path] = []

    if zips:
        print(f"Found {len(zips)} zip file(s):")
        for z in zips:
            print(f"  {z.name}")
        print()
        for z in zips:
            if _prompt(f"Extract and process {z.name}?"):
                extracted = _extract_zip(z, cwd)
                json_candidates.extend(extracted)
        print()

    # 2. Discover conversations.json files in cwd and immediate subdirs
    direct = list(cwd.glob("conversations.json"))
    subdirs = [p for p in cwd.glob("*/conversations.json") if p.parent != cwd]
    all_json = direct + subdirs

    # Add any we just extracted (avoid duplicates)
    for p in json_candidates:
        if p not in all_json:
            all_json.append(p)

    if not all_json:
        print("No conversations.json files found. Nothing to do.")
        return

    # Ask format once
    fmt_ans = input("Output format [html/md/json] (default: html): ").strip().lower()
    fmt = fmt_ans if fmt_ans in ("html", "md", "json") else "html"
    yes_ans = _prompt("Overwrite existing files without prompting?")

    print()
    for json_path in all_json:
        if _prompt(f"Process {json_path}?"):
            _process_json(json_path, fmt, yes_ans)

    # Offer to regenerate SPA
    print()
    if _prompt("Regenerate SPA viewer (output/index.html)?"):
        from formatters.spa import build_spa
        out_dir = Path("output")
        try:
            html = build_spa(out_dir)
            safe_write(out_dir / "index.html", html, yes=True)
        except ValueError as e:
            print(f"  SPA generation skipped: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Zero-args → interactive mode
    if len(sys.argv) == 1:
        interactive_mode()
        return

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
