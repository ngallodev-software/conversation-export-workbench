#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?version required}"
BINARY="${2:-dist/conv-tool}"
OUT_DIR="${3:-dist}"
ARCH="${4:-amd64}"
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT

install -d "$ROOT/DEBIAN" "$ROOT/usr/bin"
install -m 0755 "$BINARY" "$ROOT/usr/bin/conv-tool"

cat > "$ROOT/DEBIAN/control" <<CONTROL
Package: conversation-export-workbench
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: ngallodev-software
Description: Local-first ChatGPT, Claude, and DeepSeek conversation export workbench
 Converts exported AI chat histories into HTML, Markdown, normalized JSON,
 portable .cew bundles, and a searchable offline viewer.
CONTROL

mkdir -p "$OUT_DIR"
dpkg-deb --build --root-owner-group "$ROOT" "$OUT_DIR/conversation-export-workbench_${VERSION}_${ARCH}.deb"
echo "$OUT_DIR/conversation-export-workbench_${VERSION}_${ARCH}.deb"
