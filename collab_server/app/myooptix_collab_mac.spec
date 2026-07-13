# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for MyoOptix Collab — macOS .app bundle
#
# Build command (run from app/):
#   pyinstaller myooptix_collab_mac.spec
#
from pathlib import Path

ROOT = Path(SPECPATH)  # app/

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "assets"),   "assets"),
        (str(ROOT / "cardio_py"), "cardio_py"),
        (str(ROOT / "ui"),        "ui"),
        (str(ROOT / "api_client.py"),  "."),
        (str(ROOT / "token_store.py"), "."),
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
    icon=str(ROOT / "assets" / "icon.png"),
    bundle_identifier="com.tmu.myooptix.collab",
    info_plist={
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleName": "MyoOptix",
        "NSHighResolutionCapable": True,
    },
)
