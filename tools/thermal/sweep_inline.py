"""CFD cases for the in-line layout of the x8 / x16 cards (drives side by side in the card plane,
air along the card past each drive in turn). Fan operating points from analytic.py (92x38 server fan)."""
import json
import os
import sys

import foamcase

CASES = [  # (drives, gap mm, CFM, mesh)
    (2, 5, 22, "fine"), (2, 3, 13, "fine"), (2, 5, 12, "coarse"), (4, 5, 21, "coarse"),
    (4, 5, 30, "coarse"), (4, 5, 40, "coarse"), (2, 5, 30, "coarse"),
]
COARSE = dict(dx=1.5, dy=5 / 6, dz=2.5, iters=1200)


def main(root):
    out = []
    for n, g, c, mesh in CASES:
        case = os.path.join(root, f"inline_n{n}_g{g}_q{c}" + ("_coarse" if mesh == "coarse" else ""))
        if not os.path.exists(os.path.join(case, "results.json")):
            foamcase.build(case, n, g, c, 25.0, layout="inline", **(COARSE if mesh == "coarse" else {}))
            foamcase.run(case, 4)
            foamcase.results(case)
        r = json.load(open(os.path.join(case, "results.json")))
        out.append(r)
        print(n, g, c, mesh, [round(d["T_mean"], 1) for d in r["drives_T"]], round(r["dp_Pa"], 1), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
