VERSION = "0.4.0"


def get_version_string() -> str:
    """
    Returns VERSION plus the short git hash when running from source.
    e.g. "0.1.0 (43f5900)"  or just "0.1.0" in a frozen build with no git.
    """
    import subprocess, sys
    if getattr(sys, "frozen", False):
        return VERSION  # frozen build: no git available
    try:
        h = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=__file__[:__file__.rfind("\\")],
            text=True,
        ).strip()
        return f"{VERSION} ({h})"
    except Exception:
        return VERSION
