# Librefuzzer
A LibAFL Gramatron based fuzzer designed to test LibreOffice Calc cell function parsers for memory corruptions.

## Directory Structure Overview:
- `cfg_pipeline/`: holds all the scripts used to scrape function definition information from LibreOffice documentation and amalgamate an initial CFG. 
- `page_scrapes/`: Generated folder after running the scripts in `cfg_pipeline`. Caches webpages of documentation for later processing to avoid too many repeated requests going to the LibreOffice webserver.
- `preprocess/`: holds all the CFG conversion steps to go from a json CFG definition in roughly a Backus-Naur form to a Pushdown Automata. Preprocess steps will be described further below.
- `office_files/`: should hold all compressed files downloaded from https://downloadarchive.documentfoundation.org/libreoffice/old/25.8.1.1/src/. Decompressing them should provide the full source tree of the current LibreOffice version that was used to test fuzzer functionality. Follow build instructions within LibreOffice tree to produce build objects.
- `src/`: holds all the materials to build `librefuzzer` itself.

## Fuzzing pipeline structure
1. Build the grammar using the CFG pipeline
2. Preprocess the grammar into an automata for the fuzzer to use
3. Build the fuzzer and appropriate harness
4. Run the fuzzer

