mod error;
mod open;

pub use error::OpenError;
pub use open::{can_open_database, open_database};
