import pandas as pd
from FramsticksLibCompetition import FramsticksLibCompetition
import psutil



experiment_configs = {
    'superflat': 'a.sim',
    'waterflat': 'evol-speed-water.sim',
    'river': 'heightfield.sim',
    'river': 'heightfield.sim',
    'river': 'heightfield.sim',
    'river': 'heightfield.sim',
    'river': 'heightfield.sim',
    'river': 'heightfield.sim',
    'river': 'heightfield.sim',
    'river': 'heightfield.sim',
}






data = [
    {
        'genotype': 'X',
        'genotype_stats': {
            'genotype_length': 1,
            'num_joints': 1,
            'num_neurons': 0,
            'num_sensors': 0,
            'num_actuators': 0,
            'num_neuroconnections': 0,
        },
        'evaluations': [
            {
                'generation': 1,
                'seed': 4936308364390,
                'fitness': 0.00052,
                'bounding_box_dimensions': (0.5, 1, 1),
                'bounding_box_volume': 0.5,
                'simulation_steps': 2525,
            },
        ],
    }
]
STATS = {}
FRAMS_LIB_PATH = '~/Documents/fac/GECCO_Robot_Body/Framsticks54'
# framslib = FramsticksLibCompetition(FRAMS_LIB_PATH, parsed_args.lib, parsed_args.sim)
a = pd.DataFrame(data)
print(a)
STATS['memory_usage'] = psutil.Process().memory_info().rss / (1024 * 1024)
print(STATS)
tuples = [
    ("Algorithm_Meta", "evaluation_number"),
    ("Algorithm_Meta", "generation"),
    ("Genotype", "genotype_representation"),
    ("Genotype", "numparts"),
    ("Genotype", "numjoints"),
    ("Genotype", "numneurons"),
    ("Genotype", "numconnections"),
    ("Experiment", "raw"),
    ("Experiment", "time"),
    ("Experiment", "vertpos"),
    ("Experiment", "velocity"),
    ("Experiment", "distance"),
    ("Experiment", "COGpath"),
]
"""
[
    (1, "evaluation_number"), # N-th evaluation sent to the FramSticks simulator
    (1, "generation"), # What generation the evaluation belongs to
    (2, "genotype_representation"), # String representation of the genotype
    (2, "numparts"),
    (2, "numjoints"),
    (2, "numneurons"),
    (2, "numconnections"),
    (3, "raw"), # Fallback for raw output, in case of errors
    (3, "time"),
    (3, "vertpos"),
    (3, "velocity"),
    (3, "distance"),
    (3, "COGpath"),
]"""
cols = [
    "meta_evaluation_number", # N-th evaluation sent to the FramSticks simulator
    "meta_generation", # What generation the evaluation belongs to
    "meta_algorithm", # Dummy
    "geno_genotype_representation", # String representation of the genotype
    "geno_numparts",
    "geno_numjoints",
    "geno_numneurons",
    "geno_numconnections",
    "eval_raw", # Fallback for raw output, in case of errors
    "eval_time",
    "eval_vertpos",
    "eval_velocity",
    "eval_distance",
    "eval_COGpath",
]
df = pd.DataFrame(columns=[
    "meta_evaluation_number", # N-th evaluation sent to the FramSticks simulator
    "meta_timestamp", # When the evaluation took place.
    "meta_generation", # What generation the evaluation belongs to
    "meta_algorithm", # Dummy
    "algo_data",
    "geno_genotype_representation", # String representation of the genotype
    "geno_numparts",
    "geno_numjoints",
    "geno_numneurons",
    "geno_numconnections",
    "eval_raw", # Fallback for raw output, in case of errors
    "eval_time",
    "eval_vertpos",
    "eval_velocity",
    "eval_distance",
    "eval_COGpath",
])
df = df._append({
    "meta_evaluation_number": 1, # N-th evaluation sent to the FramSticks simulator
    "meta_timestamp": 1, # When the evaluation took place.
    "meta_generation": 1, # What generation the evaluation belongs to
    "meta_algorithm": "1", # Dummy
    "algo_data": {"1":"1"},
    "geno_genotype_representation": "1", # String representation of the genotype
    "geno_numparts": 1,
    "geno_numjoints": 1,
    "geno_numneurons": 1,
    "geno_numconnections": 1,
    "eval_raw": "1", # Fallback for raw output, in case of errors
    "eval_time": 1.0,
    "eval_vertpos": 1.0,
    "eval_velocity": 1.0,
    "eval_distance": 1.0,
    "eval_COGpath": 1.0,
}, ignore_index=True)
print(df)
print(df.dtypes)