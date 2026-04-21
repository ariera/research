# FileMaker Launcher — Research Notes

## Goal
Build a minimal macOS `.app` that silently opens an embedded `.fmpsl` file
using the highest installed compatible FileMaker version (16, 17, or 18).

## Approach
Hand-crafted `.app` bundle — just a directory with `Info.plist` and a shell
script as the executable. No Xcode, no Automator, no third-party tools.

Key macOS mechanisms:
- `open -a /Applications/FileMaker.app file.fmpsl` opens a file with a specific app
- `osascript -e 'display alert "..."'` shows a native alert from a shell script
- `LSUIElement = true` in Info.plist prevents a Dock icon while the script runs
- `[[ "${BASH_SOURCE[0]}" == "${0}" ]]` guard lets the script be sourced for testing

## FileMaker naming conventions observed
Versions 16–18 ship as either:
- `FileMaker Pro {N}.app`
- `FileMaker Pro Advanced {N}.app`
(Advanced was merged into the base product in v19, so v16–18 have both variants)
