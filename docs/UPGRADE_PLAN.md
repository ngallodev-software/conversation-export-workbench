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

**Exit condition:** a malicious or corrupted export cannot execute script through normal rendering, force unbounded tree traversal, or trigger obvious ZIP decompression abuse.

## Phase 2 — CI and release supply-chain hardening

1. Test every supported Python version.
2. Pin GitHub Actions to immutable commit SHAs.
3. Pin build/test tooling versions.
4. Give workflows minimum required permissions.
5. Add artifact provenance/attestations where GitHub release permissions allow it.
6. Keep SHA-256 release checksums.
7. Mark generated sample HTML as generated for GitHub language statistics.

**Exit condition:** CI accurately represents the supported runtime range and release provenance is reproducible/auditable.

## Phase 3 — Canonical conversation model

Define one versioned provider-neutral representation for:

- conversation metadata;
- user/assistant/tool/system roles;
- text;
- reasoning/thinking;
- tool use and tool results;
- search results/read links;
- attachments/media references;
- timestamps and source-provider IDs.

Provider adapters should parse exports into this model. HTML, Markdown, JSON, search, bundle, and mobile consumers should read the canonical model rather than re-parsing provider structures.

**Exit condition:** rendering/export code no longer needs provider-specific source schemas.

## Phase 4 — Portable offline workbench bundle and search

Create a versioned `.cew` bundle containing:

- manifest/schema version;
- canonical conversations;
- attachment payloads/metadata when supported;
- deterministic search data/index metadata;
- import provenance.

Add idempotent import/update behavior and duplicate detection. Full-text search must cover unopened conversations, not only content already loaded in the browser.

**Exit condition:** a single portable file can move an archive between desktop and mobile without provider credentials or network access.

## Phase 5 — Android/iOS offline viewer

Use the existing web UI through Capacitor only after Phases 1–4 are stable.

1. Package all JS/CSS/fonts locally.
2. Import `.cew` via Android Storage Access Framework and iOS document picker.
3. Copy imported archives into app-private storage.
4. Keep network access unnecessary for normal use.
5. Require deliberate user interaction before opening external links.
6. Add biometric/app-lock support as an optional privacy feature.
7. Add Android/iOS automated smoke tests for import, search, reopen, and offline operation.

**Exit condition:** airplane-mode import/view/search works using only user-selected local files.

## Phase 6 — Direct raw-export import on mobile

After the bundle/viewer path is stable, allow Android/iOS to import ChatGPT, Claude, and DeepSeek export ZIPs directly.

Prefer sharing parser logic rather than maintaining three independent mobile implementations. Evaluate extracting the canonical parser into a small Rust core with generated Python/Kotlin/Swift bindings only if duplicated TypeScript/native parsing becomes a maintenance problem.

## Phase 7 — Product polish

- attachment rendering;
- export merge/history;
- archive encryption option;
- accessibility and large-text support;
- theme improvements;
- archive statistics;
- optional PWA distribution;
- performance profiling for very large histories.

## Current implementation status

- [x] Phase 0 constraints documented.
- [x] Phase 1 security/offline hardening implemented with hostile-input tests.
- [x] Phase 2 Python CI/release supply-chain hardening implemented; mobile lockfile generation remains a follow-up reproducibility improvement.
- [~] Phase 3 canonical `cew.conversation/v1` model is implemented and used by normalized JSON/bundles/mobile; HTML/Markdown renderers still consume provider source structures.
- [~] Phase 4 `.cew` v1 bundle and corpus-wide search index are implemented; attachment payloads, duplicate-aware merge/update, and import provenance remain.
- [~] Phase 5 Capacitor mobile source is implemented for `.cew` import/search/offline viewing; native Android/iOS projects, signing, biometrics, and device smoke tests remain.
- [ ] Phase 6.
- [ ] Phase 7.
