"""Shared-fan shrouds: several cards in neighbouring slot pairs fed by one 120 mm fan.

A card with its drives is two slots thick, so the cards sit `PITCH` = 40.64 mm apart. Every card
keeps its own body, cover and slot fillers; only the part that carries the fan is shared.

  style "end"   every card has the end-fan duct of card_shroud; one adapter plate closes the gaps
                between the cards and funnels all ducts to one fan beyond the card ends.
                Three cards are 111 mm wide, which is almost exactly a 120 mm fan. Adds length,
                no height.
  style "hood"  every card has the top-feed duct of card_shroud_top without its manifold (open
                collar above the drive ends); a hood lies across all cards with one fan per two
                drives of card length, blowing down. Fresh air for every drive. Adds height,
                no length.

The result carries the per-card parts once, plus `replicas` (z offsets of the cards) and the
shared parts; build.expand() turns that into the full assembly.
"""
import math
from dataclasses import asdict

import cadquery as cq

import card_shroud
import card_shroud_top
import parts
from card_shroud import _loft, _union
from parts import box, cyl

PITCH = 2 * 20.32


def T(x=0, y=0, z=0, rx=0, ry=0, rz=0):
    return cq.Location(cq.Vector(x, y, z), (rx, ry, rz))


def build(board, n_cards=3, style="end", p=None, **kw):
    return (_end if style == "end" else _hood)(board, n_cards, p, **kw)


# ------------------------------------------------------------------------------------------------ end fan
def _end(board, n, p=None, funnel_len=40.0):
    p = p or card_shroud.ShroudParams()
    r = card_shroud.build(board, p)
    ad = r["info"]["adapter"]
    w = p.wall
    x0 = ad["x0"]
    y_in, y_ti, z_bi, z_ci = ad["rect_i"]
    y_lo, y_hi, z_bo, z_co = ad["rect_o"]
    dzs = [-k * PITCH for k in range(n)]
    z_lo, z_hi = z_bo + dzs[-1] - 9.0 - w, z_co + 9.0 + w
    s, hs, _hub = parts.FANS[p.fan]
    r_i = s / 2 - 2.0
    cyc, czc = (y_lo + y_hi) / 2, (z_lo + z_hi) / 2
    x1, x2 = x0 + 4.0, x0 + 4.0 + funnel_len
    plate = box(x0, x1, y_lo - 0.4, y_hi + 0.4, z_lo - 0.4, z_hi + 0.4)      # a little larger than the funnel: coplanar faces break the union
    pc = [box(x0 - 1, x1 + 1, y_in, y_ti, z_bi + dz, z_ci + dz) for dz in dzs]
    pc += [cyl(p.m3_clear / 2, 6, "x", (x0 - 1, y, z + dz)) for dz in dzs for (y, z) in ad["lugs"]]
    plate = plate.cut(_union(pc))
    ro = (y_lo, y_hi, z_lo, z_hi)
    ri = (y_lo + w, y_hi - w, z_lo + w, z_hi - w)
    funnel = _loft(x1 - 0.01, ro, x2, (cyc, czc, r_i + w)).cut(_loft(x1 - 0.02, ri, x2 + 0.01, (cyc, czc, r_i)))
    flange = cq.Workplane("YZ").rect(s, s).extrude(4.0).edges("|X").fillet(s * 0.055).translate((x2, cyc, czc))
    flange = flange.cut(cyl(r_i, 6, "x", (x2 - 1, cyc, czc)))
    fan_holes = [(cyc + sy * hs / 2, czc + sz * hs / 2) for sy in (-1, 1) for sz in (-1, 1)]
    flange = flange.cut(_union([cyl(1.9, 6, "x", (x2 - 1, y, z)) for (y, z) in fan_holes]))
    adapter = funnel.union(flange).union(plate)
    assert adapter.val().BoundingBox().xmax > x2 + 3.0, "shared adapter lost its funnel"

    printed = {k: v for k, v in r["printed"].items() if k != "fan_adapter"}
    hw = [h for h in r["hardware"] if h[1] not in ("fan", "scr_fan")]
    xf = x2 + 4.0
    shw = [(f"{p.fan}x{p.fan}x{int(p.fan_thick)} mm fan", "fan", parts.axial_fan, (p.fan, p.fan_thick), T(xf + p.fan_thick, cyc, czc, ry=-90))]
    shw += [("M4x12 self-tapping fan screw", "scr_fan", parts.screw_shcs, (4.0, 12.0), T(xf + 4.5, y, z, ry=90)) for (y, z) in fan_holes]
    info = dict(style="shared end fan", cards=n, pitch=PITCH, params=asdict(p), drives=r["info"]["drives"] * n,
                card_length=board.L,
                envelope=dict(length=xf + p.fan_thick, height_above_finger_bottom=max(y_hi, cyc + s / 2),
                              z=[min(z_lo, czc - s / 2), max(z_hi, czc + s / 2)]),
                per_card=r["info"])
    return dict(printed=printed, hardware=hw, shared_printed={"shared_fan_adapter": adapter}, shared_hardware=shw,
                replicas=dzs, info=info, board_solid=r["board_solid"])


# ------------------------------------------------------------------------------------------------ hood
def _hood(board, n, p=None, plenum=20.0, max_len=250.0):
    p = p or card_shroud_top.TopParams(open_top=True)
    assert p.open_top
    r = card_shroud_top.build(board, p)
    d = r["info"]["duct"]
    w, fit = p.wall, p.fit
    xa, xb = d["x"]
    z_bo, z_co = d["z"]
    z_bi, z_ci = d["zi"]
    y_edge, hood_y = d["y_edge"], d["hood_y"]
    dzs = [-k * PITCH for k in range(n)]
    s, hs, _hub = parts.FANS[p.fan]
    xs = [dr["xc"] for dr in board.drives()]
    xf = [(xs[i] + xs[i + 1]) / 2 if i + 1 < len(xs) else xs[i] for i in range(0, len(xs), 2)]   # one fan per two drives
    zc = (z_bo + dzs[-1] + z_co) / 2
    yp0 = y_edge + fit
    yp1 = yp0 + w
    yq0 = yp1 + plenum
    yq1 = yq0 + w
    lip = 2.0
    zh0 = min(z_bo + dzs[-1] - fit - lip, zc - s / 2 - 2)
    zh1 = max(z_co + fit + lip, zc + s / 2 + 2)
    xh0, xh1 = min(xa, xf[0] - s / 2 - 2), max(xb + fit + 3.0, xf[-1] + s / 2 + 2)
    x_tab = xa + w + fit                                    # inner hook tab at the bracket end
    add = [box(xh0, xh1, yp0, yp1, zh0, zh1), box(xh0, xh1, yq0, yq1, zh0, zh1),
           box(xh0, xh0 + w, yp0, yq1, zh0, zh1), box(xh1 - w, xh1, yp0, yq1, zh0, zh1),
           box(xh0, xh1, yp0, yq1, zh0, zh0 + w), box(xh0, xh1, yp0, yq1, zh1 - w, zh1)]
    cut = []
    screws = []
    for dz in dzs:
        cut.append(box(x_tab + 3.0, xb - w, yp0 - 1, yp1 + 1, z_bi + dz, z_ci + dz))               # slot over the card's two channels
        add.append(box(xa + 15, xb - 15, yp0 - 5.0, yp0 + 0.1, z_bo + dz - fit - lip, z_bo + dz - fit))    # locating lips
        add.append(box(xa + 15, xb - 15, yp0 - 5.0, yp0 + 0.1, z_co + dz + fit, z_co + dz + fit + lip))
        add.append(box(x_tab, x_tab + 3.0, hood_y - 3.5, yp0 + 0.1, z_bi + dz + 1.0, z_bi + dz + 9.0))     # hook tab
        add.append(box(xa + 0.4, x_tab + 0.1, hood_y - 1.3, hood_y + 1.3, z_bi + dz + 2.2, z_bi + dz + 7.8))   # hook
        add.append(box(xb + fit, xb + fit + 3.0, hood_y - 5.0, yp0 + 0.1, z_bi + dz, z_bi + dz + 9.0))     # screw tab at the card end
        cut.append(cyl(p.m3_clear / 2, 5, "x", (xb + fit - 1, hood_y, z_bi + dz + 4.5)))
        screws.append((xb + fit + 3.0, hood_y, z_bi + dz + 4.5))
    fan_holes = []
    for f in xf:
        cut.append(cyl(s / 2 - 2.0, w + 2, "y", (f, yq0 - 1, zc)))
        for sx in (-1, 1):
            for sz in (-1, 1):
                fan_holes.append((f + sx * hs / 2, zc + sz * hs / 2))
    for (x, z) in fan_holes:
        add.append(cyl(4.0, 6.0, "y", (x, yq0 - 6.0, z)))
        cut.append(cyl(1.9, 6.0 + w + 2, "y", (x, yq0 - 7.0, z)))
    # split a long hood between two fans: a double wall there, bolted together
    joints, split_x = [], []
    if xh1 - xh0 > max_len and len(xf) > 1:
        k = len(xf) // 2
        x_s = (xf[k - 1] + xf[k]) / 2
        split_x.append(x_s)
        add.append(box(x_s - w, x_s + w, yp0, yq1, zh0, zh1))
        for sz in (-1, 1):
            joints.append((x_s, (yp1 + yq0) / 2, zc + sz * 35.0))
            cut.append(cyl(p.m3_clear / 2, 2 * w + 2, "x", (x_s - w - 1, (yp1 + yq0) / 2, zc + sz * 35.0)))
    hood = _union(add).cut(_union(cut))
    shared = {}
    if split_x:
        x_s = split_x[0]
        shared["hood_1"] = hood.intersect(box(xh0 - 50, x_s - fit / 2, -100, 400, -400, 200))
        shared["hood_2"] = hood.intersect(box(x_s + fit / 2, xh1 + 50, -100, 400, -400, 200))
    else:
        shared["hood"] = hood

    hw = list(r["hardware"])
    for (x, y, z) in screws:                                # these repeat with every card
        if abs(z - (z_bi + 4.5)) < 0.01:
            hw.append(("M3x8 cap screw (hood to card)", "scr_hood", parts.screw_shcs, (3.0, 8.0), T(x, y, z, ry=90)))
            hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(xb, y, z, ry=90)))
    shw = []
    for f in xf:
        shw.append((f"{p.fan}x{p.fan}x{int(p.fan_thick)} mm fan", "fan", parts.axial_fan, (p.fan, p.fan_thick), T(f, yq1 + p.fan_thick, zc, rx=90)))
    for (x, z) in fan_holes:
        shw.append(("M4x12 self-tapping fan screw", "scr_fan", parts.screw_shcs, (4.0, 12.0), T(x, yq1 + 4.5, z, rx=-90)))
    for (x, y, z) in joints:
        shw.append(("M3x10 cap screw + nut (hood halves)", "scr_joint", parts.screw_shcs, (3.0, 10.0), T(x + w, y, z, ry=90)))
    info = dict(style="shared hood", cards=n, pitch=PITCH, params=asdict(p), plenum=plenum, drives=r["info"]["drives"] * n,
                fans=len(xf), drives_per_fan=round(r["info"]["drives"] * n / len(xf), 1), card_length=board.L,
                envelope=dict(length=xh1, height_above_finger_bottom=yq1 + p.fan_thick, z=[zh0, zh1]),
                fan_centres=[(round(f, 2), round(zc, 2)) for f in xf], per_card=r["info"])
    return dict(printed=dict(r["printed"]), hardware=hw, shared_printed=shared, shared_hardware=shw,
                replicas=dzs, info=info, board_solid=r["board_solid"])
