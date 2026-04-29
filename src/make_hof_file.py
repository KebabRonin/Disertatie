import re, os
from .config_loader import get_experiments_dir

PATH = get_experiments_dir()

REGEX = re.compile(r"\(np\.float64\(([\d\.]+)\),\)\s+<--\t ([\/:\-\.,=\"\|\@\*\w\n\s]+)")

for dr in os.listdir(PATH):
  print(dr)
  for f in os.listdir(os.path.join(PATH, dr)):
    m = re.match(r'results_(\d+).stdout', f)
    if m:
      runidx, = m.groups()
      if not os.path.exists(os.path.join(PATH, dr, f'hof_{runidx}.txt')):
        outstr = ''
        print(f"Creating {os.path.join(PATH, dr, f'results_{runidx}.stdout')} since it doesn't exist")
        with open(os.path.join(PATH, dr, f), 'r') as fil:
          ff = fil.read()
          ix = ff.find("Saved 'S2ViYWJSb25pblVBSUM=.results' (KebabRoninUAIC)\nBest individuals:")
          if ix > 0:
            ff = ff[ix:]
          ix = ff.find("VMNeuronManager.autoload")
          if ix > 0:
            ff = ff[:ix]
          else:
            print(f"Warning! No Best individuals list in {dr} {runidx}")
            continue
          matches = re.findall(REGEX, ff)
          if len(matches) != 10:
            print(f"Warning! {dr} {runidx} has problem ({len(matches)} matches on the results file)")
            continue
        for mm in matches:
          fitness, geno = mm
          if '\n' in geno:
            geno = geno.strip()
            geno = f"~\n{geno}\n~"
          outstr += f"""org:
genotype:{geno}
COGpath:{fitness}

"""
        print(outstr)
        print('Will write to', os.path.join(PATH, dr, f'hof_{runidx}.txt'))
        input()
        with open(os.path.join(PATH, dr, f'hof_{runidx}.txt'), 'w') as fil:
          fil.write(outstr)


print('Done with everything')