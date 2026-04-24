# KeePass Open Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small Rust crate that can validate whether a password-only KeePass database opens successfully and expose that behavior through both a library API and a CLI.

**Architecture:** The crate is library-first. `src/lib.rs` exposes `open_database` and `can_open_database`, while `src/main.rs` is a thin CLI wrapper. Error mapping lives in focused modules so typed failures stay stable even if the underlying KeePass crate changes.

**Tech Stack:** Rust, Cargo, a KeePass parsing crate from crates.io, fixture-based tests, standard library CLI argument parsing

---

### Task 1: Scaffold the crate and establish the public API with failing tests

**Files:**
- Create: `keepass-secrets-vault-approaches/Cargo.toml`
- Create: `keepass-secrets-vault-approaches/src/lib.rs`
- Create: `keepass-secrets-vault-approaches/src/error.rs`
- Create: `keepass-secrets-vault-approaches/src/open.rs`
- Create: `keepass-secrets-vault-approaches/src/main.rs`
- Create: `keepass-secrets-vault-approaches/tests/open_database.rs`
- Create: `keepass-secrets-vault-approaches/tests/fixtures/README.md`
- Create: `keepass-secrets-vault-approaches/tests/fixtures/sample.kdbx`

- [ ] **Step 1: Write the failing integration tests**

```rust
use std::path::Path;

use keepass_open_check::{can_open_database, open_database, OpenError};

#[test]
fn opens_valid_database_with_correct_password() {
    let path = Path::new("tests/fixtures/sample.kdbx");

    let result = open_database(path, "password");

    assert!(result.is_ok());
}

#[test]
fn returns_wrong_password_for_invalid_password() {
    let path = Path::new("tests/fixtures/sample.kdbx");

    let result = open_database(path, "wrong-password");

    assert!(matches!(result, Err(OpenError::WrongPassword)));
}

#[test]
fn boolean_helper_tracks_primary_api() {
    let path = Path::new("tests/fixtures/sample.kdbx");

    assert!(can_open_database(path, "password"));
    assert!(!can_open_database(path, "wrong-password"));
}
```

- [ ] **Step 2: Run the test target to verify it fails**

Run: `cargo test --test open_database`
Expected: FAIL because the crate, fixtures, or API do not exist yet

- [ ] **Step 3: Add the minimal crate skeleton**

```toml
[package]
name = "keepass-open-check"
version = "0.1.0"
edition = "2024"

[dependencies]
keepass = "0.7"
```

```rust
// src/lib.rs
mod error;
mod open;

pub use error::OpenError;
pub use open::{can_open_database, open_database};
```

```rust
// src/error.rs
#[derive(Debug, PartialEq, Eq)]
pub enum OpenError {
    WrongPassword,
    CorruptDatabase,
    UnsupportedFormat,
    Io(std::io::ErrorKind),
    Other,
}
```

```rust
// src/open.rs
use std::path::Path;

use crate::OpenError;

pub fn open_database(_path: &Path, _password: &str) -> Result<(), OpenError> {
    Err(OpenError::Other)
}

pub fn can_open_database(path: &Path, password: &str) -> bool {
    open_database(path, password).is_ok()
}
```

```rust
// src/main.rs
fn main() {
    eprintln!("not implemented");
    std::process::exit(1);
}
```

- [ ] **Step 4: Run the same test target to verify it still fails for the expected behavior**

Run: `cargo test --test open_database`
Expected: FAIL with assertion failures showing the API exists but does not yet open the database correctly

### Task 2: Implement typed database opening in the library

**Files:**
- Modify: `keepass-secrets-vault-approaches/src/error.rs`
- Modify: `keepass-secrets-vault-approaches/src/open.rs`
- Modify: `keepass-secrets-vault-approaches/tests/open_database.rs`
- Create: `keepass-secrets-vault-approaches/tests/fixtures/invalid-data.bin`

- [ ] **Step 1: Add failing tests for missing files and corrupt input**

```rust
#[test]
fn returns_io_error_for_missing_file() {
    let path = Path::new("tests/fixtures/missing.kdbx");

    let result = open_database(path, "password");

    assert!(matches!(result, Err(OpenError::Io(_))));
}

#[test]
fn returns_corrupt_database_for_non_keepass_bytes() {
    let path = Path::new("tests/fixtures/invalid-data.bin");

    let result = open_database(path, "password");

    assert!(matches!(result, Err(OpenError::CorruptDatabase)));
}
```

- [ ] **Step 2: Run the test target to verify the new cases fail**

Run: `cargo test --test open_database`
Expected: FAIL because `open_database` still returns `Other`

- [ ] **Step 3: Implement the real open path and error mapping**

```rust
use std::fs::File;
use std::io::BufReader;
use std::path::Path;

use keepass::{Database, DatabaseKey};

use crate::OpenError;

pub fn open_database(path: &Path, password: &str) -> Result<(), OpenError> {
    let file = File::open(path).map_err(|error| OpenError::Io(error.kind()))?;
    let mut reader = BufReader::new(file);
    let key = DatabaseKey::new().with_password(password);

    Database::open(&mut reader, key)
        .map(|_| ())
        .map_err(OpenError::from_keepass_error)
}
```

```rust
impl OpenError {
    pub fn from_keepass_error(error: keepass::Error) -> Self {
        match error {
            keepass::Error::BadSignature(_) => Self::UnsupportedFormat,
            keepass::Error::UnsupportedVersion(_) => Self::UnsupportedFormat,
            keepass::Error::Io(inner) => Self::Io(inner.kind()),
            keepass::Error::Cryptography(_) => Self::WrongPassword,
            keepass::Error::Xml(_) => Self::CorruptDatabase,
            _ => Self::Other,
        }
    }
}
```

- [ ] **Step 4: Run the test target to verify the library cases pass**

Run: `cargo test --test open_database`
Expected: PASS

### Task 3: Add the CLI and end-to-end verification

**Files:**
- Modify: `keepass-secrets-vault-approaches/src/main.rs`
- Create: `keepass-secrets-vault-approaches/tests/cli.rs`
- Modify: `keepass-secrets-vault-approaches/README.md`
- Modify: `keepass-secrets-vault-approaches/notes.md`

- [ ] **Step 1: Write failing CLI tests**

```rust
#[test]
fn cli_succeeds_for_valid_password() {
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_keepass-open-check"))
        .args(["--path", "tests/fixtures/sample.kdbx", "--password", "password"])
        .output()
        .unwrap();

    assert!(output.status.success());
}

#[test]
fn cli_prints_error_category_for_invalid_password() {
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_keepass-open-check"))
        .args(["--path", "tests/fixtures/sample.kdbx", "--password", "wrong-password"])
        .output()
        .unwrap();

    assert_eq!(output.status.code(), Some(1));
    assert_eq!(String::from_utf8_lossy(&output.stdout).trim(), "wrong-password");
}
```

- [ ] **Step 2: Run the CLI test target to verify it fails**

Run: `cargo test --test cli`
Expected: FAIL because the CLI is still a placeholder

- [ ] **Step 3: Implement the CLI wrapper**

```rust
use std::path::PathBuf;

use keepass_open_check::open_database;

fn main() {
    let mut args = std::env::args().skip(1);
    let mut path = None;
    let mut password = None;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--path" => path = args.next().map(PathBuf::from),
            "--password" => password = args.next(),
            _ => {}
        }
    }

    let Some(path) = path else {
        eprintln!("usage: keepass-open-check --path <file> --password <password>");
        std::process::exit(2);
    };

    let Some(password) = password else {
        eprintln!("usage: keepass-open-check --path <file> --password <password>");
        std::process::exit(2);
    };

    match open_database(&path, &password) {
        Ok(()) => std::process::exit(0),
        Err(error) => {
            println!("{}", error.as_cli_code());
            std::process::exit(1);
        }
    }
}
```

- [ ] **Step 4: Run the full test suite to verify the crate passes**

Run: `cargo test`
Expected: PASS

- [ ] **Step 5: Update documentation and research notes**

Add the implemented crate layout and actual verification commands to:

- `keepass-secrets-vault-approaches/README.md`
- `keepass-secrets-vault-approaches/notes.md`
