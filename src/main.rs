// Pull in my CLI module
mod cli;
use cli::Opt; // Make sure the type is available to main nicely

mod fuzz;
use fuzz::fuzz;

// Pull in the parser
use clap::Parser;

// Relies on Path Buffers to handle provided parameters
use std::{fs, fs::File, path::PathBuf};

// GLOBALS
const CRASH_DIR: &str = "./gt_crashes";
const CRASH_DIR_CONCRETE: &str = "./crash_reproducers";

// Debugging support
fn type_printer<T>(_: &T) {
    println!("{}", std::any::type_name::<T>());
}

fn main() {
    let args: Opt = Opt::parse();
    type_printer(&args);
    let grammar_filepath: PathBuf = args.grammar;
    type_printer(&grammar_filepath);

    let contents: String = fs::read_to_string(&grammar_filepath).unwrap();
    println!("Contents: {contents}");

}
