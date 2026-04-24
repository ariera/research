# CLI Alphanumeric Whitespace Update

Date: 2026-04-24

## Summary

Updated the `string-permutation-kata` CLI alphabet presets so `--preset letters-numbers` treats a literal space as part of the preset alphabet. The `letters-numbers-symbols` preset was also updated to remain a superset.

## Changes

- `string-permutation-kata/rust/src/bin/enumerate.rs`
  - Added `' '` to `AlphabetPreset::LettersNumbers`.
  - Added `' '` to `AlphabetPreset::LettersNumbersSymbols`.
  - Added a CLI-focused unit test that parses `--preset letters-numbers` and asserts the selected alphabet contains a space.
- `string-permutation-kata/README.md`
  - Updated the preset table counts and descriptions.

## Verification

From `string-permutation-kata/rust`:

```sh
cargo test letters_numbers_cli_preset_includes_space
cargo test
```

Results:

- Focused CLI preset test passed.
- Full test suite passed: 1 CLI unit test, 15 integration tests, and doc tests.

## Diff

The code diff is saved in `string-permutation-kata.diff`.
