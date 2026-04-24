# KeePass Open Check Design

**Date:** 2026-04-23

## Overview

This research slice focuses on a single operation: determine whether a KeePass
database can be opened with a supplied password.

The implementation target is a small Rust project that exposes the same core
behavior through both a library API and a CLI. The shared core attempts to open
and parse the KeePass database far enough to prove that the file, password, and
format are valid.

## Goals

- Optimize for low latency when checking whether a KeePass database can be
  opened
- Provide both a Rust library API and a CLI interface
- Return explicit failure categories rather than collapsing all failures into a
  generic boolean
- Limit scope to password-only KeePass database opening

## Non-Goals

- Reading or returning secrets from the database
- Writing changes back to the database
- Caching or keeping the database open between calls
- Supporting key files, challenge-response, or other non-password unlock modes
- Building Python bindings in this phase

## Why Rust

Rust is the best fit for this narrow performance-sensitive operation because it
adds minimal runtime overhead around the underlying KDF, decryption, and parse
steps required to open a KeePass database. For the `open -> validate -> return`
path, the dominant cost is still database unlock and parsing, but Rust keeps the
wrapper overhead small and gives a clean path to both library and CLI delivery.

## Public Interfaces

### Library

Primary API:

```rust
pub fn open_database(path: &Path, password: &str) -> Result<(), OpenError>
```

Convenience API:

```rust
pub fn can_open_database(path: &Path, password: &str) -> bool
```

The `can_open_database` helper simply returns `open_database(...).is_ok()`.
Typed errors remain the primary interface.

### CLI

Suggested command shape:

```bash
keepass-open-check --path /path/to/db.kdbx --password 'secret'
```

Behavior:

- Exit code `0` on success
- Nonzero exit code on failure
- Print a stable machine-readable error category on failure

Example failure output:

```text
wrong-password
```

## Error Model

The public API should expose explicit failure categories so callers can
distinguish authentication failures from operational failures.

Suggested initial error enum:

```rust
pub enum OpenError {
    WrongPassword,
    CorruptDatabase,
    UnsupportedFormat,
    Io(std::io::ErrorKind),
    Other,
}
```

Notes:

- `WrongPassword` means the file structure was recognized but password-based
  unlock failed
- `CorruptDatabase` means the file could not be parsed as a valid KeePass
  database despite appearing to be the expected format
- `UnsupportedFormat` means the database variant or feature set is not handled
  by the chosen library
- `Io` covers missing files, permissions, and other filesystem-related failures
- `Other` is a guardrail for library-specific failures that do not map cleanly

If the underlying library makes it practical, `Io` can later be split into more
precise variants such as `FileNotFound` and `PermissionDenied`.

## Internal Architecture

Suggested structure:

```text
src/
├── lib.rs        shared public API
├── error.rs      OpenError definition and mapping helpers
├── open.rs       open-and-validate implementation
└── main.rs       CLI wrapper
```

Flow:

1. Validate the supplied filesystem path can be opened
2. Pass the file handle and password into the KeePass parser/open routine
3. Map the library's success case to `Ok(())`
4. Map library failures into `OpenError`
5. Return the typed result to callers
6. In the CLI, convert the typed error into stable text plus an exit code

## Behavior Contract

Success means:

- the KeePass file exists and can be read
- the password is accepted
- the database can be parsed enough to confirm it is valid for this use case

Failure means one of the explicit `OpenError` categories is returned.

No secret extraction, no writes, and no persistent process state are involved in
this phase.

## Testing Strategy

The implementation should be verified with fixture-based tests covering:

- valid KeePass database + correct password
- valid KeePass database + wrong password
- corrupt or truncated database file
- unsupported or unexpected format fixture
- missing file
- permission-denied path where feasible in local tests

CLI tests should additionally verify:

- exit code `0` on success
- nonzero exit code on failure
- stable stdout or stderr category text for each mapped error case

## Recommended Next Step

Implement the Rust crate as library-first, with `main.rs` calling directly into
the library API. This keeps the CLI thin and ensures all behavior is testable at
the library boundary.
