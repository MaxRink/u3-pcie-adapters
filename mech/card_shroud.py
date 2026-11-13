"""Printable cooling shroud for the slot cards (x8, x16 3-drive, x16 4-drive).

Everything is derived from the board file: drive positions come from the U.3 receptacle
footprints, clamp points from the unplated M3 slots, keep-outs from the placed parts. Re-running
the build after a board change regenerates the shroud for the new layout.

Layout (board frame, see boardio.py): the drives hang on the back of the card (z < -t) and stand
up from the connector strip. Air runs along the card (x) from a fan at the far end towards the
bracket, through a `gap` mm channel on each big face of the drives: the layout the CFD in
docs/thermal covers ("in line").

Printed parts:
  body      back tub: back wall, top wall, bottom wall, filler under the drives' connector ends
  cover     front plate over the card window, screwed into the drives' four bottom holes
  adapter   funnel from the duct to the fan, bolted to lugs on body and cover
  filler    bars that close the dead-air slots between neighbouring drives
"""
import math
from dataclasses import dataclass, asdict

import cadquery as cq
import numpy as np

import parts
from parts import box, cyl


@dataclass
class ShroudParams:
    gap: float = 5.0            # air channel on each drive face (CFD: 5 mm; 3 mm needs a stiffer print)
    wall: float = 2.4           # 6 perimeters at 0.4 mm
    top_gap: float = 1.5        # clearance over the drive ends
    fan: int = 120              # fan frame size, mm (Max, 2026-11-13: design around 120 mm fans)
    fan_thick: float = 25.0     # 25 or 38: this duct needs a high-static fan, see README
    funnel_len: float = 50.0    # duct-to-fan transition length
    neck: float = 7.0           # straight section before the funnel (room for the flange screws)
    fan_z_offset: float = 0.0   # shift the fan axis off the duct centre (towards +z = component side)
    x_start: float = 1.0        # duct start at the bracket end
    y_bottom: float = 14.0      # lower edge of the body on the card's back
    clear: float = 0.5          # keep-out around board parts
    fit: float = 0.2            # clearance between printed parts
    max_len: float = 250.0      # longest printable piece; longer body/cover are split between drives
    insert_d: float = 4.0       # hole for M3 heat-set inserts
    insert_depth: float = 6.5
    m3_clear: float = 3.4


def _ray_rect(cy, cz, hy, hz, th):
    c, s = math.cos(th), math.sin(th)
    k = min(hy / abs(c) if abs(c) > 1e-9 else 1e9, hz / abs(s) if abs(s) > 1e-9 else 1e9)
    return cy + k * c, cz + k * s


def _loft(x0, rect, x1, circ, n=72):
    """Solid loft from a rectangle (y0, y1, z0, z1) at x0 to a circle (cy, cz, r) at x1."""
    y0, y1, z0, z1 = rect
    cy, cz, r = circ
    ry, rz = (y0 + y1) / 2, (z0 + z1) / 2
    a = [cq.Vector(x0, *_ray_rect(ry, rz, (y1 - y0) / 2, (z1 - z0) / 2, 2 * math.pi * k / n)) for k in range(n)]
    b = [cq.Vector(x1, cy + r * math.cos(2 * math.pi * k / n), cz + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    wa = cq.Wire.makePolygon(a + [a[0]])
    wb = cq.Wire.makePolygon(b + [b[0]])
    return cq.Workplane("XY").add(cq.Solid.makeLoft([wa, wb], True))


def _union(items):
    out = None
    for it in items:
        out = it if out is None else out.union(it)
    return out


def build(board, p=None):
    p = p or ShroudParams()
    t = board.t
    drives = board.drives()
    assert drives and all(d["back"] for d in drives), "card shroud expects drives on the back of the card"
    L = board.L
    zb = -t                                   # drive bottom plane = card back surface
    zt = min(d["z_top"] for d in drives)      # drive label face
    z_bi, z_ci = zt - p.gap, zb + p.gap       # inner faces of body back wall / cover plate
    z_bo, z_co = z_bi - p.wall, z_ci + p.wall
    y_ti = max(d["y_top"] for d in drives) + p.top_gap
    y_to = y_ti + p.wall
    xa, xb = p.x_start, L
    W2 = parts.DRIVE["W"] / 2
    # x boundaries of each drive's bay
    mids = [(drives[i]["xc"] + drives[i + 1]["xc"]) / 2 for i in range(len(drives) - 1)]
    bays = list(zip([xa] + mids, mids + [xb]))
    y_sk = [d["y_face"] - 2.4 for d in drives]          # skirt lower edge per bay
    y_in = drives[-1]["y_face"] - 0.8                  # lower edge of the duct opening at the fan end

    holes = board.mount_holes()
    bracket_holes = [h for h in holes if abs(h[2] - h[3]) < 0.01 and h[0] < 12 and min(abs(h[1] - y) for y in parts.BRACKET_TAB_Y) < 3.0]
    clamps = [h for h in holes if h not in bracket_holes]

    def bay_of(x):
        return min(range(len(bays)), key=lambda i: 0 if bays[i][0] <= x <= bays[i][1] else min(abs(x - bays[i][0]), abs(x - bays[i][1])))
    # holes well below the cover (mid-strip holes) are screwed straight from the card into the body
    direct = [h for h in clamps if h[1] < y_sk[bay_of(h[0])] - 8.0]
    clamps = [h for h in clamps if h not in direct]
    y_corner = y_ti - 7.0
    corners = [(min(6.5, drives[0]["xc"] - W2 - 6.0), y_corner), (max(drives[-1]["xc"] + W2 + 6.0, xb - 5.5), y_corner)]

    # ------------------------------------------------------------ keep-outs
    pcb = board.solid(holes_min=99)
    keep = [pcb]
    for (x0, x1, y0, y1, z0, z1, ref) in board.part_boxes():
        c = p.clear
        keep.append(box(x0 - c, x1 + c, y0 - c, y1 + c, min(z0, -t / 2) - (c if z0 < -t else 0), max(z1, -t / 2) + (c if z1 > 0 else 0)))
    bracket = parts.pcie_bracket(tab_y=[h[1] for h in bracket_holes], tab_x=bracket_holes[0][0] if bracket_holes else 7.5)
    bb = bracket[0][0].val().BoundingBox()
    for h in bracket_holes:                              # tab + screw head
        keep.append(box(-2, h[0] + 5.5, h[1] - 5, h[1] + 5, 0, 4.2))
    keepout = _union(keep)

    # ------------------------------------------------------------ cover (component side)
    cov = []
    for (x0, x1), ys in zip(bays, y_sk):
        cov.append(box(x0, x1, ys, y_to, z_ci, z_co))                       # plate
        cov.append(box(x0, x1, ys, ys + 1.65, 0.0, z_ci))                   # skirt on the card along the window edge
    for i, xm in enumerate(mids):                                           # skirt steps where neighbours differ
        lo, hi = sorted((y_sk[i], y_sk[i + 1]))
        if hi - lo > 0.1:
            cov.append(box(xm - 0.8, xm + 0.8, lo, hi + 1.65, 0.0, z_ci))
    cov.append(box(xa, xb, y_ti, y_to, zb, z_ci))                           # top wall
    cov.append(box(xa, xb, y_ti + 0.6, y_ti + 1.8, zb - 1.5, zb))           # tongue into the body's top wall
    drive_screws = []
    for d in drives:
        for dy in parts.DRIVE["hole_y"]:
            for s in (-1, 1):
                x, y = d["xc"] + s * parts.DRIVE["hole_dx"] / 2, d["y_face"] + d["dir"] * dy
                cov.append(cyl(3.6, z_ci - zb, "z", (x, y, zb)))
                drive_screws.append((x, y))
    for (x, y, dx, dy) in clamps:
        cov.append(cyl(4.2, z_ci, "z", (x, y, 0)))
        cov.append(cyl(6.5, p.wall, "z", (x, y, z_ci)))
    for (x, y) in corners:
        cov.append(cyl(4.2, z_ci - zb, "z", (x, y, zb)))
    lug_y = [y_in + 16.0, y_ti - 22.0]
    lug_yc = [lug_y[0] + 12.0, lug_y[1] - 12.0]       # cover lugs offset from the body lugs: neighbouring cards interleave
    for y in lug_yc:                                                        # lugs for the fan adapter
        cov.append(box(xb - 12, xb, y - 4.5, y + 4.5, z_co, z_co + 9.0))
    cover = _union(cov)
    # exhaust slots over the bracket-end column, clear of bosses
    x_e1 = drives[0]["xc"] - W2 - 2.0
    yy = 38.0
    while yy + 14 < y_ti - 12:
        if all(abs(yy + 7 - c[1]) > 14 for c in clamps if c[0] < 12):
            cover = cover.cut(box(xa + 1.6, x_e1, yy, yy + 14, z_ci - 0.1, z_co + 0.1))
        yy += 17.0
    holes_c = [cyl(p.m3_clear / 2, 30, "z", (x, y, zb - 5)) for (x, y) in drive_screws + corners]
    holes_c += [cyl(p.m3_clear / 2, 30, "z", (x, y, -5)) for (x, y, _, _) in clamps]
    for y in lug_yc:
        holes_c.append(cyl(p.insert_d / 2, p.insert_depth, "x", (xb - p.insert_depth, y, z_co + 4.5)))
    cover = cover.cut(_union(holes_c)).cut(keepout).intersect(box(0.3, xb, -50, 400, -100, 100))

    # ------------------------------------------------------------ body (back side)
    body = box(xa, xb, p.y_bottom, y_to, z_bo, zb).cut(box(xa - 1, xb + 1, p.y_bottom + p.wall, y_ti, z_bi, zb + 1))
    add = []
    for (x0, x1), d in zip(bays, drives):                                   # filler under the connector ends
        add.append(box(x0, x1, p.y_bottom, d["y_face"] - 0.6, z_bi - 0.1, zb))
    for (x, y, dx, dy) in clamps + direct:
        add.append(cyl(4.4, zb - z_bi, "z", (x, y, z_bi)))
    for (x, y) in corners:
        add.append(cyl(4.4, zb - z_bi, "z", (x, y, z_bi)))
    for y in lug_y:
        add.append(box(xb - 12, xb, y - 4.5, y + 4.5, z_bo - 9.0, z_bo))
    body = body.union(_union(add))
    cuts = [box(xa - 1, xb + 1, y_ti + 0.6 - p.fit, y_ti + 1.8 + p.fit, zb - 1.5 - p.fit, zb + 1)]   # groove
    cuts += [cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, zb - p.insert_depth)) for (x, y, _, _) in clamps + direct]
    cuts += [cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, zb - p.insert_depth)) for (x, y) in corners]
    cuts += [cyl(p.insert_d / 2, p.insert_depth, "x", (xb - p.insert_depth, y, z_bo - 4.5)) for y in lug_y]
    # drive envelope + insertion clearance, so the filler never touches a drive
    for d in drives:
        cuts.append(box(d["xc"] - W2 - 0.4, d["xc"] + W2 + 0.4, d["y_face"] - 0.6, d["y_top"] + 0.5, zt - 0.3, zb + 1))
    body = body.cut(_union(cuts)).cut(keepout)

    # ------------------------------------------------------------ fan adapter
    s, hs, _hub = parts.FANS[p.fan]
    cyc, czc = (y_in + y_ti) / 2, (z_bi + z_ci) / 2 + p.fan_z_offset
    x0, x1, x2 = xb + p.fit, xb + p.neck, xb + p.neck + p.funnel_len
    w = p.wall
    rect_i = (y_in, y_ti, z_bi, z_ci)
    rect_o = (y_in - w, y_to, z_bo, z_co)
    r_i = s / 2 - 2.0
    # build each hollow piece on its own, then join: OCC mis-handles one big cut here
    neck = box(x0, x1, *rect_o).cut(box(x0 - 1, x1 + 1, *rect_i))
    funnel = _loft(x1 - 0.01, rect_o, x2, (cyc, czc, r_i + w)).cut(_loft(x1 - 0.02, rect_i, x2 + 0.01, (cyc, czc, r_i)))
    flange = cq.Workplane("YZ").rect(s, s).extrude(4.0).edges("|X").fillet(s * 0.055).translate((x2, cyc, czc))
    flange = flange.cut(cyl(r_i, 6, "x", (x2 - 1, cyc, czc)))
    ears = []
    lugs = [(y, z_co + 4.5) for y in lug_yc] + [(y, z_bo - 4.5) for y in lug_y]
    for y in lug_yc:
        ears.append(box(x0, x0 + 4.0, y - 4.5, y + 4.5, z_co - 0.1, z_co + 9.0))
    for y in lug_y:
        ears.append(box(x0, x0 + 4.0, y - 4.5, y + 4.5, z_bo - 9.0, z_bo + 0.1))
    adapter = neck.union(funnel).union(flange).union(_union(ears))
    acut = []
    for (y, z) in lugs:
        acut.append(cyl(p.m3_clear / 2, 6, "x", (x0 - 1, y, z)))
    fan_holes = [(cyc + sy * hs / 2, czc + sz * hs / 2) for sy in (-1, 1) for sz in (-1, 1)]
    for (y, z) in fan_holes:
        acut.append(cyl(1.9, 6, "x", (x2 - 1, y, z)))      # M4 self-tapping into the flange
    adapter = adapter.cut(_union(acut))

    # ------------------------------------------------------------ slot fillers between drives
    fillers = []
    for i, xm in enumerate(mids):
        a, b = drives[i], drives[i + 1]
        gapw = (b["xc"] - a["xc"]) - 2 * W2
        y0 = max(a["y_face"], b["y_face"]) + 6.0
        y1 = min(a["y_top"], b["y_top"])
        bar = box(xm - gapw / 2 + 0.25, xm + gapw / 2 - 0.25, y0, y1, zt + 0.4, zb - 0.4)
        head = box(xm - 6, xm + 6, max(a["y_top"], b["y_top"]) + 0.1, y_ti - 0.2, zt + 0.4, zb - 0.4)
        stem = box(xm - gapw / 2 + 0.25, xm + gapw / 2 - 0.25, y1 - 0.1, y_ti - 0.2, zt + 0.4, zb - 0.4)
        fillers.append(bar.union(head).union(stem))

    # ------------------------------------------------------------ split long parts between drives
    def split(wp, x_lo, x_hi, name):
        if x_hi - x_lo <= p.max_len or not mids:
            return {name: wp}
        n = math.ceil((x_hi - x_lo) / p.max_len)
        cuts_x = sorted({min(mids, key=lambda m: abs(m - (x_lo + (x_hi - x_lo) * k / n))) for k in range(1, n)})
        edges = [x_lo - 50] + cuts_x + [x_hi + 50]
        out = {}
        for k in range(len(edges) - 1):
            seg = wp.intersect(box(edges[k] + (p.fit / 2 if k else 0), edges[k + 1] - (p.fit / 2 if k < len(edges) - 2 else 0), -100, 300, -200, 200))
            out[f"{name}_{k + 1}"] = seg
        return out

    printed = {}
    printed.update(split(body, xa, xb, "body"))
    printed.update(split(cover, xa, xb, "cover"))
    printed["fan_adapter"] = adapter
    for i, f in enumerate(fillers):
        printed[f"slot_filler_{i + 1}"] = f

    # ------------------------------------------------------------ bought parts with placements
    def T(x=0, y=0, z=0, rx=0, ry=0, rz=0):
        loc = cq.Location(cq.Vector(x, y, z), (rx, ry, rz))
        return loc

    hw = []
    for d in drives:
        hw.append(("drive", f"drive_{d['ref']}", parts.drive_u3, (), d["T"]))
    hw.append(("bracket", "bracket", lambda: bracket, (), T()))
    for h in bracket_holes:
        hw.append(("M3x5 pan/cap screw (bracket tab)", "scr_brk", parts.screw_shcs, (3.0, 5.0), T(h[0], h[1], parts.BRACKET["t"])))
    for (x, y) in drive_screws:
        hw.append(("M3x10 cap screw (cover to drive)", "scr_drv", parts.screw_shcs, (3.0, 10.0), T(x, y, z_co)))
    for (x, y, _, _) in clamps:
        hw.append(("M3x12 cap screw (cover-card-body)", "scr_clamp", parts.screw_shcs, (3.0, 12.0), T(x, y, z_co)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(x, y, zb)))
    for (x, y, _, _) in direct:
        hw.append(("M3x6 cap screw (card to body)", "scr_direct", parts.screw_shcs, (3.0, 6.0), T(x, y, 0)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(x, y, zb)))
    for (x, y) in corners:
        hw.append(("M3x12 cap screw (cover-card-body)", "scr_corner", parts.screw_shcs, (3.0, 12.0), T(x, y, z_co)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(x, y, zb)))
    for (y, z) in lugs:
        hw.append(("M3x8 cap screw (fan adapter)", "scr_adp", parts.screw_shcs, (3.0, 8.0), T(x0 + 4.0, y, z, ry=90)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(xb, y, z, ry=90)))
    xf = x2 + 4.0
    hw.append((f"{p.fan}x{p.fan}x{int(p.fan_thick)} mm fan", "fan", parts.axial_fan, (p.fan, p.fan_thick), T(xf + p.fan_thick, cyc, czc, ry=-90)))
    for (y, z) in fan_holes:
        hw.append(("M4x12 self-tapping fan screw", "scr_fan", parts.screw_shcs, (4.0, 12.0), T(xf + 4.5, y, z, ry=90)))

    info = dict(
        params=asdict(p), drives=len(drives), card_length=L,
        duct=dict(x=[xa, xb], y=[p.y_bottom, y_to], z=[z_bo, z_co]),
        envelope=dict(length=xf + p.fan_thick, height_above_finger_bottom=y_to,
                      back_of_card=-z_bo - t, front_of_card=z_co,
                      fan_span_z=[czc - s / 2, czc + s / 2], fan_span_y=[cyc - s / 2, cyc + s / 2]),
        channel_area_mm2=dict(front=p.gap * (y_ti - y_in), back=p.gap * (y_ti - y_in)),
        clamp_points=[(round(x, 2), round(y, 2)) for (x, y, _, _) in clamps],
        direct_points=[(round(x, 2), round(y, 2)) for (x, y, _, _) in direct],
        corner_points=[(round(x, 2), round(y, 2)) for (x, y) in corners],
        drive_screw_points=[(round(x, 2), round(y, 2)) for (x, y) in drive_screws],
        fan_centre=dict(x=xf, y=cyc, z=czc),
        adapter=dict(x0=x0, lugs=lugs, rect_i=rect_i, rect_o=rect_o),
    )
    return dict(printed=printed, hardware=hw, info=info, board_solid=pcb)
