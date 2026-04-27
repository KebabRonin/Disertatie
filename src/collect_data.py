import re, os, sys, json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import pickle, argparse
from PIL import Image
import concurrent.futures, tqdm
import matplotlib

# Import configuration loader
from .config_loader import get_disertatie_root, load_config, get_experiments_dir

# Remove warnings from console, but disable interactive plots
matplotlib.use('agg')

ARR_TO_PLOT = 'mx_arrs' # 'avg_arrs' #

HIGHLIGHT = {
    'eaSimpleF1': 'red',
    'AdaptMutF0pmut08': 'red',
}
COLORS = ['red','blue','green','black', 'orange','purple','brown', 'magenta']
N_RUNS = 20
MAX_STEPS = 100_001
example_idx = 0

# Load configuration
CONFIG = load_config()
BASE_PATH = get_disertatie_root()
# Should be pointing to the Disertatie folder
EXPERIMENTS_PATH = get_experiments_dir()
SHOW_CLASAMENT = False
IMG_SAVE_PATH = os.path.join(BASE_PATH, 'framspy', 'runplots', 'images')
GIF_SAVE_PATH = os.path.join(BASE_PATH, 'framspy', 'runplots', 'gifs')
DATA_FILE = os.path.join(BASE_PATH, 'parsed_result_data.pkl')
STATS_FILE = os.path.join(BASE_PATH, 'algo_run_dict.json')

def parseArgs():
    parser = argparse.ArgumentParser(description='This script will run multiple experiments in parallel, and save the results.')
    parser.add_argument('-s', '--silent', action='store_true', help='To output or not to output')
    parser.add_argument('--redo', action='store_true', help='To output or not to output')
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

def parse_algo_params(name: str):
    params = {}
    file_name = os.path.join(EXPERIMENTS_PATH, name, 'results_0.stdout')
    with open(file_name, 'r') as f:
        parstr = ''
        currstr = f.readline()
        while not currstr.startswith('Using Framsticks version'):
            parstr += currstr
            currstr = f.readline()
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
    return {'params': parse_algo_params(name['runname']), 'meta': [{
            'run_start': os.stat(os.path.join(EXPERIMENTS_PATH, name['runname'], f'results_{fn}.stdout')).st_mtime,
            'run_end': os.stat(os.path.join(EXPERIMENTS_PATH, name['runname'], f'results_{fn}.stdout')).st_ctime,
            'generations': int(name['generations']),
            'nonevalTime': None if name['nonevalTime'] is None else float(name['nonevalTime']),
            'totalevals': float(name['totalevals']),
            'evalTime': float(name['evalTime']),
        } for fn in range(len(get_finished_runs(name['runname'])))]
    }

def get_algo_dict(rk):
    """
    Get all experiment runs, grouped by algorithm.
    """
    names = {}
    for n in rk:
        if n['runname'] not in names:
            names[n['runname']] = get_algo_params(n)
            names[n['runname']]['runs'] = []
        names[n['runname']]['runs'].append(n['fitness'])
    return names

def get_finished_runs(runname):
    files = os.listdir(os.path.join(EXPERIMENTS_PATH, runname))
    finished_runs = [i for i in range(N_RUNS) if f'hof_{i}.txt' in files or f'hof_{i}_is_missing.txt' in files]
    return finished_runs


rgx = r'([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?|nan)'
sp = r'\s+'

def get_best_genotype_over_all_runs() -> list[list]:
    scoreboard = []
    path = os.path.join(get_disertatie_root(), 'framspy', 'S2ViYWJSb25pblVBSUM=.results')
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
def parse_data(rs=None):
    if rs is None:
        rs = {}
    for idx, d in enumerate(sorted(os.listdir(EXPERIMENTS_PATH))):
        if d in rs:
            continue
        finished_runs = get_finished_runs(d)
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
        nonevalTime_arr = []
        totalevals_arr = []
        evalTime_arr = []
        species_dicts = []
        islands_arrs = []
        for i in finished_runs:
            mx_arr = []
            mn_arr = []
            avg_arr = []
            species_dict = {}
            islands = {}
            with open(os.path.join(EXPERIMENTS_PATH, d, f'results_{i}.stdout'), 'r') as f:
                # First line tells us the arguments the run had.
                argvalues = f.readline()
                argvalues = argvalues[len('Argument values: '):]
                # arggs = re.findall('([^=]+)=([^, ]+),? ?', argvalues)
                args = parse_algo_params(d)
                # args = {a[0]: a[1] for a in arggs}
                if 'popsize' not in args:
                    args['popsize'] = 50
                for l in f:
                    m = re.match(GEN_REGEX, l)
                    if m:
                        gen, nevals, avg, stdev, mn, mx, totalevals, evalTime, nonevalTime = m.groups()
                        if int(totalevals) - len(mx_arr) != int(nevals):
                            if m.groups()[1] == args['popsize'] and int(totalevals) - len(mx_arr) == 0:
                                # For convection selection, the global population counts twice for some reason
                                continue
                            print("(Miscount nevals)", d, i, args['popsize'], m.groups(), int(totalevals), len(mx_arr), f"{int(totalevals) - len(mx_arr)} != {int(nevals)}")
                            exit(0)
                        mx_arr += [float(mx) if mx != 'nan' else -1] * (int(totalevals) - len(mx_arr))
                        mn_arr += [float(mn) if mn != 'nan' else -1] * (int(totalevals) - len(mn_arr))
                        avg_arr += [float(avg) if avg != 'nan' else -1] * (int(totalevals) - len(avg_arr))
                        assert len(mx_arr) == int(totalevals), f"(Miscount totalevals) {d}, {i}, {m.groups()}, {len(mx_arr)} != {int(totalevals)}"
                    # elif re.match(r'^starting island\s+(\d+)', l):
                    #     # We're in convection algorithm, so we should store each island separately.
                    #     island_id, = re.match(r'^starting island\s+(\d+)', l).groups()
                    #     island_id = int(island_id)
                    #     if island_id not in islands:
                    #         islands[island_id] = {
                    #             'mx_arrs': [None] * int(totalevals),
                    #             'mn_arrs': [None] * int(totalevals),
                    #             'avg_arrs': [None] * int(totalevals),
                    #         }
                    #     else:
                    #         islands[island_id]['mx_arrs'] += [islands[island_id]['mx_arrs'][-1]] * (int(totalevals) - len(islands[island_id]['mx_arrs']))
                    #         islands[island_id]['mn_arrs'] += [islands[island_id]['mn_arrs'][-1]] * (int(totalevals) - len(islands[island_id]['mn_arrs']))
                    #         islands[island_id]['avg_arrs'] += [islands[island_id]['avg_arrs'][-1]] * (int(totalevals) - len(islands[island_id]['avg_arrs']))
                    #     islands[island_id]['mx_arrs'] += [mx]# * (int(totalevals) - len(islands[island_id]['mx']))
                    #     islands[island_id]['mn_arrs'] += [mn]# * (int(totalevals) - len(islands[island_id]['mn']))
                    #     islands[island_id]['avg_arrs'] += [avg]
                    # elif re.match(GEN_REGEX_SPECIES, l):
                    #     # We're in speciation algorithm, so we should store each species separately.
                    #     gen, species_id, nevals, avg, stdev, mn, mx, totalevals, evalTime, nonevalTime = re.match(GEN_REGEX_SPECIES, l).groups()
                    #     if species_id not in species_dict:
                    #         species_dict[species_id] = {
                    #             'mx_arrs': [None] * int(totalevals),
                    #             'mn_arrs': [None] * int(totalevals),
                    #             'avg_arrs': [None] * int(totalevals),
                    #         }
                    #     else:
                    #         species_dict[species_id]['mx_arrs'] += [species_dict[species_id]['mx_arrs'][-1]] * (int(totalevals) - len(species_dict[species_id]['mx_arrs']))
                    #         species_dict[species_id]['mn_arrs'] += [species_dict[species_id]['mn_arrs'][-1]] * (int(totalevals) - len(species_dict[species_id]['mn_arrs']))
                    #         species_dict[species_id]['avg_arrs'] += [species_dict[species_id]['avg_arrs'][-1]] * (int(totalevals) - len(species_dict[species_id]['avg_arrs']))
                    #     species_dict[species_id]['mx_arrs'] += [mx]# * (int(totalevals) - len(species_dict[species_id]['mx']))
                    #     species_dict[species_id]['mn_arrs'] += [mn]# * (int(totalevals) - len(species_dict[species_id]['mn']))
                    #     species_dict[species_id]['avg_arrs'] += [avg]# * (int(totalevals) - len(species_dict[species_id]['avg']))
                if 'Lambda' in d:
                    expected_evals = 100_000 - max(int(args['popsize']), int(args['lbda'] if 'lbda' in args else 0))
                else:
                    expected_evals = 100_000 - int(args['popsize'])
                if len(mx_arr) <= expected_evals:
                    if float(nonevalTime) > 3600:
                        print("(Hit time limit)", d, i, f"{float(nonevalTime)} > 3600")
                    else:
                        print("(Stopped too early) ", d, i, f"{len(mx_arr)} <= {expected_evals}")
            mx_arr += [mx_arr[-1]] * (MAX_STEPS - len(mx_arr))
            mn_arr += [mn_arr[-1]] * (MAX_STEPS - len(mn_arr))
            avg_arr += [avg_arr[-1]] * (MAX_STEPS - len(avg_arr))
            gens_arr.append(gen)
            nonevalTime_arr.append(nonevalTime)
            totalevals_arr.append(totalevals)
            evalTime_arr.append(evalTime)
            mx_arrs.append(mx_arr)
            mn_arrs.append(mn_arr)
            avg_arrs.append(avg_arr)
            if len(islands) > 0:
                for s in islands:
                    islands[s]['mx_arrs'] += [islands[s]['mx_arrs'][-1]] * (MAX_STEPS - len(islands[s]['mx_arrs']))
                    islands[s]['mn_arrs'] += [islands[s]['mn_arrs'][-1]] * (MAX_STEPS - len(islands[s]['mn_arrs']))
                    islands[s]['avg_arrs'] += [islands[s]['avg_arrs'][-1]] * (MAX_STEPS - len(islands[s]['avg_arrs']))
                islands_arrs.append(islands)
            if len(species_dict) > 0:
                for s in species_dict:
                    species_dict[s]['mx_arrs'] += [None] * (MAX_STEPS - len(species_dict[s]['mx_arrs']))
                    species_dict[s]['mn_arrs'] += [None] * (MAX_STEPS - len(species_dict[s]['mn_arrs']))
                    species_dict[s]['avg_arrs'] += [None] * (MAX_STEPS - len(species_dict[s]['avg_arrs']))
                species_dicts.append(species_dict)
        rs[d] = {
            'mx_arrs': mx_arrs,
            'mn_arrs': mn_arrs,
            'avg_arrs': avg_arrs,
            'generations': gens_arr,
            'nonevalTime': nonevalTime_arr,
            'totalevals': totalevals_arr,
            'evalTime': evalTime_arr,
        }
        if len(species_dicts) > 0:
            rs[d]['species'] = species_dicts
        if len(islands_arrs) > 0:
            rs[d]['islands'] = islands_arrs
    return rs

def violins(names, order_fn=order_fn_median):
    plt.figure(figsize=FIGSIZE)
    ordered_names = order_fn(names)
    for idx, n in enumerate(ordered_names):
        plt.scatter([idx+1] * 20, names[n]['runs'], color=COLORS[idx % len(COLORS)], label=n)
    vp = plt.violinplot([names[n]['runs'] for n in ordered_names], showmeans=True, showmedians=True)
    for i, body in enumerate(vp['bodies']):
        body.set_facecolor(COLORS[i % len(COLORS)])
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
    plt.figure(figsize=FIGSIZE)
    ordered_names = order_fn(names)
    for idx, n in enumerate(ordered_names):
        if len(names[n]['runs']) < 20:
            HIGHLIGHT[n] = 'blue'
        plt.scatter([idx+1] * len(names[n]['runs']), names[n]['runs'], color=COLORS[idx % len(COLORS)], label=n, alpha=0.2)
    plt.boxplot([names[n]['runs'] for n in ordered_names], showmeans=True)
    plt.xticks(range(1, len(names)+1), ordered_names, rotation=45, ha='right')
    ax = plt.gca()
    for tick in ax.get_xticklabels():
        if tick.get_text() in HIGHLIGHT:
            tick.set_color(HIGHLIGHT[tick.get_text()])
    # t-test to see if better solutions are statistically significant
    from scipy.stats import ttest_ind
    BASELINE = 'AdaptMutF0pmut08'
    SIGLVL = 0.05
    if BASELINE in ordered_names:
        idx_baseline = ordered_names.index(BASELINE)
        print(f"Performing T-test between {BASELINE} and ({idx_baseline}) algorithms")
        for on in ordered_names[:idx_baseline]:
            # Perform two-sample t-test
            t_statistic, p_value = ttest_ind(names[BASELINE]['runs'], names[on]['runs'], equal_var=False)

            # Output the results
            if p_value < SIGLVL:
                print(f" {BASELINE} vs {on} ".center(90, '='))
                print(f"t-statistic: {t_statistic}")
                print(f"P-value: {p_value} ({'significant change' if p_value < SIGLVL else 'insignificant change'} for {SIGLVL} significance level)")

def show_runs(rs: dict, d, example_idx, plot=True, printout=False, arr_to_plot=ARR_TO_PLOT, replaceplot=False):
    y_vals = [i for i in range(MAX_STEPS)]
    res = []
    idx = list(rs.keys()).index(d)
    if plot:
        plotname = os.path.join(IMG_SAVE_PATH, f'{d}_{arr_to_plot}_run_{example_idx}.png')
        if replaceplot or not os.path.exists(plotname):
            print(f'Making plot for {plotname}')
            color = COLORS[idx % len(COLORS)]
            # Plot run means as a thinner line on same axes
            plt.figure(figsize=(12,6))
            plt.title(f'Evolution of {d} at run {example_idx:>3}')
            if 'islands' in rs[d]:
                for isl in rs[d]['islands']:
                    plt.plot(y_vals, isl['avg_arrs'][example_idx], label=f'{d} avg', color=color, linewidth=1.5)
                    plt.fill_between(y_vals, isl['mn_arrs'][example_idx], isl['mx_arrs'][example_idx], color=color, alpha=0.06)
            elif 'species' in rs[d]:
                for isl in rs[d]['species']:
                    plt.plot(y_vals, isl['avg_arrs'][example_idx], label=f'{d} avg', color=color, linewidth=1.5)
                    plt.fill_between(y_vals, isl['mn_arrs'][example_idx], isl['mx_arrs'][example_idx], color=color, alpha=0.06)
            else:
                # Do one plot for it
                plt.plot(y_vals, rs[d]['avg_arrs'][example_idx], label=f'{d} avg', color=color, linewidth=1.5)
                plt.fill_between(y_vals, rs[d]['mn_arrs'][example_idx], rs[d]['mx_arrs'][example_idx], color=color, alpha=0.06)
            plt.ylim(0, 800)
            plt.savefig(plotname)
            plt.close()
    res.append((d, max(rs[d][arr_to_plot][example_idx]), rs[d], example_idx))
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

def make_gif_th(th_idx):
    d = list(rs.keys())[th_idx]
    make_gif([os.path.join(IMG_SAVE_PATH, f'{d}_{ARR_TO_PLOT}_run_{idx}.png') for idx in get_finished_runs(d)], os.path.join(GIF_SAVE_PATH, f'{d}_anim.gif'))

FIGSIZE=(25,10)
if __name__ == '__main__':
    # sc = get_best_genotype_over_all_runs()
    # for s in sc[-3:]:# filter(lambda x: x[0] == '4', sc):
    #     print(s[:5])
    #     print()
    #     print(s[5])
    parsedargs = parseArgs()
    if parsedargs.silent:
        print = lambda *x, **kw: x
    if parsedargs.redo:
        os.system(f'rm {DATA_FILE}')
        os.system(f'rm {STATS_FILE}')
    if not os.path.exists(STATS_FILE):
        if not os.path.exists(DATA_FILE):
            print('Parsing results...')
            rs = parse_data()
            pickle.dump(rs, open(DATA_FILE, 'wb'))
        else:
            print('Loding results...')
            rs = pickle.load(open(DATA_FILE, 'rb'))
            rs = parse_data(rs)
        print('Results finished loading/parsing...')
        ress = []
        for d in rs.keys():
            finished_runs = get_finished_runs(d)
            for i in range(len(finished_runs)):
                ress += show_runs(rs, d, i, arr_to_plot=ARR_TO_PLOT)
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
                'runidx': i,
                'generations': f[2]['generations'][i],
                'nonevalTime': f[2]['nonevalTime'][i],
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

    print('=' * 120)
    print(f' Global clasament of {ARR_TO_PLOT} '.center(120, '='))
    print('=' * 120)
    print(f'|{"idx":>3}.|{"std":<10}|{"mean":<10}|{"median":<10}|{"max":<10}|{"overtime":<10}|{"name":<10}|{"comment":<10}|')
    print('|----' + ('|' + '-' * 10) * 7 + '|')
    names_sorted = list(names.keys())
    names_sorted.sort(key=lambda x: np.median(names[x]['runs']), reverse=True)
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
            mean = f'**{mean}**'
        median = f'{np.median(names[n]['runs']):10.5f}'
        if n == best_median:
            median = f'**{median}**'
        maxx = f'{np.max(names[n]['runs']):10.5f}'
        if n == best_max:
            maxx = f'**{maxx}**'
        comment = comments[n] if n in comments else ''
        runs_time_exceeded = len(list(filter(lambda x: x['nonevalTime'] is not None and x['nonevalTime'] > 3600, names[n]['meta'])))
        print(
            f'|{idx+1:>3}.'
            + f'|{np.std(names[n]['runs']):10.5f}|{mean}|{median}|{maxx}'
            + f'|`({runs_time_exceeded}/{len(names[n]['runs'])})`|{n}|{comment}|')

    print(' By median '.center(90, '*'))
    boxplots(names, order_fn=order_fn_median)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by median value')
    # plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(get_disertatie_root(), f'Run_results_boxplot_{ARR_TO_PLOT}_ordermedian.png'))

    print(' By mean '.center(90, '*'))
    boxplots(names, order_fn=order_fn_mean)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by mean value')
    # plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(get_disertatie_root(), f'Run_results_boxplot_{ARR_TO_PLOT}_ordermean.png'))

    print(' By max '.center(90, '*'))
    boxplots(names, order_fn=order_fn_max)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by maximum value')
    # plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(get_disertatie_root(), f'Run_results_boxplot_{ARR_TO_PLOT}_ordermax.png'))
    exit()