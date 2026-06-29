import re, os
from .config_loader import get_disertatie_root, get_framsticks_path

PATH = get_disertatie_root()


with open(os.path.join(PATH, 'globalhof.gen')) as f:
  text = f.read()

genos = re.finditer(r"""org:
name:(.*)
genotype:([\n\(\)a-zA-NP-Z:\-\d\*\.,\s\|\[\]@\/\~=\"]*)
COGpath:([\d\.]+)""", text)
import pandas as pd
df = pd.DataFrame(columns=["name", "geno", "score"])
df = df.astype({"name": "string", "geno": "string", "score": "float"})
for g in genos:
  name, geno, score = g.groups()
  geno = geno.strip('~').strip('\n')
  df = pd.concat([df, pd.DataFrame([{'name': name, 'geno': geno, 'score': float(score)}])], ignore_index=True)

import framspy.frams as frams
frams.init(get_framsticks_path())

def getCycleCount(geno):
  model = frams.Model.newFromString(geno)
  edges = model.numjoints._value()
  nodes = model.numparts._value()
  return edges - nodes + 1

df["numparts"] = df["geno"].apply(lambda g: frams.Model.newFromString(g).numparts._value())
df["numjoints"] = df["geno"].apply(lambda g: frams.Model.newFromString(g).numjoints._value())
df["numneurons"] = df["geno"].apply(lambda g: frams.Model.newFromString(g).numneurons._value())
df["numconnections"] = df["geno"].apply(lambda g: frams.Model.newFromString(g).numconnections._value())
df["numcycles"] = df["geno"].apply(lambda g: getCycleCount(g))
df["genolen"] = df["geno"].apply(lambda g: len(g)//100)

print(len(df))
fildf = (df
  .sort_values("score", ascending=False)
  .query("name.str.contains('evalfn3', na=False) or not name.str.contains('evalfn', na=False)")
  .query("name.str.contains('F0', na=False) or name.str.contains('genf0', na=False)") #F0
  # .query("name.str.contains('F1', na=False) or name.str.contains('genf1', na=False)") #F1
  .head(int(1))
  .head(int(len(df) * 0.2))
  # .query("name.str.contains(@s, na=False)", local_dict={"s": "NEAT"})
  # .sort_values("genolen", ascending=False)
  # .assign(has_cycles=df["numcycles"] > 0) \
  #            .groupby("has_cycles") \
  #            .size()
  # .groupby("numcycles").size().reset_index(name="count")
)
print(fildf)
print(fildf.iloc[0].geno)
exit(0)










































import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def plot_stacked_distributions(df, cols, name_col="name", sol_order=("f1","f0"),
                                colors=None, ncols=3, figsize_per_plot=(4,3),
                                max_xticks=6):

    d = df.copy()
    d["sol"] = np.where(d[name_col].str.contains(r"F0|genf0", case=False, regex=True), "f0", "f1")

    nrows = math.ceil(len(cols) / ncols)
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(figsize_per_plot[0]*ncols,
                                      figsize_per_plot[1]*nrows))
    axes = np.array(axes).reshape(-1)

    for i, col in enumerate(cols):
        ax = axes[i]

        ct = d.groupby([col, "sol"]).size().unstack(fill_value=0)
        ct = ct[[c for c in sol_order if c in ct.columns]]

        x_cats = ct.index

        color_list = None
        if colors is not None:
            if isinstance(colors, dict):
                color_list = [colors.get(c) for c in ct.columns]
            else:
                color_list = list(colors)

        # Plot using matplotlib directly so ticks match exactly the bar x positions.
        plot_index = np.arange(len(x_cats))
        bottom = np.zeros(len(x_cats))

        for j, sol in enumerate(ct.columns):
            vals = ct[sol].to_numpy()
            ax.bar(plot_index, vals, bottom=bottom, label=sol, width=1.0,
                   color=(color_list[j] if color_list is not None else None))
            bottom += vals

        ax.set_xlim(-0.5, len(x_cats) - 0.5)
        ax.set_xticks(plot_index)
        if col == "genolen":
          ax.set_xticklabels([str(int(v)*100) for v in x_cats], rotation=0)
        else:
          ax.set_xticklabels([str(v) for v in x_cats], rotation=0)

        # reduce clutter if many categories
        if len(x_cats) > max_xticks:
            step = max(1, int(np.ceil(len(x_cats) / max_xticks)))
            keep = plot_index[::step]
            ax.set_xticks(keep)
            if col == "genolen":
              ax.set_xticklabels([str(x_cats[k] * 100) for k in range(0, len(x_cats), step)], rotation=0)
            else:
              ax.set_xticklabels([str(x_cats[k]) for k in range(0, len(x_cats), step)], rotation=0)

        ax.set_title(f"{col}: f1 + f0")
        ax.set_xlabel(col)
        ax.set_ylabel("count")
        ax.legend()

    for j in range(len(cols), len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plt.show()

# usage
plot_stacked_distributions(
    fildf,
    cols=["numcycles","numparts","numjoints","numconnections","numneurons", "genolen"],
    name_col="name",
    sol_order=("f1","f0"),
    colors={"f1":"#1f77b4","f0":"#ff7f0e"},
    ncols=3
)
