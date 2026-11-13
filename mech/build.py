#!/usr/bin/env python3
"""Build the mechanical models: printable parts (STEP + STL), assembly STEP, BOM/fit manifest.

    python3 mech/build.py                 # everything in boards.json + the backplane cage
    python3 mech/build.py x8 x16p         # selected assemblies
    xvfb-run -a python3 mech/build.py --preview   # also quick pyvista previews (out/<name>/preview_*.png)

Photoreal renders: mech/render.py (Blender Cycles).
"""
import argparse
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
import parts  # noqa: E402
import procedural  # noqa: E402
import scene  # noqa: E402
import sled  # noqa: E402

OUT = os.path.join(HERE, "out")
BOARDS = json.load(open(os.path.join(HERE, "boards.json")))
ALL = list(BOARDS) + ["backplane"]      # plus "parts" for the bought-part STEP library


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
    if name == "backplane":
        res = backplane_cage.build()
        items = [dict(mesh=scene.tess(res["board_solid"]), material="fr4", group="board", name="pcb")]
        board = None
    else:
        board = boardio.load(name)
        res = (sled if BOARDS[name]["kind"] == "sled" else card_shroud).build(board)
        items = scene.board_items(board)
    items += scene.printed_items(res["printed"]) + scene.hardware_items(res["hardware"])
    return dict(board=board, result=res, items=items)


def fit_report(res):
    """Interference volumes (mm^3) between printed parts and the things they must clear."""
    rep = {}
    solids = [("board", res["board_solid"])]
    for (desc, nm, fn, args, loc) in res["hardware"]:
        if nm.startswith(("drive", "fan", "bracket")):
            L = loc_of(loc)
            solids.append((nm, cq.Workplane("XY").add(fn(*args)[0][0].val().located(L))))
    names = list(res["printed"])
    for k, wp in res["printed"].items():
        for nm, s in solids:
            v = wp.intersect(s).val().Volume() if wp.intersect(s).vals() else 0.0
            if v > 0.5:
                rep[f"{k} x {nm}"] = round(v, 1)
        for k2 in names[names.index(k) + 1:]:
            i = wp.intersect(res["printed"][k2])
            v = i.val().Volume() if i.vals() else 0.0
            if v > 0.5:
                rep[f"{k} x {k2}"] = round(v, 1)
    return rep


def export(name, a, check=True):
    res, board = a["result"], a["board"]
    od = os.path.join(OUT, name)
    os.makedirs(os.path.join(od, "print"), exist_ok=True)
    asm = cq.Assembly(name=name)
    asm.add(res["board_solid"], name="pcb", color=color("fr4"))
    if board is not None:
        for ref, mats, L in connector_solids(board):
            for i, (w, m) in enumerate(mats):
                asm.add(w, name=f"{ref}_{i}", loc=L, color=color(m))
    for k, wp in res["printed"].items():
        cq.exporters.export(wp, os.path.join(od, "print", f"{name}_{k}.step"))
        cq.exporters.export(wp, os.path.join(od, "print", f"{name}_{k}.stl"), tolerance=0.02, angularTolerance=0.2)
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
    man = dict(name=name, title=BOARDS.get(name, {}).get("title", "4-drive backplane cage (placeholder board)"),
               board=board.src if board is not None else "placeholder (designs/u3-backplane/README.md)",
               info=res["info"], bom=dict(cnt),
               printed={k: dict(volume_cm3=round(wp.val().Volume() / 1000, 1),
                                size_mm=[round(v, 1) for v in (wp.val().BoundingBox().xlen, wp.val().BoundingBox().ylen, wp.val().BoundingBox().zlen)],
                                petg_g=round(wp.val().Volume() / 1000 * 1.27 * 0.45, 0))
                        for k, wp in res["printed"].items()})
    if check:
        man["interference_mm3"] = fit_report(res)
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
            up = (0, 0, 1) if name == "cage" else (0, 1, 0)
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
