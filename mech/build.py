#!/usr/bin/env python3
"""Build the mechanical models: printable parts (STEP + STL), assembly STEP, BOM/fit manifest.

    python3 mech/build.py                 # everything in boards.json + the backplane cage
    python3 mech/build.py x8 x16p         # selected assemblies
    xvfb-run -a python3 mech/build.py --preview   # also quick pyvista previews (out/<name>/preview_*.png)

Photoreal renders: mech/render.py (Blender Cycles).
"""
import argparse
import re
import collections
import json
import os
import sys
import time

import cadquery as cq
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backplane_cage  # noqa: E402
import boardio  # noqa: E402
import card_shroud  # noqa: E402
import card_shroud_multi  # noqa: E402
import card_shroud_top  # noqa: E402
import parts  # noqa: E402
import procedural  # noqa: E402
import scene  # noqa: E402
import sled  # noqa: E402

OUT = os.path.join(HERE, "out")
BOARDS = json.load(open(os.path.join(HERE, "boards.json")))
CARDS = [n for n, c in BOARDS.items() if c["kind"] == "card"]
# every card gets both shroud styles: "<card>" = end fan, air along the card; "<card>_top" = top-feed, fans behind the drives
# shared fan: "<card>_end<n>" = n cards on one end fan, "<card>_hood<n>" = n cards under one hood with fans on top
MULTI = re.compile(r"^(.+)_(end|hood)(\d)$")
ALL = [n for n in BOARDS if not n.startswith("backplane")] + [n + "_top" for n in CARDS] + ["x8_end3", "x8_hood3", "x16p_hood3"] + ["backplane", "backplane6"]      # plus "parts" for the bought-part STEP library


def kind_of(name):
    if name.startswith("backplane"):
        return "backplane"
    if name.endswith("_top") and name[:-4] not in BOARDS:
        raise KeyError(name)
    if name.endswith("_top"):
        return "card_top"
    m = MULTI.match(name)
    if m:
        return "card_" + m.group(2)
    return BOARDS[name]["kind"]


def title_of(name):
    if name == "backplane":
        return "4-drive top-loading hot-plug cage behind a 120 mm case fan"
    if name == "backplane6":
        return "6-drive top-loading hot-plug cage, 120 mm wide"
    if name.endswith("_top"):
        return BOARDS[name[:-4]]["title"] + ", top-feed shroud"
    m = MULTI.match(name)
    if m:
        return f"{m.group(3)} x " + BOARDS[m.group(1)]["title"] + (", one shared end fan" if m.group(2) == "end" else ", shared hood with fans on top")
    return BOARDS[name]["title"] + (", end-fan shroud" if BOARDS[name]["kind"] == "card" else "")


def color(mat):
    r, g, b = parts.MATERIALS[mat][:3]
    return cq.Color(r, g, b)


def loc_of(M):
    if isinstance(M, cq.Location):
        return M
    from OCP.gp import gp_Trsf
    t = gp_Trsf()
    t.SetValues(*[float(v) for v in np.asarray(M)[:3, :].ravel()])
    return cq.Location(t)


def connector_solids(board):
    """(name, [(wp, material)], Location) for every footprint with a parametric model."""
    out = []
    for fp in board.d["footprints"]:
        gen = procedural.lookup(fp["fpid"])
        if gen is None:
            continue
        mats = [(w, boardio.MAT_OF_RGB.get(tuple(c), "black_plastic")) for w, c in gen()]
        out.append((fp["ref"], mats, loc_of(board.fp_matrix(fp))))
    return out


def assemble(name):
    """Return dict(board, result, items) for one assembly."""
    kind = kind_of(name)
    if kind == "backplane":
        if name in BOARDS:                              # the real board is pushed: take the geometry from it
            return assemble_backplane(name)
        res = (backplane_cage.build(backplane_cage.spec6(), backplane_cage.CageParams(max_width=120.0)) if name == "backplane6"
               else backplane_cage.build(None, backplane_cage.CageParams(max_width=80.0)))   # 80 / 120 mm wide: modules tile at the board pitch
        items = [dict(mesh=scene.tess(res["board_solid"]), material="fr4", group="board", name="pcb")]
        board = None
    elif kind in ("card_end", "card_hood"):
        m = MULTI.match(name)
        board = boardio.load(m.group(1))
        res = card_shroud_multi.build(board, int(m.group(3)), m.group(2))
        one = scene.board_items(board) + scene.printed_items(res["printed"]) + scene.hardware_items(res["hardware"])
        items = []
        for dz in res["replicas"]:
            M = np.eye(4)
            M[2, 3] = dz
            items += scene.transform(one, M)
        items += scene.printed_items(res["shared_printed"]) + scene.hardware_items(res["shared_hardware"])
        return dict(board=board, result=res, items=items)
    else:
        board = boardio.load(name[:-4] if kind == "card_top" else name)
        res = {"sled": sled, "card": card_shroud, "card_top": card_shroud_top}[kind].build(board)
        items = scene.board_items(board)
    items += scene.printed_items(res["printed"]) + scene.hardware_items(res["hardware"])
    return dict(board=board, result=res, items=items)


def assemble_backplane(name):
    """Cage around the real backplane board: receptacles and holes are read from the board file."""
    board = boardio.load(name)
    rec = sorted(board.footprints("SFF-8639_U3_Vertical"), key=lambda f: f["x"])
    pos = [board.xy(f["x"], f["y"]) for f in rec]
    spec = backplane_cage.BackplaneSpec(
        width=board.L, height=board.Hh, thickness=board.t, drive_x=tuple(round(float(x), 3) for x, _ in pos),
        drive_y=round(float(pos[0][1]), 3), holes=tuple((round(float(h[0]), 3), round(float(h[1]), 3)) for h in board.mount_holes()),
        vents=(), slimsas_x=(), power_x=(), placeholder=False)
    res = backplane_cage.build(spec, backplane_cage.CageParams(max_width=round(len(rec) * 20.0, 1)))
    b = res["info"]["board"]
    M = np.eye(4)
    M[0, 0] = M[1, 1] = -1.0                              # board turned 180 deg about z
    M[:3, 3] = (b["origin_corner"][0], b["origin_corner"][1], b["top_z"])
    res["board_solid"] = board.solid().rotate((0, 0, 0), (0, 0, 1), 180).translate(tuple(M[:3, 3]))
    res["hardware"] = [h for h in res["hardware"] if not h[1].startswith("J")]
    res["board_matrix"] = M
    # nothing printed may touch a part on the board
    clash = {}
    for (x0, x1, y0, y1, z0, z1, ref) in board.part_boxes():
        kb = backplane_cage.box(x0, x1, y0, y1, z0, z1).rotate((0, 0, 0), (0, 0, 1), 180).translate(tuple(M[:3, 3]))
        for k, wp in res["printed"].items():
            v = _vol(wp, kb)
            if v > 0.5:
                clash[f"{k} x {ref}"] = round(v, 1)
    res["info"]["board_part_clashes_mm3"] = clash
    items = scene.transform(scene.board_items(board), M) + scene.printed_items(res["printed"]) + scene.hardware_items(res["hardware"])
    return dict(board=board, result=res, items=items)


def shift(loc, dz):
    if isinstance(loc, np.ndarray):
        M = loc.copy()
        M[2, 3] += dz
        return M
    return cq.Location(cq.Vector(0, 0, dz)) * loc


def expand(res):
    """Flatten a shared-fan result (per-card parts + replicas + shared parts) into one plain result."""
    if "replicas" not in res:
        return res, [0.0]
    printed, hw = {}, []
    for k, dz in enumerate(res["replicas"]):
        for nm, wp in res["printed"].items():
            printed[f"card{k + 1}_{nm}"] = wp.translate((0, 0, dz))
        hw += [(d, nm, fn, args, shift(loc, dz)) for (d, nm, fn, args, loc) in res["hardware"]]
    printed.update(res["shared_printed"])
    return dict(printed=printed, hardware=hw + list(res["shared_hardware"]), info=res["info"], board_solid=res["board_solid"]), list(res["replicas"])


def _vol(a, b):
    ba, bb = a.val().BoundingBox(), b.val().BoundingBox()
    if (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin or ba.zmax < bb.zmin or bb.zmax < ba.zmin):
        return 0.0
    i = a.intersect(b)
    return i.val().Volume() if i.vals() else 0.0


def fit_report(res, offsets=(0.0,)):
    """Interference volumes (mm^3) between printed parts and the things they must clear."""
    rep = {}
    solids = [(f"board{k + 1}" if len(offsets) > 1 else "board", res["board_solid"].translate((0, 0, dz))) for k, dz in enumerate(offsets)]
    for (desc, nm, fn, args, loc) in res["hardware"]:
        if nm.startswith(("drive", "fan", "bracket")):
            L = loc_of(loc)
            solids.append((nm, cq.Workplane("XY").add(fn(*args)[0][0].val().located(L))))
    names = list(res["printed"])
    for k, wp in res["printed"].items():
        for nm, s in solids:
            v = _vol(wp, s)
            if v > 0.5:
                rep[f"{k} x {nm}"] = round(v, 1)
        for k2 in names[names.index(k) + 1:]:
            v = _vol(wp, res["printed"][k2])
            if v > 0.5:
                rep[f"{k} x {k2}"] = round(v, 1)
    return rep


def export(name, a, check=True):
    raw, board = a["result"], a["board"]
    res, offsets = expand(raw)
    od = os.path.join(OUT, name)
    os.makedirs(os.path.join(od, "print"), exist_ok=True)
    asm = cq.Assembly(name=name)
    for c, dz in enumerate(offsets):
        sfx = f"_card{c + 1}" if len(offsets) > 1 else ""
        asm.add(res["board_solid"], name="pcb" + sfx, loc=cq.Location(cq.Vector(0, 0, dz)), color=color("fr4"))
        if board is not None:
            base_loc = loc_of(raw["board_matrix"]) if "board_matrix" in raw else cq.Location(cq.Vector(0, 0, dz))
            for ref, mats, L in connector_solids(board):
                for i, (w, m) in enumerate(mats):
                    asm.add(w, name=f"{ref}_{i}{sfx}", loc=base_loc * L, color=color(m))
    unique = dict(raw["printed"], **raw.get("shared_printed", {}))      # print files: every different part once
    for k, wp in unique.items():
        cq.exporters.export(wp, os.path.join(od, "print", f"{name}_{k}.step"))
        cq.exporters.export(wp, os.path.join(od, "print", f"{name}_{k}.stl"), tolerance=0.02, angularTolerance=0.2)
    for k, wp in res["printed"].items():
        asm.add(wp, name=f"print_{k}", color=color("petg"))
    cnt = collections.Counter()
    cache = {}
    for (desc, nm, fn, args, loc) in res["hardware"]:
        cnt[desc] += 1
        key = (nm.split("_")[0] if nm.startswith("scr") or nm == "ins" else nm, tuple(args))
        if key not in cache:
            cache[key] = fn(*args)
        for i, (w, m) in enumerate(cache[key]):
            asm.add(w, name=f"{nm}_{cnt[desc]}_{i}", loc=loc_of(loc), color=color(m))
    step = os.path.join(od, f"{name}_assembly.step")
    asm.save(step)
    import zipfile                                  # 5-13 MB of text each: keep the repo small
    with zipfile.ZipFile(step + ".zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(step, os.path.basename(step))
    os.unlink(step)
    man = dict(name=name, title=title_of(name),
               board=board.src if board is not None else "stand-in from the backplane layout's reported geometry",
               info=res["info"], bom=dict(cnt),
               printed={k: dict(volume_cm3=round(wp.val().Volume() / 1000, 1),
                                size_mm=[round(v, 1) for v in (wp.val().BoundingBox().xlen, wp.val().BoundingBox().ylen, wp.val().BoundingBox().zlen)],
                                petg_g=round(wp.val().Volume() / 1000 * 1.27 * 0.45, 0))
                        for k, wp in unique.items()})
    if len(offsets) > 1:
        man["print_each_per_card"] = list(raw["printed"])
    if check:
        man["interference_mm3"] = fit_report(res, offsets)
    json.dump(man, open(os.path.join(od, "manifest.json"), "w"), indent=1, default=lambda o: float(o) if isinstance(o, np.floating) else str(o))
    return man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=ALL)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--no-check", action="store_true")
    a = ap.parse_args()
    if "parts" in a.names:
        print("parts:", export_parts())
        a.names.remove("parts")
    for name in a.names:
        t0 = time.time()
        asm = assemble(name)
        man = export(name, asm, check=not a.no_check)
        if a.preview:
            import preview
            up = (0, 0, 1) if name == "cage" or name.startswith("backplane") else (0, 1, 0)
            d1, d2 = ((0.6, -0.6, 0.6), (-0.5, -0.7, -0.5)) if name == "cage" else ((0.5, 0.4, 0.8), (-0.5, 0.5, -0.8))
            preview.shot(asm["items"], os.path.join(OUT, name, "preview_front.png"), d1, up=up)
            preview.shot(asm["items"], os.path.join(OUT, name, "preview_xray.png"), d2, up=up, opacity={"printed": 0.35})
        print(f"{name}: {time.time() - t0:.0f} s, printed {list(man['printed'])}, interference {man.get('interference_mm3')}")




def export_parts():
    """STEP files of the bought-part models (drive, connectors, fans, bracket, fasteners)."""
    od = os.path.join(OUT, "parts")
    os.makedirs(od, exist_ok=True)
    lib = {
        "drive_u3_2.5in_15mm_PM1735": (parts.drive_u3, ()),
        "u3_receptacle_ra_PSAS4F213002": (parts.u3_receptacle_ra, ()),
        "u3_receptacle_vertical_PSAS5F313002": (parts.u3_receptacle_vertical, ()),
        "oculink_4i_ra_G14A421211112HR": (parts.oculink_4i_ra, ()),
        "slimsas_8i_ra_U10A474": (parts.slimsas_8i_ra, ()),
        "minifit_jr_2x3_pcie_6pin": (parts.minifit, (3,)),
        "minifit_jr_2x4_pcie_8pin": (parts.minifit, (4,)),
        "pin_header_1x3_with_shunt": (parts.pin_header, (3, 2.54, 1)),
        "fan_92x38": (parts.axial_fan, (92, 38.0)),
        "fan_80x38": (parts.axial_fan, (80, 38.0)),
        "fan_60x25": (parts.axial_fan, (60, 25.0)),
        "pcie_bracket_full_height": (parts.pcie_bracket, ()),
        "screw_m3x10_shcs": (parts.screw_shcs, (3.0, 10.0)),
        "heat_set_insert_m3": (parts.heat_insert_m3, ()),
    }
    for name, (fn, args) in lib.items():
        asm = cq.Assembly(name=name)
        for i, (w, m) in enumerate(fn(*args)):
            asm.add(w, name=f"{name}_{m}_{i}", color=color(m))
        asm.save(os.path.join(od, name + ".step"))
    return list(lib)


if __name__ == "__main__":
    main()
