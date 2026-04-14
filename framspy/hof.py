import re, argparse

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-fn', default=3, help="""Evaluation Function name:
  * 3: distance between COG locations of birth and death.
    -> np.linalg.norm(path[0] - path[-1])
  * 4: run far and have COG high above ground!
    -> np.linalg.norm(path[0] - path[-1]) * np.mean(np.maximum(0, path[:, 2]))
  * 5: z coordinate of the COG should grow linearly from 0 to 1 during lifespan. Returns RMSE as a deviation measure (negated because we are maximizing, and offset to ensure positive outcomes so there is no clash with other optimization code that may assume that negative fitness indicates an invalid genotype).
    -> 1000 - np.linalg.norm(np.linspace(0, 10, len(path), endpoint=True) - path[:, 2]) / np.sqrt(len(path))""")
parsedargs = parser.parse_args()

FLOATREGEX = r'([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)'
REGEX = r'^2026-\d{2}-\d{2} \d{2}:\d{2}\s+KebabRoninUAIC\s+(\d+)\s+(\d+)\s+' \
    + FLOATREGEX + r'\s+'\
    + FLOATREGEX + r'\s+'\
    + FLOATREGEX + r'\s+'
hoff = []

m = re.compile(REGEX)
with open(r'S2ViYWJSb25pblVBSUM=.results', 'r') as f:
  for idx, l in enumerate(f.readlines()):
    ma = m.search(l)
    if ma:
      test_fn_name, eval_count, total_time, noneval_time, best_fitness = ma.groups()
      hoff.append((idx, float(best_fitness)))

hoff.sort(key=lambda x: x[1], reverse=True)

with open(f"global_hof_fn_{parsedargs.fn}.results", "w") as f:
  # Should give the line index of the runs, ordered by max fitness score.
  # Use to import the best genotypes across runs into Framsticks.
  f.writelines([str(h) + '\n' for h in hoff])