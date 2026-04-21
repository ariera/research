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
