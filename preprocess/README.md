# Preprocess Credits to LibAFL team
```
@inproceedings{libafl,
 author       = {Andrea Fioraldi and Dominik Maier and Dongjia Zhang and Davide Balzarotti},
 title        = {{LibAFL: A Framework to Build Modular and Reusable Fuzzers}},
 booktitle    = {Proceedings of the 29th ACM conference on Computer and communications security (CCS)},
 series       = {CCS '22},
 year         = {2022},
 month        = {November},
 location     = {Los Angeles, U.S.A.},
 publisher    = {ACM},
}
```

# Gramatron preprocessing scripts

In this folder live the scripts to convert a grammar into a serialized Automaton.

You need as first to convert the grammar to the GNF form using the `gnf_converter.py` Python script.

Then use the output as input of the `construct_automata` crate.

Here an example using the Ruby grammar:

```sh
./gnf_converter.py --gf grammars/ruby_grammar.json --out ruby_gnf.json --start PROGRAM
cd construct_automata
RUSTFLAGS="-C target-cpu=native" cargo run --release -- --gf ../ruby_gnf.json --out ../ruby_automaton.postcard
```

You can add the `--limit` flag to limit the stack size, as described in the Gramatron paper.
