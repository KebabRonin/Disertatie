import os, time, tqdm, sys
import concurrent.futures
import argparse, math

DATA_PATH = '/home/xwiki/Documents/fac/GECCO_Robot_Body/Disertatie/'

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

def get_command(nodet, commandargs):
    return ' '.join([
        'python runExperiment.py',
        '-path /home/xwiki/Documents/fac/GECCO_Robot_Body/Framsticks54',
        f'-sim "eval-allcriteria.sim;{"deterministic.sim;" if not nodet else ""}recording-body-coords.sim;"',
        '-opt COGpath -generations 100000000 ']
        + [commandargs]
        + [' -hof_savefile ']
    )
# '-genformat 1',
# '-algorithm convection_eaSimple -pmut 0.8', #'-migrate_after 10 -nislands 10',

def run_th(run_id, dirname, command):
    os.system(command + f' {dirname}/hof_{run_id}.txt > {dirname}/results_{run_id}.stdout')# 2> {dirname}/results_{run_id}.stderr')

def run_runs(params):
    dirname = f'{DATA_PATH}framspy/experiments/{params['runname']}'
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
    if params['nodet']:
        params['runname'] = 'no_det_' + params['runname']
    if os.path.exists(f'{DATA_PATH}framspy/experiments/{params['runname']}'):
        if not params['continuerun']:
            params['runname'] += f"_{time.time()}"
        else:
            import collect_data
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
                if os.path.exists(collect_data.PATH + params['runname'] + f'/hof_{i}.txt') or os.path.exists(collect_data.PATH + params['runname'] + f'/results_{i}.stdout'):
                    continue
                else:
                    params['runindexes'].append(i)
            print(params['commandargs'])
            print(params['runindexes'])
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
        'continuerun': parsedargs.continuerun,
    }
    main(params)
