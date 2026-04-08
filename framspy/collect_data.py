import re, os, sys, json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

PATH = '/home/xwiki/Documents/fac/GECCO_Robot_Body/Disertatie/framspy/experiments/'
HIGHLIGHT = {
    'eaSimpleF1': 'red',
    'adaptMutF0Firstpmut08': 'red',
}
COLORS = ['red','blue','green','black', 'orange','purple','brown', 'magenta']
N_RUNS = 20
MAX_STEPS = 100_001
example_idx = 0
DATA_PATH = '/home/xwiki/Documents/fac/GECCO_Robot_Body/Disertatie/'
DATA_FILE = DATA_PATH + 'parsed_result_data.json'

def running_stat(arr, fn, radius=50):
    return [fn(arr[i-radius:i+radius]) for i in range(len(arr))]

def violins(rk):
    plt.figure(figsize=(10,7))
    names = {}
    for n in rk:
        if n[0] not in names:
            names[n[0]] = []
        names[n[0]].append(n[1])
    ordered_names = list(names.keys())
    ordered_names.sort(key=lambda n: np.median(names[n]), reverse=True)
    json.dump((ordered_names, names), open(DATA_PATH + 'd.txt', 'w'))
    for idx, n in enumerate(ordered_names):
        plt.scatter([idx+1] * 20, names[n], color=COLORS[idx % len(COLORS)], label=n)
    vp = plt.violinplot([names[n] for n in ordered_names], showmeans=True, showmedians=True)
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

def parse_data():
    rs = {}
    for idx, d in enumerate(sorted(os.listdir(PATH))):
        mx_arrs = []
        mn_arrs = []
        avg_arrs = []
        for i in range(N_RUNS):
            mx_arr = []
            mn_arr = []
            avg_arr = []
            with open(os.path.join(PATH, d, f'results_{i}.stdout'), 'r') as f:
                print(d, i)
                # First line tells us the arguments the run had.
                argvalues = f.readline()
                argvalues = argvalues[len('Argument values: '):]
                arggs = re.findall('([^=]+)=([^, ]+),? ?', argvalues)
                args = {a[0]: a[1] for a in arggs}
                for l in f:
                    rgx = r'([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s+'
                    m = re.match(f'^{rgx}{rgx}{rgx}{rgx}{rgx}{rgx}{rgx}{rgx}$', l)
                    if m:
                        gen, nevals, avg, stdev, mn, mx, totalevals, nonevalTime = m.groups()
                        if int(totalevals) - len(mx_arr) != int(nevals):
                            if m.groups()[1] == args['popsize'] and int(totalevals) - len(mx_arr) == 0:
                                # For convection selection, the global population counts twice for some reason
                                continue
                            print(m.groups(), int(totalevals), len(mx_arr), f"{int(totalevals) - len(mx_arr)} != {int(nevals)}")
                            exit(0)
                        mx_arr += [float(mx)] * (int(totalevals) - len(mx_arr))
                        mn_arr += [float(mn)] * (int(totalevals) - len(mn_arr))
                        avg_arr += [float(avg)] * (int(totalevals) - len(avg_arr))
                        if len(mx_arr) != int(totalevals):
                            print(m.groups(), f"{len(mx_arr)} != {int(totalevals)}")
                            exit(0)
            print(len(mx_arr))
            mx_arr += [mx_arr[-1]] * (MAX_STEPS - len(mx_arr))
            mn_arr += [mn_arr[-1]] * (MAX_STEPS - len(mn_arr))
            avg_arr += [avg_arr[-1]] * (MAX_STEPS - len(avg_arr))
            print(len(mx_arr))
            mx_arrs.append(mx_arr)
            mn_arrs.append(mn_arr)
            avg_arrs.append(avg_arr)
        rs[d] = {
            'mx_arrs': mx_arrs,
            'mn_arrs': mn_arrs,
            'avg_arrs': avg_arrs,
        }
    return rs

def boxplots(rk):
    plt.figure(figsize=(10,7))
    names = {}
    for n in rk:
        if n[0] not in names:
            names[n[0]] = []
        names[n[0]].append(n[1])
    ordered_names = list(names.keys())
    ordered_names.sort(key=lambda n: np.median(names[n]), reverse=True)
    for idx, n in enumerate(ordered_names):
        plt.scatter([idx+1] * 20, names[n], color=COLORS[idx % len(COLORS)], label=n, alpha=0.2)
    plt.boxplot([names[n] for n in ordered_names], showmeans=True)
    plt.xticks(range(1, len(names)+1), names, rotation=45, ha='right')
    ax = plt.gca()
    for tick in ax.get_xticklabels():
        if tick.get_text() in HIGHLIGHT:
            tick.set_color(HIGHLIGHT[tick.get_text()])

if not os.path.exists(DATA_FILE):
    print('Parsing results...')
    rs = parse_data()
    os.mknod(DATA_FILE)
    json.dump(rs, open(DATA_FILE, 'w'))
else:
    print('Loding results...')
    rs = json.load(open(DATA_FILE, 'r'))

def show_runs(rs, example_idx, plot=False):
    y_vals = [i for i in range(MAX_STEPS)]
    if plot:
        plt.figure(figsize=(12,6))
    res = []
    # print(rs.keys())
    # ordered_names = list(rs.keys())
    # ordered_names.sort(key=lambda n: np.mean(rs[n]['avg_arrs'][example_idx]), reverse=True)
    for idx, d in enumerate(rs):
        if plot:
            color = COLORS[idx % len(COLORS)]
            # Plot run means as a thinner line on same axes
            plt.plot(y_vals, rs[d]['avg_arrs'][example_idx], label=f'{d} avg', color=color, linewidth=1.5)
            plt.fill_between(y_vals, rs[d]['mn_arrs'][example_idx], rs[d]['mx_arrs'][example_idx], color=color, alpha=0.06)
        res.append((d, max(rs[d]['avg_arrs'][example_idx])))
    res.sort(key=lambda x: x[1], reverse=True)
    print(f"{'Rank':>4}  {'Name':<50} {'Score':<10}")
    print('-' * 90)
    for idx, r in enumerate(res):
        print(f"{idx+1:>4}. {r[0]:<50} {r[1]:10.5f}")
    print(f" run {example_idx:>2} ".center(90, '='))
    if plot:
        plt.legend()
        plt.show()
    return res

# for example_idx in range(N_RUNS):
#     show_runs(rs, example_idx, plot=True)
# exit(0)
ress = []
for example_idx in range(N_RUNS):
    ress.append(show_runs(rs, example_idx))
global_clasament = []
for i, r in enumerate(ress):
    for f in r:
        global_clasament.append((f[0], f[1], i))
global_clasament.sort(key=lambda x: x[1], reverse=True)

print()
print()
print()
print('=' * 90)
print(' Global Ranking '.center(90, '='))
print('=' * 90)
print(f"{'Rank':>4}. {'Name':<50} {'Score':<10} | {'Run idx':>2}")
print("-" * 100)
for idx, r in enumerate(global_clasament):
    print(f"{idx+1:>4}. {r[0]:<50} {r[1]:10.5f} | {r[2]:>2}")

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

# plot_rank_gaussians(rk)
# plt.show()
violins(global_clasament)
plt.tight_layout(pad=0.2)
# plt.show()
plt.savefig(DATA_PATH + 'Run_results_violin.png')
boxplots(global_clasament)
plt.tight_layout(pad=0.2)
# plt.show()
plt.savefig(DATA_PATH + 'Run_results_boxplot.png')

exit()
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
