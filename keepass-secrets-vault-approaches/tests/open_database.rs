use std::fs;
use std::path::{Path, PathBuf};

use keepass::{Database, DatabaseKey};
use keepass_open_check::{OpenError, can_open_database, open_database};
use tempfile::TempDir;

fn write_sample_database(password: &str) -> (TempDir, PathBuf) {
    let temp_dir = tempfile::tempdir().expect("tempdir");
    let path = temp_dir.path().join("sample.kdbx");
    let database = Database::new(Default::default());
    let mut file = fs::File::create(&path).expect("create fixture database");

    database
        .save(&mut file, DatabaseKey::new().with_password(password))
        .expect("save fixture database");

    (temp_dir, path)
}

#[test]
fn opens_valid_database_with_correct_password() {
    let (_temp_dir, path) = write_sample_database("password");

    let result = open_database(path.as_path(), "password");

    assert!(result.is_ok());
}

#[test]
fn returns_wrong_password_for_invalid_password() {
    let (_temp_dir, path) = write_sample_database("password");

    let result = open_database(path.as_path(), "wrong-password");

    assert!(matches!(result, Err(OpenError::WrongPassword)));
}

#[test]
fn returns_io_error_for_missing_file() {
    let temp_dir = tempfile::tempdir().expect("tempdir");
    let path = temp_dir.path().join("missing.kdbx");

    let result = open_database(path.as_path(), "password");

    assert!(matches!(result, Err(OpenError::Io(_))));
}

#[test]
fn returns_corrupt_database_for_non_keepass_bytes() {
    let temp_dir = tempfile::tempdir().expect("tempdir");
    let path = temp_dir.path().join("invalid-data.bin");
    fs::write(&path, b"not-a-keepass-database").expect("write invalid fixture");

    let result = open_database(path.as_path(), "password");

    assert!(matches!(result, Err(OpenError::CorruptDatabase)));
}

#[test]
fn boolean_helper_tracks_primary_api() {
    let (_temp_dir, path) = write_sample_database("password");

    assert!(can_open_database(Path::new(&path), "password"));
    assert!(!can_open_database(Path::new(&path), "wrong-password"));
}

#[test]
fn opens_real_qwerty_fixture() {
    let path = Path::new("assets/qwerty.kdbx");
    let mut file = fs::File::open(path).expect("open real fixture");
    let raw_result = Database::open(&mut file, DatabaseKey::new().with_password("qwerty"));

    let result = open_database(path, "qwerty");

    assert!(
        result.is_ok(),
        "expected fixture to open, got {result:?}; raw keepass result: {raw_result:?}"
    );
}
