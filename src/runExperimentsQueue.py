import sys, os, re

# Import configuration loader
from .config_loader import get_disertatie_root, load_config, get_experiments_dir

# Load configuration
CONFIG = load_config()
BASE_PATH = get_disertatie_root()

P_SIZE = 500

SIMPLEST_GENOTYPE = {
    'f1_basic2':'XX',
    # In order: @rotation muscle, |bending muscle, Gyroscope, Gpart (Tilt), Muscle, Touch, Smell, Neuron(sigmoid), *constant
    # See https://www.framsticks.com/neurons_summary
    'f1_neurons':'XX[@][|][G][Gpart][T][S][N][*]',
    # https://www.framsticks.com/files/apps/js/creature-editor/index.html
    'f0_basic2':"""//0
p:
p:1.0
p:2.0
j:0, 1, dx=1.0, 0.0, 0.0
j:1, 2, dx=1.0, 0.0, 0.0""",
    'f0_neurons':"""//0
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

def getExperimentData(rconfig):
    convection = rconfig['convection']
    algorithm = rconfig['algorithm']
    genformat = rconfig['genformat']
    pmut = rconfig['pmut']
    extra_cargs = rconfig['extra_cargs']
    extra = rconfig['extra']
    pop = rconfig['pop']
    lbda = rconfig['lbda']
    nameSuffix = rconfig['nameSuffix']
    namePrefix = rconfig['namePrefix']
    name = f'{namePrefix}{"convection_" if convection else ""}{algorithm}F{genformat}' \
        + f'{("pmut" + str(pmut).replace(".", "")) if pmut != None else ""}'\
        + f'{("lbda" + str(lbda)) if lbda != None else ""}'\
        + f'{("pop" + str(pop)) if pop != None else ""}'
    for ec in re.findall(r'-([a-zA-Z_]+)\s(\"[\s\S]*\"|[^\s]*)', extra_cargs):
        name += ec[0] + re.sub(r'[^a-zA-Z0-9]', '', ec[1])
    name += nameSuffix
    run_str = 'python -m src.run_more -runname ' \
        + name \
        + f" {extra} " + ' -commandargs "' \
            + ((f' -genformat {genformat}') if genformat != None else '') \
            + ((f' -algorithm {"convection_" if convection else ""}{algorithm}') if genformat != None else '') \
            + ((f' -pmut {pmut}') if pmut != None else '') \
            + ((f' -lbda {lbda}') if lbda != None else '') \
            + ((f' -popsize {pop}') if pop != None else '') \
            + f" {extra_cargs} " \
        + '"'
    return name, run_str

def getUnrunExperiments():
    params = {
        'convection': [None, 'convection_'],
        'algorithm': ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda'],
        'genformat': [0, 1],
        'pmut': [None, 0.8, 0.5],
        'pop': [None, 100, 500],
        'extra': '',
        'extra_cargs': '',
    }

    import itertools
    alr_run = 0
    runns = 0
    for rconfig in itertools.product(*params.values()):
        runns += 1
        name, run_str = getExperimentData(rconfig)
        dirname = os.path.join(get_experiments_dir(), name)
        if os.path.exists(dirname):
            alr_run += 1
        else:
            print(name)
    print (f"{alr_run}/{runns} ({alr_run/runns:.3f})")

runs_cfgs = [
    # { # more best so far, so I can see how the distribution changes
    #     'convection': None, #[None, 'convection_'],
    #     'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
    #     'genformat': 0, # [0, 1],
    #     'pmut': 0.8, # [None, 0.8, 0.5],
    #     'pop': None, # [None, 100, 500],
    #     'lbda': None, # [100, 350]
    #     'extra': ' -runname AdaptMutF0pmut08initialgenotyperandomadded_indrandomdissimPHENESTRUCTGREEDYrestart_methodsoftperturbbestrestart_patience10flibclasswHistwHist_scorefnneg -continuerun -nruns 10 ', # -nodet 1
    #     'extra_cargs': ' ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
    #     'nameSuffix': '',
    #     'namePrefix': '',
    # },
    # { # best so far + f1
    #     'convection': None, #[None, 'convection_'],
    #     'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
    #     'genformat': 1, # [0, 1],
    #     'pmut': 0.8, # [None, 0.8, 0.5],
    #     'pop': None, # [None, 100, 500],
    #     'lbda': None, # [100, 350]
    #     'extra': ' ', # -nodet 1
    #     'extra_cargs': ' -pmut 0.8 -initialgenotype random -added_ind random -restart_method soft_perturb_best -restart_patience 10 -flibclass wHist -wHist_scorefn neg ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
    #     'nameSuffix': '',
    #     'namePrefix': '',
    # },
    # { # best so far evalfn4
    #     'convection': None, #[None, 'convection_'],
    #     'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
    #     'genformat': 0, # [0, 1],
    #     'pmut': 0.8, # [None, 0.8, 0.5],
    #     'pop': None, # [None, 100, 500],
    #     'lbda': None, # [100, 350]
    #     'extra': ' -runname AdaptMutF0pmut08initialgenotyperandomadded_indrandomdissimPHENESTRUCTGREEDYrestart_methodsoftperturbbestrestart_patience10flibclasswHistwHist_scorefnneg -continuerun -nruns 10 ', # -nodet 1
    #     'extra_cargs': ' -evalfn 4 -pmut 0.8 -initialgenotype random -added_ind random -restart_method soft_perturb_best -restart_patience 10 -flibclass wHist -wHist_scorefn neg ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
    #     'nameSuffix': '',
    #     'namePrefix': '',
    # },
    # { # best so far evalfn5
    #     'convection': None, #[None, 'convection_'],
    #     'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
    #     'genformat': 0, # [0, 1],
    #     'pmut': 0.8, # [None, 0.8, 0.5],
    #     'pop': None, # [None, 100, 500],
    #     'lbda': None, # [100, 350]
    #     'extra': ' -runname AdaptMutF0pmut08initialgenotyperandomadded_indrandomdissimPHENESTRUCTGREEDYrestart_methodsoftperturbbestrestart_patience10flibclasswHistwHist_scorefnneg -continuerun -nruns 10 ', # -nodet 1
    #     'extra_cargs': ' -evalfn 5 -pmut 0.8 -initialgenotype random -added_ind random -restart_method soft_perturb_best -restart_patience 10 -flibclass wHist -wHist_scorefn neg ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
    #     'nameSuffix': '',
    #     'namePrefix': '',
    # },
    # { # best so far evalfn6
    #     'convection': None, #[None, 'convection_'],
    #     'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
    #     'genformat': 0, # [0, 1],
    #     'pmut': 0.8, # [None, 0.8, 0.5],
    #     'pop': None, # [None, 100, 500],
    #     'lbda': None, # [100, 350]
    #     'extra': ' -runname AdaptMutF0pmut08initialgenotyperandomadded_indrandomdissimPHENESTRUCTGREEDYrestart_methodsoftperturbbestrestart_patience10flibclasswHistwHist_scorefnneg -continuerun -nruns 10 ', # -nodet 1
    #     'extra_cargs': ' -evalfn 6 -pmut 0.8 -initialgenotype random -added_ind random -restart_method soft_perturb_best -restart_patience 10 -flibclass wHist -wHist_scorefn neg ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
    #     'nameSuffix': '',
    #     'namePrefix': '',
    # },
    { # MAPElites
        'convection': None, #[None, 'convection_'],
        'algorithm': 'MAPElites', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
        'genformat': 0, # [0, 1],
        'pmut': None, # [None, 0.8, 0.5],
        'pop': None, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' ', # -nodet 1
        'extra_cargs': ' -popsize 20 -wHist_cacheActive 1 -flibclass wHist -wHist_ESalgo none -novelty_sel random_meta -restart_method soft_perturb_best -restart_patience 100 -tournament 50 ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
        'nameSuffix': '',
        'namePrefix': '',
    },
    { # best so far storeind, -xov_mutschema choice
        'convection': None, #[None, 'convection_'],
        'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
        'genformat': 0, # [0, 1],
        'pmut': 0.8, # [None, 0.8, 0.5],
        'pop': None, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' ', # -nodet 1
        'extra_cargs': ' -initialgenotype random -added_ind random -dissim PHENE_STRUCT_GREEDY -restart_method soft_perturb_best -restart_patience 10 -flibclass wHist -wHist_ESalgo storeind -xov_mutschema choice ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
        'nameSuffix': '',
        'namePrefix': '',
    },
    { # best so far storeind, -xov_mutschema rand
        'convection': None, #[None, 'convection_'],
        'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
        'genformat': 0, # [0, 1],
        'pmut': 0.8, # [None, 0.8, 0.5],
        'pop': None, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' ', # -nodet 1
        'extra_cargs': ' -initialgenotype random -added_ind random -dissim PHENE_STRUCT_GREEDY -restart_method soft_perturb_best -restart_patience 10 -flibclass wHist -wHist_ESalgo storeind -xov_mutschema rand ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
        'nameSuffix': '',
        'namePrefix': '',
    },
    { # best so far, without xmut
        'convection': None, #[None, 'convection_'],
        'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
        'genformat': 0, # [0, 1],
        'pmut': 0.8, # [None, 0.8, 0.5],
        'pop': None, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' ', # -nodet 1
        'extra_cargs': ' -initialgenotype random -added_ind random -dissim PHENE_STRUCT_GREEDY -restart_method soft_perturb_best -restart_patience 10 -flibclass wHist -wHist_scorefn neg -xmut_enabled 0 ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
        'nameSuffix': '',
        'namePrefix': '',
    },
]
## Maybe later if I have nothing else to do:
    # { # Baseline -1
    #     'convection': None, #[None, 'convection_'],
    #     'algorithm': 'eaSimple', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
    #     'genformat': 1, # [0, 1],
    #     'pmut': None, # [None, 0.8, 0.5],
    #     'pop': None, # [None, 100, 500],
    #     'lbda': None, # [100, 350]
    #     'extra': ' ', # -nodet 1
    #     'extra_cargs': ' -evalfn 6 ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
    #     'nameSuffix': '',
    #     'namePrefix': '',
    # },
    # { # Baseline -1
    #     'convection': None, #[None, 'convection_'],
    #     'algorithm': 'eaSimple', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
    #     'genformat': 1, # [0, 1],
    #     'pmut': None, # [None, 0.8, 0.5],
    #     'pop': None, # [None, 100, 500],
    #     'lbda': None, # [100, 350]
    #     'extra': ' ', # -nodet 1
    #     'extra_cargs': ' -evalfn 5 ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
    #     'nameSuffix': '',
    #     'namePrefix': '',
    # },
    # { # Baseline -1
    #     'convection': None, #[None, 'convection_'],
    #     'algorithm': 'eaSimple', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda', 'NEAT_speciation'],
    #     'genformat': 1, # [0, 1],
    #     'pmut': None, # [None, 0.8, 0.5],
    #     'pop': None, # [None, 100, 500],
    #     'lbda': None, # [100, 350]
    #     'extra': ' ', # -nodet 1
    #     'extra_cargs': ' -evalfn 4 ', #f' -initialgenotype \\"{SIMPLEST_GENOTYPE["f1_basic2"]}\\" ',
    #     'nameSuffix': '',
    #     'namePrefix': '',
    # },
runs = []
print('Running the following commands:')
for run in runs_cfgs:
    n, r = getExperimentData(run)
    runs.append(r)
    print(r)
print()
print()
print()
print('=' * 100)
print(f"We'll be back in {len(runs) * 7.5} h ({len(runs) * 7.5 / 24:.2f} days)")
print('=' * 100)
print()

os.chdir(get_disertatie_root())
os.system(' && '.join(runs))