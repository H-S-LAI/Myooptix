"""
GitHub Releases integration: app update checking + model weight download.
"""

import json
import sys
import urllib.request
from pathlib import Path

import platform

GITHUB_OWNER = "H-S-LAI"
GITHUB_REPO  = "Myooptix"
RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
API_LATEST   = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Dedicated release tag that hosts best_model.pth as an asset
WEIGHTS_TAG  = "model-weights"
WEIGHTS_URL  = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
    f"/releases/download/{WEIGHTS_TAG}/best_model.pth"
)

# Asset name pattern per platform
_IS_MAC = platform.system() == "Darwin"
APP_ASSET_NAME = "MyoOptix-mac.zip" if _IS_MAC else "MyoOptix-win.zip"


def weights_path() -> Path:
    """Return expected path for best_model.pth (works both frozen and from source)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    return base / "annotation_tool" / "best_model.pth"


def weights_exist() -> bool:
    return weights_path().exists()


def desktop_path() -> Path:
    """Return the user's Desktop folder."""
    return Path.home() / "Desktop"


def download_app_update(tag: str, progress_cb=None) -> Path:
    """
    Download the platform-appropriate app zip from a GitHub Release to the Desktop.
    Returns the path to the downloaded zip.
    """
    url = (
        f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
        f"/releases/download/{tag}/{APP_ASSET_NAME}"
    )
    dest = desktop_path() / APP_ASSET_NAME
    req = urllib.request.Request(url, headers={"User-Agent": "MyoOptix-updater/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        received = 0
        chunk_size = 1 << 15
        with open(dest, "wb") as fh:
            while True:
                buf = resp.read(chunk_size)
                if not buf:
                    break
                fh.write(buf)
                received += len(buf)
                if progress_cb:
                    progress_cb(received, total)
    return dest


def check_for_update(current_version: str) -> dict | None:
    """
    Query GitHub Releases API.
    Returns dict(tag, url, body) if a newer tag is found, or None.
    """
    try:
        req = urllib.request.Request(
            API_LATEST,
            headers={
                "User-Agent": "MyoOptix-updater/1.0",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        tag = data.get("tag_name", "")
        latest = tag.lstrip("v")
        if latest and latest != current_version:
            return {
                "tag": tag,
                "url": data.get("html_url", RELEASES_URL),
                "body": data.get("body", ""),
            }
    except Exception:
        pass
    return None


def download_weights(progress_cb=None) -> Path:
    """
    Download best_model.pth from GitHub Releases.
    progress_cb(received_bytes, total_bytes) is called each chunk.
    """
    dest = weights_path()
    dest.parent.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(
        WEIGHTS_URL, headers={"User-Agent": "MyoOptix-updater/1.0"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        received = 0
        chunk_size = 1 << 15  # 32 KB
        with open(dest, "wb") as fh:
            while True:
                buf = resp.read(chunk_size)
                if not buf:
                    break
                fh.write(buf)
                received += len(buf)
                if progress_cb:
                    progress_cb(received, total)
    return dest
