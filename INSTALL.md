# Installation

Conversation Export Workbench publishes platform-specific artifacts from the GitHub Releases page. Use the latest release unless you intentionally need an older version.

## Windows

Recommended artifact:

`ConversationExportWorkbench-X.Y.Z-Setup.exe`

The installer is per-user and installs `conv-tool.exe` plus Start Menu shortcuts. A portable `conv-tool-vX.Y.Z-windows.exe` is also published.

The release workflow supports Authenticode SHA-256/RFC 3161 signing when repository secrets `WINDOWS_SIGNING_PFX_BASE64` and `WINDOWS_SIGNING_PFX_PASSWORD` are configured. Unsigned builds remain available when those credentials are absent.

## macOS

Recommended artifact:

`ConversationExportWorkbench-X.Y.Z-macos.pkg`

The package installs `/usr/local/bin/conv-tool` plus an Applications launcher. A portable `conv-tool-vX.Y.Z-macos` is also published.

The release workflow can code-sign/notarize macOS artifacts when repository secrets `MACOS_CERTIFICATE_P12_BASE64` and `MACOS_CERTIFICATE_PASSWORD`, repository variables `MACOS_APPLICATION_IDENTITY` and `MACOS_INSTALLER_IDENTITY`, plus App Store Connect notarization credentials are configured. Without those credentials macOS may require explicit approval in Privacy & Security on first launch.

## Linux

Recommended Debian/Ubuntu artifact:

`conversation-export-workbench_X.Y.Z_amd64.deb`

Install with the graphical package installer or:

```bash
sudo apt install ./conversation-export-workbench_X.Y.Z_amd64.deb
```

A portable `conv-tool-vX.Y.Z-linux` is also published.

## Android

The release pipeline has two modes.

With stable Android signing secrets configured:

- `ConversationExportWorkbench-vX.Y.Z-android.apk`
- `ConversationExportWorkbench-vX.Y.Z-android.aab`

Without stable signing credentials:

- `ConversationExportWorkbench-vX.Y.Z-android-sideload.apk`

Stable Android signing uses repository secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, and `ANDROID_KEY_PASSWORD`. The fallback sideload APK is directly installable after Android permits installation from the download source, but it should not be treated as the permanent Play Store/update signing channel. Google Play upload is an optional post-release step controlled by `ENABLE_GOOGLE_PLAY_UPLOAD=true` and the configured Play service-account secret.

## iPhone / iPad

CI always produces an unsigned Simulator validation artifact:

`ConversationExportWorkbench-vX.Y.Z-ios-simulator.zip`

Signed iOS builds use repository secrets `APPLE_TEAM_ID`, `APPLE_API_KEY_ID`, `APPLE_API_ISSUER_ID`, and `APPLE_API_PRIVATE_KEY_BASE64`, plus repository variable `IOS_BUNDLE_ID`. Setting repository variable `ENABLE_TESTFLIGHT_UPLOAD=true` enables TestFlight upload only after the GitHub release has been created successfully.

An unsigned Simulator ZIP is not installable on an iPhone/iPad.

## Web / PWA

The mobile web client is also an installable PWA. Run it from a secure local/hosted origin, then use the browser's Install/Add to Home Screen action. Application-shell resources are cached locally; imported archives remain local to browser storage.

## Verify downloads

Published releases include `SHA256SUMS` and GitHub build-provenance attestations.
