use clap::{self, Parser};
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(
    version = "0.1",
    about = "A grammar aware fuzzer to target LibreOffice Calc Formula engine",
    name = "Librefuzzer",
    author = "Tristan Stapert"
)]
pub struct Opt {
    #[arg(
        short = 'g',
        long = "grammar",
        help = "Path to Postcard file format to read CFG",
        name = "GRAMMAR"
    )]
    pub grammar: PathBuf,

    #[arg(
        short = 'o',
        long = "output",
        help = "Path to output directory",
        name = "OUTPUT"
    )]
    pub output: PathBuf,
}
