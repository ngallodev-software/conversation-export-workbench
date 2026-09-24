# Mobile offline viewer

This directory contains the first Android/iOS client for Conversation Export Workbench.

It is intentionally built **after** the canonical `cew.conversation/v1` model and `.cew` bundle format so mobile does not need to duplicate ChatGPT, Claude, and DeepSeek parsing logic.

## Current capabilities

- imports a local `.cew` file through the platform file chooser;
- validates bundle/conversation schema versions;
- limits compressed input size, member size, and ZIP expansion ratio;
- stores the parsed archive in IndexedDB inside the app sandbox;
- searches the bundle-provided local full-text index;
- renders canonical text, thinking, search, read-link, tool-use, tool-result, and attachment metadata;
- constructs the DOM with `textContent` rather than inserting conversation HTML;
- packages all application resources locally;
- requires explicit user interaction before opening HTTP(S) links;
- works without provider credentials or a backend.

## Toolchain

Pinned in `package.json`:

- Capacitor 8.5.2
- Vite 8.3.0
- fflate 0.8.3

Node.js must satisfy Vite 8's supported runtime requirements.

## Web development

```bash
cd mobile
npm install
npm run dev
```

Build:

```bash
npm run build
```

## Android

One-time native project creation:

```bash
npm run android:add
```

Then:

```bash
npm run android:open
```

## iOS

Requires macOS/Xcode.

One-time native project creation:

```bash
npm run ios:add
```

Then:

```bash
npm run ios:open
```

## Security model

The app does not require an Internet connection for import, search, or viewing. The WebView CSP permits only packaged application resources. Conversation text is rendered as text nodes, not trusted HTML.

The initial implementation caps compressed `.cew` imports at 128 MiB and each required expanded member at 256 MiB. Large-archive streaming and attachment payload storage belong in a later mobile phase.

## Next mobile work

- generate and commit native Android/iOS projects once signing/package identifiers are finalized;
- add mobile build CI;
- add app-lock/biometric protection;
- add native share/open-in integration;
- support attachment payloads from a future bundle schema;
- performance-test multi-gigabyte histories before relaxing import limits.
