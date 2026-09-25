# Conversation Export Workbench Upgrade Plan

This is the canonical implementation order for security, offline capability, architecture, and mobile expansion.

## Phase 0 — Baseline and invariants

Preserve these product constraints unless an explicit later decision changes them:

- local-first processing;
- no ChatGPT, Claude, or DeepSeek credentials required;
- no hosted conversion backend required;
- provider-specific parsing separated from presentation;
- real conversation exports never committed as fixtures;
- downloadable desktop binaries remain supported.

## Phase 1 — Security and true-offline hardening

1. Treat every export as untrusted input.
2. Escape raw message HTML before Markdown rendering.
3. Allowlist navigable URL schemes and add safe external-link attributes.
4. Sanitize conversation DOM before inserting it into the SPA.
5. Remove runtime CDN/remote-script dependencies.
6. Add restrictive browser security policy and privacy headers.
7. Bound ZIP entry counts, uncompressed sizes, and compression ratios.
8. Add cycle guards to provider conversation-tree traversal.
9. Keep local serving loopback-only unless the user explicitly opts into LAN exposure.
10. Add regression tests for hostile markup, unsafe URLs, malformed archives, and cyclic trees.

**Status:** complete.

## Phase 2 — CI and release supply-chain hardening

1. Test every supported Python version.
2. Pin GitHub Actions to immutable commit SHAs.
3. Pin build/test tooling versions.
4. Give workflows minimum required permissions.
5. Add artifact provenance/attestations.
6. Keep SHA-256 release checksums.
7. Mark generated sample HTML as generated for GitHub language statistics.
8. Lock mobile dependencies and use `npm ci`.

**Status:** complete.

## Phase 3 — Canonical conversation model

The versioned `cew.conversation/v1` representation now covers:

- conversation metadata;
- user/assistant/tool/system roles;
- text;
- reasoning/thinking;
- tool use and tool results;
- search results/read links;
- attachment metadata;
- timestamps, model names, and source-provider IDs.

Provider adapters normalize exports into the canonical model. HTML, Markdown, normalized JSON, search, bundles, and the mobile client now consume that model instead of maintaining separate provider-specific rendering logic.

**Status:** complete.

## Phase 4 — Portable offline workbench bundle and search

`cew.bundle/v2` adds:

- canonical conversations;
- deterministic bundle IDs;
- source SHA-256 provenance;
- deterministic search payload;
- duplicate-aware merge/update behavior;
- merge history;
- optional attachment payloads under a constrained `attachments/` namespace;
- attachment size/hash verification and safe extraction.

Readers retain compatibility with `cew.bundle/v1`.

**Status:** core implementation complete. Provider exports do not always expose enough stable attachment metadata to automatically associate every provider attachment with a specific canonical message; manually supplied attachment directories are therefore packaged as verified bundle payloads without inventing unsupported provider links.

## Phase 5 — Android/iOS offline viewer

Implemented:

1. all application JS/CSS/icons packaged locally;
2. platform file chooser import;
3. app-private IndexedDB persistence;
4. network-independent import/search/viewing;
5. explicit confirmation before external links;
6. optional PBKDF2-backed local app-lock PIN;
7. light/dark/system themes and accessibility controls;
8. safe verified attachment Share / Save handoff;
9. Android APK build plus optional stable release signing/AAB path;
10. iOS Simulator build plus optional signed IPA/TestFlight path;
11. installable PWA shell and service worker.

Native Android/iOS projects are generated reproducibly from the pinned Capacitor sources during CI rather than committed as generated platform trees.

Native biometric unlock is implemented as a first-party Capacitor plugin over Android BiometricPrompt and iOS LocalAuthentication, with the existing PIN verifier retained as recovery. Android emulator and iOS Simulator launch/UI smoke tests now exercise generated native projects and capture evidence artifacts.

**Remaining account-dependent work:** actual App Store/TestFlight and Google Play publication requires the corresponding store accounts, signing keys, and service credentials. The workflows are credential-gated and ready for those values.

## Phase 6 — Direct raw-export import on mobile

The mobile client now detects and normalizes ChatGPT, Claude, and DeepSeek `.json` exports and ZIP archives containing `conversations.json` directly on-device. Provider adapters have cycle/resource guards and share the same canonical schema/search model used by the desktop tool.

**Status:** complete.

## Phase 7 — Product polish

Implemented:

- verified attachment payload storage and Share / Save;
- export merge/history and duplicate resolution;
- accessibility controls and reduced-motion support;
- light/dark/system themes;
- archive/provider/message/attachment statistics;
- optional PWA distribution;
- large-archive search-index profiling harness;
- local app-lock access gate.

Deliberately deferred:

- **archive encryption at rest:** Python's standard library does not provide a suitable authenticated-encryption primitive. Adding home-grown cryptography would weaken the security posture. If encrypted `.cew` archives are added, they should use a well-maintained audited dependency and a separately versioned encrypted-envelope format.
- **physical-device UI automation:** emulator/simulator launch tests are implemented; real-device farms are optional future coverage.

## Current implementation status

- [x] Phase 0 — invariants documented.
- [x] Phase 1 — security and true-offline hardening.
- [x] Phase 2 — CI/release/supply-chain hardening and mobile lockfile.
- [x] Phase 3 — canonical model and canonical HTML/Markdown rendering.
- [x] Phase 4 — CEW v2 provenance, merge/history, search, and attachment payloads.
- [x] Phase 5 — offline mobile client, packaging, PIN + native biometric unlock, signing hooks, emulator/simulator UI smoke coverage.
- [x] Phase 6 — direct raw provider ZIP/JSON import on mobile.
- [x] Phase 7 — major polish complete, including streamed mobile ZIP import; authenticated archive encryption remains intentionally deferred pending an audited crypto dependency decision.
