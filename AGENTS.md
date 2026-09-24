# Repository Agent Instructions

- Treat this as a local-first, multi-provider conversation export tool for ChatGPT, Claude, and DeepSeek.
- Do not add real conversation exports, credentials, or personal chat content to fixtures.
- Preserve Python 3.10+ standard-library-only runtime behavior unless the task explicitly changes that constraint.
- Keep provider detection deterministic and template-based.
- Run `python -m pytest -q tests/test_regressions.py` for code changes.
- Run `./scripts/smoke_test.sh` when formatter, provider, or SPA behavior changes.
- Packaged binary documentation must use the `format`, `generate-spa`, and `serve` subcommands.
