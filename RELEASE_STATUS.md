# Release Status

Tracks which platform has packaged and uploaded each version.
Both sides should update this file before pushing a release.

| Version | Windows zip | Mac zip | Notes |
|---------|-------------|---------|-------|
| v0.1.0 | ✅ `MyoOptix_v0.1.0_Windows.zip` | ❌ not uploaded | Old asset naming — auto-update won't work from this version |
| v0.2.0 | ✅ `MyoOptix-win.zip` | ✅ `MyoOptix-mac.zip` | |
| v0.3.0 | ❌ skipped  | ✅ `MyoOptix_v0.3.0_Mac.zip` | Mac-only; superseded by v0.3.1 |
| v0.3.1 | ✅ `MyoOptix-v0.3.1-win.zip` | ✅ `MyoOptix-v0.3.1-mac.zip` | Quick Analysis preset, toast close() fix |
| collab-v1.0.0 | ✅ `MyoOptix-collab-v1.0.0-win.zip` | ✅ `MyoOptix-collab-v1.0.0-mac.zip` | Collab Edition — separate app+server, see DEVLOG |

## Checklist for each new release

1. Both sides pull latest `main`
2. Bump `VERSION` in `version.py` (one side does this, pushes, other side pulls)
3. Each platform runs PyInstaller from that exact commit
4. Windows uploads `MyoOptix-vX.Y.Z-win.zip` to the GitHub Release tag
5. Mac uploads `MyoOptix-vX.Y.Z-mac.zip` to the same tag
6. Update this table: ⏳ → ✅
7. Push `RELEASE_STATUS.md`
