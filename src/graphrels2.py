import json
import numpy as np
# Load 
from .config_loader import get_disertatie_root, load_config, get_experiments_dir
import os, json, sys
BASE_PATH = get_disertatie_root()
STATS_FILE = os.path.join(BASE_PATH, 'algo_run_dict.json')
with open(STATS_FILE, 'r', encoding='UTF8') as f:
  data = json.load(f)
names = list(data.keys())
names.sort()
import numpy as np
names=names
mat = np.zeros(shape=(len(names), len(names)))
for i, namei in enumerate(names):
  for j, namej in enumerate(names):
    if i == j:
      continue
    for k in data[namei]['params']:
      if k in data[namej]['params'] and data[namei]['params'][k] == data[namej]['params'][k]:
        mat[i, j] += 1
np.set_printoptions(threshold=sys.maxsize)
import json
from typing import List, Tuple, Dict, Any, Optional

def adjacency_to_forcegraph_json(
    node_names: List[str],
    edges: List[Tuple[str, str]] = None,
    adj_matrix: Optional[List[List[int]]] = None,
    directed: bool = False,
    allow_self_loops: bool = False
) -> Dict[str, Any]:
    """
    Produces a JSON-serializable dict compatible with many "force graph" inputs:
      {
        "nodes": [{"id": <name>} , ...],
        "links": [{"source": <name>, "target": <name>, "value": <weight?>}, ...]
      }

    Provide either:
      - edges=[(u,v), ...]
      OR
      - adj_matrix=[[0/1/weight,...], ...] (square, len == number of nodes)

    If adj_matrix entries are >0, they become links with value=<entry>.
    If directed=False, matrix is treated as undirected and only i<j links are emitted.
    """
    n = len(node_names)
    name_to_i = {name: i for i, name in enumerate(node_names)}

    nodes = [{"id": name} for name in node_names]
    links = []

    if adj_matrix is not None:
        if len(adj_matrix) != n or any(len(row) != n for row in adj_matrix):
            raise ValueError("adj_matrix must be a square matrix with size == len(node_names).")

        for i in range(n):
            for j in range(n):
                if not allow_self_loops and i == j:
                    continue

                w = adj_matrix[i][j]
                if w is None or w == 0:
                    continue

                if directed:
                    # keep all i->j edges
                    links.append({"source": node_names[i], "target": node_names[j], "value": w})
                else:
                    # undirected: emit each pair once (assuming matrix is symmetric)
                    if i < j:
                        # for non-symmetric matrices, we take the max weight across both directions
                        w_ij = adj_matrix[i][j]
                        w_ji = adj_matrix[j][i]
                        w_eff = max(w_ij, w_ji)
                        if w_eff != 0:
                            links.append({"source": node_names[i], "target": node_names[j], "value": w_eff})

    else:
        if edges is None:
            raise ValueError("Provide either adj_matrix or edges.")
        for u, v in edges:
            if u not in name_to_i or v not in name_to_i:
                raise ValueError(f"Edge contains unknown node(s): ({u}, {v})")
            if (not allow_self_loops) and u == v:
                continue
            links.append({"source": u, "target": v, "value": 1})

    return {"nodes": nodes, "links": links}


def convert_to_json_string(payload: Dict[str, Any], pretty: bool = True) -> str:
    return json.dumps(payload, indent=2 if pretty else None)


mat[mat < 45] = 0

payload = adjacency_to_forcegraph_json(names, adj_matrix=mat, directed=False)
# print(convert_to_json_string(payload, pretty=True))

html = """
<head>
  <style> body { margin: 0; } </style>

  <script src="../force-graph/dist/force-graph.js"></script>
</head>

<body>
  <div id="graph"></div>

  <script>
const data = ____html____;
      const Graph = new ForceGraph(document.getElementById('graph'))
        .graphData(data)
        .nodeId('id')
        .nodeVal('val')
        .nodeLabel('id')
        .nodeAutoColorBy('group')
        .linkSource('source')
        .linkTarget('target')
  </script>
</body>
"""

html = html.replace('____html____', convert_to_json_string(payload, pretty=False))
print(html)