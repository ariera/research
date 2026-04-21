# FileMaker Launcher `.app` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a hand-crafted macOS `.app` bundle that silently finds the highest compatible FileMaker version (16/17/18) installed and opens an embedded `.fmpsl` solution file.

**Architecture:** A shell script (`launcher`) lives at `Contents/MacOS/launcher` inside the bundle. It exposes a sourceable `_find_fm` function that scans `/Applications` for FileMaker variants in descending version order, then calls `open -a` to launch. On failure it fires a native macOS alert via `osascript`. A `build.sh` assembles the bundle from sources. The `BASH_SOURCE` guard lets the script be sourced by tests without triggering `_main`.

**Tech Stack:** bash, macOS `open`, `osascript` (AppleScript), standard macOS `.app` bundle structure (no Xcode required).

---

## File Map

| File | Role |
|------|------|
| `filemaker-launcher/notes.md` | Research log, updated throughout |
| `filemaker-launcher/launcher` | Shell script — detection + launch logic |
| `filemaker-launcher/test_launcher.sh` | Tests for `_find_fm` detection function |
| `filemaker-launcher/Info.plist` | App bundle metadata |
| `filemaker-launcher/build.sh` | Assembles `FileMakerLauncher.app/` from sources |
| `filemaker-launcher/README.md` | Final research report |
| `filemaker-launcher/FileMakerLauncher.app/` | Output of `build.sh` (committed) |

---

### Task 1: Create project folder and notes

**Files:**
- Create: `filemaker-launcher/notes.md`

- [ ] **Step 1: Create the folder and notes file**

```bash
mkdir filemaker-launcher
```

Create `filemaker-launcher/notes.md`:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add filemaker-launcher/notes.md
git commit -m "research(filemaker-launcher): create project folder and notes"
```

---

### Task 2: Write failing detection tests

**Files:**
- Create: `filemaker-launcher/test_launcher.sh`

- [ ] **Step 1: Write the test file**

Create `filemaker-launcher/test_launcher.sh`:

```bash
#!/bin/bash
# Tests for the _find_fm detection function.
# Sources launcher to get _find_fm without running _main.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "PASS: $desc"
    PASS=$((PASS+1))
  else
    echo "FAIL: $desc"
    echo "  expected: $expected"
    echo "  actual:   $actual"
    FAIL=$((FAIL+1))
  fi
}

assert_fails() {
  local desc="$1" result
  shift
  result=$("$@" 2>/dev/null) && {
    echo "FAIL: $desc (expected failure, got: $result)"
    FAIL=$((FAIL+1))
  } || {
    echo "PASS: $desc"
    PASS=$((PASS+1))
  }
}

# Source launcher to import _find_fm (BASH_SOURCE guard prevents _main from running)
# shellcheck source=launcher
source "$SCRIPT_DIR/launcher"

TMPBASE=$(mktemp -d)
trap 'rm -rf "$TMPBASE"' EXIT

# Test 1: picks v18 over v16 when both installed
T="$TMPBASE/t1"
mkdir -p "$T/FileMaker Pro 16.app" "$T/FileMaker Pro 18.app"
assert_eq "prefers v18 over v16" "$T/FileMaker Pro 18.app" "$(_find_fm "$T")"

# Test 2: falls back to v17 when v18 absent
T="$TMPBASE/t2"
mkdir -p "$T/FileMaker Pro 17.app"
assert_eq "uses v17 when only v17 present" "$T/FileMaker Pro 17.app" "$(_find_fm "$T")"

# Test 3: falls back to v16 when only v16 present
T="$TMPBASE/t3"
mkdir -p "$T/FileMaker Pro 16.app"
assert_eq "uses v16 as last resort" "$T/FileMaker Pro 16.app" "$(_find_fm "$T")"

# Test 4: finds Advanced variant when regular absent
T="$TMPBASE/t4"
mkdir -p "$T/FileMaker Pro Advanced 17.app"
assert_eq "finds Advanced variant" "$T/FileMaker Pro Advanced 17.app" "$(_find_fm "$T")"

# Test 5: prefers regular over Advanced for same version
T="$TMPBASE/t5"
mkdir -p "$T/FileMaker Pro 18.app" "$T/FileMaker Pro Advanced 18.app"
assert_eq "prefers regular over Advanced same version" "$T/FileMaker Pro 18.app" "$(_find_fm "$T")"

# Test 6: v18 Advanced beats v17 regular
T="$TMPBASE/t6"
mkdir -p "$T/FileMaker Pro Advanced 18.app" "$T/FileMaker Pro 17.app"
assert_eq "v18 Advanced beats v17 regular" "$T/FileMaker Pro Advanced 18.app" "$(_find_fm "$T")"

# Test 7: returns failure when no FM present
T="$TMPBASE/t7"
mkdir -p "$T"
assert_fails "fails when no FM present" _find_fm "$T"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
```

- [ ] **Step 2: Make test file executable**

```bash
chmod +x filemaker-launcher/test_launcher.sh
```

- [ ] **Step 3: Run tests — confirm they fail (launcher doesn't exist yet)**

```bash
cd filemaker-launcher && bash test_launcher.sh
```

Expected: error like `launcher: No such file or directory` — the script can't be sourced yet.

---

### Task 3: Implement launcher script

**Files:**
- Create: `filemaker-launcher/launcher`

- [ ] **Step 1: Write the launcher script**

Create `filemaker-launcher/launcher`:

```bash
#!/bin/bash
set -euo pipefail

# Finds highest compatible FileMaker version in search_path (default: /Applications).
# Prints the full .app path and returns 0 on success, 1 if none found.
_find_fm() {
  local search_path="${1:-/Applications}"
  local version name app
  for version in 18 17 16; do
    for name in "FileMaker Pro $version" "FileMaker Pro Advanced $version"; do
      app="$search_path/$name.app"
      if [ -d "$app" ]; then
        echo "$app"
        return 0
      fi
    done
  done
  return 1
}

_main() {
  local script_dir
  script_dir="$(cd "$(dirname "$0")" && pwd)"
  local fmpsl="$script_dir/../Resources/solution.fmpsl"

  local fm_app
  fm_app=$(_find_fm) || {
    osascript -e 'display alert "No compatible FileMaker version found." message "FileMaker Pro 16, 17, or 18 is required to open this solution."'
    exit 1
  }

  open -a "$fm_app" "$fmpsl"
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] && _main "$@"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x filemaker-launcher/launcher
```

- [ ] **Step 3: Run tests — confirm they pass**

```bash
cd filemaker-launcher && bash test_launcher.sh
```

Expected output:
```
PASS: prefers v18 over v16
PASS: uses v17 when only v17 present
PASS: uses v16 as last resort
PASS: finds Advanced variant
PASS: prefers regular over Advanced same version
PASS: v18 Advanced beats v17 regular
PASS: fails when no FM present

Results: 7 passed, 0 failed
```

- [ ] **Step 4: Commit**

```bash
git add filemaker-launcher/launcher filemaker-launcher/test_launcher.sh
git commit -m "research(filemaker-launcher): add launcher script and detection tests"
```

---

### Task 4: Write Info.plist

**Files:**
- Create: `filemaker-launcher/Info.plist`

- [ ] **Step 1: Write the plist**

Create `filemaker-launcher/Info.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>FileMakerLauncher</string>
  <key>CFBundleExecutable</key>
  <string>launcher</string>
  <key>CFBundleIdentifier</key>
  <string>com.yourorg.filemaker-launcher</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>10.12</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
```

`LSUIElement = true` suppresses the Dock bounce during the brief script execution.

- [ ] **Step 2: Validate the plist**

```bash
plutil -lint filemaker-launcher/Info.plist
```

Expected: `filemaker-launcher/Info.plist: OK`

- [ ] **Step 3: Commit**

```bash
git add filemaker-launcher/Info.plist
git commit -m "research(filemaker-launcher): add Info.plist"
```

---

### Task 5: Write build.sh and assemble the bundle

**Files:**
- Create: `filemaker-launcher/build.sh`
- Create (output): `filemaker-launcher/FileMakerLauncher.app/`

- [ ] **Step 1: Write build.sh**

Create `filemaker-launcher/build.sh`:

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="$SCRIPT_DIR/FileMakerLauncher.app"

echo "Building $BUNDLE..."

rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS"
mkdir -p "$BUNDLE/Contents/Resources"

cp "$SCRIPT_DIR/launcher" "$BUNDLE/Contents/MacOS/launcher"
chmod +x "$BUNDLE/Contents/MacOS/launcher"

cp "$SCRIPT_DIR/Info.plist" "$BUNDLE/Contents/Info.plist"

if [ -f "$SCRIPT_DIR/AppIcon.icns" ]; then
  cp "$SCRIPT_DIR/AppIcon.icns" "$BUNDLE/Contents/Resources/AppIcon.icns"
  echo "  icon: copied AppIcon.icns"
else
  echo "  icon: AppIcon.icns not found — skipping (place it next to build.sh to include)"
fi

if [ -f "$SCRIPT_DIR/solution.fmpsl" ]; then
  cp "$SCRIPT_DIR/solution.fmpsl" "$BUNDLE/Contents/Resources/solution.fmpsl"
  echo "  solution: copied solution.fmpsl"
else
  touch "$BUNDLE/Contents/Resources/solution.fmpsl"
  echo "  solution: placeholder created — replace Contents/Resources/solution.fmpsl before distributing"
fi

echo ""
echo "Done: $BUNDLE"
```

- [ ] **Step 2: Make build.sh executable**

```bash
chmod +x filemaker-launcher/build.sh
```

- [ ] **Step 3: Run build.sh**

```bash
cd filemaker-launcher && bash build.sh
```

Expected output:
```
Building .../FileMakerLauncher.app...
  icon: AppIcon.icns not found — skipping (place it next to build.sh to include)
  solution: placeholder created — replace Contents/Resources/solution.fmpsl before distributing

Done: .../FileMakerLauncher.app
```

- [ ] **Step 4: Verify bundle structure**

```bash
find filemaker-launcher/FileMakerLauncher.app -type f | sort
```

Expected:
```
filemaker-launcher/FileMakerLauncher.app/Contents/Info.plist
filemaker-launcher/FileMakerLauncher.app/Contents/MacOS/launcher
filemaker-launcher/FileMakerLauncher.app/Contents/Resources/solution.fmpsl
```

- [ ] **Step 5: Verify the launcher inside the bundle is executable**

```bash
ls -la filemaker-launcher/FileMakerLauncher.app/Contents/MacOS/launcher
```

Expected: permissions include `-rwxr-xr-x`

- [ ] **Step 6: Commit**

```bash
git add filemaker-launcher/build.sh filemaker-launcher/FileMakerLauncher.app
git commit -m "research(filemaker-launcher): add build.sh and assembled bundle"
```

---

### Task 6: Write README.md and final commit

**Files:**
- Create: `filemaker-launcher/README.md`
- Modify: `filemaker-launcher/notes.md`

- [ ] **Step 1: Write README.md**

Create `filemaker-launcher/README.md`:

````markdown
# FileMaker Launcher

A native macOS `.app` that silently opens an embedded FileMaker solution file
(`.fmpsl`) using the highest compatible FileMaker version installed on the
machine. No UI. Compatible with FileMaker Pro / FileMaker Pro Advanced 16, 17,
and 18.

## How it works

`FileMakerLauncher.app` is a hand-crafted `.app` bundle — a directory structure
macOS recognises as an application, with no Xcode project or Cocoa runtime
required. When double-clicked, macOS executes the shell script at
`Contents/MacOS/launcher`.

The script:
1. Scans `/Applications` for FileMaker Pro [16|17|18].app in descending order
2. Picks the highest version found (regular variant preferred over Advanced for
   the same version number)
3. Calls `open -a "$fm_app" "$fmpsl"` to open the embedded solution
4. On failure, shows a native macOS alert via `osascript`

`LSUIElement = true` in `Info.plist` prevents a Dock icon from appearing during
the brief script execution.

## Bundle structure

```
FileMakerLauncher.app/
└── Contents/
    ├── Info.plist            ← app metadata
    ├── MacOS/
    │   └── launcher          ← shell script (executable)
    └── Resources/
        ├── solution.fmpsl    ← your FileMaker shortcut file
        └── AppIcon.icns      ← your app icon
```

## Customising for distribution

1. Place your `solution.fmpsl` file next to `build.sh`
2. Place your `AppIcon.icns` file next to `build.sh`
3. Edit `Info.plist` — update `CFBundleIdentifier` to your organisation's
   reverse domain (e.g. `com.acme.my-solution`)
4. Run `bash build.sh` to assemble the bundle
5. Distribute `FileMakerLauncher.app`

## Compatibility

| FileMaker version | Detected app names |
|-------------------|--------------------|
| 18                | FileMaker Pro 18.app, FileMaker Pro Advanced 18.app |
| 17                | FileMaker Pro 17.app, FileMaker Pro Advanced 17.app |
| 16                | FileMaker Pro 16.app, FileMaker Pro Advanced 16.app |

## Testing

The detection logic is covered by a pure shell test suite that creates mock
`.app` directories in a temp folder — no FileMaker installation required:

```bash
bash test_launcher.sh
```

## Limitations

- Non-standard install locations (outside `/Applications`) are not supported
- Code signing / notarization is not included — Gatekeeper may block on first
  launch; right-click → Open to bypass
- FileMaker versions outside 16–18 are out of scope
````

- [ ] **Step 2: Append final findings to notes.md**

Append to `filemaker-launcher/notes.md`:

```markdown

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
```

- [ ] **Step 3: Final commit**

```bash
git add filemaker-launcher/README.md filemaker-launcher/notes.md
git commit -m "research(filemaker-launcher): add README and final notes"
```
