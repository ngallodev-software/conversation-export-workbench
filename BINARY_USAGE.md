# conv-tool — Pre-built Binary Usage

`conv-tool` is the packaged executable for Conversation Export Workbench. It processes exported **ChatGPT**, **Claude**, and **DeepSeek** histories locally and can convert them to HTML, Markdown, or normalized JSON.

## Download

Use the latest release:

https://github.com/ngallodev-software/conversation-export-workbench/releases/latest

Assets are versioned by tag:

| Platform | Asset pattern |
|---|---|
| Linux x86_64 | `conv-tool-vX.Y.Z-linux` |
| macOS | `conv-tool-vX.Y.Z-macos` |
| Windows | `conv-tool-vX.Y.Z-windows.exe` |

Each release also includes per-file SHA-256 checksum files and a combined `SHA256SUMS`.

## Make it executable

Linux/macOS:

```bash
chmod +x conv-tool-vX.Y.Z-linux
# or
chmod +x conv-tool-vX.Y.Z-macos
```

For convenience, you can rename the downloaded file to `conv-tool`.

## Command structure

The packaged executable uses subcommands:

```text
conv-tool format [format options]
conv-tool generate-spa [viewer options]
conv-tool serve [server options]
```

This differs from source mode, where the equivalent entry points are `format_conversations.py`, `generate_spa.py`, and `serve_spa.py`.

## Convert an export

Linux example:

```bash
./conv-tool-vX.Y.Z-linux format --input ~/Downloads/export.zip --format html --yes
```

macOS example:

```bash
./conv-tool-vX.Y.Z-macos format --input ~/Downloads/export.zip --format md --yes
```

Windows example:

```powershell
.\conv-tool-vX.Y.Z-windows.exe format --input .\export.zip --format html --yes
```

### Format options

| Option | Default | Description |
|---|---|---|
| `--input FILE` | `conversations.json` | Input JSON or ZIP containing `conversations.json` |
| `--output DIR` | `output/<provider>/` | Output directory |
| `--provider NAME` | auto-detected | Force `chatgpt`, `claude`, or `deepseek` |
| `--format FORMAT` | `html` | `html`, `md`, or `json` |
| `--id ID` | all | Export one conversation by ID |
| `--list` | — | List conversation IDs and titles |
| `--combined` | — | Combine conversations into one HTML/Markdown file |
| `--yes` / `-y` | prompt | Overwrite existing output without prompting |

Examples:

```bash
# List conversations
./conv-tool-vX.Y.Z-linux format --input export.zip --list

# Convert all conversations to HTML
./conv-tool-vX.Y.Z-linux format --input export.zip --format html --yes

# Force provider only if auto-detection cannot identify the export
./conv-tool-vX.Y.Z-linux format --input conversations.json --provider claude --format md
```

## Generate and serve the workbench

```bash
./conv-tool-vX.Y.Z-linux generate-spa --output output --yes
./conv-tool-vX.Y.Z-linux serve --output output
```

Open the local URL printed by the `serve` command.

## Verify checksums

Linux/macOS:

```bash
sha256sum -c conv-tool-vX.Y.Z-linux.sha256
```

Or download `SHA256SUMS` and verify the relevant asset against it.

## Notes

- The executable is built with PyInstaller.
- Provider templates and viewer configuration are bundled with the binary.
- No ChatGPT, Claude, or DeepSeek API key is required.
- Conversation conversion is local; no hosted conversion backend is used.
- For source development and provider extension, see [README.md](README.md).
