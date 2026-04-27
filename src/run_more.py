import os, time, tqdm, sys
import concurrent.futures
import argparse, math

from .config_loader import get_disertatie_root, get_framsticks_path, load_config, get_simfiles_path, get_experiments_dir

BASE_PATH = get_disertatie_root()
# Should be pointing to the Disertatie folder

# Load configuration
CONFIG = load_config()

def parseArgs():
    parser = argparse.ArgumentParser(description='This script will run multiple experiments in parallel, and save the results.')
    parser.add_argument('-runname', default='run', help='The name under which the experiment should be saved')
    parser.add_argument('-commandargs', default='', help='The name under which the experiment should be saved')
    parser.add_argument('-nruns', type=int, default=20, help='How many experiments to run')
    parser.add_argument('-numworkers', type=int, default=10, help='Number of parallel workers')
    parser.add_argument('-continuerun', action='store_true', help='If the trial already exists, add the new runs to it, taking the commandargs from the existing runs')
    """
    -nodet
    @since 12 Apr 2025, 21:43 # Change this to before you run the experiment
    """
    parser.add_argument('-nodet', type=int, default=0, help='1 if determinism.sim should be disabled')
    return parser.parse_args()

def get_command(nodet, commandargs, framsticks_path=None):
    if framsticks_path is None:
        # Load from config
        framsticks_path = get_framsticks_path(CONFIG)
    simfiles = ';'.join([
        os.path.join(get_simfiles_path(), 'eval-allcriteria.sim'),
        os.path.join(get_simfiles_path(), 'deterministic.sim') if not nodet else '',
        os.path.join(get_simfiles_path(), 'recording-body-coords.sim'),
    ])
    return ' '.join([
        'python -m src.runExperiment',
        f'-path {framsticks_path}',
        f'-sim "{simfiles}"',
        '-opt COGpath -generations 100000000 ']
        + [commandargs] #.replace('|','^|')] ## FIXME: THIS IS A FIX FOR WINDOWS ONLY!!!
        + [' -hof_savefile ']
    )
# '-genformat 1',
# '-algorithm convection_eaSimple -pmut 0.8', #'-migrate_after 10 -nislands 10',

def run_th(run_id, dirname, command):
    hof_file = os.path.join(dirname, f'hof_{run_id}.txt')
    stdout_file = os.path.join(dirname, f'results_{run_id}.stdout')
    os.system(command + f' {hof_file} > {stdout_file}')# 2> {os.path.join(dirname, f'results_{run_id}.stderr')}

def run_runs(params):
    dirname = os.path.join(get_experiments_dir(), params['runname'])
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    elif not params['continuerun']:
        print('Continuerun param is not set, but the run already exists')
        exit()
    command = get_command(params['nodet'], params['commandargs'])
    print("Running the following command:")
    print(command + f' {dirname}/hof_{0}.txt > {dirname}/results_{0}.stdout')
    print("Started at " + time.ctime())
    print("Expected finish time: ", time.ctime(time.time() + (3.75 * 60 * 60) * math.ceil(params['nruns'] / 10)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=params['numworkers']) as executor:
        future_fns = {executor.submit(run_th, i, dirname, command): i for i in (params['runindexes'] if 'runindexes' in params else range(params['nruns']))}
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
    experiments_dir = get_experiments_dir()
    if not os.path.exists(experiments_dir):
        os.mkdir(experiments_dir)
    if params['nodet']:
        params['runname'] = 'no_det_' + params['runname']
    run_dir = os.path.join(experiments_dir, params['runname'])
    if os.path.exists(run_dir):
        if not params['continuerun']:
            params['runname'] += f"_{time.time()}"
        else:
            from . import collect_data
            params['commandargs'] = collect_data.parse_algo_params(params['runname'])
            params_str = ''
            for pname in params['commandargs']:
                if params['commandargs'][pname] != 'None':
                    if pname == 'dissim' and params['commandargs'][pname].startswith('DissimMethod.'):
                        params['commandargs'][pname] = params['commandargs'][pname][len('DissimMethod.'):]
                    params_str += f' -{pname} "{params['commandargs'][pname]}"'
            params['commandargs'] = params_str
            params['runindexes'] = []
            i = -1
            while len(params['runindexes']) < params['nruns']:
                i += 1
                hof_path = os.path.join(collect_data.EXPERIMENTS_PATH, params['runname'], f'hof_{i}.txt')
                results_path = os.path.join(collect_data.EXPERIMENTS_PATH, params['runname'], f'results_{i}.stdout')
                if os.path.exists(hof_path) or os.path.exists(results_path):
                    continue
                else:
                    params['runindexes'].append(i)
            print(params['commandargs'])
            print(params['runindexes'])
    os.chdir(get_disertatie_root())
    run_runs(params)
    exit()
    os.system("python -m src.collect_data --redo")
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
        'continuerun': parsedargs.continuerun,
    }
    main(params)
