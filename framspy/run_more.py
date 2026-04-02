import os, time, tqdm
import concurrent.futures

dirname = f'experiments/{time.time()}'
os.mkdir(dirname)

COMMAND = 'python runExperiment.py -path /home/xwiki/Documents/fac/GECCO_Robot_Body/Framsticks54 -sim "eval-allcriteria.sim;deterministic.sim;recording-body-coords.sim;" -opt COGpath -genformat 0 -pmut 0.8 -generations 100000000 -algorithm convection_AdaptMut -migrate_after 10 -nislands 10 -hof_savefile '

def run_th(run_id):
    global dirname, COMMAND
    os.system(COMMAND + f' {dirname}/hof_{run_id}.txt > {dirname}/results_{run_id}.stdout')# 2> {dirname}/results_{run_id}.stderr')


print("Started at " + time.ctime())
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    future_fns = {executor.submit(run_th, i): i for i in range(20)}
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
