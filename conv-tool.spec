# conv-tool.spec — PyInstaller spec for the conv-tool single-binary bundle.
#
# Build with:
#   pip install pyinstaller
#   pip install tomli  # only needed for Python < 3.11
#   pyinstaller conv-tool.spec
#
# Output: dist/conv-tool

a = Analysis(
    ["cli_main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("provider_templates", "provider_templates"),
        ("config",             "config"),
    ],
    hiddenimports=["tomllib", "tomli"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="conv-tool",
    debug=False,
    strip=False,
    upx=True,
    console=True,
    onefile=True,
)
