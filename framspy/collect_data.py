import re, os, sys, json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import pickle, argparse
from PIL import Image
import concurrent.futures, tqdm
import matplotlib
matplotlib.use('agg')
# /\/\/\ Non-interactive plt

ARR_TO_PLOT = 'mx_arrs'

HIGHLIGHT = {
    'eaSimpleF1': 'red',
    'AdaptMutF0pmut08': 'red',
}
COLORS = ['red','blue','green','black', 'orange','purple','brown', 'magenta']
N_RUNS = 20
MAX_STEPS = 100_001
example_idx = 0
DATA_PATH = '/home/xwiki/Documents/fac/GECCO_Robot_Body/Disertatie/'
PATH = DATA_PATH + 'framspy/experiments/'
SHOW_CLASAMENT = False
IMG_SAVE_PATH = DATA_PATH + 'framspy/runplots/images/'
GIF_SAVE_PATH = DATA_PATH + 'framspy/runplots/gifs/'
DATA_FILE = DATA_PATH + 'parsed_result_data.pkl'
STATS_FILE = DATA_PATH + 'algo_run_dict.json'

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
    file_name = PATH + name + '/results_0.stdout'
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
            'run_start': os.stat(PATH + name['runname'] + f'/results_{fn}.stdout').st_mtime,
            'run_end': os.stat(PATH + name['runname'] + f'/results_{fn}.stdout').st_ctime,
            'generations': name['generations'],
            'nonevalTime': name['nonevalTime'],
            'totalevals': name['totalevals'],
            'evalTime': name['evalTime'],
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
    files = os.listdir(os.path.join(PATH, runname))
    finished_runs = [i for i in range(N_RUNS) if f'hof_{i}.txt' in files or f'hof_{i}_is_missing.txt' in files]
    return finished_runs


rgx = r'([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?|nan)'
sp = r'\s+'
GEN_REGEX = re.compile(f'^([0-9]+){sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}?{sp}?$')
GEN_REGEX_SPECIES = re.compile(f'^([0-9]+)\\.([0-9]+){sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}{sp}{rgx}?{sp}?$')
def parse_data(rs=None):
    if rs is None:
        rs = {}
    for idx, d in enumerate(sorted(os.listdir(PATH))):
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
            with open(os.path.join(PATH, d, f'results_{i}.stdout'), 'r') as f:
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
                        if len(mx_arr) != int(totalevals):
                            print("(Miscount totalevals)", d, i, m.groups(), f"{len(mx_arr)} != {int(totalevals)}")
                            exit(0)
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
    plt.figure(figsize=FIGSIZE)
    ordered_names = order_fn(names)
    for idx, n in enumerate(ordered_names):
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
        plotname = IMG_SAVE_PATH + f'{d}_{arr_to_plot}_run_{example_idx}.png'
        if replaceplot or not os.path.exists(plotname):
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
    make_gif([IMG_SAVE_PATH + f'{d}_run_{idx}.png' for idx in get_finished_runs(d)], GIF_SAVE_PATH + f'{d}_anim.gif')

def gaussian(x, mu, sigma):
    return np.exp(-0.5*((x-mu)/sigma)**2) / (sigma*np.sqrt(2*np.pi))

def plot_rank_gaussians(data, sigma_min=0.2, x_pad=0.5, figsize=(8,4)):
    """
    data: sorted list of (name, score, meta); rank = position in list (1..N).
    Repeats allowed. Plots one regular (unstacked) Gaussian per unique name,
    centered at mean rank with sigma = max(std, sigma_min). All curves use same amplitude (pdf).
    """
    # collect ranks
    ranks_by_name = defaultdict(list)
    for i, (name, score, meta) in enumerate(data, start=1):
        ranks_by_name[name].append(i)

    N = len(data)
    x = np.linspace(1 - x_pad, N + x_pad, 1200)
    plt.figure(figsize=figsize)

    for i, (name, ranks) in enumerate(ranks_by_name.items()):
        rs = np.array(ranks, dtype=float)
        mu = rs.mean()
        sigma = max(rs.std(ddof=0), sigma_min)
        y = gaussian(x, mu, sigma)
        plt.plot(x, y, label=f"{name} (μ={mu:.2f}, σ={sigma:.2f})", color=f"C{i%10}")

    plt.xlim(1 - x_pad, N + x_pad)
    plt.xlabel("Rank (1 = top)")
    plt.ylabel("Gaussian PDF")
    plt.xticks(range(1, N+1))
    plt.legend(loc='upper right', fontsize='small', ncol=1)
    plt.title("Rank-distribution Gaussians per name")
    plt.gca().invert_xaxis()  # remove if you prefer rank 1 at left
    plt.tight_layout()
    return plt.gcf(), plt.gca()


FIGSIZE=(25,10)
if __name__ == '__main__':
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
            os.mknod(DATA_FILE)
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
        # for d in rs:
        #     print('Making gif for ', d)
        #     make_gif([IMG_SAVE_PATH + f'{d}_run{idx}.png' for idx in range(N_RUNS)], GIF_SAVE_PATH + f'{d}_anim.gif')
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
    # plt.savefig(DATA_PATH + 'Run_results_violin.png')

    print('=' * 120)
    print(f' Global clasament of {ARR_TO_PLOT} '.center(120, '='))
    print('=' * 120)
    print(f'|{"idx":>3}.|{"std":<15}|{"mean":<15}|{"median":<15}|{"max":<15}|{"name"}|comment|')
    print('|---' * 8 + '|')
    names_sorted = list(names.keys())
    names_sorted.sort(key=lambda x: np.median(names[x]['runs']), reverse=True)
    for idx, n in enumerate(names_sorted):
        print(f'|{idx+1:>3}.|{np.std(names[n]['runs']):10.5f}|{np.mean(names[n]['runs']):10.5f}|{np.median(names[n]['runs']):10.5f}|{np.max(names[n]['runs']):10.5f}|{n}||')

    print(' By median '.center(90, '*'))
    boxplots(names, order_fn=order_fn_median)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by median value')
    # plt.tight_layout(pad=0.2)
    plt.savefig(DATA_PATH + f'Run_results_boxplot_{ARR_TO_PLOT}_ordermedian.png')

    print(' By mean '.center(90, '*'))
    boxplots(names, order_fn=order_fn_mean)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by mean value')
    # plt.tight_layout(pad=0.2)
    plt.savefig(DATA_PATH + f'Run_results_boxplot_{ARR_TO_PLOT}_ordermean.png')

    print(' By max '.center(90, '*'))
    boxplots(names, order_fn=order_fn_max)
    plt.title(f'Experiment {ARR_TO_PLOT} (maximum value over all generations, for each run). Sorted by maximum value')
    # plt.tight_layout(pad=0.2)
    plt.savefig(DATA_PATH + f'Run_results_boxplot_{ARR_TO_PLOT}_ordermax.png')
    exit()
"""
for i in range(0):
    # running max
    # Build x-axis values: per-step median totalevals across runs (robust)
    x_vals = []
    for s in range(max_steps):
        vals = tot_arr[:, s]
        valid = vals[~np.isnan(vals)]
        x_vals.append(float(np.median(valid)) if valid.size else np.nan)
    x_vals = np.array(x_vals)

    # Trim to last valid x
    valid_steps = np.where(~np.isnan(x_vals))[0]
    if valid_steps.size == 0:
        continue
    last_valid = valid_steps[-1] + 1
    x_vals = x_vals[:last_valid]
    avg_arr = avg_arr[:, :last_valid]
    mx_arr  = mx_arr[:, :last_valid]

    # Per-step stats (equal weight per run: mean of available runs at that step)
    step_means = []
    step_stds  = []
    step_mins  = []
    step_maxs  = []
    for s in range(last_valid):
        vals = avg_arr[:, s]
        valid = vals[~np.isnan(vals)]
        if valid.size == 0:
            step_means.append(np.nan); step_stds.append(np.nan); step_mins.append(np.nan); step_maxs.append(np.nan)
        else:
            step_means.append(float(np.mean(valid)))
            step_stds.append(float(np.std(valid)))
            step_mins.append(float(np.min(valid)))
            step_maxs.append(float(np.max(valid)))
    step_means = np.array(step_means); step_stds = np.array(step_stds)
    step_mins  = np.array(step_mins);  step_maxs = np.array(step_maxs)

    # Per-run largest positive jump positions (1-based step AFTER jump) computed on per-run avg curve
    per_run_jump_positions = []
    per_run_jump_values = []
    for r in range(N_RUNS):
        row = avg_arr[r]
        valid_idx = np.where(~np.isnan(row))[0]
        if valid_idx.size < 2:
            per_run_jump_positions.append(np.nan); per_run_jump_values.append(np.nan); continue
        last = valid_idx[-1]
        diffs = np.diff(row[: last+1])
        if diffs.size == 0 or np.all(np.isnan(diffs)):
            per_run_jump_positions.append(np.nan); per_run_jump_values.append(np.nan); continue
        j_idx = int(np.nanargmax(diffs))
        j_val = float(diffs[j_idx])
        per_run_jump_positions.append(j_idx + 2)  # 1-based step after jump
        per_run_jump_values.append(j_val)

    avg_jump_pos = float(np.nanmean(per_run_jump_positions)) if np.any(~np.isnan(per_run_jump_positions)) else None
    median_jump_pos = float(np.nanmedian(per_run_jump_positions)) if np.any(~np.isnan(per_run_jump_positions)) else None

    # Also compute largest jump on mean curve
    mean_max_jump_pos = None; mean_max_jump_val = None
    if len(step_means) >= 2:
        mean_diffs = np.diff(step_means)
        mm_idx = int(np.nanargmax(mean_diffs))
        mean_max_jump_pos = mm_idx + 2  # 1-based step after jump
        mean_max_jump_val = float(mean_diffs[mm_idx])

    # Plot mean average-of-averages (equal run weight) and min/max area
    plt.plot(x_vals, step_means, label=f'{d} mean', color=color, linewidth=2)
    # plt.fill_between(x_vals, step_mins, step_maxs, color=color, alpha=0.12)

    # Mark average per-run jump position (map fractional step to x via interpolation)
    if avg_jump_pos is not None:
        xp = np.interp(avg_jump_pos - 1, np.arange(len(x_vals)), x_vals)  # avg_jump_pos is 1-based
        plt.axvline(x=xp, color=color, linestyle=':', alpha=0.9)
        plt.annotate(f'Avg run jump {avg_jump_pos:.2f}\n(med {median_jump_pos:.2f})',
                     xy=(xp, np.nanmax(step_means)),
                     xytext=(xp, np.nanmax(step_means) + 0.05 * (np.nanmax(step_maxs)-np.nanmin(step_mins))),
                     ha='center', color=color, fontsize=9)

    # Mark mean-curve largest jump (use exact x value)
    if mean_max_jump_pos is not None and mean_max_jump_pos - 1 < len(x_vals):
        xm = x_vals[mean_max_jump_pos - 1]
        plt.axvline(x=xm, color=color, linestyle='--', alpha=0.6)
        plt.annotate(f'Mean jump @ {int(xm)} evals\nΔ={mean_max_jump_val:.3g}',
                     xy=(xm, step_means[mean_max_jump_pos - 1]),
                     xytext=(xm, step_means[mean_max_jump_pos - 1] + 0.05 * (np.nanmax(step_maxs)-np.nanmin(step_mins))),
                     arrowprops=dict(arrowstyle='->', color=color), color=color, fontsize=9, ha='center')

    # --- Running-max of per-step max (mx) averaged across runs (equal run weight) ---
    # Compute per-run running max preserving NaNs after last valid
    runmax_arr = np.full_like(mx_arr, np.nan)
    for r in range(N_RUNS):
        row = mx_arr[r].copy()
        valid_idx = np.where(~np.isnan(row))[0]
        if valid_idx.size == 0:
            continue
        last = valid_idx[-1]
        running = np.maximum.accumulate(row[: last+1])
        runmax_arr[r, : last+1] = running

    runmax_means = []; runmax_mins = []; runmax_maxs = []; runmax_stds = []
    for s in range(last_valid):
        vals = runmax_arr[:, s]
        valid = vals[~np.isnan(vals)]
        if valid.size == 0:
            runmax_means.append(np.nan); runmax_mins.append(np.nan); runmax_maxs.append(np.nan); runmax_stds.append(np.nan)
        else:
            runmax_means.append(float(np.mean(valid)))
            runmax_mins.append(float(np.min(valid)))
            runmax_maxs.append(float(np.max(valid)))
            runmax_stds.append(float(np.std(valid)))
    runmax_means = np.array(runmax_means); runmax_mins = np.array(runmax_mins)
    runmax_maxs = np.array(runmax_maxs); runmax_stds = np.array(runmax_stds)

    # Per-run largest jump positions on runmax curves
    per_run_runmax_jump_positions = []
    for r in range(N_RUNS):
        row = runmax_arr[r]
        valid_idx = np.where(~np.isnan(row))[0]
        if valid_idx.size < 2:
            per_run_runmax_jump_positions.append(np.nan); continue
        last = valid_idx[-1]
        diffs = np.diff(row[: last+1])
        j_idx = int(np.nanargmax(diffs))
        per_run_runmax_jump_positions.append(j_idx + 2)
    avg_runmax_jump_pos = float(np.nanmean(per_run_runmax_jump_positions)) if np.any(~np.isnan(per_run_runmax_jump_positions)) else None


    if avg_runmax_jump_pos is not None:
        xr = np.interp(avg_runmax_jump_pos - 1, np.arange(len(x_vals)), x_vals)
        plt.axvline(x=xr, color=color, linestyle=':', linewidth=1, alpha=0.6)


# Finalize plot
plt.title('Comparison: mean(avg) and mean running-max vs totalevals')
plt.xlabel('Total evaluations')
plt.ylabel('Value')
plt.legend(loc='best', fontsize='small')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
"""