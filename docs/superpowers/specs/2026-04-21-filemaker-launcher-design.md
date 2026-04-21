# FileMaker Launcher — Design Spec

**Date:** 2026-04-21

## Overview

A native macOS `.app` bundle that silently opens an embedded `.fmpsl` FileMaker solution file using the highest compatible FileMaker version installed on the machine. No UI beyond a system alert on failure.

## Bundle Structure

```
FileMakerLauncher.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── launcher          ← shell script, chmod +x
│   └── Resources/
│       ├── solution.fmpsl    ← embedded solution file
│       └── AppIcon.icns      ← user-provided icon
```

The script computes its own path via `$(dirname "$0")` and resolves `../Resources/solution.fmpsl` relative to itself, making the bundle fully relocatable.

## Info.plist

Minimal metadata — no document type registration, no Dock presence:

| Key                  | Value                            |
|----------------------|----------------------------------|
| CFBundleName         | FileMakerLauncher                |
| CFBundleExecutable   | launcher                         |
| CFBundleIdentifier   | com.yourorg.filemaker-launcher   |
| CFBundlePackageType  | APPL                             |
| CFBundleIconFile     | AppIcon                          |

## Version Detection

Compatible FileMaker versions: **16, 17, 18** (in that priority order, highest wins).

The script checks both naming conventions used across those versions:

- `FileMaker Pro {N}.app`
- `FileMaker Pro Advanced {N}.app`

Detection order (descending): 18 → 17 → 16. First match wins.

Search location: `/Applications/`

## Launch Logic

```
SCRIPT_DIR=$(dirname "$0")
FMPSL="$SCRIPT_DIR/../Resources/solution.fmpsl"

for version in 18 17 16; do
  for name in "FileMaker Pro $version" "FileMaker Pro Advanced $version"; do
    app="/Applications/$name.app"
    if [ -d "$app" ]; then
      open -a "$app" "$FMPSL"
      exit 0
    fi
  done
done

osascript -e 'display alert "No compatible FileMaker version found." message "FileMaker Pro 16, 17, or 18 is required to open this solution."'
exit 1
```

## Error Handling

| Condition                        | Behaviour                              |
|----------------------------------|----------------------------------------|
| Compatible FM found              | Opens solution silently, app exits     |
| No compatible FM found           | macOS system alert via `osascript`     |
| `.fmpsl` missing from bundle     | `open` fails silently (edge case)      |

## Deliverables (Research Output)

Following the project's AGENTS.md conventions:

- `filemaker-launcher/notes.md` — research log and findings
- `filemaker-launcher/README.md` — summary report
- `filemaker-launcher/FileMakerLauncher.app/` — the working app bundle (excluding user-provided `.fmpsl` and `.icns` which are slot-in files)
- `filemaker-launcher/launcher` — the shell script source
- `filemaker-launcher/Info.plist` — the plist source

## Out of Scope

- Handling FileMaker versions outside 16–18
- Checking whether the `.fmpsl` file is valid before opening
- Supporting non-standard FileMaker install locations
- Code signing or notarization
