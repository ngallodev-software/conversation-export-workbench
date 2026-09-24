# Mobile offline viewer

The mobile client is a Capacitor 8 application and installable PWA that consumes the same `cew.conversation/v1` model used by the desktop workbench.

## Current capabilities

- imports `.cew` v1/v2 archives;
- imports raw ChatGPT, Claude, and DeepSeek export ZIP/JSON files directly on-device;
- validates conversation and bundle schemas;
- limits compressed/member sizes and ZIP expansion ratios;
- stores the parsed archive in IndexedDB inside the app sandbox;
- searches every imported conversation locally;
- renders text, thinking, search, read-link, tool-use, tool-result, and attachment metadata with DOM text nodes rather than trusted conversation HTML;
- verifies CEW v2 attachment size and SHA-256 before accepting payloads;
- shares/saves verified attachments through the browser/OS handoff instead of rendering arbitrary attachments as active content;
- packages all application resources locally;
- requires explicit user interaction before opening HTTP(S) links;
- supports system/dark/light themes, reduced-motion preferences, skip navigation, and accessible labels;
- shows conversation/message/provider/attachment archive statistics;
- provides an optional local app-lock PIN;
- installs as a standalone PWA with offline application-shell caching;
- works without provider credentials or a backend.

The app-lock PIN is an access gate, not encryption. The archive remains protected primarily by the platform app sandbox/device security.

## Reproducible toolchain

Pinned in `package.json` and `package-lock.json`:

- Capacitor 8.5.2
- Vite 8.3.0
- fflate 0.8.3

Use Node.js 22.16+.

```bash
cd mobile
npm ci
npm test
npm run build
```

Synthetic large-archive search profiling:

```bash
npm run profile
npm run profile -- 50000
```

## Android

For local development:

```bash
npm ci
npm run build
npx cap add android
npx cap sync android
npx cap open android
```

Release CI always builds an installable sideload APK. If stable release-signing secrets are configured it instead also produces a signed release APK and Google Play AAB.

Repository secrets used for stable Android signing:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

No keystore bytes or passwords are stored in the repository.

## iOS / TestFlight

Local native project generation requires macOS/Xcode:

```bash
npm ci
npm run build
npx cap add ios
npx cap sync ios
npx cap open ios
```

CI always validates an unsigned iOS Simulator build. A device-installable IPA is built when these repository secrets are configured:

- `APPLE_TEAM_ID`
- `APPLE_API_KEY_ID`
- `APPLE_API_ISSUER_ID`
- `APPLE_API_PRIVATE_KEY_BASE64`

And this repository variable is configured:

- `IOS_BUNDLE_ID`

Set repository variable `ENABLE_TESTFLIGHT_UPLOAD=true` to upload the signed IPA to TestFlight automatically after export.

## Native project policy

The `android/` and `ios/` platform trees are generated from the pinned Capacitor version in CI and development commands rather than committed. This keeps generated IDE/platform files out of the source of truth while still exercising native generation and builds on every release candidate.

## Security limits

Current mobile imports cap the compressed source at 128 MiB, individual required members at 256 MiB, total accepted attachment payloads at 128 MiB, and suspicious compression ratios at 200:1.

Encrypted CEW archives are intentionally not implemented with home-grown cryptography. Any future encrypted bundle envelope should use a maintained authenticated-encryption library and a separately versioned format.

## Remaining optional work

- automated emulator/device UI smoke tests;
- native biometric unlock layered on top of the existing local app lock;
- streaming import for archives larger than the current mobile memory limits;
- App Store / Play Store publication once account/signing credentials are configured.
