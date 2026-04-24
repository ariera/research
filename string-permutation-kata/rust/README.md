# String Neighborhood Kata Rust CLI

This directory contains the Rust implementation of the `enumerate` command-line tool.

## Build

From this directory:

```bash
cargo build
cargo test
cargo bench --no-run
```

For an optimized binary:

```bash
cargo build --release
```

## Run

Run the CLI with a seed string and optional flags:

```bash
cargo run --bin enumerate -- pattern
cargo run --bin enumerate -- pattern --max 1 --qwerty --limit 20
cargo run --bin enumerate -- pattern --min 1 --max 2 --preset letters-numbers
cargo run --bin enumerate -- "café" --alphabet "café" --max 1
```

To inspect the full argument list:

```bash
cargo run --bin enumerate -- --help
```

## What The CLI Does

`enumerate` prints all distinct strings in a bounded edit-distance neighborhood of the seed.

The output is:

- ordered by increasing edit distance
- ranked within the same distance layer by likelihood
- deterministic
- deduplicated

It writes candidates to standard output and a summary line to standard error unless `--quiet` is set.

## Arguments

### Positional

- `seed`: the string to explore around

### Flags

- `--min <N>`: minimum edit distance, inclusive. Default: `1`
- `--max <N>`: maximum edit distance, inclusive. Default: `1`
- `--preset <NAME>`: choose a predefined alphabet. Default: `lowercase`
- `--alphabet <STRING>`: provide a custom alphabet string. This overrides `--preset`
- `--qwerty`: enable QWERTY keyboard-neighbor ranking for replacements
- `--limit <N>`: print at most `N` candidates. `0` means no limit
- `--quiet`: suppress the final candidate-count line on standard error

## Alphabet Presets

The built-in `--preset` values are:

| Preset | Characters |
|---|---|
| `lowercase` | `a-z` |
| `letters` | `a-zA-Z` |
| `letters-numbers` | `a-zA-Z0-9` plus space |
| `letters-numbers-symbols` | letters, numbers, space, and common symbols |
| `full-ascii` | all printable ASCII |

Use `--alphabet` if you want a custom character set instead of one of the presets.

## Examples

Show the first 20 one-edit candidates:

```bash
cargo run --bin enumerate -- pattern --max 1 --limit 20
```

Use QWERTY-weighted replacement ranking:

```bash
cargo run --bin enumerate -- pattern --max 1 --qwerty
```

Search a larger neighborhood with letters and numbers:

```bash
cargo run --bin enumerate -- admin --min 1 --max 2 --preset letters-numbers
```

Use a custom Unicode alphabet:

```bash
cargo run --bin enumerate -- "café" --alphabet "café" --max 1
```

## Troubleshooting

- `min_distance must be <= max_distance`: lower `--min` or raise `--max`.
- `alphabet must not be empty`: provide a non-empty `--alphabet` or use a preset.
- `seed contains characters outside alphabet`: make sure the chosen alphabet includes every character in the seed.

## Notes

- The binary is defined in `src/bin/enumerate.rs`.
- The library entry points live in `src/lib.rs`, but this README stays focused on CLI usage.
