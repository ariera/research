# Notes

- 2026-04-24: Created investigation folder `string-permutation-kata-cli-whitespace`.
- 2026-04-24: Request: add whitespace as a valid alphanumeric character to the CLI flags.
- 2026-04-24: CLI presets live in `string-permutation-kata/rust/src/bin/enumerate.rs`.
- 2026-04-24: Current `AlphabetPreset::LettersNumbers` is `a-z`, `A-Z`, `0-9`; whitespace is only included by `FullAscii`.
- 2026-04-24: Added red test `letters_numbers_preset_includes_space`; it failed because the preset did not contain `' '`.
- 2026-04-24: Updated `LettersNumbers` to include space and `LettersNumbersSymbols` to remain a superset.
- 2026-04-24: Updated CLI preset documentation in `string-permutation-kata/README.md`.
- 2026-04-24: Tightened the test to parse the actual `--preset letters-numbers` CLI flag before checking the alphabet.
- 2026-04-24: Verification: `cargo test` passed with 1 CLI unit test, 15 integration tests, and doc tests.
