# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for UltraStar Clone GUI."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ["src/ultrastar_clone/gui_app.py"],
    pathex=["src"],
    binaries=[
        ("src/ultrastar_clone/bin/ffmpeg.exe", "."),
    ],
    datas=[
        *collect_data_files("qfluentwidgets"),
    ],
    hiddenimports=[
        *collect_submodules("qfluentwidgets"),
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PySide2",
        "PySide6",
        "shiboken6",
        "shiboken2",
        "beautifulsoup4",
        "bs4",
        "requests",
        "pytest",
        "unittest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="UltraStar-Clone",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ---- post-build: zip the exe for GitHub Releases ----
import os as _os
import zipfile as _zipfile

_dist_dir = _os.path.join(SPECPATH, "dist")
_exe_path = _os.path.join(_dist_dir, "UltraStar-Clone.exe")
_zip_path = _os.path.join(_dist_dir, "UltraStar-Clone.zip")

if _os.path.exists(_exe_path):
    with _zipfile.ZipFile(_zip_path, "w", _zipfile.ZIP_DEFLATED) as _zf:
        _zf.write(_exe_path, "UltraStar-Clone.exe")
    print(f"  -> zipped: {_zip_path}")
