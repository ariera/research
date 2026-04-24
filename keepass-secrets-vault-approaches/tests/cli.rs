use std::fs;
use std::path::PathBuf;
use std::process::Command;

use keepass::{Database, DatabaseKey};
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
fn cli_succeeds_for_valid_password() {
    let (_temp_dir, path) = write_sample_database("password");

    let output = Command::new(env!("CARGO_BIN_EXE_keepass-open-check"))
        .args([
            "--path",
            path.to_str().expect("path utf-8"),
            "--password",
            "password",
        ])
        .output()
        .expect("run CLI");

    assert!(output.status.success());
    assert_eq!(String::from_utf8_lossy(&output.stdout).trim(), "");
}

#[test]
fn cli_prints_error_category_for_invalid_password() {
    let (_temp_dir, path) = write_sample_database("password");

    let output = Command::new(env!("CARGO_BIN_EXE_keepass-open-check"))
        .args([
            "--path",
            path.to_str().expect("path utf-8"),
            "--password",
            "wrong-password",
        ])
        .output()
        .expect("run CLI");

    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&output.stdout).trim(),
        "wrong-password"
    );
}
