# Rust CLI README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a crate-local README for `string-permutation-kata/rust` that explains how to build and run the CLI, what the `enumerate` binary does, and how each command-line flag changes behavior.

**Architecture:** Keep the README focused on the binary entrypoint and its runtime behavior. Organize it as a quickstart, a command reference, examples, preset table, and troubleshooting notes, all derived from the actual `src/bin/enumerate.rs` interface. Do not expand into the library internals or the kata-wide problem statement, because those already live in the top-level README.

**Tech Stack:** Markdown documentation, Rust `cargo` commands, `clap` CLI flags exposed by `src/bin/enumerate.rs`.

---

## File Map

| File | Role |
|------|------|
| `string-permutation-kata/rust/README.md` | New crate-local CLI documentation |
| `string-permutation-kata/rust/src/bin/enumerate.rs` | Source of truth for CLI flags, presets, and behavior |
| `string-permutation-kata/rust/passwordless-refactor/notes.md` | Investigation log, append documentation changes here |

### Task 1: Write the crate README

**Files:**
- Create: `string-permutation-kata/rust/README.md`
- Modify: `string-permutation-kata/rust/passwordless-refactor/notes.md`

- [ ] **Step 1: Draft the README with build and run instructions**

Create `string-permutation-kata/rust/README.md` with:

```markdown
# String Neighborhood Kata Rust CLI

This directory contains the Rust implementation of the `enumerate` CLI.

## Build

```bash
cd string-permutation-kata/rust
cargo build
cargo test
cargo bench --no-run
```

## Run

```bash
cargo run --bin enumerate -- pattern
cargo run --bin enumerate -- pattern --max 1 --qwerty --limit 20
cargo run --bin enumerate -- pattern --min 1 --max 2 --preset letters-numbers
cargo run --bin enumerate -- "café" --alphabet "café" --max 1
```

## CLI

`enumerate` prints strings in a bounded edit-distance neighborhood of a seed.

### Positional argument

- `seed`: the string to explore around

### Flags

- `--min <N>`: minimum edit distance, inclusive, default `1`
- `--max <N>`: maximum edit distance, inclusive, default `1`
- `--preset <NAME>`: predefined alphabet, default `lowercase`
- `--alphabet <STRING>`: custom alphabet string; overrides `--preset`
- `--qwerty`: enable keyboard-neighbor likelihood ranking
- `--limit <N>`: print at most `N` candidates, with `0` meaning no limit
- `--quiet`: suppress the final candidate-count status line on stderr

### Presets

| Preset | Characters |
|---|---|
| `lowercase` | `a-z` |
| `letters` | `a-zA-Z` |
| `letters-numbers` | `a-zA-Z0-9` plus space |
| `letters-numbers-symbols` | letters, numbers, space, and common symbols |
| `full-ascii` | all printable ASCII |

## Examples

- Show the first 20 one-edit candidates for `pattern` with QWERTY weighting.
- Enumerate a two-edit neighborhood with the `letters-numbers` preset.
- Use a custom Unicode alphabet when the seed itself includes non-ASCII characters.

## Troubleshooting

- If `cargo run` reports `min_distance must be <= max_distance`, make sure `--min` is not greater than `--max`.
- If `cargo run` reports `alphabet must not be empty`, pass a non-empty `--alphabet` value or use a preset.
- If `cargo run` reports `seed contains characters outside alphabet`, choose a preset or custom alphabet that includes every character in the seed.
```

- [ ] **Step 2: Append a note to the investigation log**

Add a short line to `string-permutation-kata/rust/passwordless-refactor/notes.md` recording that the crate-local README was added.

- [ ] **Step 3: Verify the README matches the CLI**

Run:

```bash
cd string-permutation-kata/rust
cargo run --bin enumerate -- --help
```

Expected: the help output lists the `seed` positional argument plus `--min`, `--max`, `--preset`, `--alphabet`, `--qwerty`, `--limit`, and `--quiet`.

- [ ] **Step 4: Commit**

```bash
git add string-permutation-kata/rust/README.md string-permutation-kata/rust/passwordless-refactor/notes.md docs/superpowers/plans/2026-04-24-rust-cli-readme.md
git commit -m "docs(rust): add CLI readme"
```
