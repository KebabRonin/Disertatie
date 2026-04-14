import sys, os, re

P_SIZE = 500

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
    name = f'{namePrefix}{"convection_" if convection != None else ""}{algorithm}F{genformat}' \
        + f'{("pmut" + str(pmut).replace(".", "")) if pmut != None else ""}'\
        + f'{("lbda" + str(lbda)) if lbda != None else ""}'\
        + f'{("pop" + str(pop)) if pop != None else ""}'
    for ec in re.findall(r'-([a-zA-Z_]+) ([^\s]*)', extra_cargs):
        name += ec[0] + ec[1].replace('.','')
    name += nameSuffix
    run_str = 'python run_more.py -runname ' \
        + name \
        + extra + ' -commandargs "' \
            + ((f' -genformat {genformat}') if genformat != None else '') \
            + ((f' -algorithm {"convection_" if convection != None else ""}{algorithm}') if genformat != None else '') \
            + ((f' -pmut {pmut}') if pmut != None else '') \
            + ((f' -lbda {lbda}') if lbda != None else '') \
            + ((f' -popsize {pop}') if pop != None else '') \
            + extra_cargs \
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
        'convection': None, #[None, 'convection_'],
        'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda'],
        'genformat': 0, # [0, 1],
        'pmut': 0.8, # [None, 0.8, 0.5],
        'pop': None, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' -nodet 1 -numworkers 20 ',
        'extra_cargs': ' ',
        'nameSuffix': '',
        'namePrefix': 'nodet_',
    }, # 08:00
    {
        'convection': 'convection_', #[None, 'convection_'],
        'algorithm': 'eaSimple', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda'],
        'genformat': 1, # [0, 1],
        'pmut': None, # [None, 0.8, 0.5],
        'pop': 100, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' -nodet 1 ',
        'extra_cargs': ' ',
        'nameSuffix': '',
        'namePrefix': 'nodet_',
    }, # 15:30
    {
        'convection': None, #[None, 'convection_'],
        'algorithm': 'eaSimple', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda'],
        'genformat': 1, # [0, 1],
        'pmut': None, # [None, 0.8, 0.5],
        'pop': None, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' -nodet 1 ',
        'extra_cargs': ' ',
        'nameSuffix': '',
        'namePrefix': 'nodet_',
    }, # 24:00
    {
        'convection': 'convection_', #[None, 'convection_'],
        'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda'],
        'genformat': 0, # [0, 1],
        'pmut': None, # [None, 0.8, 0.5],
        'pop': 500, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' -nodet 1 -numworkers 20 ',
        'extra_cargs': ' ',
        'nameSuffix': '',
        'namePrefix': 'nodet_',
    }, # 5:30
    {
        'convection': None, #[None, 'convection_'],
        'algorithm': 'AdaptMut', # ['AdaptMut', 'eaSimple', 'eaMuPlusLambda', 'eaMuCommaLambda'],
        'genformat': 0, # [0, 1],
        'pmut': None, # [None, 0.8, 0.5],
        'pop': None, # [None, 100, 500],
        'lbda': None, # [100, 350]
        'extra': ' -nodet 1 -numworkers 20 ',
        'extra_cargs': ' ',
        'nameSuffix': '',
        'namePrefix': 'nodet_',
    }, # 11:00
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
print(f"We'll be back in {len(runs) * 7.5} h ({len(runs) * 7.5 / 24:.2f} days)")
print('=' * 100)
print()

os.system(' && '.join(runs))