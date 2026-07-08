# Release Status

Tracks which platform has packaged and uploaded each version.
Both sides should update this file before pushing a release.

| Version | Windows zip | Mac zip | Notes |
|---------|-------------|---------|-------|
| v0.1.0 | ✅ `MyoOptix_v0.1.0_Windows.zip` | ❌ not uploaded | Old asset naming — auto-update won't work from this version |
| v0.2.0 | ✅ `MyoOptix-win.zip` | ❌ pending | New naming: `MyoOptix-win.zip` / `MyoOptix-mac.zip` |
| v0.3.0 | ⏳ pending | ⏳ pending | UI overhaul, microscope presets, grant credits |

## Checklist for each new release

1. Both sides pull latest `main`
2. Bump `VERSION` in `version.py` (one side does this, pushes, other side pulls)
3. Each platform runs PyInstaller from that exact commit
4. Windows uploads `MyoOptix-win.zip` to the GitHub Release tag
5. Mac uploads `MyoOptix-mac.zip` to the same tag
6. Update this table: ⏳ → ✅
7. Push `RELEASE_STATUS.md`
