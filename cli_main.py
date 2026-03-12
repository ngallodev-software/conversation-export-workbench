#!/usr/bin/env python3
"""
conv-tool — single entry point for the conversation export workbench.

Subcommands:
  format        Format conversation exports to HTML
  generate-spa  Generate the SPA viewer (output/index.html)
  serve         Serve the SPA output directory via HTTP
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="conv-tool",
        description="Conversation export workbench.",
    )
    subs = parser.add_subparsers(dest="cmd", required=True)
    subs.add_parser("format",       help="Format conversation exports to HTML")
    subs.add_parser("generate-spa", help="Generate SPA viewer (output/index.html)")
    subs.add_parser("serve",        help="Serve SPA output directory via HTTP")

    # Parse only the first positional; each sub-main() re-parses sys.argv
    cmd = parser.parse_args(sys.argv[1:2]).cmd
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if cmd == "format":
        from format_conversations import main as _m
        _m()
    elif cmd == "generate-spa":
        from generate_spa import main as _m
        _m()
    elif cmd == "serve":
        from serve_spa import main as _m
        _m()


if __name__ == "__main__":
    main()
