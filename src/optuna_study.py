"""
Optuna hyperparameter optimization study for Framsticks evolutionary algorithms.

PARALLEL EXECUTION:
===================
To run multiple trials in parallel (e.g., 10 trials at once):

1. Change N_JOBS = 1 to N_JOBS = 10
2. Run: python optuna_study.py
3. Each process runs independently, won't interfere

Early stopping behavior with parallel:
- Each trial's early stopping is independent (trial-specific)
- Trial A being pruned doesn't affect Trial B
- If Trial A is underperforming, only IT gets stopped (not others)
- Running trials finish peacefully, aren't interrupted by other trials

Database safety:
- SQLite with Optuna handles concurrent writes automatically (WAL mode)
- Trials are serialized to database atomically
- No corruption risk with multiple jobs

Advantages:
- 10 jobs × 4h = 40h compute in 4h wall-clock time
- Better resource utilization (fills idle CPU cores)
- Faster overall study completion

METHODOLOGY NOTES:
==================

1. Is Optuna good for genetic algorithm studies?
   YES, with the right setup. Here's why:
   - Optuna can handle stochastic objectives by accepting mean values
   - Multiple runs per trial (20 in our case) gives stable fitness estimates
   - Intermediate reporting + pruning helps reject bad configs early

2. Early stopping for non-deterministic algorithms - is it good practice?
   YES, IF done carefully:
   - Must have minimum runs (MIN_RUNS_BEFORE_EARLY_STOP) before pruning
   - Pruner uses statistical confidence (not just one bad run)
   - HyperbandPruner is ideal: it works with curves, not just final values
   - We report intermediate results after each run for better pruning decisions

3. Running 20 trials per config to get mean+std:
   YES, this is excellent practice for non-deterministic algorithms:
   - Gives you confidence intervals for comparing algorithms
   - Allows pruning to work on confidence bounds, not just means
   - Each report() call lets the pruner see the curve stabilizing
   - Even with early stopping, you'll typically run 5+ trials before pruning

OPTIMIZATION TARGETS:
====================
Currently set to optimize for "robustness" across multiple test functions.
To switch to single function optimization:
- Change: return np.mean(all_fitnesses)
- To:     return fitness_for_selected_function
And comment out the loop over TEST_FUNCTIONS.

ABOUT WEIGHTED ALGORITHM SAMPLING:
==================================
Standard Optuna doesn't support weighted categoricals directly. We handle this by:
1. Sampling algorithm first with suggest_int + mapping (hacky but works)
2. Using the fact that each configuration is independent
3. A better approach would be a custom sampler, but this is simpler for now
Alternative: Use study.sampler.before_trial_complete() hook to reject trials

PERSISTENT STORAGE:
===================
Uses SQLite database for persistence. Each run of optimize() will:
- Load existing trials if they exist
- Add new trials to the same study
- Avoid duplicate computations
"""

import optuna
from optuna.samplers import TPESampler
from optuna.pruners import HyperbandPruner
import json
import os
import numpy as np
from pathlib import Path

# Import configuration loader
from .config_loader import get_disertatie_root, get_framsticks_path, get_database_path, load_config


# ============================================================================
# CONFIGURATION
# ============================================================================

# Database storage
STUDY_NAME = "framsticks-study"

# Load configuration
CONFIG = load_config()
DATA_PATH = get_disertatie_root()
FRAMSTICKS_PATH = get_framsticks_path(CONFIG)
DATABASE_URL = f"sqlite:///{get_database_path(CONFIG)}"
STATS_FILE = os.path.join(DATA_PATH, 'algo_run_dict.json')
EXPERIMENT_SCRIPT = "./runExperiment.py"

# Algorithm weights (relative probabilities)
# AdaptMut: last year's winner, should try it more
# eaSimple: baseline, try occasionally
# Others: exploratory
# ALGORITHM_WEIGHTS = {
#     "AdaptMut": 0.30,
#     "eaSimple": 0.15,
#     "eaMuPlusLambda": 0.0,
#     "eaMuCommaLambda": 0.0,
#     "convection_eaSimple": 0.15,
#     "convection_AdaptMut": 0.15,
#     "NEAT_speciation": 0.25,
# }

# Test configurations
# Change TEST_FUNCTIONS or TEST_CRITERIA to switch optimization targets
TEST_FUNCTIONS = [3]  # Evaluate functions, leave blank [] to test single function # 3, 4, 5
TEST_CRITERIA = "COGpath"    # What to optimize for (or use multiple: "velocity,COGpath")

# Multiple runs per configuration
RUNS_PER_TRIAL = 10  # Number of algorithm runs to get mean+std
MIN_RUNS_BEFORE_EARLY_STOP = 10  # Don't prune until we have some confidence

# Other parameters
OPTUNA_STUDY_KWARGS = {
    "n_trials": 100,  # How many configurations to try
    "timeout": None,  # Max time in seconds (None = no limit)
    "show_progress_bar": True,
}

# PARALLEL EXECUTION
# Set n_jobs > 1 to run multiple trials in parallel
# Each trial runs its own algorithm (RUNS_PER_TRIAL times)
# Early stopping is trial-specific: won't affect other running trials
# Example: n_jobs=10 means 10 trials in parallel, each ~4h (20 runs per trial)
N_JOBS = 10  # Change to 10 for parallel execution
# Note: SQLite automatically uses WAL mode for concurrent access in Optuna>=3.0


# ============================================================================
# ALGORITHM DEFINITIONS
# ============================================================================

SIMPLEST_GENOTYPE = {
    'f1_simplest':None,
    'f0_simplest':None,
    'f1_XX':'XX',
    # In order: @rotation muscle, |bending muscle, Gyroscope, Gpart (Tilt), Muscle, Touch, Smell, Neuron(sigmoid), *constant
    # See https://www.framsticks.com/neurons_summary
    'f1_XXneurons':'XX[@][|][G][Gpart][T][S][N][*]',
    # https://www.framsticks.com/files/apps/js/creature-editor/index.html
    'f0_XX':"""//0
p:
p:1.0
p:2.0
j:0, 1, dx=1.0, 0.0, 0.0
j:1, 2, dx=1.0, 0.0, 0.0""",
    'f0_XXneurons':"""//0
p:
p:1.0
p:2.0
j:0, 1, dx=1.0, 0.0, 0.0
j:1, 2, dx=1.0, 0.0, 0.0
n:j=1, d=@:p=0.25
n:j=1, d=|
n:j=1, d=G
n:p=2, d=Gpart
n:p=2, d=T
n:p=2, d=S
n:p=2
n:p=2, d=*""",
}

def get_algorithm_specific_params(trial: optuna.Trial, algorithm: str) -> dict:
    """
    Suggest only the parameters relevant to the chosen algorithm.
    This prevents the search space from exploding with irrelevant parameters.
    """
    params = {}

    # Common parameters for all algorithms
    params["algorithm"] = algorithm
    params["genformat"] = trial.suggest_categorical("genformat", [0, 1])
    params["pmut"] = trial.suggest_float("pmut", 0.1, 1.0, step=0.005)
    params["initialgenotype"] = trial.suggest_categorical("initialgenotype", ["simplest", "XX", "XXneurons"])

    # Algorithm-specific parameters
    if algorithm == 'eaOnePlusLambdaLambda':
        params["popsize"] = trial.suggest_int("popsize", 1, 1)
    else:
        params["popsize"] = trial.suggest_int("popsize", 1, 500)
        params["tournament"] = trial.suggest_int("tournament", 2, 20) # FIXME This doesn't help in OnePlusLambdaLambda

    if algorithm in ['eaMuPlusLambda', 'eaMuCommaLambda']:
        params["lbda"] = trial.suggest_int("lbda", params['popsize'], 500, step=5)
        # They require the sum of pmut and pxov to be 1 for some reason...
        params["pxov"] = trial.suggest_float('pxov', 1 - params['pmut'], 1 - params['pmut'], step=0.005)
    else:
        params["pxov"] = trial.suggest_float("pxov", 0.0, 1.0, step=0.005)

    if "convection" in algorithm:
        # convection_eaSimple, convection_AdaptMut
        params["nislands"] = trial.suggest_int("nislands", 2, 100)
        params["migrate_after"] = trial.suggest_int("migrate_after", 1, 50)
        params["island_eval_order"] = "bestToWorst"

    if algorithm == "NEAT_speciation":
        params["nislands"] = trial.suggest_int("nislands", 3, 15)
        # params["delta"] = trial.suggest_float("delta", 1.0, 10.0)
        params["dissim"] = trial.suggest_categorical(
            "dissim",
            [
                "PHENE_STRUCT_OPTIM",
                "GENE_LEVENSHTEIN",
                "PHENE_STRUCT_GREEDY",
                "PHENE_DESCRIPTORS",
                "PHENE_DENSITY_COUNT",
                "PHENE_DENSITY_FREQ",
                "FITNESS",
            ],
        )

    if algorithm == "AdaptMut":
        params["xmut_enabled"] = trial.suggest_categorical("xmut_enabled", [0, 1])
        params["added_ind"] = trial.suggest_categorical("added_ind", ['initial', 'random'])
        params["restart_method"] = trial.suggest_categorical("restart_method", ['none', 'hard', 'soft_perturb_best'])
        if params["restart_method"] != 'none':
            params["restart_patience"] = trial.suggest_int("restart_patience", 2, 100)

    return params


def suggest_algorithm(trial: optuna.Trial) -> str:
    """
    Suggest an algorithm with weighted probabilities.

    This is a workaround for Optuna not supporting weighted categoricals.
    We use suggest_int + cumulative weights to pick an algorithm.
    """
    return trial.suggest_categorical("algorithm", [
        'AdaptMut', 'eaSimple',
        'convection_eaSimple', 'convection_AdaptMut',
        'NEAT_speciation',
        'eaMuPlusLambda', 'eaMuCommaLambda',
        'eaOnePlusLambdaLambda',
    ])
    # algorithms = list(ALGORITHM_WEIGHTS.keys())
    # weights = list(ALGORITHM_WEIGHTS.values())

    # Normalize weights to probabilities
    total_weight = sum(weights)
    probabilities = [w / total_weight for w in weights]
    cumsum_probs = np.cumsum(probabilities).tolist()

    # Sample a random uniform value and find which bin it falls into
    random_val = trial.suggest_float("_algorithm_weight", 0.0, 1.0)

    for algo, threshold in zip(algorithms, cumsum_probs):
        if random_val <= threshold:
            # Store the actual algorithm choice for reproducibility
            trial.set_user_attr("algorithm", algo)
            return algo

    # Fallback (should never reach here)
    return algorithms[-1]


# ============================================================================
# EXPERIMENT EXECUTION
# ============================================================================

import re
ALNUM_PATTERN = re.compile(r"[\W_]+")

def get_run_name(algorithm, params, test_func):
    name = 'evalfn' + str(test_func) + '_' + algorithm
    def normalizeString(s):
        return ALNUM_PATTERN.sub('', str(s))
    for p in sorted(params.keys()):
        if p == 'initialgenotype':
            cval = [k for k, v in SIMPLEST_GENOTYPE.items() if v == params[p]][0]
        elif p == 'nodet' or p == 'evalfn':
            continue
        else:
            cval = params[p]
        name += '_' + normalizeString(p)[:4] + normalizeString(cval)
    return name


import src.run_more as rmore

def run_more(algorithm, params, test_func, n_runs, trial: optuna.Trial):
    params['initialgenotype'] = SIMPLEST_GENOTYPE[f"f{params['genformat']}_{params['initialgenotype']}"]
    if params['initialgenotype'] == None:
        # Framsticks knows to handle the simplest genotype by default.
        del params['initialgenotype']
    if test_func != [3]:
        print(f"Warning: test_func is {test_func}, but get_run_name() is only designed for single function optimization. Consider updating get_run_name() to include test_func in the name.")
        exit(0)

    for evalfn in test_func:
        params["evalfn"] = evalfn
        runname = 'rn_' + get_run_name(algorithm, params, params['evalfn'])
        p = {
            'nruns': n_runs,
            'nodet': params['nodet'],
            'runname': runname,
            'noredo': False,
            'numworkers': N_JOBS,
            'commandargs': ' '.join([f"-{k} \"{v}\"" for k, v in params.items() if k != 'nodet']),
        }
        print(p)
        rmore.main(p)
    with open(STATS_FILE, 'r') as f:
        data = json.load(f)
    run_fitnesses = data[runname]['runs']

    # Calculate metrics
    mean_fitness = np.mean(run_fitnesses)
    std_fitness = np.std(run_fitnesses)
    max_fitness = max(run_fitnesses)
    min_fitness = min(run_fitnesses)


    # Store custom attributes (available after trial completes)
    trial.set_user_attr("meta", data[runname]['meta'])
    trial.set_user_attr("runs", run_fitnesses)
    trial.set_user_attr("raw_params", params)
    trial.set_user_attr("mean", mean_fitness)
    trial.set_user_attr("std", std_fitness)
    trial.set_user_attr("median", np.median(run_fitnesses))
    trial.set_user_attr("max", max_fitness)
    trial.set_user_attr("nruns", len(run_fitnesses))
    trial.set_user_attr("name", runname)

    fitness = mean_fitness
    return fitness

# ============================================================================
# OPTUNA OBJECTIVE FUNCTION
# ============================================================================

def objective(trial: optuna.Trial) -> float:
    """
    Optuna objective function.

    Workflow:
    1. Suggest an algorithm (weighted)
    2. Suggest algorithm-specific hyperparameters
    3. Run the algorithm RUNS_PER_TRIAL times across TEST_FUNCTIONS
    4. Report intermediate results for pruning
    5. Return mean fitness (robustness metric)

    For SINGLE FUNCTION optimization instead of robustness:
    - Comment out the loop: for test_func in TEST_FUNCTIONS
    - Set: test_func = 3  # or your chosen function
    - Return np.mean(all_fitnesses) for that single function
    """

    # Step 1: Choose algorithm (weighted)
    algorithm = suggest_algorithm(trial)

    # Step 2: Get algorithm-specific parameters
    params = get_algorithm_specific_params(trial, algorithm)
    params["nodet"] = trial.suggest_categorical("nodet", [0])

    # Step 3 & 4: Run multiple times, report intermediate results

    if not TEST_FUNCTIONS:
        # Single function optimization
        TEST_FUNCTIONS_TO_USE = [3]  # Default if not specified
    else:
        TEST_FUNCTIONS_TO_USE = TEST_FUNCTIONS

    # Run across all test functions for robustness evaluation
    fitness = run_more(algorithm, params, TEST_FUNCTIONS_TO_USE, RUNS_PER_TRIAL, trial)

    return fitness


# ============================================================================
# STUDY MANAGEMENT
# ============================================================================

def create_study() -> optuna.Study:
    """Create or load a persistent Optuna study."""
    # sampler = TPESampler(seed=42, consider_prior=True)
    import optunahub
    module = optunahub.load_module(package="samplers/auto_sampler")
    sampler = module.AutoSampler()

    # HyperbandPruner: more suitable for our case than MedianPruner
    # - Works with curves (reports intermediate values)
    # - Aggressive pruning of unpromising trials
    # - Suitable for non-deterministic objectives
    # pruner = HyperbandPruner(
    #     min_resource=MIN_RUNS_BEFORE_EARLY_STOP,
    #     max_resource=RUNS_PER_TRIAL,
    #     reduction_factor=3,
    # )

    study = optuna.create_study(
        study_name=STUDY_NAME,
        storage=DATABASE_URL,
        sampler=sampler,
        # pruner=pruner,
        direction="maximize",  # We want to maximize fitness
        load_if_exists=True,
    )

    return study


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main optimization loop."""

    print("=" * 80)
    print("Framsticks Algorithm Optimization Study")
    print("=" * 80)
    print(f"Database: {DATABASE_URL}")
    print(f"Study: {STUDY_NAME}")
    print(f"Test Functions: {TEST_FUNCTIONS if TEST_FUNCTIONS else 'Single (default 3)'}")
    print(f"Optimization Criteria: {TEST_CRITERIA}")
    print(f"Runs per Trial: {RUNS_PER_TRIAL}")
    # print(f"Algorithm Weights: {ALGORITHM_WEIGHTS}")
    print("=" * 80)

    # Create or load study
    study = create_study()

    # Optionally load previous trials
    # load_previous_trials(study, filepath="previous_trials.json")

    # Print current best
    if study.best_trial:
        print(f"\nCurrent best trial (#{study.best_trial.number}):")
        print(f"  Fitness: {study.best_trial.value:.4f}")
        print(f"  Params: {study.best_trial.params}")

    # Run optimization
    print(f"\nStarting optimization (n_jobs={N_JOBS})...\n")

    study.optimize(
        objective,
        n_trials=OPTUNA_STUDY_KWARGS["n_trials"],
        timeout=OPTUNA_STUDY_KWARGS["timeout"],
        show_progress_bar=OPTUNA_STUDY_KWARGS["show_progress_bar"],
        n_jobs=1,  # Parallel execution
    )

    # Print results
    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)

    print(f"\nBest trial: #{study.best_trial.number}")
    print(f"Algorithm: {study.best_trial.user_attrs.get('algorithm', 'unknown')}")
    print(f"Best Fitness: {study.best_value:.4f}")
    print(f"Parameters: {study.best_trial.params}")

    # Print top 10 trials
    print("\n" + "=" * 80)
    print("Top 10 Trials:")
    print("=" * 80)
    trials = sorted(study.get_trials(), key=lambda t: t.value, reverse=True)
    for i, trial in enumerate(trials[:10], 1):
        print(
            f"{i}. #{trial.number}: {trial.user_attrs.get('algorithm', '?')} "
            f"- Fitness: {trial.value:.4f}"
        )


if __name__ == "__main__":
    main()
