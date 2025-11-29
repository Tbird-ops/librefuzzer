# Librefuzzer
**A LibAFL Gramatron based fuzzer designed to test LibreOffice Calc cell function parsers for memory corruptions.**

## General Overview of project
This project aims to use grammar-aware fuzzing to identify possible vulnerabilities present in LibreOffice Calc by fuzzing 
cells with mostly valid formula entries. The desired goal is to identify erroneous states where functions conflict or fail 
to handle unexpected input, leading to underlying memory corruption and crashes. This project has 3 key stages: the grammar 
creation, the grammar preprocessing, and finally the fuzzing. This document will outline the repository with key information.
Note: LibreOffice src is not provided directly within this repository. It can be found at their source archive here: 
https://downloadarchive.documentfoundation.org/libreoffice/old/25.8.1.1/src/

## Work In Progress
Unfortunately, this fuzzer is not entirely functional as of yet. The only missing piece is a **harness** that can interface 
with LibreOffice Calc and provide each fuzzing test to be calculated and monitored for crash conditions.

## Directory Structure Overview:
- `cfg_pipeline/`: holds all the scripts used to scrape function definition information from LibreOffice documentation and amalgamate an initial Context Free Grammar (CFG). 
  - `page_scrapes/`: Generated folder after running the scripts in `cfg_pipeline`. Caches webpages of documentation for later processing to avoid too many repeated requests going to the LibreOffice webserver.
  - `downsized_progress/`: A history of reworking the grammar to be fairly comprehensive, but with less recursive structural elements to allow for rapid processing. Initially, the grammar in GNF form was 50MB. Simplified it became 700KB
- `preprocess/`: holds all the CFG conversion steps to take a roughly Backus-Naur form CFG in JSON and then create a Pushdown Automata. Preprocess steps will be described further below.
- `office_files/`: should hold all compressed files downloaded from https://downloadarchive.documentfoundation.org/libreoffice/old/25.8.1.1/src/. Decompressing them should provide the full source tree of the current LibreOffice version that was used to test fuzzer functionality. Build instructions to follow.
- `src/`: holds all the materials to build `librefuzzer` and the testing harness.

## Fuzzing pipeline structure
1. Build the grammar using the CFG pipeline
2. Preprocess the grammar into an automata for the fuzzer to use
3. Build the fuzzer and appropriate harness
4. Run the fuzzer

## DEPENDENCIES
### LibAFL
This project relies on LibAFL for the basis of the fuzzer design. Please ensure this is cloned or downloaded in your system.
They have a clearly outlined guide on what you need to have to get started here: https://aflplus.plus/libafl-book/getting_started/setup.html
**NOTE!!!** : Any "`Cargo.toml`" file within this repository needs to be edited to provide the local LibAFL path. Ensure
these changes occur to both the repository root and preprocess/construct_automata `Cargo.toml`.

### Building LibreOffice
The best and most formal way to initially build LibreOffice for testing is to follow their recommendations outlined here: https://wiki.documentfoundation.org/Development/BuildingOnLinux.
This README will only outline key differences in approaches but expects that all dependencies are installed as outlined in their document.

To build LibreOffice in a local environment, it is simple to redefine an install location as well as omit some unnecessary components to maximize compile time efficiency.
Change the following `--prefix` parameter to align with desired installation directory for easy access.
```
cd /path/to/libreoffice_src
autogen.sh --prefix $HOME/source/librefuzz/office_files/instdir --enable-debug --without-junit --without-java --without-doxygen --without-help --without-myspell-dicts
make -j8
```

## Building 
### CFG Pipeline
To maintain consistency between tests, the grammar is built more programmatically to easily reproduce across different systems.
Building the pipeline requires the following python packages to be made available:
```
beautifulsoup4==4.14.2
certifi==2025.11.12
charset-normalizer==3.4.4
idna==3.11
requests==2.32.5
soupsieve==2.8
typing_extensions==4.15.0
urllib3==2.5.0
```
This can be installed using the following command:
`pip install -r requirements.txt`

The pipeline itself is fully automated and should be able to be built using the following commands:
```bash
cd cfg_pipeline
bash run.sh
```
`run.sh` simply chains the python scripts in the necessary order from webscraping -> grammar extraction -> CFG building.

The output file is named "`amalgamation.json`". This is needed for the next stage of the process. Put this file where it 
is most convenient for you to work with further. It is not required to stay in this directory.

### Grammar Preprocessing
The output grammar format is not quite fuzzer ready and needs to go through a two-stage preprocessing. First, it will
get converted from its current form into a Greibach Normal Form (GNF) CFG. Then the GNF will go through a process to be 
serialized as an push down automaton (PDA) used as input to the GRAMATRON fuzzer for generating inputs.

First, ensure that the following "construct_automata" crate is built using the following:
```bash
cd preprocess/construct_automata
cargo build --release
```
This should place a binary inside a new directory structure similar to `preprocess/construct_automata/target/release/construct_automata`

With this binary accessible, return to the project root directory
`cd ../..`

Now, run the following commands to finalize the grammar preproces:
```bash
python3 preprocess/gnf_converter.py --gf path/to/amalgamation.json --out amalgamation_GNF.json --start "START"
preprocess/construct_automata/target/release/construct_automata -g amalgamation_GNF.json -o amalgamation_automata.postcard -l 10
```

The final `amalgamation_automata.postcard` is used as the input grammar requirement for the fuzzer itself.

### Building the fuzzer
With the dependencies met above, the fuzzer itelf can be built from the repository root using:
```bash
cargo build
# OR
cargo build --release
```
Using the release build greatly optimizes the produced binary ensuring minimal overhead.

## Running the fuzzer
Depending on whether debug or release build was run, use the following structure to run the fuzzer itself
```bash
target/BUILD_TYPE/librefuzzer --grammar amalgamation_automata.postcard --output "crashes"
```

## TODO
- Continue working on developing a harness to interface with LibreOffice Calc (current fails due to compiler dependency errors or initialization instability)
- Add multithreading support to the current fuzzer