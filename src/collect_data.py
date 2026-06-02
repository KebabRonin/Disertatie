import re, os, sys, json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import pickle, argparse
from PIL import Image
import concurrent.futures, tqdm
import matplotlib, time
import random
# Import configuration loader
from .config_loader import get_disertatie_root, load_config, get_experiments_dir

# Remove warnings from console, but disable interactive plots
matplotlib.use('agg')

BASELINE = 'AdaptMutF0pmut08added_indrandom'
# BASELINE = 'AdaptMutF0pmut08'
ARR_TO_PLOT = 'mx_arrs' # 'avg_arrs' #

BASELINES = [
    BASELINE,
    'AdaptMutF0pmut08added_indrandomevalfn4',
    'AdaptMutF0pmut08added_indrandomevalfn5',
    'AdaptMutF0pmut08added_indrandomevalfn6',
]

HIGHLIGHT = {
    'eaSimpleF1': 'red',
    # 'AdaptMutF0pmut08added_indrandom': 'red',
    # 'AdaptMutF0pmut08': 'red',
    BASELINE: 'red'
}
COLORS = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'magenta']

def get_algo_color(algo_name):
    random.seed(algo_name)
    return random.choice(COLORS)

N_RUNS = 20
MAX_STEPS = 100_001
example_idx = 0

# Load configuration
CONFIG = load_config()
BASE_PATH = get_disertatie_root()
# Should be pointing to the Disertatie folder
EXPERIMENTS_PATH = get_experiments_dir()
SHOW_CLASAMENT = False
IMG_SAVE_PATH = os.path.join(BASE_PATH, 'runplots', 'images')
GIF_SAVE_PATH = os.path.join(BASE_PATH, 'runplots', 'gifs')
if not os.path.exists(IMG_SAVE_PATH):
    os.makedirs(IMG_SAVE_PATH)
if not os.path.exists(GIF_SAVE_PATH):
    os.makedirs(GIF_SAVE_PATH)
DATA_FILE = os.path.join(BASE_PATH, 'parsed_result_data.pkl')
STATS_FILE = os.path.join(BASE_PATH, 'algo_run_dict.json')

def parseArgs():
    parser = argparse.ArgumentParser(description='This script will run multiple experiments in parallel, and save the results.')
    parser.add_argument('-s', '--silent', action='store_true', help='To output or not to output')
    parser.add_argument('--redo', action='store_true', help='To output or not to output')
    parser.add_argument('--latex', action='store_true', help='To output the leaderboard in latex format')
    return parser.parse_args()

def running_stat(arr, fn, radius=50):
    return [fn(arr[i-radius:i+radius]) for i in range(len(arr))]

def order_fn_median(names):
    ordered_names = list(names.keys())
    ordered_names.sort(key=lambda n: np.median(names[n]['runs']), reverse=True)
    return ordered_names

def order_fn_mean(names):
    ordered_names = list(names.keys())
    ordered_names.sort(key=lambda n: np.mean(names[n]['runs']), reverse=True)
    return ordered_names

def order_fn_max(names):
    ordered_names = list(names.keys())
    ordered_names.sort(key=lambda n: max(names[n]['runs']), reverse=True)
    return ordered_names

def order_fn_min(names):
    ordered_names = list(names.keys())
    ordered_names.sort(key=lambda n: min(names[n]['runs']), reverse=True)
    return ordered_names

def parse_algo_params(name: str):
    params = {}
    ook = False
    for file_name in [p for p in os.listdir(os.path.join(EXPERIMENTS_PATH, name)) if re.match(r'^results_\d+\.stdout$', p)]:
        with open(os.path.join(EXPERIMENTS_PATH, name, file_name), 'r') as f:
            parstr = ''
            ok = False
            for currstr in f.readlines():
                if currstr.startswith('Using Framsticks version'):
                    ok = True
                    break
                parstr += currstr
                currstr = f.readline()
            if not ok:
                continue
            ook = True
            break
    if ook == False:
        raise ("No valid files in folder " + name)
    parstr = parstr.strip()
    nextarg = ', skipinitialgenotype=' if parstr.split(', initialgenotype=')[1].find(', skipinitialgenotype=') != -1 else ', algorithm='
    params['initialgenotype'] = parstr.split(', initialgenotype=')[1].split(nextarg)[0]
    parstr = parstr.split(', initialgenotype=')[0] + nextarg + parstr.split(nextarg)[1]
    pp = re.findall(PARAM_PATT, parstr)
    for g in pp:
        params[g[0]] = g[1]
    return params

PARAM_PATT = re.compile(r'\b([\w0-9]+)=([\w0-9_\-\n \/.;:]+)')
def get_algo_params(name):
    return {
            'run_start': os.stat(os.path.join(EXPERIMENTS_PATH, name['runname'], f'results_{name['runidx']}.stdout')).st_mtime,
            'run_end': os.stat(os.path.join(EXPERIMENTS_PATH, name['runname'], f'results_{name['runidx']}.stdout')).st_ctime,
            'generations': int(name['generations']),
            'invalid_genos': int(name['invalid_genos']),
            'nonevalTime': None if name['nonevalTime'] is None else float(name['nonevalTime']),
            'totalevals': int(name['totalevals']),
            'evalTime': float(name['evalTime']),
        }

def get_algo_dict(rk):
    """
    Get all experiment runs, grouped by algorithm.
    """
    names = {}
    for n in rk:
        if n['runname'] not in names:
            names[n['runname']] = {
                'params': parse_algo_params(n['runname']),
                'meta': [],
                'runs': [],
            }
        names[n['runname']]['meta'].append(get_algo_params(n))
        names[n['runname']]['runs'].append(n['fitness'])
    return names

def get_finished_runs(runname):
    files = os.listdir(os.path.join(EXPERIMENTS_PATH, runname))
    finished_runs = []
    for f in files:
        g = re.match(r'hof_(\d+).txt', f)
        if g:
            finished_runs.append(int(g.groups()[0]))
    return finished_runs


rgx = r'([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?|nan)'
sp = r'\s+'

def get_best_genotypes_over_all_runs() -> list[list]:
    scoreboard = []
    path = os.path.join(get_disertatie_root(), 'S2ViYWJSb25pblVBSUM=.results')
    if os.path.exists(path):
        with open(path, 'r') as f:
            # '2026-04-27 20:13	KebabRoninUAIC	3	100001	14627.3	86.6475	373.5824823213579	//0'
            regex = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}\tKebabRoninUAIC\t(\d)\t(\d+)\t' + f"{rgx}{sp}{rgx}{sp}{rgx}{sp}(.*)")
            next_entry = None
            for l in f.readlines():
                m = regex.match(l)
                if m:
                    if next_entry:
                        scoreboard.append(next_entry)
                        next_entry = None
                    evalfn, totalevals, time, nonevaltime, fitness, genotype = m.groups()
                    if genotype.startswith('//0'):
                        genotype += '\n'
                    next_entry = [evalfn, int(totalevals), float(time), float(nonevaltime), float(fitness), genotype]
                elif next_entry:
                    next_entry[5] += l
    scoreboard.sort(key=lambda x: x[4])
    return scoreboard

GEN_REGEX = re.compile(f'^([0-9]+){sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}?{sp}?$')
GEN_REGEX_SPECIES = re.compile(f'^([0-9]+)\\.([0-9]+){sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}?{sp}?$')
GEN_REGEX_ISLAND_START = r'^starting island\s+(\d+)\s+$'
GEN_REGEX_INVALID_GENOS = r'^Selection: ignoring (\d+) infeasible solution in a population of size (\d+)$'
def parse_data(rs=None):
    if rs is None:
        rs = {}
    modified = False
    # print("I already have these:", rs.keys())
    pbar = tqdm.tqdm(sorted(os.listdir(EXPERIMENTS_PATH)), desc="Parsing algos", position=0, leave=True)
    for idx, d in enumerate(pbar):
        # if ('convection' not in d):
        #     continue
        finished_runs = get_finished_runs(d)
        if d in rs:
            if len(rs[d]['mx_arrs']) == len(finished_runs):
                continue
            else:
                print(f"Updating runs for {d}, since I found more (I have {len(rs[d]['mx_arrs'])}, now there's {len(finished_runs)})")
        if len(finished_runs) == 0:
            print(f"Skipping {d} since it has no finished runs")
            continue
        if len(finished_runs) < N_RUNS:
            print(f"[WARNING] {d} is not complete - it has {len(finished_runs)} finished runs")
            # continue
        mx_arrs = []
        mn_arrs = []
        avg_arrs = []
        gens_arr = []
        std_arrs = []
        nonevalTime_arr = []
        totalevals_arr = []
        evalTime_arr = []
        species_dicts = []
        islands_arrs = []
        invalid_genos_arr_count = []
        for i in finished_runs:
            mx_arr = []
            mn_arr = []
            avg_arr = []
            std_arr = []
            species_dict = {}
            islands = {}
            invalid_genos_count = 0
            with open(os.path.join(EXPERIMENTS_PATH, d, f'results_{i}.stdout'), 'r') as f:
                # First line tells us the arguments the run had.
                argvalues = f.readline()
                argvalues = argvalues[len('Argument values: '):]
                # arggs = re.findall('([^=]+)=([^, ]+),? ?', argvalues)
                args = parse_algo_params(d)
                # args = {a[0]: a[1] for a in arggs}
                if 'popsize' not in args:
                    args['popsize'] = 50
                island_id = None
                prevTevals = None
                last_totalevals = None
                for lidx, l in enumerate(f):
                    totalevals = None
                    m = re.match(GEN_REGEX, l)
                    m_species = re.match(GEN_REGEX_SPECIES, l)
                    m_species_end = re.match(r"^Removed species (\d+).*$", l)
                    m_island  = re.match(GEN_REGEX_ISLAND_START, l)
                    m_invalid = re.match(GEN_REGEX_INVALID_GENOS, l)
                    if m:
                        gen, nevals, avg, stdev, mn, mx, totalevals, evalTime, nonevalTime = m.groups()
                        if totalevals == prevTevals:
                            # For convection runs, count this as a regular step, not as an island step.
                            island_id = None
                        if island_id is None:
                            mx_arr += [(int(totalevals), float(mx) if mx != 'nan' else None)]
                            mn_arr += [(int(totalevals), float(mn) if mn != 'nan' else None)]
                            avg_arr += [(int(totalevals), float(avg) if avg != 'nan' else None)]
                            std_arr += [(int(totalevals), float(stdev) if stdev != 'nan' else None)]
                        else:
                            islands[island_id]['mx_arrs'] += [(int(totalevals), float(mx) if mx != 'nan' else None)]
                            islands[island_id]['mn_arrs'] += [(int(totalevals), float(mn) if mn != 'nan' else None)]
                            islands[island_id]['avg_arrs'] += [(int(totalevals), float(avg) if avg != 'nan' else None)]
                            islands[island_id]['std_arrs'] += [(int(totalevals), float(stdev) if stdev != 'nan' else None)]
                    elif m_island:
                        # We're in convection algorithm, so we should store each island separately.
                        island_id, = m_island.groups()
                        island_id = int(island_id)
                        if island_id not in islands:
                            islands[island_id] = {
                                'mx_arrs': [],
                                'mn_arrs': [],
                                'avg_arrs': [],
                                'std_arrs': [],
                            }
                        continue
                    elif m_species_end:
                        species_id, = m_species_end.groups()
                        if species_id in species_dict:
                            spec_i = 0
                            while f"{species_id}-{spec_i}" in species_dict:
                                spec_i += 1
                            lastidx = len(species_dict[species_id]['avg_arrs']) - 1
                            while lastidx > 0 and (
                                    species_dict[species_id]['avg_arrs'][lastidx][0] == species_dict[species_id]['avg_arrs'][lastidx - 1][0]
                                    ):
                                # Since island ids are imperfect, several islands can share the same id.
                                # This loop treats the case when, after island X is killed, a new island X is generated,
                                # but it is removed before it can do another loop (eg. it contained only infeasible individuals)
                                species_dict[species_id]['avg_arrs'] = species_dict[species_id]['avg_arrs'][:-1]
                                species_dict[species_id]['mx_arrs']  = species_dict[species_id]['mx_arrs'][:-1]
                                species_dict[species_id]['mn_arrs']  = species_dict[species_id]['mn_arrs'][:-1]
                                species_dict[species_id]['std_arrs'] = species_dict[species_id]['std_arrs'][:-1]
                                lastidx = len(species_dict[species_id]['avg_arrs']) - 1
                            species_dict[f"{species_id}-{spec_i}"] = species_dict[species_id]
                            species_dict.pop(species_id)
                        else:
                            pass
                    elif m_species:
                        # We're in speciation algorithm, so we should store each species separately.
                        gen, species_id, nevals, avg, stdev, mn, mx, totalevals, evalTime, nonevalTime = m_species.groups()
                        if species_id not in species_dict:
                            species_dict[species_id] = {
                                'mx_arrs': [],
                                'mn_arrs': [],
                                'avg_arrs': [],
                                'std_arrs': [],
                            }
                        species_dict[species_id]['mx_arrs'] += [(int(totalevals), float(mx) if mx != 'nan' else None)]
                        species_dict[species_id]['mn_arrs'] += [(int(totalevals), float(mn) if mn != 'nan' else None)]
                        species_dict[species_id]['avg_arrs'] += [(int(totalevals), float(avg) if avg != 'nan' else None)]
                        species_dict[species_id]['std_arrs'] += [(int(totalevals), float(stdev) if stdev != 'nan' else None)]
                    elif m_invalid:
                        invalid_genos, popsize_invalid = m_invalid.groups()
                        invalid_genos_count += int(invalid_genos)
                    prevTevals = totalevals
                    last_totalevals = totalevals if totalevals is not None else last_totalevals
                if 'Lambda' in d:
                    expected_evals = 100_000 - max(int(args['popsize']), int(args['lbda'] if 'lbda' in args else 0))
                elif 'convection' in d:
                    expected_evals = 100_000 - int(args['popsize']) * int(args['migrate_after'])
                else:
                    expected_evals = 100_000 - int(args['popsize'])
                if mx_arr[-1][0] <= expected_evals:
                    if nonevalTime is not None and float(nonevalTime) > 3600:
                        print("(Hit time limit)", d, i, f"{float(nonevalTime)} > 3600")
                    else:
                        print("(Stopped too early) ", d, i, f"{mx_arr[-1][0]} <= {expected_evals}")
                # print(len(islands))
                # for i in islands.keys():
                #     print(i)
                #     print(len(islands[list(islands.keys())[i]]['avg_arrs']))
                #     print(islands[list(islands.keys())[i]]['avg_arrs'][-10:])
                # exit(0)
            gens_arr.append(gen)
            nonevalTime_arr.append(nonevalTime)
            totalevals_arr.append(last_totalevals)
            evalTime_arr.append(evalTime)
            mx_arrs.append(mx_arr)
            mn_arrs.append(mn_arr)
            avg_arrs.append(avg_arr)
            std_arrs.append(std_arr)
            invalid_genos_arr_count.append(invalid_genos_count)
            if len(islands) > 0:
                islands_arrs.append(islands)
            if len(species_dict) > 0:
                species_dicts.append(species_dict)
        pbar.set_postfix_str(d)
        rs[d] = {
            'params': args,
            'run_idx': i,
            'mx_arrs': mx_arrs,
            'mn_arrs': mn_arrs,
            'avg_arrs': avg_arrs,
            'generations': gens_arr,
            'invalid_genos': invalid_genos_arr_count,
            'nonevalTime': nonevalTime_arr,
            'totalevals': totalevals_arr,
            'evalTime': evalTime_arr,
            'species_dicts': species_dicts,
            'islands_arrs': islands_arrs,
        }
        modified = True
        if len(species_dicts) > 0:
            rs[d]['species'] = species_dicts
        if len(islands_arrs) > 0:
            rs[d]['islands'] = islands_arrs
    return rs, modified

def violins(names, order_fn=order_fn_median):
    plt.figure(figsize=FIGSIZE)
    ordered_names = order_fn(names)
    for idx, n in enumerate(ordered_names):
        plt.scatter([idx+1] * 20, names[n]['runs'], color=get_algo_color(n), label=n)
    vp = plt.violinplot([names[n]['runs'] for n in ordered_names], showmeans=True, showmedians=True)
    for i, body in enumerate(vp['bodies']):
        body.set_facecolor(get_algo_color(n))
        body.set_edgecolor('blue')
    vp['cmeans'].set_color('black')
    vp['cmeans'].set_linewidth(1.5)
    vp['cmedians'].set_color('white')
    vp['cmedians'].set_linestyle(':')
    vp['cmedians'].set_linewidth(1.5)
    plt.xticks(range(1, len(names)+1), names, rotation=45, ha='right')
    plt.legend(handles = [vp['cmeans'], vp['cmedians']],labels=['mean', 'median'])
    ax = plt.gca()
    for tick in ax.get_xticklabels():
        if tick.get_text() in HIGHLIGHT:
            tick.set_color(HIGHLIGHT[tick.get_text()])

def boxplots(names, order_fn=order_fn_median):
    global HIGHLIGHT
    hhighlight = {}
    hhighlight.update(HIGHLIGHT)
    bbest = []
    plt.figure(figsize=FIGSIZE)
    ordered_names = order_fn(names)
    for idx, n in enumerate(ordered_names):
        if len(names[n]['runs']) < 20:
            hhighlight[n] = 'blue'
        if names[n]['params']['algorithm'] not in bbest:
            hhighlight[n] = 'green'
            bbest.append(names[n]['params']['algorithm'])
    for idx, n in enumerate(reversed(ordered_names)):
        plt.scatter(names[n]['runs'], [idx+1] * len(names[n]['runs']), color=get_algo_color(n), label=n, alpha=0.2)
    plt.boxplot([names[n]['runs'] for n in reversed(ordered_names)], showmeans=True, orientation='horizontal')
    plt.yticks(range(1, len(names)+1), reversed(ordered_names), rotation=0, ha='right')
    ax = plt.gca()
    for tick in ax.get_yticklabels():
        if tick.get_text() in hhighlight:
            tick.set_color(hhighlight[tick.get_text()])
    idx_baseline = ordered_names.index(BASELINE)
    return ordered_names[:idx_baseline]

HOF_SCORE = re.compile(f"\\nCOGpath:{rgx}\\n")
PLOT_FIGSIZE=(15, 6)
def show_runs(rs: dict, d, example_idx, run_idx, plot=True, printout=False, arr_to_plot=ARR_TO_PLOT, replaceplot=False):
    res = []
    if plot:
        plotname = os.path.join(IMG_SAVE_PATH, f'{d}_run_{run_idx}.png')
        if replaceplot or not os.path.exists(plotname):
            # print(f'Making plot for {plotname}')
            color = get_algo_color(d)
            # Plot run means as a thinner line on same axes
            plt.figure(figsize=PLOT_FIGSIZE)
            plt.title(f'Evolution of {d} at run {example_idx:>3}')
            if 'islands' in rs[d]:
                # print(d, example_idx)
                for islid in rs[d]['islands'][example_idx]:
                    if islid != 9:
                        # Only plot best island, to reduce clutter
                        continue
                    isl = rs[d]['islands'][example_idx][islid]
                    y_vals = [x[0] for x in isl['avg_arrs']]
                    x_vals = [x[1] if x[1] else 0 for x in isl['avg_arrs']]
                    x_vals_mn = [x[1] if x[1] else 0 for x in isl['mn_arrs']]
                    x_vals_mx = [x[1] if x[1] else 0 for x in isl['mx_arrs']]
                    plt.plot(y_vals, x_vals, label=f'{d} avg', color=color, linewidth=1.5)
                    plt.fill_between(y_vals, x_vals_mn, x_vals_mx, color=color, alpha=0.15)
                    break
                y_vals = [x[0] for x in rs[d]['avg_arrs'][example_idx]]
                x_vals = [x[1] if x[1] else 0 for x in rs[d]['avg_arrs'][example_idx]]
                x_vals_mn = [x[1] if x[1] else 0 for x in rs[d]['mn_arrs'][example_idx]]
                x_vals_mx = [x[1] if x[1] else 0 for x in rs[d]['mx_arrs'][example_idx]]
                plt.plot(y_vals, x_vals, label=f'{d} avg', color='black', linewidth=1.5)
                plt.fill_between(y_vals, x_vals_mn, x_vals_mx, color='black', alpha=0.15)
                best_ind =  sorted(rs[d]['mx_arrs'][example_idx], key=lambda x: x[1] if x[1] is not None else -10.0, reverse=True)[0]
                plt.scatter(best_ind[0], best_ind[1], s=200, marker='*', color='green')
            elif 'species' in rs[d]:
                FILTER_SPECIES_AGE = 10
                shown_species = list(filter(lambda x: len(rs[d]['species'][example_idx][x]['avg_arrs']) >= FILTER_SPECIES_AGE, rs[d]['species'][example_idx]))
                # print(len(rs[d]['species'][example_idx]))
                # print(len(shown_species))
                for i, isl_name in enumerate(shown_species):
                    if len(rs[d]['species'][example_idx][isl_name]['avg_arrs']) < FILTER_SPECIES_AGE:
                        continue
                    isl = rs[d]['species'][example_idx][isl_name]
                    y_vals = [x[0] for x in isl['avg_arrs']]
                    x_vals = [x[1] if x[1] else 0 for x in isl['avg_arrs']]
                    x_vals_mn = [x[1] if x[1] else 0 for x in isl['mn_arrs']]
                    x_vals_mx = [x[1] if x[1] else 0 for x in isl['mx_arrs']]
                    plt.plot(y_vals, x_vals, label=f'{d} avg', color=color, linewidth=1.5)
                    # plt.fill_between(y_vals, x_vals_mn, x_vals_mx, color=color, alpha=0.15)
                y_vals = [x[0] for x in rs[d]['avg_arrs'][example_idx]]
                x_vals = [x[1] if x[1] else 0 for x in rs[d]['avg_arrs'][example_idx]]
                x_vals_mn = [x[1] if x[1] else 0 for x in rs[d]['mn_arrs'][example_idx]]
                x_vals_mx = [x[1] if x[1] else 0 for x in rs[d]['mx_arrs'][example_idx]]
                plt.plot(y_vals, x_vals, label=f'{d} avg', color='black', linewidth=1.5)
                plt.fill_between(y_vals, x_vals_mn, x_vals_mx, color='black', alpha=0.15)
                best_ind =  sorted(rs[d]['mx_arrs'][example_idx], key=lambda x: x[1] if x[1] is not None else -10.0, reverse=True)[0]
                plt.scatter(best_ind[0], best_ind[1], s=200, marker='*', color='green')
            else:
                # Do one plot for it
                # print(d, plotname)
                y_vals = [x[0] for x in rs[d]['avg_arrs'][example_idx]]
                x_vals = [x[1] if x[1] else 0 for x in rs[d]['avg_arrs'][example_idx]]
                x_vals_mn = [x[1] if x[1] else 0 for x in rs[d]['mn_arrs'][example_idx]]
                x_vals_mx = [x[1] if x[1] else 0 for x in rs[d]['mx_arrs'][example_idx]]
                plt.plot(y_vals, x_vals, label=f'{d} avg', color=color, linewidth=1.5)
                plt.fill_between(y_vals, x_vals_mn, x_vals_mx, color=color, alpha=0.15)
                best_ind =  sorted(rs[d]['mx_arrs'][example_idx], key=lambda x: x[1] if x[1] is not None else -10.0, reverse=True)[0]
                plt.scatter(best_ind[0], best_ind[1], s=200, marker='*', color='green')
            match rs[d]['params'].get('evalfn', '3'):
                case '5':
                    plt.ylim(994, 1000)
                case '4':
                    plt.ylim(0, 500)
                case '3':
                    plt.ylim(0, 800)
            plt.xlim(0, 100_000)
            plt.tight_layout(pad=0.2)
            plt.savefig(plotname)
            plt.close()
    # actual_idx = rs[d]['run_idx']
    # with open(os.path.join(get_experiments_dir(), d, f"hof_{actual_idx}.txt"), 'r') as f:
    #     content = f.read()
    #     m = re.findall(HOF_SCORE, content)
    #     print(m, d, actual_idx)
    #     if len(m) > 0:
    #         best_val_hof = float(m[0])
    #     else:
    #         print("[Warning] Empty hof file? For ", example_idx, d)
    #         best_val_hof = -1
    best_val = max(map(lambda x: x[1] if x[1] else 0, rs[d][arr_to_plot][example_idx]))
    if 'islands' in rs[d]:
        islbests = []
        for isl in rs[d]['islands'][example_idx]:
            islbests += list(map(lambda x: x[1] if x[1] else 0, rs[d]['islands'][example_idx][isl][arr_to_plot]))
        best_val = max(best_val, max(islbests))
    # if f"{best_val:.3f}" != f"{best_val_hof:.3f}":
    #     print(f"[Warning] Best mismatch between hof ({best_val_hof:.6f}) and my parsed best ({best_val:.6f}) For ", example_idx, d)
    res.append((d, max(best_val, best_val), rs[d], example_idx))
    if printout:
        print(f" run {example_idx:>2} ".center(90, '='))
        print(f"{'Rank':>4}  {'Name':<50} {'Score':<10}")
        print('-' * 90)
        for idx, r in enumerate(res):
            print(f"{idx+1:>4}. {r[0]:<50} {r[1]:10.5f}")
    return res

def run_ths(run_th, runs, title='', numworkers=20):
    datas = []
    if numworkers == 1:
        for i in tqdm.trange(runs, desc=title + '_main_thread'):
            datas.append(run_th(i))
        return datas
    with concurrent.futures.ThreadPoolExecutor(max_workers=numworkers) as executor:
        future_fns = {executor.submit(run_th, i): i for i in range(runs)}
        for future in tqdm.tqdm(concurrent.futures.as_completed(future_fns), total=len(future_fns), desc=title):
            url = future_fns[future]
            try:
                data = future.result()
                datas.append(data)
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))
            else:
                # print('%r finished' % (url))
                pass
    return datas

def make_gif(images, gif_name):
    if os.path.exists(gif_name):
        return
    frames = [Image.open(image) for image in images]
    frame_one = frames[0]
    frame_one.save(gif_name, format="GIF", append_images=frames, save_all=True, duration=150, loop=0)
    del frames

def make_gif_th(th_idx):
    d = list(rs.keys())[th_idx]
    make_gif([os.path.join(IMG_SAVE_PATH, f'{d}_run_{idx}.png') for idx in get_finished_runs(d)], os.path.join(GIF_SAVE_PATH, f'{d}_anim.gif'))


def print_clasament(names, latex):
    print('=' * 120)
    print(f' Global clasament of {ARR_TO_PLOT} '.center(120, '='))
    print('=' * 120)
    print(f'|{"idx":>3}.|{"std":<10}|{"mean":<10}|{"median":<10}|{"max":<10}|{"overtime":<10}|{"name":<10}|{"comment":<10}|')
    print('|----' + ('|' + '-' * 10) * 7 + '|')
    if len(names) == 0:
        print('No such runs')
        return

    names_sorted = list(names.keys())
    names = {n: names[n] for n in names_sorted} # Ensure different evalfns are not listed together
    names_sorted.sort(key=lambda x: np.mean(names[x]['runs']), reverse=True)
    comments = json.load(open(os.path.join(get_disertatie_root(), 'algo_comments.json'), 'r'))

    best_max = [(n, np.max(names[n]['runs'])) for n in names_sorted]
    best_max.sort(key=lambda x: x[1], reverse=True)
    best_max = best_max[0][0]
    best_mean = [(n, np.mean(names[n]['runs'])) for n in names_sorted]
    best_mean.sort(key=lambda x: x[1], reverse=True)
    best_mean = best_mean[0][0]
    best_median = [(n, np.median(names[n]['runs'])) for n in names_sorted]
    best_median.sort(key=lambda x: x[1], reverse=True)
    best_median = best_median[0][0]

    for idx, n in enumerate(names_sorted):
        mean = f'{np.mean(names[n]['runs']):10.5f}'
        if n == best_mean:
            mean = f'**{mean.strip()}**' if not latex else '\\textbf{' + mean.strip() + '}'
        median = f'{np.median(names[n]['runs']):10.5f}'
        if n == best_median:
            median = f'**{median.strip()}**' if not latex else '\\textbf{' + median.strip() + '}'
        maxx = f'{np.max(names[n]['runs']):10.5f}'
        if n == best_max:
            maxx = f'**{maxx.strip()}**' if not latex else '\\textbf{' + maxx.strip() + '}'
        comment = comments[n] if n in comments else ''
        runs_time_exceeded = len(list(filter(lambda x: x['nonevalTime'] is not None and x['nonevalTime'] > 3600, names[n]['meta'])))
        if n in BASELINES:
            namm = f'***{n} - baseline***' if not latex else '\\textbf{\\textit{' + n + '}}'
        else:
            namm = n
        if latex:
            print(
                f'{idx+1:>3}.'
                + f'&{np.std(names[n]['runs']):10.5f}&{mean}&{median}&{maxx}'
                + f'&({runs_time_exceeded}/{len(names[n]['runs'])})&\\seqsplit{"{"}{namm.replace('_', '\\_')}{"}"}\\\\ \\hline')
        else:
            print(
                f'|{idx+1:>3}.'
                + f'|{np.std(names[n]['runs']):10.5f}|{mean}|{median}|{maxx}'
                + f'|`({runs_time_exceeded}/{len(names[n]['runs'])})`|{namm}|{comment}|')

FIGSIZE=(25,25)
if __name__ == '__main__':
    sc = get_best_genotypes_over_all_runs()
    print(len(sc))
    for s in list(filter(lambda x: x[0] == '3', sc))[-1:]:
        print(s[:5])
        print()
        print(s[5])
    parsedargs = parseArgs()
    if parsedargs.silent:
        print = lambda *x, **kw: x
    if parsedargs.redo:
        os.system(f'rm {DATA_FILE}')
    os.system(f'rm {STATS_FILE}')
    if not os.path.exists(STATS_FILE):
        if not os.path.exists(DATA_FILE):
            print('Parsing results...')
            rs, modified = parse_data()
            pickle.dump(rs, open(DATA_FILE, 'wb'))
        else:
            print('Loading results...')
            rs = pickle.load(open(DATA_FILE, 'rb'))
            rs, modified = parse_data(rs)
            if modified:
                pickle.dump(rs, open(DATA_FILE, 'wb'))
        print('Results finished loading/parsing...')

        ress = []
        for d in tqdm.tqdm(list(rs.keys()), position=0, desc="Experiments"):
            finished_runs = get_finished_runs(d)
            for i, idxxx in enumerate(finished_runs):
                ress += show_runs(rs, d, i, idxxx, arr_to_plot=ARR_TO_PLOT)
        ress.sort(key=lambda x: x[1], reverse=True)
        run_ths(make_gif_th, len(rs.keys()), title='Making gifs...')
        print('Making clasament...')
        global_clasament = []
        for f in ress:
            i = f[3]
            # for f in r:
            global_clasament.append({
                'runname': f[0],
                'fitness': f[1],
                'runidx': f[2]['run_idx'],
                'generations': f[2]['generations'][i],
                'nonevalTime': f[2]['nonevalTime'][i],
                'invalid_genos': f[2]['invalid_genos'][i],
                'totalevals': f[2]['totalevals'][i],
                'evalTime': f[2]['evalTime'][i],
            })
        print('Sorting clasament...')
        global_clasament.sort(key=lambda x: x['fitness'], reverse=True)

        if SHOW_CLASAMENT:
            print()
            print()
            print()
            print('=' * 90)
            print(' Global Ranking '.center(90, '='))
            print('=' * 90)
            print(f"{'Rank':>4}. {'Name':<50} {'Score':<10} | {'Run idx':>2}")
            print("-" * 100)
            for idx, r in enumerate(global_clasament):
                print(f"{idx+1:>4}. {r['fitness']:<50} {r['runname']:10.5f} | {r['runidx']:>2}")

        # ress.sort(key=lambda r: max([np.mean(f) for f in r]))
        # print(ress[0])
        # for d in rs:
        #     rs[d]['mean_arr']

        print('Making stats file...')
        names = get_algo_dict(global_clasament)
        with open(STATS_FILE, 'w', encoding='UTF8') as f:
            a = json.dumps(names)
            a = re.sub(r'"([a-zA-Z0-9_\-]*)": {"params"', '\n\t"\\1": {\n\t\t"params"', a)
            a = re.sub(r', "meta": ', ',\n\t\t"meta": ', a)
            a = re.sub(r', "runs": ', ',\n\t\t"runs": ', a)
            f.write(a)
    else:
        with open(STATS_FILE, 'r', encoding='UTF8') as f:
            names = json.load(f)

    # ## This is useless and doesn't tell me much.
    # plot_rank_gaussians(global_clasament)
    # plt.show()
    # violins(global_clasament)
    # plt.tight_layout(pad=0.2)
    # # plt.show()
    # plt.savefig(BASE_PATH + 'Run_results_violin.png')
    print(' Evalfn4 '.center(130, '*'))
    print_clasament({n: names[n] for n in names.keys() if 'evalfn4' in n}, parsedargs.latex)
    print(' Evalfn5 '.center(130, '*'))
    print_clasament({n: names[n] for n in names.keys() if 'evalfn5' in n}, parsedargs.latex)
    print(' Evalfn3 '.center(130, '*'))
    names = {n: names[n] for n in names.keys() if 'evalfn5' not in n and 'evalfn4' not in n}
    # print_clasament({n: names[n] for n in names.keys() if 'evalfn5' not in n and 'evalfn4' not in n})
    print_clasament(names, parsedargs.latex)

    ordered_names = [] # For T-test
    print(' By median '.center(90, '*'))
    ordered_names += boxplots(names, order_fn=order_fn_median)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by median value')
    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(get_disertatie_root(), f'Run_results_boxplot_{ARR_TO_PLOT}_ordermedian.png'))

    print(' By mean '.center(90, '*'))
    ordered_names += boxplots(names, order_fn=order_fn_mean)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by mean value')
    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(get_disertatie_root(), f'Run_results_boxplot_{ARR_TO_PLOT}_ordermean.png'))

    print(' By max '.center(90, '*'))
    ordered_names += boxplots(names, order_fn=order_fn_max)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by maximum value')
    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(get_disertatie_root(), f'Run_results_boxplot_{ARR_TO_PLOT}_ordermax.png'))

    print(' By min '.center(90, '*'))
    boxplots(names, order_fn=order_fn_min)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by minimum value')
    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(get_disertatie_root(), f'Run_results_boxplot_{ARR_TO_PLOT}_ordermin.png'))

    ordered_names = set(ordered_names)
    # t-test to see if better solutions are statistically significant
    from scipy.stats import ttest_ind
    SIGLVL = 0.05
    for on in ordered_names:
        # Perform two-sample t-test
        t_statistic, p_value = ttest_ind(names[BASELINE]['runs'], names[on]['runs'], equal_var=False)

        # Output the results
        if p_value < SIGLVL:
            print(f"P-value: {p_value:.6f} {on} ({BASELINE})")
            # print(f"t-statistic: {t_statistic}")

    exit()