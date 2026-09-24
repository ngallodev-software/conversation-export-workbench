#!/usr/bin/env python3
"""Build or inspect portable Conversation Export Workbench (.cew) archives."""

import argparse
import json
import sys

from workbench_bundle import build_bundle, read_bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a portable offline .cew archive from ChatGPT, Claude, or DeepSeek exports."
    )
    parser.add_argument("--input", help="Source provider JSON/ZIP, or .cew when using --inspect")
    parser.add_argument("--output", default="conversation-workbench.cew", help="Output .cew path")
    parser.add_argument("--provider", choices=["chatgpt", "claude", "deepseek"], help="Force provider")
    parser.add_argument("--inspect", action="store_true", help="Inspect an existing .cew bundle")
    args = parser.parse_args()

    if not args.input:
        parser.error("--input is required")

    try:
        if args.inspect:
            manifest, conversations, search_index = read_bundle(args.input)
            print(json.dumps(
                {
                    **manifest,
                    "conversation_count": len(conversations),
                    "search_record_count": len(search_index),
                },
                indent=2,
                ensure_ascii=False,
            ))
            return 0

        manifest = build_bundle(args.input, args.output, provider=args.provider)
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
