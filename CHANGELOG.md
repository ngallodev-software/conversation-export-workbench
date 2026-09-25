# Changelog

## 0.4.0 — 2026-09-24

### Added

- first-party Capacitor native biometric bridge using Android BiometricPrompt and iOS LocalAuthentication;
- biometric unlock action layered over the existing PBKDF2 PIN app lock, with PIN recovery preserved;
- Android emulator launch/UI smoke tests with screenshot and accessibility-tree evidence;
- iOS Simulator install/launch smoke tests with screenshot evidence;
- credential-gated Google Play internal-track publication hook for signed AAB releases.

### Changed

- generated iOS projects receive the Face ID privacy description automatically during native configuration;
- release-candidate builds compile the native biometric plugin on both mobile platforms;
- native UI smoke tests are now part of release-branch qualification.

### Distribution

- Google Play upload remains disabled unless the repository is configured with a stable Android keystore, Google Play service-account JSON, and `ENABLE_GOOGLE_PLAY_UPLOAD=true`;
- App Store/TestFlight upload continues to use the existing Apple credential-gated path.

## 0.3.0 — 2026-09-24

### Added

- provider-neutral canonical HTML and Markdown rendering shared by ChatGPT, Claude, and DeepSeek;
- `cew.bundle/v2` with deterministic bundle IDs, source SHA-256 provenance, merge history, and duplicate-aware updates;
- optional hashed attachment payloads with safe extraction and merge preservation;
- direct on-device ChatGPT, Claude, and DeepSeek ZIP/JSON import;
- mobile attachment verification plus Share / Save handoff instead of active in-WebView rendering;
- optional local app-lock PIN, light/dark/system themes, archive statistics, installable PWA shell, and offline service worker;
- large-archive profiling harness;
- committed npm lockfile and `npm ci` mobile/native builds.

### Distribution

- optional stable Android release signing produces signed APK and AAB when repository keystore secrets are configured;
- optional signed iOS IPA and TestFlight upload path using Apple Developer/App Store Connect credentials;
- optional Windows Authenticode signing and macOS Developer ID signing/notarization hooks;
- unsigned desktop/mobile fallbacks remain available when signing credentials are absent.

### Security

- CEW attachment namespace, size, compression-ratio, declared-path, and SHA-256 validation;
- mobile attachment SHA-256 verification before local use;
- app-lock credentials are PBKDF2-SHA-256 derived with a random salt; the app lock is an access gate, not archive encryption.


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
