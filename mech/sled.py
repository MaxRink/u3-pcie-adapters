"""Printable sled with a ducted fan for the OCuLink cage board (one drive lying on the board's
top side). Parts: tray (floor, side walls, pillars), lid, fan adapter. Derived from the board file
like the card shroud: drive position from the receptacle, board pillars from the M3 slots.
"""
from dataclasses import dataclass, asdict

import cadquery as cq

import parts
from card_shroud import _loft, _union
from parts import box, cyl


@dataclass
class SledParams:
    gap: float = 5.0          # air channel beside and above the drive
    under: float = 9.0        # space under the board (OCuLink receptacle + plug)
    wall: float = 2.4
    fan: int = 60
    fan_thick: float = 25.0
    funnel_len: float = 30.0
    clear: float = 0.5
    insert_d: float = 4.0
    insert_depth: float = 6.5
    m3_clear: float = 3.4


def build(board, p=None):
    p = p or SledParams()
    t = board.t
    d = board.drives()[0]
    assert not d["back"]
    W2 = parts.DRIVE["W"] / 2
    w = p.wall
    zf = -t - p.under                         # floor top
    z_li = d["z_top"] + p.gap                 # lid inner
    x0i, x1i = min(d["xc"] - W2 - p.gap, -1.0), max(d["xc"] + W2 + p.gap, board.L + 1.0)
    y0, y1 = -1.0, d["y_top"] + 2.0           # tray from the board's cable edge to past the drive end
    keep = [board.solid(holes_min=99)]
    for (a, b, c, e, f, g, ref) in board.part_boxes():
        k = p.clear
        keep.append(box(a - k, b + k, c - k, e + k, f - k, g + k))
    # cable exits: OCuLink plug (below the board) and the 6-pin plug (above), towards -y
    for fp, zr in ((board.footprints("OCuLink"), (zf, -t)), (board.footprints("Mini-Fit"), (0, 16))):
        for f in fp:
            x, y = board.xy(f["x"], f["y"])
            keep.append(box(x - 13, x + 13, -30, y, zr[0], zr[1]))
    keepout = _union(keep)

    tray = [box(x0i - w, x1i + w, y0, y1, zf - w, zf),
            box(x0i - w, x0i, y0, y1, zf, z_li), box(x1i, x1i + w, y0, y1, zf, z_li)]
    holes = board.mount_holes()
    for (x, y, dx, dy) in holes:
        tray.append(cyl(4.2, -t - zf, "z", (x, y, zf)))
    drv = [(d["xc"] + s * parts.DRIVE["hole_dx"] / 2, d["y_face"] + d["dir"] * dy) for dy in parts.DRIVE["hole_y"] for s in (-1, 1)]
    for (x, y) in drv:
        tray.append(cyl(4.2, d["z_bottom"] - zf, "z", (x, y, zf)))
    # baffle under the board end so air goes over and under the drive, not under the board
    tray.append(box(x0i, x1i, d["y_face"] - 3.0, d["y_face"] - 1.0, zf, -t))
    lid_pts = [(x0i - w / 2 - 0.0, yy) for yy in (y0 + 12, (y0 + y1) / 2, y1 - 22)] + [(x1i + w / 2, yy) for yy in (y0 + 12, (y0 + y1) / 2, y1 - 22)]
    for (x, y) in lid_pts:                                    # bosses for the lid screws
        tray.append(cyl(4.0, 12, "z", (x, y, z_li - 12)).intersect(box(x0i - w - 3.5, x1i + w + 3.5, y0, y1, zf, z_li)))
    tray = _union(tray)
    cuts = [cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, -t - p.insert_depth)) for (x, y, _, _) in holes]
    eng = 2.6                                                 # thread engagement in the drive
    cb = (d["z_bottom"] - (zf - w)) - (12.0 - eng)
    for (x, y) in drv:
        cuts.append(cyl(p.m3_clear / 2, 40, "z", (x, y, zf - w - 1)))
        cuts.append(cyl(3.1, cb + 1, "z", (x, y, zf - w - 1)))
    cuts += [cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, z_li - p.insert_depth)) for (x, y) in lid_pts]
    tray = tray.cut(_union(cuts)).cut(keepout)

    lid = box(x0i - w, x1i + w, y0, y1, z_li, z_li + w).union(box(x0i - w - 3.5, x1i + w + 3.5, y0, y1 - 11, z_li, z_li + w))
    lid = lid.cut(_union([cyl(p.m3_clear / 2, 10, "z", (x, y, z_li - 1)) for (x, y) in lid_pts]))
    lid = lid.cut(keepout)

    s, hs, _ = parts.FANS[p.fan]
    rect_i = (x0i, x1i, zf, z_li)
    rect_o = (x0i - w, x1i + w, zf - w, z_li + w)
    cxc, czc = (x0i + x1i) / 2, (zf + z_li) / 2
    ya, yb, yc = y1 + 0.2, y1 + 6.0, y1 + 6.0 + p.funnel_len

    def loft_y(y_a, rect, y_b, circ):
        # _loft works along x with (y, z) sections; build it there and rotate x -> y
        l = _loft(y_a, (-rect[1], -rect[0], rect[2], rect[3]), y_b, (-circ[0], circ[1], circ[2]))
        return l.rotate((0, 0, 0), (0, 0, 1), 90)

    r_i = s / 2 - 2.0
    neck = box(rect_o[0] - w - 0.3, rect_o[1] + w + 0.3, y1 - 10, yb, rect_o[2] - w - 0.3, rect_o[3] + w + 0.3)
    neck = neck.cut(box(rect_o[0] - 0.3, rect_o[1] + 0.3, y1 - 11, ya, rect_o[2] - 0.3, rect_o[3] + 0.3)).cut(box(rect_i[0], rect_i[1], y1 - 11, yb + 1, rect_i[2], rect_i[3]))
    funnel = loft_y(yb - 0.01, rect_o, yc, (cxc, czc, r_i + w)).cut(loft_y(yb - 0.02, rect_i, yc + 0.01, (cxc, czc, r_i)))
    flange = cq.Workplane("XZ").rect(s, s).extrude(-4.0).edges("|Y").fillet(s * 0.055).translate((cxc, yc, czc))
    flange = flange.cut(cyl(r_i, 6, "y", (cxc, yc - 1, czc)))
    adapter = neck.union(funnel).union(flange)
    fan_holes = [(cxc + sx * hs / 2, czc + sz * hs / 2) for sx in (-1, 1) for sz in (-1, 1)]
    adapter = adapter.cut(_union([cyl(1.9, 6, "y", (x, yc - 1, z)) for (x, z) in fan_holes]))
    adapter = adapter.cut(cyl(p.m3_clear / 2, 10, "x", (rect_o[1], y1 - 5, czc))).cut(cyl(p.m3_clear / 2, 10, "x", (rect_o[0] - 10, y1 - 5, czc)))

    def T(x=0, y=0, z=0, rx=0, ry=0, rz=0):
        return cq.Location(cq.Vector(x, y, z), (rx, ry, rz))

    hw = [("drive", f"drive_{d['ref']}", parts.drive_u3, (), d["T"])]
    for (x, y, _, _) in holes:
        hw.append(("M3x6 cap screw (board to tray)", "scr_board", parts.screw_shcs, (3.0, 6.0), T(x, y, 0)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(x, y, -t)))
    for (x, y) in drv:
        hw.append(("M3x12 cap screw (tray to drive)", "scr_drv", parts.screw_shcs, (3.0, 12.0), T(x, y, zf - w + cb, rx=180)))
    for (x, y) in lid_pts:
        hw.append(("M3x8 cap screw (lid)", "scr_lid", parts.screw_shcs, (3.0, 8.0), T(x, y, z_li + w)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(x, y, z_li)))
    yf = yc + 4.0
    hw.append((f"{p.fan}x{p.fan}x{int(p.fan_thick)} mm fan", "fan", parts.axial_fan, (p.fan, p.fan_thick), T(cxc, yf + p.fan_thick, czc, rx=90)))
    for (x, z) in fan_holes:
        hw.append(("M4x12 self-tapping fan screw", "scr_fan", parts.screw_shcs, (4.0, 12.0), T(x, yf + 4.5, z, rx=-90)))
    hw.append(("M3x6 self-tapping screw (fan adapter)", "scr_adp", parts.screw_shcs, (3.0, 6.0), T(rect_o[1] + w + 0.3, y1 - 5, czc, ry=90)))
    hw.append(("M3x6 self-tapping screw (fan adapter)", "scr_adp", parts.screw_shcs, (3.0, 6.0), T(rect_o[0] - w - 0.3, y1 - 5, czc, ry=-90)))
    info = dict(params=asdict(p), envelope=dict(x=[x0i - w, x1i + w], y=[y0, yf + p.fan_thick], z=[zf - w, z_li + w]),
                board_pillars=[(round(x, 2), round(y, 2)) for (x, y, _, _) in holes])
    return dict(printed={"tray": tray, "lid": lid, "fan_adapter": adapter}, hardware=hw, info=info, board_solid=keep[0])
