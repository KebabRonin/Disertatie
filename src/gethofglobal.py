
from .config_loader import get_disertatie_root, load_config, get_experiments_dir
import sys, os, numpy, re
frams_escape = lambda name: name#f"~\n{name}\n~" if '\n' in name else name
for alg in os.listdir(get_experiments_dir()):
  leaderboard = []
  for run in os.listdir(os.path.join(get_experiments_dir(), alg)):
    m = re.match(r'hof_(\d+).txt', run)
    if m:
      idx, = m.groups()
      with open(os.path.join(get_experiments_dir(), alg, run)) as f:
        text = f.read()
      it = re.finditer(r"""
org:
genotype:([\n\(\)a-zA-NP-Z:\-\d\*\.,\s\|\[\]@\/\~=\"]*)
COGpath:([\d\.]+)""", text)
      for i in it:
        geno, score = i.groups()
        leaderboard.append((float(score), geno))
        break
  leaderboard.sort(key=lambda x: x[0], reverse=True)
  for i, l in enumerate(leaderboard):
    genotype = l[1]
    score = l[0]
    name=f"best-{i:0>2}{alg}"
    name = frams_escape(name)
    genotype = frams_escape(genotype)
    info = '' #frams_escape(info)
    print(f"""
org:
name:{name}
genotype:{genotype}
COGpath:{score}

""")