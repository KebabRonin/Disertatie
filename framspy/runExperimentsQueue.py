import sys, os

P_SIZE = 500

def getExperimentData(rconfig):
    convection = rconfig['convection']
    algorithm = rconfig['algorithm']
    genformat = rconfig['genformat']
    pmut = rconfig['pmut']
    extra_cargs = rconfig['extra_cargs']
    extra = rconfig['extra']
    pop = rconfig['pop']
    name = f'{"convection_" if convection != None else ""}{algorithm}F{genformat}' \
        + f'{("pmut" + str(pmut).replace(".", "")) if pmut != None else ""}{("pop" + str(pop)) if pop != None else ""}'
    run_str = 'python run_more.py -runname ' \
        + name \
        + extra + ' -commandargs "' \
            + ((f' -genformat {genformat}') if genformat != None else '') \
            + ((f' -algorithm {"convection_" if convection != None else ""}{algorithm}') if genformat != None else '') \
            + ((f' -pmut {pmut}') if pmut != None else '') \
            + ((f' -popsize {pop}') if pop != None else '') \
            + extra_cargs \
        + '"'
    return name, run_str

def getUnrunExperiments():
    params = {
        'convection': [None, 'convection_'],
        'algorithm': ['AdaptMut', 'eaSimple'],
        'genformat': [0, 1],
        'pmut': [None, 0.8, 0.5],
        'pop': [None, 100, 500],
        'extra': '',
        'extra_cargs': '',
    }
    DATA_PATH = '/home/xwiki/Documents/fac/GECCO_Robot_Body/Disertatie/'

    import itertools
    alr_run = 0
    runns = 0
    for rconfig in itertools.product(*params.values()):
        runns += 1
        name, run_str = getExperimentData(rconfig)
        dirname = f'{DATA_PATH}framspy/experiments/{name}'
        if os.path.exists(dirname):
            alr_run += 1
        else:
            print(name)
    print (f"{alr_run}/{runns} ({alr_run/runns:.3f})")

runs_cfgs = [
    {
        'convection': 'convection_', #[None, 'convection_'],
        'algorithm': 'eaSimple', # ['AdaptMut', 'eaSimple'],
        'genformat': 1, # [0, 1],
        'pmut': 0.7, # [None, 0.8, 0.5],
        'pop': None, # [None, 100, 500],
        'extra': '',
        'extra_cargs': '',
    },
]
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
print(f"We'll be back in {len(runs) * 8} h ({len(runs) * 8 / 24:.2f} days)")
print('=' * 100)
print()
os.system(' && '.join(runs))