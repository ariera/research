use std::path::PathBuf;

use keepass_open_check::open_database;

fn usage() -> ! {
    eprintln!("usage: keepass-open-check --path <file> --password <password>");
    std::process::exit(2);
}

fn main() {
    let mut args = std::env::args().skip(1);
    let mut path = None;
    let mut password = None;

    while let Some(argument) = args.next() {
        match argument.as_str() {
            "--path" => path = args.next().map(PathBuf::from),
            "--password" => password = args.next(),
            _ => usage(),
        }
    }

    let Some(path) = path else {
        usage();
    };

    let Some(password) = password else {
        usage();
    };

    match open_database(&path, &password) {
        Ok(()) => std::process::exit(0),
        Err(error) => {
            println!("{}", error.as_cli_code());
            std::process::exit(1);
        }
    }
}
