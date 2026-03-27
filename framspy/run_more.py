import os, time, tqdm

dirname = f'experiments/{time.time()}'
os.mkdir(dirname)

COMMAND = 'python runExperiment.py -path /home/xwiki/Documents/fac/GECCO_Robot_Body/Framsticks54 -sim "eval-allcriteria.sim;deterministic.sim;recording-body-coords.sim;" -opt COGpath -genformat 0 -pmut 0.8 -generations 100000000 -algorithm AdaptMut -hof_savefile '

for i in tqdm.trange(20):
    os.system(COMMAND + f' {dirname}/hof_{i}.txt > {dirname}/results_{i}.stdout')# 2> {dirname}/results_{i}.stderr')