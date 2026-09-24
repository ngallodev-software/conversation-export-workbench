# Changelog

## 0.2.0 — 2026-09-24

### Added

- versioned `cew.conversation/v1` provider-neutral conversation model;
- portable `.cew` offline archive format and `conv-tool bundle`;
- corpus-wide local full-text search;
- Capacitor mobile offline viewer foundation for Android and iOS;
- Claude tool-use/tool-result preservation;
- release provenance attestations.

### Security

- escape untrusted raw HTML before Markdown rendering;
- restrict generated links to safe URL schemes;
- sanitize conversation DOM before SPA insertion;
- remove the runtime Tailwind CDN dependency;
- add CSP and privacy-oriented HTTP headers;
- bound ZIP/JSON sizes, entry counts, and compression ratios;
- guard malformed conversation trees against cycles;
- require explicit opt-in before serving conversations outside loopback.

### Changed

- minimum supported Python version is now 3.11;
- CI covers Python 3.11 through 3.14;
- release/test tool versions and GitHub Actions are pinned;
- normalized JSON now includes explicit schema/provider metadata.

### Distribution

- Windows installer, macOS package, Linux Debian package, portable binaries, and Android sideload APK are built by the v0.2 release pipeline.
- iOS native build support is prepared, but installable device/TestFlight distribution requires Apple signing and provisioning credentials.
