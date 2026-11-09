"""3D render of a CFD case: drive surface temperature + air streamlines coloured by temperature.

Needs `foamToVTK -latestTime -fields '(T U p_rgh)'` run in the case first (run() in foamcase.py
does not do it; render() below runs it if VTK/ is missing).

Usage: xvfb-run -a python3 render_cfd.py <case_dir> <out.png>
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
import pyvista as pv

import foamcase as fc


def load(case):
    if not glob.glob(os.path.join(case, "VTK", "*", "internal.vtu")):
        subprocess.run(["bash", "-c", f"source {fc.FOAM_ENV} >/dev/null 2>&1; foamToVTK -latestTime -fields '(T U p_rgh)'"],
                       cwd=case, check=True, stdout=subprocess.DEVNULL)
    d = sorted(glob.glob(os.path.join(case, "VTK", "*_*/")))[-1]
    vol = pv.read(os.path.join(d, "internal.vtu")).scale(1000, inplace=False)
    drives = pv.read(os.path.join(d, "boundary", "drives.vtp")).scale(1000, inplace=False)
    card = pv.read(os.path.join(d, "boundary", "card.vtp")).scale(1000, inplace=False)
    shroud = pv.read(os.path.join(d, "boundary", "shroud.vtp")).scale(1000, inplace=False)
    for m in (vol, drives):
        if "T" in m.point_data:
            m.point_data["T_C"] = m.point_data["T"] - 273.15
        if "T" in m.cell_data:
            m.cell_data["T_C"] = m.cell_data["T"] - 273.15
    return vol, drives, card, shroud


def render(case, out, size=(1800, 1200)):
    meta = json.load(open(os.path.join(case, "results.json")))
    vol, drives, card, shroud = load(case)
    vol = vol.cell_data_to_point_data()
    drives = drives.cell_data_to_point_data()
    X, W, Z = meta["dims_mm"]
    rng = np.random.default_rng(1)
    seeds = pv.PolyData(np.c_[np.full(170, 2.0), rng.uniform(0.5, W - 0.5, 170), rng.uniform(2, Z - 2, 170)])
    sl = vol.streamlines_from_source(seeds, vectors="U", max_length=400, integration_direction="forward",
                                     initial_step_length=0.5, max_steps=4000)
    tmax = max(d["T_mean"] for d in meta["drives_T"])
    clim = (meta["T_in"], max(tmax + 10, meta["T_in"] + 20))
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("#f4f4f2")
    p.add_mesh(drives, scalars="T_C", cmap="turbo", clim=clim, smooth_shading=True,
               scalar_bar_args=dict(title="temperature (°C)", vertical=True, position_x=0.88, position_y=0.2,
                                    height=0.6, color="#222222", title_font_size=16, label_font_size=13))
    p.add_mesh(sl.tube(radius=0.22), scalars="T_C", cmap="turbo", clim=clim, show_scalar_bar=False, opacity=0.9)
    p.add_mesh(card, color="#1d3b2a", opacity=0.85)
    p.add_mesh(shroud.extract_feature_edges(), color="#555555", line_width=1.5)
    p.add_mesh(shroud, color="#c8c8c8", opacity=0.08)
    p.add_text(f"{meta['drives']} drives x {meta['power_W']:.0f} W, {meta['gap_mm']:.0f} mm gaps, {meta['cfm']:.0f} CFM, "
               f"{meta['T_in']:.0f} °C inlet  |  drive case (mean): "
               + ", ".join(f"{d['T_mean']:.0f} °C" for d in meta["drives_T"]),
               position="upper_left", font_size=11, color="#222222")
    c = np.array([X / 2, W / 2, Z / 2])
    p.camera_position = [tuple(c + np.array([-1.0, -1.25, 0.9]) * 230), tuple(c), (0, 0, 1)]
    p.screenshot(out)
    p.close()


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
