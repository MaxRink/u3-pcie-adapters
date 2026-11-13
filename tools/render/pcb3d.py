"""Build a textured 3D scene of a KiCad board (board + parts) as pyvista meshes.

Frame: X right, Y up (= -KiCad Y), Z up; the board top surface is Z = 0, origin at the board
bounding-box centre. Copper/mask/silk are baked into textures from the real layer geometry, so
the render shows the actual routing; parts use KiCad library STEP models where available and
simplified models (procedural.py) otherwise.
"""
import json
import os
import subprocess
import tempfile

import numpy as np
import pyvista as pv
import trimesh
from PIL import Image, ImageDraw
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

import procedural
import stepmesh

HERE = os.path.dirname(os.path.abspath(__file__))
MODELDIRS = [os.path.join(HERE, "models3d"), "/usr/share/kicad/3dmodels"]

THEMES = {
    "black": dict(mask=(18, 18, 20), mask_cu=(40, 40, 44), silk=(235, 235, 235), cu=(214, 172, 86), fr4=(150, 128, 80)),
    "green": dict(mask=(14, 82, 40), mask_cu=(40, 120, 60), silk=(240, 240, 240), cu=(214, 172, 86), fr4=(150, 128, 80)),
    "blue": dict(mask=(20, 50, 120), mask_cu=(45, 85, 160), silk=(240, 240, 240), cu=(214, 172, 86), fr4=(150, 128, 80)),
}


def dump(pcb_path):
    """Run dump_board.py with KiCad's python and return the parsed JSON."""
    out = tempfile.mktemp(suffix=".json")
    subprocess.run(["/usr/bin/python3", os.path.join(HERE, "dump_board.py"), pcb_path, out], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.load(open(out))
    os.unlink(out)
    return d


class Board:
    def __init__(self, data, theme="black", ppmm=24):
        self.d = data
        self.t = data["thickness"]
        x0, y0, x1, y1 = data["bbox"]
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.cx, self.cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.theme = THEMES[theme]
        self.ppmm = ppmm

    # ---- coordinates
    def to3d(self, kx, ky):
        return kx - self.cx, -(ky - self.cy)

    # ---- textures
    def _raster(self, name):
        W = int((self.x1 - self.x0) * self.ppmm) + 1
        H = int((self.y1 - self.y0) * self.ppmm) + 1
        im = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(im)
        for poly in self.d["layers"].get(name, []):
            pts = [((x - self.x0) * self.ppmm, (y - self.y0) * self.ppmm) for x, y in poly["outer"]]
            if len(pts) >= 3:
                dr.polygon(pts, fill=255)
            for h in poly["holes"]:
                hp = [((x - self.x0) * self.ppmm, (y - self.y0) * self.ppmm) for x, y in h]
                if len(hp) >= 3:
                    dr.polygon(hp, fill=0)
        return np.asarray(im) > 127

    def texture(self, side):
        cu, mask, silk = (self._raster(f"{side}.{n}") for n in ("Cu", "Mask", "SilkS"))
        th = self.theme
        img = np.zeros(cu.shape + (3,), np.uint8)
        img[:] = th["mask"]
        img[cu & ~mask] = th["mask_cu"]
        img[mask & ~cu] = th["fr4"]
        img[mask & cu] = th["cu"]
        img[silk & ~mask] = th["silk"]
        # drill holes (dark) so vias read correctly
        pim = Image.fromarray(img)
        dr = ImageDraw.Draw(pim)
        for h in self.d["holes"]:
            r = min(h["dx"], h["dy"]) / 2 * self.ppmm
            px, py = (h["x"] - self.x0) * self.ppmm, (h["y"] - self.y0) * self.ppmm
            ex = (abs(h["dx"] - h["dy"]) / 2) * self.ppmm
            ang = np.radians(h.get("rot", 0))
            vx, vy = (ex, 0) if h["dx"] >= h["dy"] else (0, ex)
            vx, vy = vx * np.cos(ang) + vy * np.sin(ang), -vx * np.sin(ang) + vy * np.cos(ang)
            for s in np.linspace(-1, 1, 9):
                dr.ellipse([px + s * vx - r, py + s * vy - r, px + s * vx + r, py + s * vy + r], fill=(8, 8, 8))
        return np.asarray(pim)

    # ---- geometry
    def outline_polygon(self, min_hole=1.5):
        polys = []
        for o in self.d["outline"]:
            polys.append(Polygon([self.to3d(*p) for p in o["outer"]], [[self.to3d(*p) for p in h] for h in o["holes"]]))
        shape = unary_union(polys)
        cut = []
        for h in self.d["holes"]:
            if min(h["dx"], h["dy"]) >= min_hole:
                x, y = self.to3d(h["x"], h["y"])
                r = min(h["dx"], h["dy"]) / 2
                ex = abs(h["dx"] - h["dy"]) / 2
                ang = np.radians(h.get("rot", 0))
                dx, dy = (ex, 0) if h["dx"] >= h["dy"] else (0, ex)
                dx, dy = dx * np.cos(ang) - dy * np.sin(ang), dx * np.sin(ang) + dy * np.cos(ang)
                from shapely.geometry import LineString
                cut.append(LineString([(x - dx, y - dy), (x + dx, y + dy)]).buffer(r, 24) if ex > 0.01 else Point(x, y).buffer(r, 24))
        if cut:
            shape = shape.difference(unary_union(cut))
        return shape

    def board_meshes(self):
        shape = self.outline_polygon()
        geoms = list(shape.geoms) if hasattr(shape, "geoms") else [shape]
        out = []
        tex = {s: pv.Texture(self.texture(s)) for s in ("F", "B")}
        for g in geoms:
            tm = trimesh.creation.extrude_polygon(g, self.t)
            tm.apply_translation((0, 0, -self.t))
            m = pv.wrap(tm)
            n = m.compute_normals(cell_normals=True, point_normals=False)["Normals"]
            for side, sel, z in (("F", n[:, 2] > 0.9, 0.0), ("B", n[:, 2] < -0.9, -self.t)):
                sub = m.extract_cells(np.where(sel)[0]).extract_surface(algorithm=None)
                p = sub.points
                u = (p[:, 0] + self.cx - self.x0) / (self.x1 - self.x0)
                v = 1 - (-(p[:, 1]) + self.cy - self.y0) / (self.y1 - self.y0)
                sub.active_texture_coordinates = np.c_[u, v].astype(np.float32)
                out.append(dict(mesh=sub, texture=tex[side], kind="board"))
            sides = m.extract_cells(np.where(np.abs(n[:, 2]) <= 0.9)[0]).extract_surface(algorithm=None)
            out.append(dict(mesh=sides, color=(0.62, 0.55, 0.36), kind="board"))
        return out

    # ---- parts
    def _model_meshes(self, fp):
        """Return [(mesh, color)] in KiCad 3D-model frame for a footprint, plus model transform."""
        res = []
        for m in fp["models"]:
            if not m["show"]:
                continue
            rel = m["file"].split("3DMODEL_DIR}/")[-1]
            base = os.path.splitext(rel)[0]
            path = None
            for d in MODELDIRS:
                for ext in (".step", ".stp", ".STEP"):
                    c = os.path.join(d, base + ext)
                    if os.path.exists(c) and os.path.getsize(c) > 3000:
                        path = c
                        break
                if path:
                    break
            if path:
                res.append((stepmesh.load_step(path), m))
        if res:
            return res
        gen = procedural.lookup(fp["fpid"])
        if gen is None:
            if fp["fpid"].startswith(("MountingHole", "Connector_PCBEdge")) or not fp["fab"]:
                return []
            fab = fp["fab"]
            if fp["back"]:
                fab = [fab[0], -fab[3], fab[2], -fab[1]]
            parts = procedural.box_from_fab(fab)
        else:
            parts = gen()
        meshes = self._tess(parts)
        ident = dict(offset=[0, 0, 0], rot=[0, 0, 0], scale=[1, 1, 1])
        return [(meshes, ident)]

    def part_meshes(self, skip=()):
        out = []
        for fp in self.d["footprints"]:
            if fp["ref"] in skip:
                continue
            for meshes, m in self._model_meshes(fp):
                T = self.placement(fp, m)
                for mesh, col in meshes:
                    mm = mesh.transform(T, inplace=False)
                    out.append(dict(mesh=mm, color=col, kind="part", ref=fp["ref"]))
        return out

    def placement(self, fp, m):
        def R(axis, deg):
            a = np.radians(deg)
            c, s = np.cos(a), np.sin(a)
            M = np.eye(4)
            i, j = {"x": (1, 2), "y": (2, 0), "z": (0, 1)}[axis]
            M[i, i], M[i, j], M[j, i], M[j, j] = c, -s, s, c
            return M

        def Tr(x, y, z):
            M = np.eye(4)
            M[:3, 3] = (x, y, z)
            return M

        x, y = self.to3d(fp["x"], fp["y"])
        z = -self.t if fp["back"] else 0.0
        M = Tr(x, y, z) @ R("z", fp["rot"])
        if fp["back"]:
            M = M @ R("y", 180) @ R("z", 180)
        o = m["offset"]
        M = M @ Tr(*o) @ R("z", -m["rot"][2]) @ R("y", -m["rot"][1]) @ R("x", -m["rot"][0])
        S = np.diag(list(m["scale"]) + [1.0])
        return M @ S

    @staticmethod
    def _tess(parts):
        out = []
        for wp, col in parts:
            shp = wp.val() if hasattr(wp, "val") else wp
            vs, fs = shp.tessellate(0.02, 0.3)
            pts = np.array([v.toTuple() for v in vs])
            faces = np.hstack([np.full((len(fs), 1), 3), np.array(fs)]).ravel()
            out.append((pv.PolyData(pts, faces), col))
        return out

    def drive_meshes(self, mating_y=-11.75, plug_z=3.8):
        """A 2.5-inch 15 mm drive plugged into every right-angle U.3 receptacle."""
        out = []
        ident = dict(offset=[0, 0, 0], rot=[0, 0, 0], scale=[1, 1, 1])
        drive = self._tess(procedural.drive_25())
        for fp in self.d["footprints"]:
            if "SFF-8639_U3_RA" not in fp["fpid"]:
                continue
            T = self.placement(fp, ident)
            T = T @ np.array([[1, 0, 0, 0], [0, 1, 0, mating_y], [0, 0, 1, plug_z], [0, 0, 0, 1]], float)
            for mesh, col in drive:
                out.append(dict(mesh=mesh.transform(T, inplace=False), color=col, kind="drive", ref=fp["ref"]))
        return out

    def scene(self, skip=(), drives=False):
        items = self.board_meshes() + self.part_meshes(skip)
        return items + (self.drive_meshes() if drives else [])
