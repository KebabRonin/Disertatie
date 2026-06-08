import datetime, sqlite3
import json, numpy as np
import optuna
import copy
import os
from optuna.study import StudyDirection

# Import configuration loader
from .config_loader import get_database_path, load_config, get_disertatie_root

# Load configuration
CONFIG = load_config()
DB_PATH = get_database_path(CONFIG)

SIMPLEST_GENOTYPE = {
    '_random': 'random',
    '_simplest':'None',
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

PARAM_DISTRIBUTIONS = {
  # Common parameters (all algorithms)
  'evalfn': optuna.distributions.CategoricalDistribution([3, 4, 5]),
  'algorithm': optuna.distributions.CategoricalDistribution([
    'AdaptMut', 'eaSimple',
    'convection_eaSimple', 'convection_AdaptMut',
    'NEAT_speciation', 'MAPElites',
    'eaMuPlusLambda', 'eaMuCommaLambda',
    'eaOnePlusLambdaLambda',
  ]),
  'nodet': optuna.distributions.CategoricalDistribution([0, 1]),
  'genformat': optuna.distributions.CategoricalDistribution([0, 1]),
  'initialgenotype': optuna.distributions.CategoricalDistribution(['simplest', 'XX', 'XXneurons', 'random']),
  # EA parameters
  'popsize': optuna.distributions.IntDistribution(1, 500, step=1),
  'tournament': optuna.distributions.IntDistribution(2, 50),
  'pmut': optuna.distributions.FloatDistribution(0.1, 1.0, step=0.005),
  'pxov': optuna.distributions.FloatDistribution(0.0, 1.0, step=0.005),
  # Convection-specific parameters
  'nislands': optuna.distributions.IntDistribution(2, 100),
  'migrate_after': optuna.distributions.IntDistribution(1, 50),
  'added_ind': optuna.distributions.CategoricalDistribution(['initial', 'random']),
  'island_eval_order': optuna.distributions.CategoricalDistribution(['bestToWorst', 'worstToBest', 'interleaved']),
  # NEAT_speciation-specific parameters
  'delta': optuna.distributions.FloatDistribution(1.0, 10.0),
  'delta_under_mult': optuna.distributions.FloatDistribution(0.8, 1.0),
  'delta_over_mult': optuna.distributions.FloatDistribution(1.0, 2.0),
  'dissim': optuna.distributions.CategoricalDistribution([
    'PHENE_STRUCT_OPTIM',
    'GENE_LEVENSHTEIN',
    'PHENE_STRUCT_GREEDY',
    'PHENE_DESCRIPTORS',
    'PHENE_DENSITY_COUNT',
    'PHENE_DENSITY_FREQ',
    'FITNESS',
  ]),
  # AdaptMut-specific parameters
  'xmut_enabled': optuna.distributions.CategoricalDistribution([0, 1]),
  'restart_patience': optuna.distributions.IntDistribution(2, 100),
  'restart_method': optuna.distributions.CategoricalDistribution(
    ['none', 'hard', 'soft_perturb_best', 'soft_perturb_best_all']),
  'softperturbbest_bestratio': optuna.distributions.FloatDistribution(0.1, 1.0, step=0.05),
  'softperturbbest_maxnewmutcount': optuna.distributions.IntDistribution(1, 10),
  # Lambda (eaMuPlusLambda, eaMuCommaLambda) parameters
  'lbda': optuna.distributions.IntDistribution(20, 500, step=1),
  # General parameters
  'selMethod': optuna.distributions.CategoricalDistribution(['tournament', 'roulette', 'best']),
  'flibclass': optuna.distributions.CategoricalDistribution(['competition', 'wHist']),
  'wHist_scorefn': optuna.distributions.CategoricalDistribution(['ratio', 'pos', 'neg', 'neg_conservative', 'const', 'ratio_fifthrule', 'ratio_v2']),
  'wHist_decay': optuna.distributions.FloatDistribution(0.9, 1.0, step=0.005),
  'wHist_norm_method': optuna.distributions.CategoricalDistribution(['mean', 'mean100', 'none', 'eps']),
  'wHist_ESalgo': optuna.distributions.CategoricalDistribution(['none', 'cmaes', 'freqWindow', 'indstore']),
  'fix_invalid': optuna.distributions.CategoricalDistribution(['none', 'mutate']),
  'maxmutationsperstep': optuna.distributions.IntDistribution(1, 20),
  'xov_mutschema': optuna.distributions.CategoricalDistribution(['choice', 'rand']),
  # MAPElites-specific parameters
  'novelty_features': optuna.distributions.CategoricalDistribution([
    # 'geno_numparts',
    # 'geno_numjoints',
    # 'geno_numneurons',
    # 'geno_numconnections',
    # 'geno_numparts,geno_numjoints',
    # 'geno_numparts,geno_numneurons',
    # 'geno_numparts,geno_numjoints,geno_numneurons',
    'geno_numparts,geno_numjoints,geno_numneurons,geno_numconnections',
  ]),
  'novelty_sel': optuna.distributions.CategoricalDistribution(['random', 'random_meta', 'quality', 'curiosity']),
}

DEFAULTS = {
  'evalfn': 3,
  # 'genformat': 0,
  'initialgenotype': 'simplest',
  'sim': 'eval-allcriteria.sim;deterministic.sim;recording-body-coords.sim;',
  'popsize': 50,
  'tournament': 5,
  'pmut': 0.9,
  'pxov': 0.2,
  'nislands': 10,
  'migrate_after': 10,
  'added_ind': 'initial',
  'island_eval_order': 'worstToBest',
  'delta': 3.0,
  'delta_under_mult': 0.96,
  'delta_over_mult': 1.33,
  'dissim': 'PHENE_STRUCT_OPTIM',
  'xmut_enabled': 1,
  'restart_patience': 15,
  'restart_method': 'none',
  'softperturbbest_bestratio': 0.25,
  'softperturbbest_maxnewmutcount': 4,
  'lbda': 100,
  'selMethod': 'tournament',
  'flibclass': 'competition',
  'wHist_scorefn': 'ratio',
  'wHist_decay': 0.985,
  'wHist_norm_method': 'mean',
  'wHist_ESalgo': 'freqWindow',
  'fix_invalid': 'none',
  'maxmutationsperstep': 5,
  'xov_mutschema': 'choice',
  'novelty_features': 'geno_numparts,geno_numjoints,geno_numneurons,geno_numconnections',
  'novelty_sel': 'random',
}

# Parameters to EXCLUDE from import (not relevant for optimization)
# EXCLUDE_PARAMS = {
#     'path', 'lib', 'sim', 'hof_savefile', 'max_numparts',
#     'max_numjoints', 'max_numneurons', 'max_numconnections',
#     'max_numgenochars', 'initpop_zero', 'skipinitialgenotype',
#     'island_eval_order', 'delta_under_mult', 'delta_over_mult',
#     'hof_size', 'generations'
# }

def try_cast(value: str, type):
  try:
    cval = type(value)
    if str(cval) == value:
      return cval
  except:
     return None

def from_str_to_type(algo_data_param, param_name: str):
  print(param_name)
  value = algo_data_param.get(param_name)
  if param_name == 'initialgenotype':
    if value not in SIMPLEST_GENOTYPE.values():
      print("Oops, not valid initialgenotype: ", value)
      exit(0)
    cval = [k for k,v in SIMPLEST_GENOTYPE.items() if v == value][0]
    print('cval', cval)
    if cval.startswith('f0'):
      if algo_data_param['genformat'] == 1:
        print(f"Warning: genotype {value} is not compatible with genformat=1")
        exit(1)
    elif cval.startswith('f1'):
      if algo_data_param['genformat'] == 0:
        print(f"Warning: genotype {value} is not compatible with genformat=0")
        exit(1)
    return cval.split('_')[1]
  cval = try_cast(value, float)
  if cval is not None: return cval
  cval = try_cast(value, int)
  if cval is not None: return cval
  cval = try_cast(value, bool)
  if cval is not None: return cval
  if value == 'None': return None
  if value.startswith('DissimMethod.'):
    cval = value.split('.')[1]
    return cval
  return value


def update_db_datetimes(number, start_ts, end_ts):
  print(f"Updating trial_id {number} with start_ts {datetime.datetime.fromtimestamp(start_ts).isoformat()} and end_ts {datetime.datetime.fromtimestamp(end_ts).isoformat()}")
  with sqlite3.connect(DB_PATH) as conn:
    cur = conn.cursor()
    cur.execute(
      """
      UPDATE trials
      SET datetime_start = ?, datetime_complete = ?
      WHERE number = ?
      """,
      (datetime.datetime.fromtimestamp(start_ts).isoformat(), datetime.datetime.fromtimestamp(end_ts).isoformat(), number),
    )
    conn.commit()

COMMON_PARAMS = ['evalfn', 'algorithm', 'genformat', 'initialgenotype', 'popsize', 'tournament', 'pmut', 'pxov', 'generations', 'selMethod', 'flibclass', 'fix_invalid', 'xov_mutschema']
ALGO_PARAMS = {
  'convection_eaSimple': COMMON_PARAMS + ['nislands', 'migrate_after', 'island_eval_order'],
  'convection_AdaptMut': COMMON_PARAMS + ['nislands', 'migrate_after', 'island_eval_order', 'xmut_enabled', 'added_ind', 'restart_patience', 'restart_method', 'softperturbbest_bestratio', 'softperturbbest_maxnewmutcount'],
  'NEAT_speciation': COMMON_PARAMS + ['dissim', 'delta', 'delta_under_mult', 'delta_over_mult'],
  'AdaptMut': COMMON_PARAMS + ['xmut_enabled', 'restart_patience', 'restart_method', 'added_ind'],
  'eaSimple': COMMON_PARAMS,
  'eaMuPlusLambda': COMMON_PARAMS + ['lbda'],
  'eaMuCommaLambda': COMMON_PARAMS + ['lbda'],
  'MAPElites': COMMON_PARAMS + ['novelty_sel'], #'novelty_features', 
  # TODO
  'eaOnePlusLambdaLambda': ['evalfn', 'algorithm', 'genformat', 'initialgenotype', 'popsize', 'tournament', 'selMethod', 'flibclass', 'fix_invalid', 'xov_mutschema'] + ['lbda'],
}

def create_study_and_import(study: optuna.Study, algo_key: str, algo_data: dict):
    """Import a single algorithm's runs into Optuna as a study."""
    params = {} # copy.deepcopy(algo_data['params'])
    # Set the parameter values
    if algo_data['params'].get('restart_method', None) == 'none' \
        or algo_data['params'].get('restart_patience', None) == '100000000':
      algo_data['params'].pop('restart_patience')
    if algo_data['params'].get('xmut_enabled', None) not in ['0', 'False']:
      algo_data['params']['xmut_enabled'] = '1'
    else:
      algo_data['params']['xmut_enabled'] = '0'
    if algo_data['params'].get('population_initialization', None) == 'random':
      algo_data['params']['initialgenotype'] = 'random'
    if algo_data['params'].get('population_initialization', None) is not None:
      algo_data['params'].pop('population_initialization')
    print(algo_data['params'])
    for param_name in PARAM_DISTRIBUTIONS.keys():
      if param_name in ALGO_PARAMS[algo_data['params']['algorithm']]:
        params[param_name] = DEFAULTS[param_name] if param_name not in algo_data['params'] or algo_data['params'][param_name] == 'None' else from_str_to_type(algo_data['params'], param_name)
    print(params)

    meta_list = algo_data['meta']
    runs = algo_data['runs']
    mean = np.mean(runs)
    std = np.std(runs)

    if params['evalfn'] not in EVAL_FN_TO_IMPORT:
      print(f"Runs for {algo_key} have evalfn != 3 (was {params['evalfn']}). Skipping...")
      return None

    # baseline_mean = np.mean(BASELINE['runs'])  # or reference fitness
    # fitness = (mean - baseline_mean) / std
    fitness = mean

    dists = {param: PARAM_DISTRIBUTIONS[param] for param in params.keys()}

    trial = optuna.create_trial(
      params=params,
      user_attrs={
        'meta': meta_list,
        'runs': runs,
        'raw_params': algo_data['params'],
        'mean': mean,
        'std': std,
        'median': np.median(runs),
        'max': max(runs),
        'nruns': len(runs),
        'name': algo_key,
      },
      distributions=dists,
      value=fitness,
      state=optuna.trial.TrialState.COMPLETE,
      # system_attrs={
      #   "datetime_start": datetime.datetime.fromtimestamp(min(map(lambda x: x['run_start'], meta_list))).isoformat(),
      #   "datetime_complete": datetime.datetime.fromtimestamp(max(map(lambda x: x['run_end'], meta_list))).isoformat(),
      # }
    )
    # Import each run as a trial
    # for i, (run_meta, fitness) in enumerate(zip(meta_list, runs)):
        # Create trial with parameters
    study.add_trial(trial)

    DATETIMES.append((
      study.get_trials()[-1].number,
      min(map(lambda x: x['run_start'], meta_list)),
      max(map(lambda x: x['run_end'], meta_list)),
    ))

    print(f"  Total trials in study: {len(study.trials)}")
    return study

if __name__ == '__main__':
  EVAL_FN_TO_IMPORT = [3]
  import argparse
  parser = argparse.ArgumentParser(description='Import algorithm runs into Optuna database')
  parser.add_argument('--silent', action='store_true', help='Suppress output')
  parser.add_argument('--noredo', action='store_true', help='Suppress output')
  parsedargs = parser.parse_args()

  import os, time
  os.chdir(get_disertatie_root())
  if not parsedargs.noredo:
    os.system("python -m src.collect_data")
  # exit(0)

  # Load the algo_run_dict.json data
  d = json.load(open(os.path.join(get_disertatie_root(), 'algo_run_dict.json'), 'r'))

  # Import all algorithms
  print("Starting import to Optuna database...")
  print(f"Database path: {DB_PATH}")
  print(f"Number of algorithms: {len(d)}")
  os.rename(DB_PATH, os.path.join(get_disertatie_root(), "db_backups", f"algo_runs_backup_{int(time.time())}.db"))
  # Create or load the study
  study = optuna.create_study(
      study_name='framsticks-study',
      direction=StudyDirection.MAXIMIZE,  # Fitness values are to be maximized
      storage=f'sqlite:///{DB_PATH}',
      load_if_exists=True
  )
  # dummytrial = study.get_trials()[0]
  # print(dummytrial.params)
  # exit()
  # BASELINE = d['AdaptMutF0pmut08']
  DATETIMES = []
  ordered_keys = sorted(d.keys(), key=lambda k: min(map(lambda x: x['run_start'], d[k]['meta'])), reverse=False)
  # ordered_keys = list(filter(lambda k: d['run_start'], d[k]['meta'])), ordered_keys)
  # evalfn
  for algo_key in ordered_keys:
    algo_data = d[algo_key]
    print(f"\nImporting: {algo_key}")
    create_study_and_import(study, algo_key, algo_data)

  for d in DATETIMES:
    update_db_datetimes(d[0], d[1], d[2])

  if not parsedargs.silent:
    print("\n=== Import complete ===")

    import pandas as pd
    with sqlite3.connect(DB_PATH) as conn:
      df = pd.read_sql_query("SELECT * FROM trials", conn)
      print(df.sort_values('datetime_start', ascending=False))
