#[cfg(windows)]
use std::ptr::write_volatile;
use std::{
    fs,
    io::{BufReader, Read},
    path::{Path, PathBuf},
};

use libafl::{
    corpus::{InMemoryCorpus, OnDiskCorpus},
    events::SimpleEventManager,
    executors::{ExitKind, inprocess::InProcessExecutor},
    feedback_or, feedback_or_fast,
    feedbacks::{CrashFeedback, MaxMapFeedback, TimeFeedback, TimeoutFeedback},
    fuzzer::{Fuzzer, StdFuzzer},
    generators::{Automaton, GramatronGenerator},
    inputs::GramatronInput,
    monitors::MultiMonitor,
    mutators::{
        GramatronRandomMutator, GramatronRecursionMutator, GramatronSpliceMutator,
        HavocScheduledMutator,
    },
    observers::{HitcountsMapObserver, StdMapObserver, TimeObserver, CanTrack},
    schedulers::{IndexesLenTimeMinimizerScheduler, QueueScheduler},
    stages::CalibrationStage,
    stages::mutational::StdMutationalStage,
    state::StdState,
};
use libafl_bolts::{
    rands::StdRand,
    shmem::{ShMemProvider, StdShMemProvider},
    tuples::tuple_list,
};
use libafl_targets::{libfuzzer_initialize, libfuzzer_test_one_input, std_edges_map_observer};

fn read_automaton_from_file<P: AsRef<Path>>(path: P) -> Automaton {
    let file = fs::File::open(path).unwrap();
    let mut reader = BufReader::new(file);
    let mut buffer = Vec::new();
    reader.read_to_end(&mut buffer).unwrap();
    postcard::from_bytes(&buffer).unwrap()
}

// TODO Make basic Gramatron Fuzzer single threaded
// TODO Then add LLMP multithreading support with Shared Memory
// TODO Verify concrete output creation
// TODO See options
// - MiMalloc for performance??
// - Other performance optimizations?
// - Set up good debug logging?
pub fn fuzz(grammar_postcard: PathBuf, output_dir: PathBuf) {
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      MONITOR
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // The Monitor trait define how the fuzzer stats are reported to the user
    let monitor = MultiMonitor::new(|s| println!("{s}"));

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      HARNESS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // Vector to store current fuzzing testcase
    let mut bytes = vec![];

    // TODO FIX THIS TO BE HARNESS
    // The closure that we want to fuzz
    let mut harness = |input: &GramatronInput| {
        input.unparse(&mut bytes);
        unsafe {
            println!(">>> {}", std::str::from_utf8_unchecked(&bytes));
        }
        ExitKind::Ok
    };

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      OBSERVERS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // Create an observation channel using the both edges map and time based tracking
    let edges_observer =
        HitcountsMapObserver::new(unsafe{ std_edges_map_observer("edges")}).track_indices();
    let time_observer = TimeObserver::new("time");

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      FEEDBACKS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // Feedback to rate the interestingness of an input
    let map_feedback = MaxMapFeedback::new(&edges_observer);
    let time_feedback = TimeFeedback::new(&time_observer);

    // Compose feedback based on both edges and timing
    let mut feedback = feedback_or!(map_feedback, time_feedback);

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      OBJECTIVES
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // A feedback to choose if an input is a solution or not
    let mut objective = feedback_or_fast!(CrashFeedback::new(), TimeoutFeedback::new());

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      STATE
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // TODO Eventually rewrite this to have state.unwrap_or_else for restarting mgr and other things
    // create a State from scratch
    let mut state = StdState::new(
        // RNG
        StdRand::new(),
        // Corpus that will be evolved, we keep it in memory for performance
        InMemoryCorpus::new(),
        // Corpus in which we store solutions (crashes in this example),
        // on disk so the user can get them after stopping the fuzzer
        OnDiskCorpus::new(output_dir).unwrap(),
        // States of the feedbacks.
        // The feedbacks can report the data that should persist in the State.
        &mut feedback,
        // Same for objective feedbacks
        &mut objective,
    )
    .unwrap();

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      MANAGERS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // The event manager handle the various events generated during the fuzzing loop
    // such as the notification of the addition of a new item to the corpus
    let mut mgr = SimpleEventManager::new(monitor);

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      SCHEDULERS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // A queue policy to get testcasess from the corpus
    let scheduler = QueueScheduler::new();

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      FUZZERS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // A fuzzer with feedbacks and a corpus scheduler
    let mut fuzzer = StdFuzzer::new(scheduler, feedback, objective);

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      EXECUTORS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // Create the executor for an in-process function with just one observer
    let mut executor = InProcessExecutor::new(
        &mut harness,
        tuple_list!(edges_observer, time_observer),
        &mut fuzzer,
        &mut state,
        &mut mgr,
    )
    .expect("Failed to create the Executor");

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      CFG PARSER
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    let automaton = read_automaton_from_file(grammar_postcard);
    let mut generator = GramatronGenerator::new(&automaton);

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      GENERATE INPUTS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // Generate 8 initial inputs
    state
        .generate_initial_inputs_forced(&mut fuzzer, &mut executor, &mut generator, &mut mgr, 8)
        .expect("Failed to generate the initial corpus");

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      MUTATORS
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    // Setup a mutational stage with a basic bytes mutator
    let mutator = HavocScheduledMutator::with_max_stack_pow(
        tuple_list!(
            GramatronRandomMutator::new(&generator),
            GramatronRandomMutator::new(&generator),
            GramatronRandomMutator::new(&generator),
            GramatronSpliceMutator::new(),
            GramatronSpliceMutator::new(),
            GramatronRecursionMutator::new()
        ),
        2,
    );

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      STAGES
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    let mut stages = tuple_list!(StdMutationalStage::new(mutator));

    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    //      RUN
    //%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    fuzzer
        .fuzz_loop(&mut stages, &mut executor, &mut state, &mut mgr)
        .expect("Error in the fuzzing loop");
}
