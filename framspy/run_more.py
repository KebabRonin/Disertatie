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

def get_command(nodet, commandargs):
    return ' '.join([
        'python runExperiment.py',
        '-path /home/xwiki/Documents/fac/GECCO_Robot_Body/Framsticks54',
        f'-sim "eval-allcriteria.sim;{"deterministic.sim;" if not nodet else ""}recording-body-coords.sim;"',
        '-opt COGpath -generations 1 '] # 100000000
        + [commandargs]
        + [' -hof_savefile ']
    )
# '-genformat 1',
# '-algorithm convection_eaSimple -pmut 0.8', #'-migrate_after 10 -nislands 10',

def run_th(run_id, dirname, command):

    os.system(command + f' {dirname}/hof_{run_id}.txt > {dirname}/results_{run_id}.stdout')# 2> {dirname}/results_{run_id}.stderr')

def run_runs(params):
    dirname = f'{DATA_PATH}framspy/experiments/{params['runname']}'
    os.mkdir(dirname)
    command = get_command(params['nodet'], params['commandargs'])
    print("Running the following command:")
    print(command)
    print("Started at " + time.ctime())
    print("Expected finish time: ", time.ctime(time.time() + 7.5 * 60 * 60))
    with concurrent.futures.ThreadPoolExecutor(max_workers=params['numworkers']) as executor:
        future_fns = {executor.submit(run_th, i, dirname, command): i for i in range(params['nruns'])}
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

def main(params):
    if params['nodet']:
        params['runname'] = 'no_det_' + params['runname']
    if os.path.exists(f'{DATA_PATH}framspy/experiments/{params['runname']}'):
        params['runname'] += f"_{time.time()}"
    # if os.path.exists(f'{DATA_PATH}framspy/experiments/{RUN_FOLDER_NAME}'):
    #     print("[STOPPING] Experiment already exists: " + f'{DATA_PATH}framspy/experiments/{RUN_FOLDER_NAME}')
    #     exit(0)
    run_runs(params)
    if os.path.exists(DATA_PATH + 'algo_run_dict.json'):
        os.remove(DATA_PATH + 'algo_run_dict.json')
    # if os.path.exists(DATA_PATH + 'parsed_result_data.pkl'):
    #     os.remove(DATA_PATH + 'parsed_result_data.pkl')

    os.system("python collect_data.py --redo")
    print()
    print(' * '.center(100, '='))
    print()
    print()
    # os.system("python load_optuna.py --silent")


if __name__ == '__main__':
    parsedargs = parseArgs()
    print(parsedargs)
    nnodet = bool(parsedargs.nodet)
    params = {
        'nodet': nnodet,
        'runname': parsedargs.runname,
        'nruns': parsedargs.nruns,
        'commandargs':parsedargs.commandargs,
        'numworkers': parsedargs.numworkers,
    }
    main(params)
