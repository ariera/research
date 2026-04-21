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
