# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for MyoOptix — macOS .app bundle
#
# Build command (run from myooptix_app/):
#   pyinstaller myooptix_mac.spec --noconfirm
#
# Result: dist/MyoOptix.app
# best_model.pth is bundled under annotation_tool/ — no download needed at first launch.
#
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent  # repo root (one level above myooptix_app/)

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT / "myooptix_app"), str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "myooptix_app" / "assets"),             "assets"),
        (str(ROOT / "cardio_py"),                           "cardio_py"),
        (str(ROOT / "version.py"),                          "."),
        (str(ROOT / "annotation_tool" / "best_model.pth"), "annotation_tool"),
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
    console=False,
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

app = BUNDLE(
    coll,
    name="MyoOptix.app",
    icon=None,
    bundle_identifier="com.tmu.myooptix",
    info_plist={
        "CFBundleShortVersionString": "0.4.1",
        "CFBundleName": "MyoOptix",
        "NSHighResolutionCapable": True,
    },
)
