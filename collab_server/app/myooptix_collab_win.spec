# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for MyoOptix Collab Edition — Windows
#
# Build command (run from collab_server/app/):
#   pyinstaller myooptix_collab_win.spec --noconfirm
#
# Output: dist/MyoOptix/  → zip as MyoOptix-collab-v1.0.0-win.zip
# Upload to GitHub release: collab-v1.0.0
#
from pathlib import Path

APP_DIR   = Path(SPECPATH)           # collab_server/app/
REPO_ROOT = APP_DIR.parent.parent    # myooptix/ — contains cardio_py/

a = Analysis(
    ["main.py"],
    pathex=[str(APP_DIR), str(REPO_ROOT)],
    binaries=[],
    datas=[
        (str(APP_DIR   / "assets"),       "assets"),
        (str(APP_DIR   / "ui"),           "ui"),
        (str(APP_DIR   / "api_client.py"), "."),
        (str(APP_DIR   / "token_store.py"), "."),
        (str(REPO_ROOT / "cardio_py"),    "cardio_py"),
        (str(REPO_ROOT / "annotation_tool" / "best_model.pth"), "annotation_tool"),
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
