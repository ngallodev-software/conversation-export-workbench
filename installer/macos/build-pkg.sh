#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?version required}"
BINARY="${2:-dist/conv-tool}"
OUT_DIR="${3:-dist}"
APP_NAME="Conversation Export Workbench"
PKG_NAME="ConversationExportWorkbench-${VERSION}-macos.pkg"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

install -d "$STAGE/usr/local/bin"
install -m 0755 "$BINARY" "$STAGE/usr/local/bin/conv-tool"

APP="$STAGE/Applications/$APP_NAME.app"
install -d "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleExecutable</key><string>ConversationExportWorkbench</string>
  <key>CFBundleIdentifier</key><string>software.ngallodev.conversationexportworkbench.desktop</string>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleDisplayName</key><string>$APP_NAME</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
</dict></plist>
PLIST

cat > "$APP/Contents/MacOS/ConversationExportWorkbench" <<'LAUNCHER'
#!/bin/zsh
/usr/bin/osascript <<'APPLESCRIPT'
tell application "Terminal"
    activate
    do script "cd ~/Documents && /usr/local/bin/conv-tool format"
end tell
APPLESCRIPT
LAUNCHER
chmod 0755 "$APP/Contents/MacOS/ConversationExportWorkbench"

mkdir -p "$OUT_DIR"
pkgbuild \
  --root "$STAGE" \
  --identifier "software.ngallodev.conversationexportworkbench" \
  --version "$VERSION" \
  --install-location "/" \
  "$OUT_DIR/$PKG_NAME"

echo "$OUT_DIR/$PKG_NAME"
