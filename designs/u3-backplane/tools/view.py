"""Quick layout viewer: python3 tools/view.py board.kicad_pcb out.png x0 y0 x1 y1 [plane_layer] [px_per_mm]
Coordinates are board-local (sheet minus the 100,100 origin used by pcbkit).  Draws the filled zone of
plane_layer (default In1_Cu = L2) in grey, L6 copper blue, L1 copper red (on top), vias, NPTH, edge cuts."""
import sys
import pcbnew as P
from PIL import Image, ImageDraw

pcb, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(float, sys.argv[3:7])
plane = getattr(P, sys.argv[7]) if len(sys.argv) > 7 else P.In1_Cu
S = float(sys.argv[8]) if len(sys.argv) > 8 else 40.0
O = 100.0
b = P.LoadBoard(pcb)
W, H = int((x1 - x0) * S), int((y1 - y0) * S)
im = Image.new("RGB", (W, H), (15, 15, 15))
dr = ImageDraw.Draw(im, "RGBA")


def tp(v):
    return ((P.ToMM(v.x) - O - x0) * S, (P.ToMM(v.y) - O - y0) * S)


def poly(sp, fill):
    for i in range(sp.OutlineCount()):
        o = sp.Outline(i)
        pts = [tp(o.CPoint(j)) for j in range(o.PointCount())]
        if len(pts) > 2:
            dr.polygon(pts, fill=fill)
        for h in range(sp.HoleCount(i)):
            hh = sp.Hole(i, h)
            pts = [tp(hh.CPoint(j)) for j in range(hh.PointCount())]
            if len(pts) > 2:
                dr.polygon(pts, fill=(15, 15, 15, 255))


for z in b.Zones():
    if not z.GetIsRuleArea() and z.IsOnLayer(plane) and z.HasFilledPolysForLayer(plane):
        poly(z.GetFilledPolysList(plane), (90, 90, 90, 255))
for L, col in ((P.B_Cu, (60, 110, 255, 170)), (P.F_Cu, (230, 60, 40, 170))):
    for z in b.Zones():
        if not z.GetIsRuleArea() and z.IsOnLayer(L) and z.HasFilledPolysForLayer(L):
            poly(z.GetFilledPolysList(L), col[:3] + (90,))
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetLayer() == L:
            dr.line([tp(t.GetStart()), tp(t.GetEnd())], fill=col, width=max(1, int(P.ToMM(t.GetWidth()) * S)))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.IsOnLayer(L):
                poly(p.GetEffectivePolygon(), col)
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        c = tp(t.GetPosition()); r = P.ToMM(t.GetWidth()) / 2 * S; rd = P.ToMM(t.GetDrillValue()) / 2 * S
        dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(220, 200, 0, 255))
        dr.ellipse([c[0] - rd, c[1] - rd, c[0] + rd, c[1] + rd], fill=(0, 0, 0, 255))
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetAttribute() == P.PAD_ATTRIB_NPTH:
            c = tp(p.GetPosition()); r = P.ToMM(p.GetDrillSize().x) / 2 * S
            dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(255, 255, 255, 255), width=2)
for d in b.GetDrawings():
    if d.GetLayer() == P.Edge_Cuts:
        dr.line([tp(d.GetStart()), tp(d.GetEnd())], fill=(255, 255, 0, 255), width=2)
# 1 mm grid ticks
for gx in range(int(x0), int(x1) + 1):
    dr.line([((gx - x0) * S, 0), ((gx - x0) * S, 6)], fill=(200, 200, 200, 255))
for gy in range(int(y0), int(y1) + 1):
    dr.line([(0, (gy - y0) * S), (6, (gy - y0) * S)], fill=(200, 200, 200, 255))
im.save(out)
print("saved", out, W, H)
