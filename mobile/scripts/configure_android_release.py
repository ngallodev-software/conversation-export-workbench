#!/usr/bin/env python3
"""Append opt-in CI release signing to a Capacitor Android Gradle file."""

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "// CEW_RELEASE_SIGNING"
BLOCK = r'''
// CEW_RELEASE_SIGNING
def cewKeystore = System.getenv("CEW_ANDROID_KEYSTORE")
if (cewKeystore) {
    def cewRelease = android.signingConfigs.findByName("cewRelease")
    if (cewRelease == null) {
        cewRelease = android.signingConfigs.create("cewRelease")
    }
    cewRelease.storeFile = file(cewKeystore)
    cewRelease.storePassword = System.getenv("CEW_ANDROID_KEYSTORE_PASSWORD")
    cewRelease.keyAlias = System.getenv("CEW_ANDROID_KEY_ALIAS")
    cewRelease.keyPassword = System.getenv("CEW_ANDROID_KEY_PASSWORD")
    android.buildTypes.release.signingConfig = cewRelease
}
'''


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: configure_android_release.py <android/app/build.gradle>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    if MARKER not in text:
        path.write_text(text.rstrip() + "\n" + BLOCK.lstrip(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
