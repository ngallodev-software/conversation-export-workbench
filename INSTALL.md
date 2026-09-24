# Installation

Conversation Export Workbench 0.2.0 publishes platform-specific release artifacts from the GitHub Releases page.

## Windows

Recommended artifact:

`ConversationExportWorkbench-0.2.0-Setup.exe`

The installer is per-user and does not require administrator rights. It installs `conv-tool.exe` under the user's local Programs directory and adds Start Menu shortcuts for guided conversion and viewer generation.

A portable `conv-tool-v0.2.0-windows.exe` is also published.

## macOS

Recommended artifact:

`ConversationExportWorkbench-0.2.0-macos.pkg`

The package installs:

- `/usr/local/bin/conv-tool`;
- an Applications launcher that opens guided mode in Terminal.

The current package is not Developer-ID signed/notarized yet, so macOS may require explicit approval in Privacy & Security before first launch.

A portable `conv-tool-v0.2.0-macos` is also published.

## Linux

Recommended Debian/Ubuntu artifact:

`conversation-export-workbench_0.2.0_amd64.deb`

Install by opening it in the system package installer or with:

```bash
sudo apt install ./conversation-export-workbench_0.2.0_amd64.deb
```

A portable `conv-tool-v0.2.0-linux` is also published.

## Android

Artifact:

`ConversationExportWorkbench-v0.2.0-android-sideload.apk`

Open the downloaded APK on the Android device and allow installation from the download source when prompted.

For v0.2.0 this APK uses the CI/debug signing identity. It is intended for direct sideload evaluation, not as the permanent Play Store/update signing channel. A stable release keystore must be configured before Play Store publication or long-lived sideload upgrades.

## iPhone / iPad

There is no unsigned one-click iOS package that can be installed normally on arbitrary devices.

The repository builds an unsigned iOS Simulator artifact to verify the Capacitor/Xcode project. A device-installable build requires an Apple Developer team, a matching bundle ID/App Store Connect app record, distribution signing, and provisioning. TestFlight is the intended first distribution channel once those credentials are configured.

The GitHub release may contain:

`ConversationExportWorkbench-v0.2.0-ios-simulator.zip`

That ZIP is for Simulator validation and is **not** an iPhone/iPad installer.

## Verify downloads

The release publishes a `SHA256SUMS` file and GitHub build-provenance attestations for release assets.
