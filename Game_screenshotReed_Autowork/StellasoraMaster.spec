# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for the Stellasora Master application."""

from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

SPEC_PATH = Path(sys.argv[0]).resolve()
PROJECT_ROOT = SPEC_PATH.parent

# Include dynamically imported dependencies (e.g. cv2 modules)
hiddenimports = collect_submodules("cv2") + [
    "numpy",
    "ddddocr",
    "PIL",
    "flask",
]

def _data_entry(src: Path, dest: str):
    return (str(src), dest)

DATAS = collect_data_files("ddddocr")

# Bundle web static assets if present
static_dir = PROJECT_ROOT / "webapp" / "static"
if static_dir.exists():
    DATAS.append(_data_entry(static_dir, "webapp/static"))

# Bundle Flask templates if present
templates_dir = PROJECT_ROOT / "webapp" / "templates"
if templates_dir.exists():
    DATAS.append(_data_entry(templates_dir, "webapp/templates"))

# Core automation scripts and OpenCV templates
core_dir = PROJECT_ROOT / "core"
if core_dir.exists():
    DATAS.append(_data_entry(core_dir, "core"))

templates_zh_cn = PROJECT_ROOT / "templates_zh-CN"
if templates_zh_cn.exists():
    DATAS.append(_data_entry(templates_zh_cn, "templates_zh-CN"))

templates_zh_hant = PROJECT_ROOT / "templates_zh-Hant"
if templates_zh_hant.exists():
    DATAS.append(_data_entry(templates_zh_hant, "templates_zh-Hant"))

# Optional additional assets (frontend public files, etc.)
frontend_public = PROJECT_ROOT / "webapp" / "frontend" / "public"
if frontend_public.exists():
    DATAS.append(_data_entry(frontend_public, "webapp/frontend/public"))

config_file = PROJECT_ROOT / "config.json"
if config_file.exists():
    DATAS.append(_data_entry(config_file, "."))


a = Analysis(
    [str(PROJECT_ROOT / "run_app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="StellasoraMaster",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="StellasoraMaster",
)
