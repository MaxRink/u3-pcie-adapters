"""Render helpers: put scene items into a pyvista plotter and save standard views.

CLI:  xvfb-run -a python3 tools/render/render.py <board.kicad_pcb> <out_dir> [--theme black] [--drive]
"""
import argparse
import os
import sys

import numpy as np
import pyvista as pv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcb3d  # noqa: E402

BG = "#f4f4f2"


def plotter(size=(1800, 1200)):
    p = pv.Plotter(off_screen=True, window_size=size, lighting="none")
    p.set_background(BG)
    p.add_light(pv.Light(position=(1, -1, 2), light_type="camera light", intensity=0.55))
    p.add_light(pv.Light(position=(-200, 300, 500), focal_point=(0, 0, 0), intensity=0.55, light_type="scene light"))
    p.add_light(pv.Light(position=(300, -200, -400), focal_point=(0, 0, 0), intensity=0.25, light_type="scene light"))
    p.add_light(pv.Light(position=(0, 0, 0), light_type="headlight", intensity=0.25))
    try:
        p.enable_anti_aliasing("ssaa")
    except Exception:
        pass
    return p


def add(p, items, opacity=1.0):
    for it in items:
        kw = dict(smooth_shading=False, specular=it.get("specular", 0.25), specular_power=20, ambient=0.18,
                  diffuse=0.85, opacity=it.get("opacity", opacity))
        if "texture" in it:
            p.add_mesh(it["mesh"], texture=it["texture"], **kw)
        else:
            p.add_mesh(it["mesh"], color=it["color"], **kw)


def view(p, items, direction, up=(0, 0, 1), zoom=1.0, parallel=False):
    pts = np.vstack([it["mesh"].points for it in items if it["mesh"].n_points])
    c = (pts.min(0) + pts.max(0)) / 2
    r = np.linalg.norm(pts.max(0) - pts.min(0))
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    p.camera_position = [tuple(c + d * r * 2.2), tuple(c), up]
    p.camera.view_angle = 24
    if parallel:
        p.enable_parallel_projection()
        p.camera.parallel_scale = r * 0.38 / zoom
    else:
        p.camera.zoom(zoom)


VIEWS = {
    "iso_top": dict(direction=(-0.55, -0.9, 0.85)),
    "iso_top_back": dict(direction=(0.6, 0.85, 0.8)),
    "iso_bottom": dict(direction=(-0.5, -0.9, -0.8)),
    "top": dict(direction=(0, 0, 1), up=(0, 1, 0), parallel=True),
    "bottom": dict(direction=(0, 0, -1), up=(0, 1, 0), parallel=True),
}


def render_views(items, out_dir, prefix, views=VIEWS, size=(1800, 1200)):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, v in views.items():
        p = plotter(size)
        add(p, items)
        view(p, items, **v)
        path = os.path.join(out_dir, f"{prefix}_{name}.png")
        p.screenshot(path)
        p.close()
        paths.append(path)
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pcb")
    ap.add_argument("out")
    ap.add_argument("--prefix")
    ap.add_argument("--theme", default="black")
    ap.add_argument("--drives", action="store_true", help="also render with 2.5in drives plugged in")
    a = ap.parse_args()
    b = pcb3d.Board(pcb3d.dump(a.pcb), theme=a.theme)
    prefix = a.prefix or os.path.splitext(os.path.basename(a.pcb))[0]
    for pth in render_views(b.scene(), a.out, prefix):
        print(pth)
    if a.drives:
        v = {k: VIEWS[k] for k in ("iso_top", "iso_top_back", "iso_bottom")}
        for pth in render_views(b.scene(drives=True), a.out, prefix + "_drive", views=v):
            print(pth)


if __name__ == "__main__":
    main()
