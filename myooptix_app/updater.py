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

# Dedicated release tag that hosts best_model.pth as an asset
WEIGHTS_TAG  = "model-weights"
WEIGHTS_URL  = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
    f"/releases/download/{WEIGHTS_TAG}/best_model.pth"
)

_IS_MAC      = platform.system() == "Darwin"
_PLATFORM    = "mac" if _IS_MAC else "win"


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
    Tries versioned name first (MyoOptix-v0.3.1-mac.zip) then plain (MyoOptix-mac.zip).
    Returns the path to the downloaded zip.
    """
    import urllib.error
    candidates = [
        f"MyoOptix-{tag}-{_PLATFORM}.zip",   # versioned: MyoOptix-v0.3.1-mac.zip
        f"MyoOptix-{_PLATFORM}.zip",          # plain:     MyoOptix-mac.zip / MyoOptix-win.zip
    ]
    last_err = None
    for asset_name in candidates:
        url = (
            f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
            f"/releases/download/{tag}/{asset_name}"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MyoOptix-updater/1.0"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                dest = desktop_path() / asset_name
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
        except urllib.error.HTTPError as e:
            if e.code == 404:
                last_err = e
                continue
            raise
    raise last_err or RuntimeError(f"No app asset found for tag {tag} on {_PLATFORM}")


def check_for_update(current_version: str) -> dict | None:
    """
    Query GitHub Releases API.
    Returns dict(tag, url, body) if a newer main-app tag is found, or None.
    Only considers releases with tags matching vX.Y.Z (ignores collab/other releases).
    """
    import re
    _VER_RE = re.compile(r"^v\d+\.\d+\.\d+$")

    def _ver(s):
        try:
            return tuple(int(x) for x in s.split("."))
        except Exception:
            return (0, 0, 0)

    try:
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases?per_page=20"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MyoOptix-updater/1.0",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            releases = json.loads(resp.read())
        for release in releases:
            tag = release.get("tag_name", "")
            if not _VER_RE.match(tag):
                continue  # skip collab/model-weights/other tags
            latest = tag.lstrip("v")
            if _ver(latest) > _ver(current_version):
                return {
                    "tag": tag,
                    "url": release.get("html_url", RELEASES_URL),
                    "body": release.get("body", ""),
                }
            break  # latest is same or older → up to date
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
