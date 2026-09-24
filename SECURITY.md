# Security Policy

Conversation Export Workbench processes files that can contain sensitive chat history. Security issues that could expose, corrupt, or unexpectedly transmit conversation data are treated as high priority.

## Supported versions

Security fixes are applied to the current default branch and, when appropriate, the latest tagged release.

## Reporting a vulnerability

Do not include private conversation exports, credentials, API keys, or other sensitive data in a public issue.

Prefer GitHub private vulnerability reporting for this repository when that option is available. If private reporting is not available, contact the repository owner through GitHub without publishing exploit details, then provide reproduction details through an agreed private channel.

Include:

- affected version or commit;
- operating system and Python version, when relevant;
- minimal reproduction steps using synthetic data;
- expected versus actual behavior;
- impact;
- any proposed mitigation.

## Privacy model

The formatter and viewer build process operate on local files and do not require ChatGPT, Claude, or DeepSeek credentials or a hosted conversion service. Generated viewer assets are self-contained and do not execute a runtime CDN script. The bundled server binds to loopback by default; exposing it to another interface requires `--allow-network`.

Generated conversation output may still contain everything present in the source export. Treat the output directory with the same sensitivity as the original archive.


## Mobile local protection

The mobile/PWA client can enable an optional PIN app lock. It stores only a PBKDF2-SHA-256 derived verifier with a random salt. This is an application access gate; it does **not** encrypt the imported archive at rest. Device/app sandbox protection remains the primary storage boundary.

CEW v2 attachment payloads are constrained to the `attachments/` namespace and validated for declared size, compression ratio, and SHA-256 integrity. The mobile client verifies payload hashes before making attachments available and hands them to the operating system through Share / Save rather than rendering arbitrary attachment content as active WebView HTML.

Authenticated CEW archive encryption is intentionally deferred until the project adopts a maintained audited cryptographic dependency. The project will not implement custom encryption primitives merely to preserve the Python-standard-library-only runtime.
