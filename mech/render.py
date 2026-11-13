#!/usr/bin/env python3
"""Photoreal renders of the assemblies with Blender Cycles (bpy as a Python module, CPU).

    python3 mech/render.py                      # all assemblies, all views -> docs/img/mech/
    python3 mech/render.py x8 --views hero xray --samples 64

Views: hero (component side), back (drive side), xray (shroud translucent), exploded,
board (card and drives only, both sides). Boards carry their real copper / mask / silk as textures.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402
import parts  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

S = 0.01          # mm -> Blender units
IMG = os.path.join(os.path.dirname(HERE), "docs", "img", "mech")
UP = {"cage": "z"}    # default: board y is up (card standing in its slot)


def to_world(pts, up):
    p = np.asarray(pts, float)
    if up == "y":
        return np.c_[p[:, 0], -p[:, 2], p[:, 1]] * S
    return p * S


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 16
    sc.render.threads_mode = "AUTO"
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "Medium High Contrast"
    except Exception:
        pass
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.92, 0.93, 0.95, 1)
    bg.inputs[1].default_value = 0.35
    return sc


_mats = {}


def material(name, rgb=None, metallic=0.0, rough=0.5, alpha=1.0, tex=None, printed=False, up="y"):
    key = (name, alpha)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"{name}_{alpha}")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1) if rgb else (0.5, 0.5, 0.5, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if tex is not None:
        im = bpy.data.images.new(name, tex.shape[1], tex.shape[0])
        rgba = np.ones(tex.shape[:2] + (4,), np.float32)
        rgba[..., :3] = (tex[::-1] / 255.0) ** 2.2                # sRGB -> linear, rows bottom-up
        im.pixels.foreach_set(rgba.ravel())
        im.colorspace_settings.name = "Non-Color"
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = im
        nt.links.new(tn.outputs["Color"], b.inputs["Base Color"])
        # gold where the copper is exposed: bright warm pixels become metallic
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(tn.outputs["Color"], sep.inputs[0])
        sub = nt.nodes.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        nt.links.new(sep.outputs[0], sub.inputs[0])
        nt.links.new(sep.outputs[2], sub.inputs[1])
        gt = nt.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.2
        nt.links.new(sub.outputs[0], gt.inputs[0])
        nt.links.new(gt.outputs[0], b.inputs["Metallic"])
        b.inputs["Roughness"].default_value = 0.32
    if printed:                                                    # FDM layer lines
        tc = nt.nodes.new("ShaderNodeTexCoord")
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.wave_type = "BANDS"
        wv.bands_direction = "Y" if up == "y" else "Z"             # print axis: board z = world -Y for cards
        wv.inputs["Scale"].default_value = 1.0 / (0.2 * S) / 6.2832 * 3.14159
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.12
        bump.inputs["Distance"].default_value = 0.0005
        nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
        nt.links.new(wv.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        b.inputs["Roughness"].default_value = 0.15
    _mats[key] = m
    return m


def add_mesh(it, up, offset=(0, 0, 0), alpha=1.0):
    m = it["mesh"]
    if not m.n_points:
        return None
    m = m.triangulate() if not m.is_all_triangles else m
    pts = to_world(m.points + np.asarray(offset), up)
    faces = m.faces.reshape(-1, 4)[:, 1:]
    me = bpy.data.meshes.new(it.get("name", "m"))
    me.from_pydata(pts.tolist(), [], faces.tolist())
    if "tex_img" in it:
        uv = np.asarray(m.active_texture_coordinates)
        layer = me.uv_layers.new(name="uv")
        loops = np.zeros(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", loops)
        layer.data.foreach_set("uv", uv[loops].ravel())
        mat = material(it["tex_key"], tex=it["tex_img"])
    else:
        name = it.get("material")
        if name:
            r, g, b, met, ro = parts.MATERIALS[name]
            mat = material(name, (r, g, b), met, ro, alpha=alpha, printed=it.get("group") == "printed", up=up)
        else:
            c = tuple(it.get("color", (0.5, 0.5, 0.5)))
            dark = max(c) < 0.25
            mat = material("c%02x%02x%02x" % tuple(int(255 * v) for v in c), c, 0.0 if dark or it.get("group") == "board" else 0.6, 0.45)
    me.materials.append(mat)
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(ob)
    if it.get("group") != "board":
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        mod = ob.modifiers.new("es", "EDGE_SPLIT")
        mod.split_angle = np.radians(32)
    return ob


def stage(bounds):
    lo, hi = bounds
    c = (lo + hi) / 2
    r = float(np.linalg.norm(hi - lo)) / 2
    bpy.ops.mesh.primitive_plane_add(size=r * 60, location=(c[0], c[1], lo[2] - 0.0005))
    floor = bpy.context.object
    floor.data.materials.append(material("floor", (0.62, 0.63, 0.65), 0.0, 0.6))

    def area(loc, energy, size, col=(1, 1, 1)):
        ld = bpy.data.lights.new("l", "AREA")
        ld.energy = energy * r * r * 0.3
        ld.size = size * r
        ld.color = col
        ob = bpy.data.objects.new("l", ld)
        ob.location = Vector(c) + Vector(loc) * r
        bpy.context.scene.collection.objects.link(ob)
        d = Vector(c) - ob.location
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return c, r, area


def camera(c, r, direction, size, lens=70, zoom=1.0):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.sensor_width = 36
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    d = Vector(direction).normalized()
    fov = 2 * np.arctan(36 / (2 * lens)) * min(1.0, size[1] / size[0] * 1.5)
    dist = r / np.sin(fov / 2) * 1.12 / zoom
    cam.location = Vector(c) + d * dist
    cam.rotation_euler = (Vector(c) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cd.clip_end = dist * 10
    cd.dof.use_dof = False
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = size


def render(items, path, up="y", direction=(0.5, -0.8, 0.45), samples=96, size=(1920, 1280), alpha=None, explode=None, hide=(), zoom=1.0):
    sc = reset()
    _mats.clear()
    pts = []
    for it in items:
        grp, name = it.get("group"), it.get("name", "")
        if grp in hide or any(name.startswith(h) for h in hide):
            continue
        off = (0, 0, 0)
        for k, v in (explode or {}).items():
            if name.startswith(k) or grp == k:
                off = v
                break
        a = 1.0
        for k, v in (alpha or {}).items():
            if name.startswith(k) or grp == k:
                a = v
        ob = add_mesh(it, up, off, a)
        if ob is not None:
            m = it["mesh"]
            pts.append(to_world(np.array(m.bounds).reshape(3, 2).T + np.asarray(off), up))
    pts = np.vstack(pts)
    c, r, area = stage((pts.min(0), pts.max(0)))
    d = np.array(direction, float)
    side = np.cross(d, (0, 0, 1))
    side /= np.linalg.norm(side)
    key = d / np.linalg.norm(d) * 2.2 + side * 1.6 + np.array((0, 0, 2.4))
    area(key, 260, 2.2, (1.0, 0.97, 0.93))
    area(d / np.linalg.norm(d) * 2.0 - side * 2.6 + np.array((0, 0, 1.0)), 110, 3.0, (0.92, 0.95, 1.0))
    area(-d / np.linalg.norm(d) * 2.5 + np.array((0, 0, 2.8)), 160, 2.5)
    camera(c, r, direction, size, zoom=zoom)
    sc.cycles.samples = samples
    sc.render.filepath = path
    sc.render.image_settings.file_format = "PNG"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    return path


# view name -> kwargs; directions are in the Blender frame (z up; for cards the component side faces -y)
CARD_EXPLODE = {"cover": (0, 0, 55), "scr_drv": (0, 0, 80), "scr_clamp": (0, 0, 80), "scr_corner": (0, 0, 80), "scr_brk": (0, 0, 25),
                "body": (0, 0, -55), "ins": (0, 0, -55), "slot_filler": (0, 45, -20), "fan_adapter": (45, 0, 0), "scr_adp": (70, 0, 0),
                "fan": (95, 0, 0), "scr_fan": (125, 0, 0), "drive": (0, 0, -18)}
VIEWS = {
    "card": {
        "hero": dict(direction=(0.55, -0.75, 0.38)),
        "back": dict(direction=(-0.5, 0.8, 0.4)),
        "xray": dict(direction=(-0.45, 0.8, 0.42), alpha={"printed": 0.28}),
        "exploded": dict(direction=(0.5, -0.7, 0.5), explode=CARD_EXPLODE),
        "board_front": dict(direction=(0.35, -0.85, 0.35), hide=("printed", "hardware")),
        "board_back": dict(direction=(-0.35, 0.85, 0.35), hide=("printed", "hardware")),
    },
    "sled": {
        "hero": dict(direction=(0.6, -0.65, 0.5)),
        "xray": dict(direction=(0.6, -0.65, 0.5), alpha={"printed": 0.28}),
        "exploded": dict(direction=(0.6, -0.65, 0.5), explode={"lid": (0, 0, 40), "scr_lid": (0, 0, 60), "fan_adapter": (0, 40, 0), "scr_adp": (0, 40, 0),
                                                              "fan": (0, 75, 0), "scr_fan": (0, 100, 0), "drive": (0, 0, 18), "scr_drv": (0, 0, -25)}),
        "board": dict(direction=(0.5, -0.7, 0.55), hide=("printed", "hardware")),
    },
    "backplane": {
        "hero": dict(direction=(0.65, -0.6, 0.45)),
        "back": dict(direction=(-0.6, 0.65, 0.4)),
        "xray": dict(direction=(0.65, -0.6, 0.45), alpha={"printed": 0.28}),
        "exploded": dict(direction=(0.65, -0.6, 0.5), explode={"fan_plate": (0, 0, 45), "scr_plate": (0, 0, 45), "fan": (0, 0, 80), "scr_fan": (0, 0, 110),
                                                              "drive": (0, 0, 0), "pcb": (0, 0, -30), "J": (0, 0, -30), "scr_bp": (0, 0, -50)}),
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=build.ALL)
    ap.add_argument("--views", nargs="*")
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--size", type=int, nargs=2, default=(1920, 1280))
    ap.add_argument("--out", default=IMG)
    a = ap.parse_args()
    for name in a.names:
        kind = "backplane" if name == "backplane" else build.BOARDS[name]["kind"]
        asm = build.assemble(name)
        up = UP.get(name, "y")
        if name == "backplane":
            up = "y"
        for v, kw in VIEWS[kind].items():
            if a.views and v not in a.views:
                continue
            p = render(asm["items"], os.path.join(a.out, f"{name}_{v}.png"), up=up, samples=a.samples, size=tuple(a.size), **kw)
            print(p, flush=True)


if __name__ == "__main__":
    main()
