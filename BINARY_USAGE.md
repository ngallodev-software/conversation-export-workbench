# conv-tool — Binary Usage

`conv-tool` is a self-contained executable (no Python required) that converts DeepSeek, Claude, and ChatGPT conversation exports into HTML, Markdown, or JSON.

## Download

Grab the latest binary for your platform from the [Releases page](https://github.com/ngallodev-software/conversation-export-workbench/releases/latest):

| Platform | File |
|---|---|
| Linux (x86_64) | `conv-tool-linux` |
| macOS | `conv-tool-macos` |
| Windows | `conv-tool-windows.exe` |

## Setup

**Linux / macOS** — make executable once:
```bash
chmod +x conv-tool-linux   # or conv-tool-macos
```

**Windows** — double-click opens interactive mode, or run from a terminal:
```cmd
conv-tool-windows.exe [options]
```

## Interactive mode (recommended for first use)

Drop the binary in the same folder as your export `.zip` or `conversations.json`, then run with no arguments:

```bash
./conv-tool-linux
```

The tool scans for archives and JSON files, prompts before each action, and optionally builds the SPA viewer at the end.

## CLI reference

```
conv-tool [options]
```

| Option | Default | Description |
|---|---|---|
| `--input FILE` | `conversations.json` | Path to input JSON or `.zip` archive |
| `--output DIR` | `output/<provider>/` | Where to write output files |
| `--provider NAME` | auto-detected | Force provider: `deepseek` \| `claude` \| `chatgpt` |
| `--format FORMAT` | `html` | Output format: `html` \| `md` \| `json` |
| `--id ID` | all | Export only the conversation with this ID |
| `--list` | — | Print all conversations with IDs and exit |
| `--combined` | — | Write all conversations to a single file |
| `--yes` / `-y` | prompt | Overwrite existing files without prompting |

## Common examples

```bash
# List available conversations
./conv-tool-linux --list

# Export all as HTML (auto-detects provider)
./conv-tool-linux --format html --yes

# Export directly from a zip
./conv-tool-linux --input ~/Downloads/claude-export.zip --format html --yes

# Export a single conversation by ID
./conv-tool-linux --id <uuid>

# One combined HTML file for all conversations
./conv-tool-linux --format html --combined --yes

# Force provider when auto-detection is ambiguous
./conv-tool-linux --provider deepseek --format md
```

## SPA viewer

The binary also bundles the SPA generator. After exporting, build the interactive viewer:

```bash
./conv-tool-linux --spa --output output/ --yes
```

Then serve it (requires a real HTTP server for `fetch()`):

```bash
python3 -m http.server 8080 --directory output/
# Open http://localhost:8080
```

## Notes

- The binary is a PyInstaller bundle — no Python installation required.
- Config and template files (`config/`, `provider_templates/`) are embedded; no extra files needed alongside the binary.
- For source install, advanced configuration, or adding custom providers, see the [full README](README.md).
