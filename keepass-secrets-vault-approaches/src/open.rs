use std::fs::File;
use std::io::BufReader;
use std::path::Path;

use keepass::{Database, DatabaseKey};

use crate::error::OpenError;

pub fn open_database(path: &Path, password: &str) -> Result<(), OpenError> {
    let file = File::open(path).map_err(|error| OpenError::Io(error.kind()))?;
    let mut reader = BufReader::new(file);
    let key = DatabaseKey::new().with_password(password);

    Database::get_xml(&mut reader, key)
        .map(|_| ())
        .map_err(OpenError::from_keepass_error)
}

pub fn can_open_database(path: &Path, password: &str) -> bool {
    open_database(path, password).is_ok()
}
