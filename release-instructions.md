 .github/workflows/build.yml is ready. Here's how it works:

  Triggers:                                                                                                                             
  - Any v* tag push (e.g. git tag v1.0.0 && git push --tags) — builds + creates a GitHub Release with all three binaries attached
  - workflow_dispatch — lets you trigger a manual build from the Actions UI without tagging                                             
                                                                                                             
  Build matrix: runs pyinstaller conv-tool.spec in parallel on ubuntu-latest, macos-latest, and windows-latest using Python 3.11.
                                         
  Release job: only runs on tag pushes. Downloads the three artifacts, renames them (conv-tool-linux, conv-tool-macos,
  conv-tool-windows.exe), and attaches them to the GitHub Release via softprops/action-gh-release.

  To ship a release:
  git tag v1.0.0
  git push origin v1.0.0