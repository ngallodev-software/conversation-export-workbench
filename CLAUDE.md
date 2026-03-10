# Project Instructions

## Code Search — jcodemunch

Always use the jcodemunch MCP tools for code exploration in this project:
- Use `mcp__jcodemunch__search_symbols` to find functions, classes, and methods by name
- Use `mcp__jcodemunch__get_file_outline` to understand a file's structure before reading it
- Use `mcp__jcodemunch__search_text` for full-text search across the codebase
- Use `mcp__jcodemunch__get_symbol` to fetch a specific symbol's implementation
- Prefer these over Grep/Glob for code navigation unless the task is a simple file pattern match

The folder is already indexed at `local/conversation-export-workbench`. Run `mcp__jcodemunch__index_folder` with `incremental: true` if new files have been added since the last session.
