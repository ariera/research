# KeePass Open Check Research

This investigation narrowed the broader "KeePass as a poor man's secrets vault"
idea down to one performance-sensitive operation:

- attempt to open a KeePass database with a password
- report success or an explicit failure category

The chosen direction is a small Rust project with a shared core and two thin
interfaces on top:

- a Rust library API for direct embedding
- a CLI for scripting and shell use

That design has now been implemented in this folder as a standalone Rust crate.

## Recommendation

Use Rust for this slice.

Reasoning:

- it has the lowest wrapper overhead around the required unlock and parse steps
- it supports both library and CLI delivery cleanly
- it leaves room for future FFI bindings without duplicating logic

The main caveat from the research is that the dominant cost is still KeePass
database opening itself: key derivation, decryption, and parsing. Rust improves
the surrounding implementation cost, but it does not remove the inherent cost of
opening the database on every call.

## Recommended API

Primary API:

```rust
pub fn open_database(path: &Path, password: &str) -> Result<(), OpenError>
```

Convenience API:

```rust
pub fn can_open_database(path: &Path, password: &str) -> bool
```

CLI behavior:

- exit code `0` on success
- nonzero exit code on failure
- print a stable error category such as `wrong-password` or `io-error`

Implemented CLI usage:

```bash
cargo run -- --path /path/to/database.kdbx --password 'secret'
```

## Build and Use

Build the crate:

```bash
cargo build --release
```

Run the CLI without installing it:

```bash
cargo run -- --path /path/to/database.kdbx --password 'secret'
```

Run the compiled release binary directly:

```bash
./target/release/keepass-open-check --path /path/to/database.kdbx --password 'secret'
```

Success behavior:

- exit code `0`
- no stdout output

Failure behavior:

- exit code `1`
- stdout contains a stable error code such as `wrong-password`

Usage error behavior:

- exit code `2`
- stderr prints the expected argument format

Example shell usage:

```bash
if ./target/release/keepass-open-check --path secrets.kdbx --password "$PASSWORD"; then
  echo "database opened"
else
  echo "database failed to open"
fi
```

Example of reading the failure category:

```bash
result="$(./target/release/keepass-open-check --path secrets.kdbx --password "$PASSWORD")"
status=$?

if [ "$status" -eq 0 ]; then
  echo "ok"
else
  echo "failed with: $result"
fi
```

## Error Model

The approved direction is to expose explicit failure categories rather than
collapsing all failures into a generic boolean.

Initial categories:

- `WrongPassword`
- `CorruptDatabase`
- `UnsupportedFormat`
- `Io`
- `Other`

Current CLI codes:

- `wrong-password`
- `corrupt-db`
- `unsupported-format`
- `io-error`
- `other-error`

## Scope

Included in this research slice:

- password-only KeePass open checks
- library and CLI interface design
- explicit typed error handling
- tested Rust implementation

Out of scope for now:

- reading secrets
- writing to the database
- caching or daemon/sidecar designs
- non-password unlock methods
- language bindings beyond Rust

## Files

- `notes.md`: working log of the investigation
- `keepass-open-check-design.md`: approved design spec for the next phase
- `keepass-open-check-implementation-plan.md`: execution plan used for implementation
- `src/`: Rust library and CLI source
- `tests/`: integration tests covering library and CLI behavior

## Verification

Verified with:

```bash
cargo test --test open_database
cargo test --test cli
cargo test
```

The tests generate temporary KeePass fixtures at runtime using the same
`keepass` crate's KDBX4 save support, so no binary fixture file needs to be
checked into the research folder.
