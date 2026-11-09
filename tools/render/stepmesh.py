"""Load a STEP file with its colours (OCP / XCAF) and tessellate it into pyvista meshes.

Returns a list of (pyvista.PolyData, (r, g, b)) grouped by colour. Results are cached as .vtp
next to the cache dir so repeated renders are fast.
"""
import hashlib
import json
import os

import numpy as np
import pyvista as pv
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.Quantity import Quantity_Color, Quantity_TOC_sRGB
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.XCAFDoc import XCAFDoc_ColorGen, XCAFDoc_ColorSurf, XCAFDoc_DocumentTool

DEFAULT = (0.55, 0.55, 0.55)
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")


def _color_of(ctool, shape):
    c = Quantity_Color()
    for kind in (XCAFDoc_ColorSurf, XCAFDoc_ColorGen):
        if ctool.GetColor(shape, kind, c):
            return c.Values(Quantity_TOC_sRGB)
    return None


def _faces(shape, ctool, inherited, buckets):
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        f = TopoDS.Face_s(exp.Current())
        col = _color_of(ctool, f) or inherited or DEFAULT
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is not None:
            tr = loc.Transformation()
            pts = np.array([[*tri.Node(i).Transformed(tr).Coord()] for i in range(1, tri.NbNodes() + 1)])
            tris = []
            rev = f.Orientation() == TopAbs_REVERSED
            for i in range(1, tri.NbTriangles() + 1):
                a, b, c = tri.Triangle(i).Get()
                tris.append((a - 1, c - 1, b - 1) if rev else (a - 1, b - 1, c - 1))
            key = tuple(round(x, 3) for x in col)
            buckets.setdefault(key, []).append((pts, np.array(tris)))
        exp.Next()


def load_step(path, deflection=0.02):
    os.makedirs(CACHE, exist_ok=True)
    h = hashlib.sha1((os.path.abspath(path) + str(os.path.getmtime(path)) + str(deflection)).encode()).hexdigest()[:16]
    meta = os.path.join(CACHE, h + ".json")
    if os.path.exists(meta):
        out = []
        for i, col in enumerate(json.load(open(meta))):
            out.append((pv.read(os.path.join(CACHE, f"{h}_{i}.vtp")), tuple(col)))
        return out

    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    r = STEPCAFControl_Reader()
    r.SetColorMode(True)
    r.SetNameMode(True)
    if r.ReadFile(path) != IFSelect_RetDone:
        raise IOError(path)
    r.Transfer(doc)
    stool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ctool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    labels = TDF_LabelSequence()
    stool.GetFreeShapes(labels)
    buckets = {}

    def walk(label, loc, inherited):
        shape = stool.GetShape_s(label)
        col = _color_of(ctool, shape) or inherited
        if stool.IsAssembly_s(label):
            comps = TDF_LabelSequence()
            stool.GetComponents_s(label, comps)
            for i in range(1, comps.Length() + 1):
                c = comps.Value(i)
                cl = stool.GetLocation_s(c)
                ref = c
                rl = TDF_Label()
                if stool.GetReferredShape_s(c, rl):
                    ref = rl
                ccol = _color_of(ctool, stool.GetShape_s(c)) or col
                walk(ref, loc.Multiplied(cl), ccol)
            return
        s = shape.Moved(loc)
        BRepMesh_IncrementalMesh(s, deflection, False, 0.3, True)
        _faces(s, ctool, col, buckets)

    for i in range(1, labels.Length() + 1):
        walk(labels.Value(i), TopLoc_Location(), None)

    out, cols = [], []
    for col, parts in buckets.items():
        pts, faces, off = [], [], 0
        for p, t in parts:
            pts.append(p)
            faces.append(np.hstack([np.full((len(t), 1), 3), t + off]))
            off += len(p)
        m = pv.PolyData(np.vstack(pts), np.vstack(faces).ravel())
        m.save(os.path.join(CACHE, f"{h}_{len(out)}.vtp"))
        out.append((m, col))
        cols.append(col)
    json.dump(cols, open(meta, "w"))
    return out
