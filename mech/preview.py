"""Fast flat-shaded previews (pyvista) for checking geometry; the real renders come from render.py."""
import os
import sys

import numpy as np
import pyvista as pv

import parts


def shot(items, path, direction=(-0.6, -0.5, 0.7), up=(0, 1, 0), size=(1500, 1000), hide=(), opacity=None, zoom=1.0):
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("#f4f4f2")
    pts = []
    for it in items:
        if it.get("group") in hide or it.get("name") in hide:
            continue
        m = it["mesh"]
        if not m.n_points:
            continue
        pts.append(np.array(m.bounds).reshape(3, 2).T)
        op = (opacity or {}).get(it.get("group"), (opacity or {}).get(it.get("name"), 1.0))
        if "texture" in it:
            p.add_mesh(m, texture=it["texture"], opacity=op)
        else:
            col = parts.MATERIALS[it["material"]][:3] if it.get("material") else it.get("color", (0.5, 0.5, 0.5))
            p.add_mesh(m, color=col, opacity=op, specular=0.2, smooth_shading=False)
    pts = np.vstack(pts)
    c = (pts.min(0) + pts.max(0)) / 2
    r = np.linalg.norm(pts.max(0) - pts.min(0))
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    p.camera_position = [tuple(c + d * r * 1.6), tuple(c), up]
    p.camera.zoom(zoom)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    p.screenshot(path)
    p.close()
