use keepass::error::{DatabaseKeyError, DatabaseOpenError, DatabaseVersionParseError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OpenError {
    WrongPassword,
    CorruptDatabase,
    UnsupportedFormat,
    Io(std::io::ErrorKind),
    Other,
}

impl OpenError {
    pub fn as_cli_code(&self) -> &'static str {
        match self {
            Self::WrongPassword => "wrong-password",
            Self::CorruptDatabase => "corrupt-db",
            Self::UnsupportedFormat => "unsupported-format",
            Self::Io(_) => "io-error",
            Self::Other => "other-error",
        }
    }

    pub fn from_keepass_error(error: DatabaseOpenError) -> Self {
        match error {
            DatabaseOpenError::Io(inner) => Self::Io(inner.kind()),
            DatabaseOpenError::UnexpectedEof => Self::CorruptDatabase,
            DatabaseOpenError::UnsupportedVersion => Self::UnsupportedFormat,
            DatabaseOpenError::VersionParse(DatabaseVersionParseError::InvalidKDBXVersion {
                ..
            }) => Self::UnsupportedFormat,
            DatabaseOpenError::VersionParse(DatabaseVersionParseError::InvalidKDBXIdentifier)
            | DatabaseOpenError::VersionParse(DatabaseVersionParseError::UnexpectedEof) => {
                Self::CorruptDatabase
            }
            DatabaseOpenError::Key(DatabaseKeyError::IncorrectKey) => Self::WrongPassword,
            DatabaseOpenError::Format(_) => Self::CorruptDatabase,
            DatabaseOpenError::Key(_) | DatabaseOpenError::Cryptography(_) => Self::Other,
        }
    }
}
