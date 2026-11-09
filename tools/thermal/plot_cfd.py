"""Plots for the CFD sweep: mid-height slices of air temperature and speed, plus a summary chart
comparing CFD with the analytic model.

The mesh is a single structured block with the drive cells removed (subsetMesh keeps cell order),
so cell centres are rebuilt from the block parameters in meta.json instead of running a function
object (broken in the Debian OpenFOAM v1912 build).

Usage: python3 plot_cfd.py <sweep_dir> <out_dir>
"""
import json
import os
import re
import sys

import numpy as np

import analytic
import foamcase as fc


def centres(meta):
    X, W, Z = meta["dims_mm"]
    nx, ny, nz = meta["cells_xyz"]

    def edges(lengths, counts):
        e = [0.0]
        for Ls, n in zip(lengths, counts):
            e += list(e[-1] + np.arange(1, n + 1) * Ls / n)
        return np.array(e)

    ex = edges([fc.UP, fc.L, fc.DOWN], nx)
    ey = np.linspace(0, W, ny + 1)
    ez = edges([fc.H, fc.TOP], nz)
    cx, cy, cz = (ex[1:] + ex[:-1]) / 2, (ey[1:] + ey[:-1]) / 2, (ez[1:] + ez[:-1]) / 2
    Zc, Yc, Xc = np.meshgrid(cz, cy, cx, indexing="ij")
    P = np.c_[Xc.ravel(), Yc.ravel(), Zc.ravel()]
    keep = np.ones(len(P), bool)
    for b in meta["boxes"]:
        keep &= ~((P[:, 0] > b[0]) & (P[:, 0] < b[3]) & (P[:, 1] > b[1]) & (P[:, 1] < b[4]) & (P[:, 2] < b[5]))
    return (cx, cy, cz), keep


def internal(path, vector=False):
    s = open(path).read()
    m = re.search(r"internalField\s+nonuniform\s+List<\w+>\s*(\d+)\s*\(", s)
    n = int(m.group(1))
    body = s[m.end():]
    if vector:
        return np.array(re.findall(r"\(([-\deE.+]+) ([-\deE.+]+) ([-\deE.+]+)\)", body[: n * 60])[:n], float)
    return np.array(body.split(None, n)[:n], float)


def slice_plot(case, out_png, z_mm=50.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    meta = json.load(open(os.path.join(case, "results.json")))
    t = meta["time"]
    (cx, cy, cz), keep = centres(meta)
    T = np.full(keep.size, np.nan)
    T[keep] = internal(os.path.join(case, t, "T")) - 273.15
    U = np.full((keep.size, 3), np.nan)
    U[keep] = internal(os.path.join(case, t, "U"), vector=True)
    shape = (len(cz), len(cy), len(cx))
    k = int(np.argmin(abs(cz - z_mm)))
    Ts = T.reshape(shape)[k]
    Us = np.linalg.norm(U.reshape(shape + (3,))[k], axis=-1)
    fig, axes = plt.subplots(2, 1, figsize=(10, 1.4 + 0.085 * meta["dims_mm"][1] * 2), dpi=150, sharex=True)
    for ax, data, lab, cmap in ((axes[0], Ts, "air temperature (°C)", "inferno"), (axes[1], Us, "air speed (m/s)", "viridis")):
        im = ax.pcolormesh(cx, cy, data, cmap=cmap, shading="auto")
        for i, (b, d) in enumerate(zip(meta["boxes"], meta["drives_T"])):
            ax.add_patch(Rectangle((b[0], b[1]), b[3] - b[0], b[4] - b[1], fc="#9aa0a6", ec="k", lw=0.6))
            ax.text((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, f"drive {i+1}: {d['T_mean']:.0f} °C (max {d['T_max']:.0f})",
                    ha="center", va="center", fontsize=7)
        ax.set_aspect("equal")
        ax.set_ylabel("y (mm)")
        fig.colorbar(im, ax=ax, label=lab, fraction=0.025, pad=0.01)
    axes[1].set_xlabel("x (mm), airflow left to right")
    axes[0].set_title(f"{meta['drives']} drives x {meta['power_W']:.0f} W, {meta['gap_mm']:.0f} mm gaps, "
                      f"{meta['cfm']:.0f} CFM, {meta['T_in']:.0f} °C inlet: slice at {cz[k]:.0f} mm height")
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def summary(results, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=150)
    cfm = np.linspace(8, 60, 120)
    styles = {(2, 5): "#d1495b", (2, 3): "#1f6fb2", (4, 5): "#2a9d5c"}
    for (n, g), col in styles.items():
        ax.plot(cfm, [analytic.stack(n, g, c * analytic.CFM)["Tmax"] for c in cfm], color=col, lw=1.5, ls="--",
                label=f"analytic, {n} drives, {g} mm")
        pts = sorted((r["cfm"], max(d["T_mean"] for d in r["drives_T"]), max(d["T_max"] for d in r["drives_T"]))
                     for r in results if r["drives"] == n and r["gap_mm"] == g)
        if pts:
            x, ym, yx = zip(*pts)
            ax.plot(x, ym, "o-", color=col, lw=2, label=f"CFD mean, {n} drives, {g} mm")
            ax.vlines(x, ym, yx, color=col, lw=1, alpha=0.6)
    ax.axhline(70, color="#444", ls="--", lw=1)
    ax.text(59, 71, "70 °C", ha="right", fontsize=8)
    ax.set_xlabel("airflow through the shroud (CFM)")
    ax.set_ylabel("hottest drive case temperature (°C)")
    ax.set_title("25 W per drive, 35 °C inlet. Bars: CFD hot spot (uniform-flux upper bound)")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def main(sweep, out):
    os.makedirs(out, exist_ok=True)
    results = []
    for d in sorted(os.listdir(sweep)):
        rp = os.path.join(sweep, d, "results.json")
        if os.path.exists(rp):
            r = json.load(open(rp))
            results.append(r)
            slice_plot(os.path.join(sweep, d), os.path.join(out, f"cfd_slice_{d}.png"))
    summary(results, os.path.join(out, "cfd_vs_analytic.png"))
    rows = ["| drives | gap | airflow | inlet speed | drive mean (°C) | drive hot spot (°C) | Δp (Pa) | air out (°C) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in sorted(results, key=lambda r: (r["drives"], r["gap_mm"], r["cfm"])):
        rows.append(f"| {r['drives']} | {r['gap_mm']:.0f} mm | {r['cfm']:.0f} CFM | {r['U_in']:.2f} m/s | "
                    + ", ".join(f"{d['T_mean']:.0f}" for d in r["drives_T"]) + " | "
                    + ", ".join(f"{d['T_max']:.0f}" for d in r["drives_T"])
                    + f" | {r['dp_Pa']:.1f} | {r['T_out_mean']:.1f} |")
    open(os.path.join(out, "cfd_table.md"), "w").write("\n".join(rows) + "\n")
    json.dump(results, open(os.path.join(out, "cfd_results.json"), "w"), indent=1)
    print("\n".join(rows))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
