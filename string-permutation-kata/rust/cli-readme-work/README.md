# CLI README Investigation Report

## Scope

Added a crate-local README at `string-permutation-kata/rust/README.md` focused on the `enumerate` CLI only.

## What Changed

- Added build instructions for `cargo build`, `cargo test`, `cargo bench --no-run`, and `cargo build --release`.
- Documented the `enumerate` positional seed argument and all CLI flags.
- Added a preset table for the built-in alphabets.
- Included CLI examples for basic use, QWERTY weighting, larger neighborhoods, and custom Unicode alphabets.
- Added a troubleshooting section for the three validation errors raised by `SearchConfig::new`.

## Verification

- `cargo run --bin enumerate -- --help`

## Notes

- The new README stays intentionally CLI-only and does not describe the library modules.
