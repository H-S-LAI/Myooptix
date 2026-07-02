# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for MyoOptix — macOS .app bundle
#
# Build command (run from myooptix_app/):
#   pyinstaller myooptix_mac.spec
#
# Result: dist/MyoOptix.app
#
from pathlib import Path

ROOT = Path(SPECPATH).parent  # repo root

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
    name="MyoOptix",
)

app = BUNDLE(
    coll,
    name="MyoOptix.app",
    icon=None,
    bundle_identifier="com.tmu.myooptix",
    info_plist={
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleName": "MyoOptix",
        "NSHighResolutionCapable": True,
    },
)
