"""Read a KiCad board for the mechanical model.

Frame used everywhere in mech/ ("board frame"): origin at the lower-left corner of the board
outline as seen from the component side, x right, y up, z = 0 on the top (F) surface, the board
occupies z in [-t, 0]. For the slot cards this puts x = 0 at the bracket-end edge and y = 0 at
the bottom of the gold fingers.

The board itself is not edited here. Boards are read from the git ref listed in boards.json, so
the mechanical model follows the board threads' branches and is regenerated when they change.
"""
import json
import os
import subprocess
import sys

import cadquery as cq
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "render"))
import parts  # noqa: E402
import pcb3d  # noqa: E402
import procedural  # noqa: E402

KICAD_PY = os.environ.get("KICAD_PYTHON", "/usr/bin/python3.12" if os.path.exists("/usr/bin/python3.12") else "/usr/bin/python3")
CACHE = os.path.join(HERE, ".cache")
SEAT = 10.05      # drive end face from the receptacle peg line (Amphenol PSAS4F213002 drawing)
PLUG_H = 3.5      # plug centreline above the receptacle's mounting surface (approx, see README)


def _rgb(mat):
    return tuple(parts.MATERIALS[mat][:3])


MAT_OF_RGB = {tuple(v[:3]): k for k, v in parts.MATERIALS.items()}


def _as_proc(fn, *a, **k):
    return lambda: [(w, _rgb(m)) for w, m in fn(*a, **k)]


# better connector models for the renderer's registry (same frames as the footprints)
procedural.REGISTRY.update({
    "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD": _as_proc(parts.u3_receptacle_ra),
    "Amphenol_G14A421211112HR_OCuLink_4i_RA_SMD": _as_proc(parts.oculink_4i_ra),
    "Molex_Mini-Fit_Jr_5569-06A2_2x03_P4.20mm_Horizontal": _as_proc(parts.minifit, 3),
    "Molex_Mini-Fit_Jr_5569-08A2_2x04_P4.20mm_Horizontal": _as_proc(parts.minifit, 4),
    "PinHeader_1x03_P2.54mm_Vertical_SMD": _as_proc(parts.pin_header, 3, shunt_at=1),
    "Amphenol_PSAS5F313002_SFF-8639_U3_Vertical_SMD": _as_proc(parts.u3_receptacle_vertical),
    "Amphenol_U10A474_SlimSAS_8i_SFF-8654_RA_SMD": _as_proc(parts.slimsas_8i_ra),
})


def fetch(ref, path):
    """Return a local copy of `path` at git `ref` ("WORKTREE" = the checked-out file)."""
    if ref == "WORKTREE":
        return os.path.join(ROOT, path)
    os.makedirs(CACHE, exist_ok=True)
    sha = subprocess.check_output(["git", "-C", ROOT, "rev-parse", f"{ref}:{path}"], text=True).strip()
    out = os.path.join(CACHE, f"{sha[:12]}_{os.path.basename(path)}")
    if not os.path.exists(out):
        with open(out, "wb") as fh:
            fh.write(subprocess.check_output(["git", "-C", ROOT, "show", f"{ref}:{path}"]))
    return out


def dump(pcb_path):
    out = pcb_path + ".json"
    if not os.path.exists(out):
        subprocess.run([KICAD_PY, os.path.join(ROOT, "tools", "render", "dump_board.py"), pcb_path, out],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.load(open(out))


class MechBoard:
    def __init__(self, name, ref, path, theme="black"):
        self.name = name
        self.src = dict(ref=ref, path=path)
        if ref != "WORKTREE":
            self.src["commit"] = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", ref], text=True).strip()
        self.d = dump(fetch(ref, path))
        self.b = pcb3d.Board(self.d, theme=theme)
        xs = [p[0] for o in self.d["outline"] for p in o["outer"]]
        ys = [p[1] for o in self.d["outline"] for p in o["outer"]]
        self.X0, self.Y0 = min(xs), max(ys)
        self.L, self.Hh = max(xs) - min(xs), max(ys) - min(ys)
        self.t = self.d["thickness"]
        self.shift = np.array([self.b.cx - self.X0, self.Y0 - self.b.cy, 0.0])

    # ---- frames
    def xy(self, kx, ky):
        return kx - self.X0, self.Y0 - ky

    def fp_matrix(self, fp):
        ident = dict(offset=[0, 0, 0], rot=[0, 0, 0], scale=[1, 1, 1])
        T = self.b.placement(fp, ident)
        T[:3, 3] += self.shift
        return T

    # ---- geometry queries
    def footprints(self, key):
        return [f for f in self.d["footprints"] if key in f["fpid"]]

    def drives(self):
        """Seated drive placements: list of dict(ref, T (4x4, drive frame -> board frame), xc,
        y_face, y_top, z_bottom, z_top, back)."""
        out = []
        for fp in sorted(self.footprints("SFF-8639_U3_RA"), key=lambda f: f["x"]):
            T = self.fp_matrix(fp) @ _tr(0, -SEAT, PLUG_H)
            c = T @ np.array([0, 0, 0, 1.0])
            far = T @ np.array([0, -parts.DRIVE["L"], 0, 1.0])
            zb = (T @ np.array([0, 0, -parts.DRIVE["plug_z"], 1.0]))[2]
            zt = (T @ np.array([0, 0, parts.DRIVE["H"] - parts.DRIVE["plug_z"], 1.0]))[2]
            out.append(dict(ref=fp["ref"], T=T, xc=c[0], y_face=c[1], y_top=far[1], z_bottom=zb, z_top=zt,
                            back=fp["back"], dir=np.sign(far[1] - c[1])))
        return out

    def mount_holes(self, dmin=3.1):
        """Unplated M3 holes and slots: list of (x, y, dx, dy)."""
        out = []
        for h in self.d["holes"]:
            if not h["plated"] and min(h["dx"], h["dy"]) >= dmin:
                x, y = self.xy(h["x"], h["y"])
                out.append((x, y, h["dx"], h["dy"]))
        return sorted(out)

    def outline_points(self):
        return [self.xy(*p) for p in self.d["outline"][0]["outer"]]

    # ---- solids
    def solid(self, holes_min=0.9):
        pts = self.outline_points()
        wp = cq.Workplane("XY").polyline(pts).close().extrude(-self.t)
        for o in self.d["outline"]:
            for h in o["holes"]:
                wp = wp.cut(cq.Workplane("XY").polyline([self.xy(*p) for p in h]).close().extrude(-self.t - 1).translate((0, 0, 0.5)))
        cutters = None
        for h in self.d["holes"]:
            if min(h["dx"], h["dy"]) < holes_min:
                continue
            x, y = self.xy(h["x"], h["y"])
            if abs(h["dx"] - h["dy"]) < 0.01:
                c = cq.Workplane("XY").circle(h["dx"] / 2).extrude(self.t + 1)
            else:
                c = cq.Workplane("XY").slot2D(max(h["dx"], h["dy"]), min(h["dx"], h["dy"]), 0 if h["dx"] > h["dy"] else 90).extrude(self.t + 1)
                c = c.rotate((0, 0, 0), (0, 0, 1), h.get("rot", 0))
            c = c.translate((x, y, -self.t - 0.5))
            cutters = c if cutters is None else cutters.union(c)
        return wp.cut(cutters) if cutters is not None else wp

    # ---- meshes for the renderer (pyvista items in the board frame)
    def items(self, skip=()):
        out = []
        tex = {s: self.b.texture(s) for s in ("F", "B")}
        for it in self.b.board_meshes() + self.b.part_meshes(skip):
            it = dict(it)
            if "texture" in it:                         # keep the raw image for the Blender renderer
                side = "F" if it["mesh"].points[:, 2].mean() > -self.t / 2 else "B"
                it["tex_img"], it["tex_key"] = tex[side], f"{self.name}_{side}"
            it["mesh"] = it["mesh"].translate(self.shift, inplace=False)
            if "color" in it:
                it["material"] = MAT_OF_RGB.get(tuple(it["color"]))
            out.append(it)
        return out

    def part_boxes(self, zmin_h=0.0):
        """Bounding boxes (x0, x1, y0, y1, z0, z1, ref) of every placed part, for keep-outs."""
        out = []
        for it in self.b.part_meshes():
            m = it["mesh"]
            if not m.n_points:
                continue
            b = np.array(m.bounds).reshape(3, 2) + self.shift[:, None]
            out.append((b[0, 0], b[0, 1], b[1, 0], b[1, 1], b[2, 0], b[2, 1], it.get("ref")))
        merged = {}
        for b in out:
            m = merged.get(b[6])
            merged[b[6]] = b if m is None else (min(m[0], b[0]), max(m[1], b[1]), min(m[2], b[2]), max(m[3], b[3]), min(m[4], b[4]), max(m[5], b[5]), b[6])
        return list(merged.values())


def _tr(x, y, z):
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def load(name):
    cfg = json.load(open(os.path.join(HERE, "boards.json")))[name]
    return MechBoard(name, cfg["ref"], cfg["path"])
