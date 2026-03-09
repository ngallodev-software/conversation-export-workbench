#!/usr/bin/env python3
"""
Generate the SPA viewer (output/index.html).

Scans output/<provider>/ directories for exported HTML conversations,
reads their metadata, and writes a single-page app that lets you browse
all providers with a tab switcher.

Usage:
  python generate_spa.py [options]

Options:
  --output DIR        Root output directory (default: output/)
  --provider NAME     Include only this provider: deepseek, claude
                      (default: all providers with exported files)
  --config PATH       Path to spa.toml config (default: config/spa.toml)
  --yes               Overwrite index.html without prompting
"""

import argparse
import sys
from pathlib import Path

from formatters.shared import safe_write
from formatters.spa import PROVIDERS, build_spa


def main():
    parser = argparse.ArgumentParser(
        description="Generate SPA viewer for exported conversations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--output", default="output", help="Root output directory")
    parser.add_argument("--provider", choices=PROVIDERS,
                        help="Include only one provider (default: all)")
    parser.add_argument("--config", default="config/spa.toml",
                        help="Path to spa.toml config (default: config/spa.toml)")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Overwrite index.html without prompting")
    args = parser.parse_args()

    out_dir = Path(args.output)
    if not out_dir.is_dir():
        print(f"Error: output directory '{out_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    config_path = Path(args.config)
    providers = [args.provider] if args.provider else None

    try:
        html = build_spa(out_dir, config_path=config_path, providers=providers)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    index_path = out_dir / "index.html"
    safe_write(index_path, html, args.yes)


if __name__ == "__main__":
    main()
