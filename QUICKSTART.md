# Chat Export Viewer — Quick Start

Convert DeepSeek, Claude, or ChatGPT conversation exports into HTML, Markdown, or cleaned JSON — no external dependencies, pure Python 3.10+.

![All providers view](readme_assets/sample-all.png)

<p align="center">
  <img src="readme_assets/sample-deepseek.png" width="49%" alt="DeepSeek view">
  <img src="readme_assets/sample-claude.png" width="49%" alt="Claude view">
</p>

## Requirements

- **Python 3.10+** (stdlib only — no `pip install` needed)

## Installation

```bash
git clone <repo-url>
cd conversation-export-workbench
```

## Zero-argument interactive mode

Run with no arguments to be guided through discovery and export:

```bash
python3 format_conversations.py
```

The tool will:
1. Find any `.zip` export archives in the current directory and offer to extract them
2. Discover `conversations.json` files in the current directory and subdirectories
3. Auto-detect provider (DeepSeek / Claude / ChatGPT) from file structure templates
4. Ask for output format and process everything

## CLI usage

```bash
python3 format_conversations.py [options]
```

| Option | Default | Description |
|---|---|---|
| `--input FILE` | `conversations.json` | Path to input JSON file |
| `--output DIR` | `output/<provider>/` | Output directory |
| `--provider NAME` | auto-detected | Force provider: `deepseek`, `claude`, or `chatgpt` |
| `--format FORMAT` | `html` | Output format: `html`, `md`, `json` |
| `--id ID` | all | Export only the conversation with this ID |
| `--list` | — | List all conversations and exit |
| `--combined` | — | Combine all conversations into one file (html/md only) |
| `--yes` / `-y` | prompt | Overwrite existing files without prompting |

### Examples

```bash
# List all conversations in a DeepSeek export
python3 format_conversations.py --list

# Export everything as HTML (auto-detects provider)
python3 format_conversations.py --format html --yes

# Export a single conversation by ID
python3 format_conversations.py --id <uuid> --format html

# Export Claude data from a non-default path
python3 format_conversations.py --input ~/Downloads/claude-data.json --format md

# Combine all conversations into one HTML file
python3 format_conversations.py --format html --combined
```

## SPA viewer

After exporting HTML files, generate and browse an interactive single-page viewer:

```bash
# Generate the SPA index
python3 generate_spa.py --output output/ --yes

# Serve locally (required — the SPA uses fetch())
python3 serve_spa.py
# Then open the printed URL

# For LAN access from other devices
python3 serve_spa.py --host 0.0.0.0 --start-port 8080 --end-port 80890
```

The viewer includes a provider filter (DeepSeek / Claude / ChatGPT / All) in the settings menu, live search with full-text highlighting, collapsible thinking blocks, and jump navigation between turns.

To customise the SPA's colours or layout, edit the CSS files in `config/spa_output_templates/` and re-run `generate_spa.py`. Use `--config` to point at a different `spa.toml`:

```bash
python3 generate_spa.py --config path/to/custom.toml --output output/ --yes
```

![Settings menu](readme_assets/sample-menu.png)

## Provider auto-detection

The tool auto-detects whether an input file is a DeepSeek, Claude, or ChatGPT export by matching it against JSON templates in `provider_templates/`. If no template matches, it asks you to confirm provider explicitly (or pass `--provider`). Custom templates for other providers can be added there — see the existing templates for the expected format.

## Privacy

Your `conversations.json`, zip exports, and `output/` directory are git-ignored by default to prevent accidental data leaks. Only source code and templates are tracked.
