# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for MyoOptix
#
# Build command (run from myooptix_app/):
#   pyinstaller myooptix.spec
#
# The resulting bundle is in dist/MyoOptix/
# best_model.pth is NOT bundled — it is downloaded by the app at first launch.
#
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent  # repo root (one level above myooptix_app/)

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT / "myooptix_app"), str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "myooptix_app" / "assets"), "assets"),
        (str(ROOT / "cardio_py"),               "cardio_py"),
        (str(ROOT / "version.py"),              "."),
    ],
    hiddenimports=[
        "segmentation_models_pytorch",
        "timm",
        "timm.models",
        "skimage",
        "skimage.measure",
        "scipy.ndimage",
        "cv2",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MyoOptix",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # no terminal window; set True for debugging
    # icon="assets/heart.ico",  # uncomment after converting heart.svg → .ico
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MyoOptix",
)
