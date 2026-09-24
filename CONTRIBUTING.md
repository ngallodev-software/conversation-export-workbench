# Contributing

Contributions are welcome for ChatGPT, Claude, and DeepSeek export compatibility, rendering fidelity, the local viewer, tests, and documentation.

## Ground rules

- Do not commit real conversation exports or other private user data.
- Use synthetic/minimized fixtures for bug reproduction.
- Preserve the no-third-party-runtime-dependency design unless there is a strong reason to change it.
- Keep provider-specific parsing in the provider adapter and shared behavior in shared modules.
- Prefer deterministic provider detection from structural signatures over heuristic guessing.

## Development setup

Runtime requires Python 3.10+.

```bash
git clone https://github.com/ngallodev-software/conversation-export-workbench.git
cd conversation-export-workbench
python -m pip install pytest
```

## Tests

Run the regression suite:

```bash
python -m pytest -q tests/test_regressions.py
```

Run the all-provider smoke test:

```bash
./scripts/smoke_test.sh
```

For provider changes, add or update synthetic fixtures and verify HTML/Markdown/JSON behavior as applicable.

## Adding a provider

A new provider generally requires:

1. a structural detection template under `provider_templates/`;
2. a formatter module under `formatters/`;
3. registration in `format_conversations.py`;
4. synthetic sample data;
5. regression coverage;
6. README/provider-table updates.

## Pull requests

Keep changes focused and describe:

- what changed;
- which provider(s) are affected;
- how the change was tested;
- whether output format or compatibility changes are user-visible.
