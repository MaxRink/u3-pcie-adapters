"""Turn boards, printed parts and bought parts into one list of render/export items.

An item is a dict: mesh (pyvista PolyData, board frame, mm), material (name in parts.MATERIALS) or
color, optional texture (board faces), group ("board", "part", "drive", "printed", "hardware"), name.
"""
import functools

import cadquery as cq
import numpy as np
import pyvista as pv

import parts


def tess(wp, tol=0.03, ang=0.25):
    shp = wp.val() if hasattr(wp, "val") else wp
    if hasattr(wp, "vals") and len(wp.vals()) > 1:
        shp = cq.Compound.makeCompound(wp.vals())
    vs, fs = shp.tessellate(tol, ang)
    pts = np.array([v.toTuple() for v in vs])
    faces = np.hstack([np.full((len(fs), 1), 3), np.array(fs)]).ravel()
    return pv.PolyData(pts, faces)


@functools.lru_cache(maxsize=None)
def _part_meshes(fn, args):
    return [(tess(w), m) for w, m in fn(*args)]


def matrix(loc):
    if isinstance(loc, np.ndarray):
        return loc
    T = loc.wrapped.Transformation()
    M = np.eye(4)
    for i in range(3):
        for j in range(4):
            M[i, j] = T.Value(i + 1, j + 1)
    return M


def hardware_items(hw):
    out = []
    for (desc, name, fn, args, loc) in hw:
        M = matrix(loc)
        try:
            meshes = _part_meshes(fn, tuple(args))
        except TypeError:                       # unhashable (lambda with prebuilt solids)
            meshes = [(tess(w), m) for w, m in fn(*args)]
        for mesh, mat in meshes:
            out.append(dict(mesh=mesh.transform(M, inplace=False), material=mat,
                            group="drive" if name.startswith("drive") else "hardware", name=name, desc=desc))
    return out


def printed_items(printed, material="petg"):
    return [dict(mesh=tess(wp, 0.05, 0.2), material=material, group="printed", name=k) for k, wp in printed.items()]


def board_items(board):
    out = []
    for it in board.items():
        it["group"] = "board" if it.get("kind") == "board" else "part"
        it["name"] = it.get("ref", "pcb")
        out.append(it)
    return out


def transform(items, M):
    out = []
    for it in items:
        it = dict(it)
        it["mesh"] = it["mesh"].transform(M, inplace=False)
        out.append(it)
    return out
