"""Fit the analytic model's per-layout heat-transfer correction a * (Re/5000)**b and the
pressure-drop multiplier (analytic.CAL) to the CFD cases, and write cal.json next to analytic.py.

The target is T_iso, the isothermal-case temperature derived from each uniform-flux CFD run (see
foamcase.results). Coarse-mesh cases are included after subtracting the mean coarse-vs-fine
offset of the cases that were run on both meshes.

Usage: python3 calibrate.py <sweep_dir> [<sweep_dir> ...]
"""
import json
import os
import sys

import numpy as np

import analytic


def load(dirs):
    out = []
    for root in dirs:
        for d in sorted(os.listdir(root)):
            p = os.path.join(root, d, "results.json")
            if os.path.exists(p):
                r = json.load(open(p))
                r["name"], r["coarse"] = d, d.endswith("_coarse")
                out.append(r)
    fine = {r["name"]: r for r in out if not r["coarse"]}
    pairs = [(r, fine[r["name"][:-7]]) for r in out if r["coarse"] and r["name"][:-7] in fine]
    bias = float(np.mean([np.mean([d["T_iso"] for d in c["drives_T"]]) - np.mean([d["T_iso"] for d in f["drives_T"]])
                          for c, f in pairs])) if pairs else 0.0
    for r in out:
        r["T_target"] = np.array([d["T_iso"] for d in r["drives_T"]]) - (bias if r["coarse"] else 0.0)
    return out, bias


def predict(r):
    m = analytic.LAYOUTS[r.get("layout", "stack")](r["drives"], r["gap_mm"], r["cfm"] * analytic.CFM)
    return np.array(m["T"]), m["dp"]


def main(dirs):
    cases, bias = load(dirs)
    analytic.CAL.update(turb=1.0, dp=1.0)
    fits = {}
    analytic.CAL["re_range"] = {}
    for layout in ("stack", "inline"):
        res_ = [analytic.LAYOUTS[layout](r["drives"], r["gap_mm"], r["cfm"] * analytic.CFM)["Re"]
                for r in cases if r.get("layout", "stack") == layout]
        analytic.CAL["re_range"][layout] = [round(min(res_)), round(max(res_))]
    analytic.CAL["re_range"]["parallel"] = analytic.CAL["re_range"]["stack"]
    for layout in ("stack", "inline"):
        sub = [r for r in cases if r.get("layout", "stack") == layout]
        best = None
        # in line, the CFD h rises only weakly with flow (b ~ -0.6); only trust the fit inside the CFD range
        for a in np.arange(0.4, 1.61, 0.01):
            for b in np.arange(-1.0, 0.41, 0.02):
                analytic.CAL["h"][layout] = [a, b]
                err = np.concatenate([predict(r)[0] - r["T_target"] for r in sub])
                rms = float(np.sqrt((err ** 2).mean()))
                if best is None or rms < best[0]:
                    best = (rms, round(float(a), 2), round(float(b), 2))
        analytic.CAL["h"][layout] = [best[1], best[2]]
        fits[layout] = dict(rms_T_err_C=round(best[0], 2), n_cases=len(sub))
    # the parallel (cross-flow) layout has no CFD; it is closest to the facing stack's channels
    analytic.CAL["h"]["parallel"] = list(analytic.CAL["h"]["stack"])
    ratios = [r["dp_Pa"] / predict(r)[1] for r in cases if not r["coarse"]]
    analytic.CAL["dp"] = round(float(np.median(ratios)), 2)
    res = dict(h=analytic.CAL["h"], re_range=analytic.CAL["re_range"], dp=analytic.CAL["dp"], fits=fits, coarse_bias_C=round(bias, 2), target="T_iso",
               cases=[dict(case=r["name"],
                           cfd_T=[round(float(x), 1) for x in r["T_target"]],
                           model_T=[round(x, 1) for x in predict(r)[0]],
                           cfd_dp=round(r["dp_Pa"], 1), model_dp=round(predict(r)[1], 1)) for r in cases])
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cal.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
