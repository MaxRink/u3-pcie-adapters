"""Run the CFD sweep used in docs/thermal (sequential; ~5 min per case on 4 cores)."""
import json
import os
import sys

import foamcase

CASES = [  # (drives, gap mm, CFM): bracket the fan operating points from analytic.py
    (2, 5, 15), (2, 5, 30), (2, 3, 24), (4, 5, 32), (4, 5, 51),
]
MESH = dict(dx=1.5, dy=5 / 6, dz=2.5, iters=1200)   # sweep mesh; the 2-drive 21 CFM baseline uses the fine default


def main(root):
    os.makedirs(root, exist_ok=True)
    allres = []
    for n, g, c in CASES:
        case = os.path.join(root, f"n{n}_g{g}_q{c}")
        res_path = os.path.join(case, "results.json")
        if not os.path.exists(res_path):
            foamcase.build(case, n, g, c, 25.0, **MESH)
            foamcase.run(case, 4)
            foamcase.results(case)
        r = json.load(open(res_path))
        allres.append(r)
        print(n, g, c, [round(d["T_mean"], 1) for d in r["drives_T"]], round(r["dp_Pa"], 1), flush=True)
    json.dump(allres, open(os.path.join(root, "cfd_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
