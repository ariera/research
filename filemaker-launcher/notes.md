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

## Key findings

- A `.app` bundle is just a directory — no Xcode needed. macOS reads `Info.plist`
  for metadata and executes whatever is at `Contents/MacOS/<CFBundleExecutable>`.
- Shell scripts work as the bundle executable when `chmod +x` is set.
- `LSUIElement = true` prevents a Dock bounce during brief execution.
- `osascript -e 'display alert "..."'` produces native macOS alerts from shell.
  Works even with `LSUIElement = true` because osascript spawns its own process.
- `open -a App file` is asynchronous — the script exits immediately, which is
  the desired silent behaviour.
- The `[[ "${BASH_SOURCE[0]}" == "${0}" ]]` guard makes the script sourceable
  for unit testing without triggering the launch logic.
- FileMaker Pro and FileMaker Pro Advanced are separate app names for v16–18;
  v19+ merged them. Detection must handle both variants.
- Gatekeeper will block unsigned apps on first run. Right-click → Open bypasses
  this for testing. Production use requires code signing.
