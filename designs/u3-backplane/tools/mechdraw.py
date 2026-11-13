"""Mechanical drawing (SVG) of a generated board, seen from the drive side: outline, cut-outs, mounting holes with
coordinates, connector bodies (solid = drive side, dashed = underside), overall dimensions and a hole table.
usage: python3 tools/mechdraw.py board.kicad_pcb out.svg "title" ["note" ...]
Coordinates are board-local mm (origin = top-left corner of the outline, x right, y down)."""
import sys
import pcbnew as P

pcb, out, title = sys.argv[1:4]
notes = sys.argv[4:]
b = P.LoadBoard(pcb)
O = 100.0
mm = lambda v: P.ToMM(v) - O
S = 6.0                        # px per mm
ep = [p for d in b.GetDrawings() if d.GetLayer() == P.Edge_Cuts for p in (d.GetStart(), d.GetEnd())]
x0, y0, x1, y1 = min(mm(p.x) for p in ep), min(mm(p.y) for p in ep), max(mm(p.x) for p in ep), max(mm(p.y) for p in ep)
MX, MY = 28.0, 22.0            # margins in mm
Wd, Hd = (x1 - x0) + 2 * MX + 62, (y1 - y0) + 2 * MY + 8 + 4.5 * len(notes)
X = lambda x: (x - x0 + MX) * S
Y = lambda y: (y - y0 + MY) * S
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd * S:.0f}" height="{Hd * S:.0f}" viewBox="0 0 {Wd * S:.0f} {Hd * S:.0f}" '
     f'font-family="DejaVu Sans, Arial, sans-serif">', f'<rect width="100%" height="100%" fill="white"/>']


def line(xa, ya, xb, yb, st="stroke:#111;stroke-width:1.6"):
    o.append(f'<line x1="{X(xa):.1f}" y1="{Y(ya):.1f}" x2="{X(xb):.1f}" y2="{Y(yb):.1f}" style="{st}"/>')


def text(x, y, s, size=11, anchor="middle", fill="#111", rot=0):
    tr = f' transform="rotate({rot} {X(x):.1f} {Y(y):.1f})"' if rot else ""
    o.append(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}"{tr}>{s}</text>')


for d in b.GetDrawings():
    if d.GetLayer() != P.Edge_Cuts:
        continue
    s, e = d.GetStart(), d.GetEnd()
    line(mm(s.x), mm(s.y), mm(e.x), mm(e.y))
holes = []
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    ref = f.GetReference()
    pos = f.GetPosition(); px, py = mm(pos.x), mm(pos.y)
    if ref.startswith("H"):
        holes.append((ref, px, py))
        o.append(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="{1.6 * S:.1f}" fill="none" stroke="#c00" stroke-width="1.6"/>')
        line(px - 2.6, py, px + 2.6, py, "stroke:#c00;stroke-width:0.8"); line(px, py - 2.6, px, py + 2.6, "stroke:#c00;stroke-width:0.8")
        text(px, py - 2.4, ref, 10, fill="#c00")
        continue
    if not ref.startswith("J"):
        continue
    xs, ys = [], []
    for g in f.GraphicalItems():
        if g.GetLayer() in (P.F_Fab, P.B_Fab) and g.GetClass() != "FP_TEXT":
            for p in (g.GetStart(), g.GetEnd()):
                xs.append(mm(p.x)); ys.append(mm(p.y))
    if not xs:
        continue
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    dash = ' stroke-dasharray="7 4"' if f.IsFlipped() else ""
    col = "#06c" if f.IsFlipped() else "#080"
    o.append(f'<rect x="{X(bx0):.1f}" y="{Y(by0):.1f}" width="{(bx1 - bx0) * S:.1f}" height="{(by1 - by0) * S:.1f}" '
             f'fill="{col}" fill-opacity="0.08" stroke="{col}" stroke-width="1.4"{dash}/>')
    tall = (by1 - by0) > (bx1 - bx0) * 1.5
    text((bx0 + bx1) / 2, (by0 + by1) / 2 + 1, ref, 11, fill=col, rot=-90 if tall else 0)
    if tall:                                                   # drive receptacle: centre line position
        text(px, y0 - 2.0, f"{px:.1f}", 10, fill="#080")
        line(px, y0 - 1.2, px, y0, "stroke:#080;stroke-width:0.8")
# overall dimensions
line(x0, y1 + 7, x1, y1 + 7, "stroke:#111;stroke-width:0.8"); text((x0 + x1) / 2, y1 + 10.5, f"{x1 - x0:.1f} mm", 13)
line(x0, y1 + 5.5, x0, y1 + 8.5, "stroke:#111;stroke-width:0.8"); line(x1, y1 + 5.5, x1, y1 + 8.5, "stroke:#111;stroke-width:0.8")
line(x0 - 9, y0, x0 - 9, y1, "stroke:#111;stroke-width:0.8"); text(x0 - 11, (y0 + y1) / 2, f"{y1 - y0:.1f} mm", 13, rot=-90)
line(x0 - 10.5, y0, x0 - 7.5, y0, "stroke:#111;stroke-width:0.8"); line(x0 - 10.5, y1, x0 - 7.5, y1, "stroke:#111;stroke-width:0.8")
text(x0, y0 - 14.5, title, 16, anchor="start")
text(x0, y0 - 10.0, "View from the drive side. Origin = top-left corner, x right, y down, mm. Green = drive side, "
                    "blue dashed = underside.", 10, anchor="start", fill="#444")
text(x0, y0 - 6.3, "Numbers above the board = x of each drive receptacle centre line.", 10, anchor="start", fill="#444")
# hole table
tx = x1 + 14
text(tx, y0 + 2, "Mounting holes (3.2 mm, M3)", 12, anchor="start")
for i, (ref, px, py) in enumerate(holes):
    text(tx, y0 + 7 + 4.2 * i, f"{ref}:  x {px - x0:6.2f}   y {py - y0:6.2f}", 11, anchor="start")
for i, n in enumerate(notes):
    text(x0, y1 + 17 + 4.5 * i, n, 11, anchor="start", fill="#333")
o.append("</svg>")
open(out, "w").write("\n".join(o))
print("wrote", out, len(holes), "holes")
