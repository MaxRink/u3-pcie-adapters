#!/usr/bin/python3
"""Dump a .kicad_pcb into JSON for the renderer (run with KiCad's own python: /usr/bin/python3).

Output: board outline (with holes), thickness, per-layer copper/mask/silk polygons, drill holes,
and footprint placements with their 3D model references and local Fab/courtyard boxes.
Coordinates are in mm, KiCad frame (x right, y down).
"""
import json
import sys

import pcbnew

MM = 1e-6


def polyset_to_list(ps):
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        outer = [(ol.CPoint(j).x * MM, ol.CPoint(j).y * MM) for j in range(ol.PointCount())]
        holes = []
        for h in range(ps.HoleCount(i)):
            hl = ps.Hole(i, h)
            holes.append([(hl.CPoint(j).x * MM, hl.CPoint(j).y * MM) for j in range(hl.PointCount())])
        out.append({"outer": outer, "holes": holes})
    return out


def local_box(fp, layers):
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayerName() not in layers or not hasattr(g, "GetStart0"):
            continue
        for p in (g.GetStart0(), g.GetEnd0()):
            xs.append(p.x * MM)
            ys.append(p.y * MM)
    if not xs:
        return None
    return [min(xs), min(ys), max(xs), max(ys)]


def main(path, out):
    b = pcbnew.LoadBoard(path)
    data = {"source": path, "thickness": b.GetDesignSettings().GetBoardThickness() * MM}
    o = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(o)
    data["outline"] = polyset_to_list(o)
    bb = b.GetBoardEdgesBoundingBox()
    data["bbox"] = [bb.GetX() * MM, bb.GetY() * MM, bb.GetRight() * MM, bb.GetBottom() * MM]

    layers = {}
    for name, lid in [("F.Cu", pcbnew.F_Cu), ("B.Cu", pcbnew.B_Cu), ("F.Mask", pcbnew.F_Mask),
                      ("B.Mask", pcbnew.B_Mask), ("F.SilkS", pcbnew.F_SilkS), ("B.SilkS", pcbnew.B_SilkS)]:
        ps = pcbnew.SHAPE_POLY_SET()
        b.ConvertBrdLayerToPolygonalContours(lid, ps)
        ps.Fracture(pcbnew.SHAPE_POLY_SET.PM_FAST)
        layers[name] = polyset_to_list(ps)
    data["layers"] = layers

    holes = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            holes.append({"x": t.GetPosition().x * MM, "y": t.GetPosition().y * MM,
                          "dx": t.GetDrillValue() * MM, "dy": t.GetDrillValue() * MM, "rot": 0, "plated": True})
    fps = []
    for f in b.GetFootprints():
        for p in f.Pads():
            ds = p.GetDrillSize()
            if ds.x > 0:
                holes.append({"x": p.GetPosition().x * MM, "y": p.GetPosition().y * MM, "dx": ds.x * MM,
                              "dy": ds.y * MM, "rot": p.GetOrientationDegrees(),
                              "plated": p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH})
        models = []
        for m in f.Models():
            models.append({"file": m.m_Filename, "show": bool(m.m_Show),
                           "offset": [m.m_Offset.x, m.m_Offset.y, m.m_Offset.z],
                           "rot": [m.m_Rotation.x, m.m_Rotation.y, m.m_Rotation.z],
                           "scale": [m.m_Scale.x, m.m_Scale.y, m.m_Scale.z]})
        back = f.GetLayer() == pcbnew.B_Cu
        side = "B" if back else "F"
        fps.append({"ref": f.GetReference(), "value": f.GetValue(), "fpid": f.GetFPIDAsString(),
                    "x": f.GetPosition().x * MM, "y": f.GetPosition().y * MM,
                    "rot": f.GetOrientationDegrees(), "back": back, "models": models,
                    "dnp": bool(f.GetAttributes() & getattr(pcbnew, "FP_EXCLUDE_FROM_BOM", 0) and False),
                    "fab": local_box(f, {f"{side}.Fab"}), "crtyd": local_box(f, {f"{side}.CrtYd"})})
    data["holes"] = holes
    data["footprints"] = fps
    with open(out, "w") as fh:
        json.dump(data, fh)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
