import os, time, tqdm, sys
import concurrent.futures
import argparse

DATA_PATH = '/home/xwiki/Documents/fac/GECCO_Robot_Body/Disertatie/'

def parseArgs():
    parser = argparse.ArgumentParser(description='This script will run multiple experiments in parallel, and save the results.')
    parser.add_argument('-runname', default='run', help='The name under which the experiment should be saved')
    parser.add_argument('-commandargs', default='', help='The name under which the experiment should be saved')
    parser.add_argument('-nruns', type=int, default=20, help='How many experiments to run')
    parser.add_argument('-numworkers', type=int, default=10, help='Number of parallel workers')
    """
    -nodet
    @since 12 Apr 2025, 21:43 # Change this to before you run the experiment
    """
    parser.add_argument('-nodet', type=int, default=0, help='1 if determinism.sim should be disabled')
    return parser.parse_args()
parsedargs = parseArgs()
print(parsedargs)
N_RUNS = parsedargs.nruns
RUN_FOLDER_NAME = parsedargs.runname
DET = bool(parsedargs.nodet)
if DET:
    RUN_FOLDER_NAME = 'no_det_' + RUN_FOLDER_NAME
# if os.path.exists(f'{DATA_PATH}framspy/experiments/{RUN_FOLDER_NAME}'):
#     print("[STOPPING] Experiment already exists: " + f'{DATA_PATH}framspy/experiments/{RUN_FOLDER_NAME}')
#     exit(0)

RUN_FOLDER_NAME = RUN_FOLDER_NAME if not os.path.exists(f'{DATA_PATH}framspy/experiments/{RUN_FOLDER_NAME}') else f"{RUN_FOLDER_NAME}_{time.time()}"
dirname = f'{DATA_PATH}framspy/experiments/{RUN_FOLDER_NAME}'
os.mkdir(dirname)

COMMAND = ' '.join([
    'python runExperiment.py',
    '-path /home/xwiki/Documents/fac/GECCO_Robot_Body/Framsticks54',
    f'-sim "eval-allcriteria.sim;{"deterministic.sim;" if not DET else ""}recording-body-coords.sim;"',
    '-opt COGpath -generations 100000000 '] + [parsedargs.commandargs] + [' -hof_savefile '])
# '-genformat 1',
# '-algorithm convection_eaSimple -pmut 0.8', #'-migrate_after 10 -nislands 10',

def run_th(run_id):
    global dirname, COMMAND
    os.system(COMMAND + f' {dirname}/hof_{run_id}.txt > {dirname}/results_{run_id}.stdout')# 2> {dirname}/results_{run_id}.stderr')

def run_runs():
    print("Running the following command:")
    print(COMMAND)
    print("Started at " + time.ctime())
    print("Expected finish time: ", time.ctime(time.time() + 7.5 * 60 * 60))
    with concurrent.futures.ThreadPoolExecutor(max_workers=parsedargs.numworkers) as executor:
        future_fns = {executor.submit(run_th, i): i for i in range(N_RUNS)}
        for future in tqdm.tqdm(concurrent.futures.as_completed(future_fns), total=len(future_fns)):
            url = future_fns[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))
            else:
                # print('%r finished' % (url))
                pass
    print("Ended at " + time.ctime())


run_runs()
if os.path.exists(DATA_PATH + 'algo_run_dict.json'):
    os.remove(DATA_PATH + 'algo_run_dict.json')
if os.path.exists(DATA_PATH + 'parsed_result_data.pkl'):
    os.remove(DATA_PATH + 'parsed_result_data.pkl')

os.system("python collect_data.py")
print()
print(' * '.center(100, '='))
print()
print()
print()