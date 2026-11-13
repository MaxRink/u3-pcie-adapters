"""Top-feed shroud for the slot cards: 120 mm fans lie flat behind the drives, one per two drives.

Air path: fan -> chamber behind the back wall -> up and over the drive ends (U-turn in the top
cap) -> down both faces of every drive in `gap` mm channels -> out at the connector strip (front)
and between the receptacles towards the motherboard (back). Every drive gets fresh air and the
path is short, so ordinary 120 mm fans work; this is the "parallel" layout of tools/thermal.
It adds no length to the card, but about 44 mm of thickness behind it and `cap` mm of height.

Printed parts:
  body      back wall with end walls and clamp pillars (back of the card)
  manifold  fan wall, chamber walls and top cap; screwed to the body from inside
  cover     front plate over the card window, screwed into the drives' bottom holes
  filler    bars between neighbouring drives
"""
import math
from dataclasses import dataclass, asdict

import cadquery as cq

import parts
from card_shroud import _union
from parts import box, cyl


@dataclass
class TopParams:
    gap: float = 5.0
    wall: float = 2.4
    cap: float = 10.0           # height of the U-turn over the drive ends
    chamber: float = 16.0       # depth of the chamber between back wall and fan wall
    fan: int = 120
    fan_thick: float = 25.0
    x_start: float = 1.0
    y_bottom: float = 14.0
    clear: float = 0.5
    fit: float = 0.2
    max_len: float = 250.0
    insert_d: float = 4.0
    insert_depth: float = 6.5
    m3_clear: float = 3.4


def build(board, p=None):
    p = p or TopParams()
    t, w = board.t, p.wall
    drives = board.drives()
    assert drives and all(d["back"] for d in drives)
    L = board.L
    zb = -t
    zt = min(d["z_top"] for d in drives)
    z_bi, z_ci = zt - p.gap, zb + p.gap
    z_bo, z_co = z_bi - w, z_ci + w
    z_fi = z_bo - p.chamber                    # fan wall, chamber side
    z_fo = z_fi - w
    y_dtop = max(d["y_top"] for d in drives)
    y_ti = y_dtop + p.cap
    y_to = y_ti + w
    W2 = parts.DRIVE["W"] / 2
    fs, hs, _hub = parts.FANS[p.fan]
    # fans: one per pair of drives
    nf = math.ceil(len(drives) / 2)
    xf = []
    for k in range(nf):
        pair = drives[2 * k: 2 * k + 2]
        xf.append((pair[0]["xc"] + pair[1]["xc"]) / 2 if len(pair) == 2 else (xf[-1] + fs + 6 if xf else pair[0]["xc"]))
    xa = p.x_start
    xb = max(L, xf[-1] + fs / 2 + 4)
    xb_card = L
    yc = y_ti - 2 - fs / 2
    y_ch0 = yc - fs / 2 - 2
    mids = [(drives[i]["xc"] + drives[i + 1]["xc"]) / 2 for i in range(len(drives) - 1)]
    bays = list(zip([xa] + mids, mids + [xb_card]))
    y_sk = [d["y_face"] - 2.4 for d in drives]

    holes = board.mount_holes()
    bracket_holes = [h for h in holes if abs(h[2] - h[3]) < 0.01 and h[0] < 12]
    clamps = [h for h in holes if h not in bracket_holes]
    direct = [h for h in clamps if h[1] < min(y_sk) - 8.0]
    clamps = [h for h in clamps if h not in direct]
    y_corner = y_dtop - 6.0
    corners = [(min(6.5, drives[0]["xc"] - W2 - 6.0), y_corner), (max(drives[-1]["xc"] + W2 + 6.0, xb_card - 5.5), y_corner)]
    if corners[1][0] > xb_card - 4.3:           # no room beyond the last drive (4-drive card): go above its end
        corners[1] = (xb_card - 6.5, y_dtop + p.cap / 2)

    pcb = board.solid(holes_min=99)
    keep = [pcb]
    for (x0, x1, y0, y1, z0, z1, ref) in board.part_boxes():
        c = p.clear
        keep.append(box(x0 - c, x1 + c, y0 - c, y1 + c, min(z0, -t / 2) - (c if z0 < -t else 0), max(z1, -t / 2) + (c if z1 > 0 else 0)))
    bracket = parts.pcie_bracket(tab_y=[h[1] for h in bracket_holes], tab_x=bracket_holes[0][0] if bracket_holes else 7.5)
    for h in bracket_holes:
        keep.append(box(-2, h[0] + 5.5, h[1] - 5, h[1] + 5, 0, 4.2))
    keepout = _union(keep)

    # ------------------------------------------------------------ cover: plate, end ribs, top wall; open at the strip
    cov = []
    for (x0, x1), ys in zip(bays, y_sk):
        cov.append(box(x0, x1, ys, y_to, z_ci, z_co))
    cov.append(box(xa, xb_card, y_ti, y_to, zb, z_ci))                       # top wall
    cov.append(box(xa, xb_card, y_ti + 0.6, y_ti + 1.8, zb - 1.5, zb))       # tongue into the manifold's top wall
    cov.append(box(xa, xa + w, y_sk[0], y_to, zb, z_ci))                     # end ribs close the channel sideways
    cov.append(box(xb_card - w, xb_card, y_sk[-1], y_to, zb, z_ci))
    drive_screws = []
    for d in drives:
        for dy in parts.DRIVE["hole_y"]:
            for s in (-1, 1):
                x, y = d["xc"] + s * parts.DRIVE["hole_dx"] / 2, d["y_face"] + d["dir"] * dy
                cov.append(cyl(3.6, z_ci - zb, "z", (x, y, zb)))
                drive_screws.append((x, y))
    for (x, y, dx, dy) in clamps:
        cov.append(cyl(4.2, z_ci, "z", (x, y, 0)))
        cov.append(cyl(6.5, w, "z", (x, y, z_ci)))
    for (x, y) in corners:
        cov.append(cyl(4.2, z_ci - zb, "z", (x, y, zb)))
    cover = _union(cov)
    hc = [cyl(p.m3_clear / 2, 30, "z", (x, y, zb - 5)) for (x, y) in drive_screws + corners]
    hc += [cyl(p.m3_clear / 2, 30, "z", (x, y, -5)) for (x, y, _, _) in clamps]
    cover = cover.cut(_union(hc)).cut(keepout).intersect(box(0.3, xb_card, -50, 400, -100, 100))

    # ------------------------------------------------------------ body: back wall up to the drive ends, end walls, pillars
    y_bw = y_dtop + 1.0
    bod = [box(xa, xb_card, p.y_bottom, y_bw, z_bo, z_bi),
           box(xa, xa + w, p.y_bottom, y_ti - p.fit, z_bo, zb), box(xb_card - w, xb_card, p.y_bottom, y_ti - p.fit, z_bo, zb)]
    for (x, y, dx, dy) in clamps + direct:
        bod.append(cyl(4.4, zb - z_bi, "z", (x, y, z_bi)))
    for (x, y) in corners:
        bod.append(cyl(4.4, zb - z_bi, "z", (x, y, z_bi)))
        if y > y_bw:
            bod.append(box(x - 4.4, x + 4.4, y_bw - 0.1, y, z_bo, z_bi + 3))    # web that carries a pillar above the back wall
    body = _union(bod)
    # manifold standoff points: either side of each fan, two heights
    sp = []
    for x in sorted({round(v, 2) for f in xf for v in (f - fs / 2 - 6, f + fs / 2 + 6)}):
        if xa + 6 < x < xb_card - 6:
            sp += [(x, yc - 38), (x, yc + 30)]
    sp = [(x, y) for (x, y) in sp if y < y_bw - 6 and all(abs(x - d["xc"]) > 0 for d in drives)]
    bc = [cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, zb - p.insert_depth)) for (x, y, _, _) in clamps + direct]
    bc += [cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, zb - p.insert_depth)) for (x, y) in corners]
    for (x, y) in sp:                                                       # countersunk from the channel side
        bc.append(cyl(p.m3_clear / 2, w + 2, "z", (x, y, z_bo - 1)))
        bc.append(cq.Workplane("XY").circle(3.1).workplane(offset=-1.5).circle(1.6).loft(combine=True).translate((x, y, z_bi + 0.01)))
    for d in drives:
        bc.append(box(d["xc"] - W2 - 0.4, d["xc"] + W2 + 0.4, d["y_face"] - 0.6, d["y_top"] + 0.5, zt - 0.3, zb + 1))
    body = body.cut(_union(bc)).cut(keepout)

    # ------------------------------------------------------------ manifold: fan wall, chamber walls, top cap
    man = [box(xa, xb, y_ch0 - w, y_to, z_fo, z_fi),                        # fan wall
           box(xa, xb, y_ch0 - w, y_ch0, z_fi, z_bo),                       # chamber floor
           box(xa, xa + w, y_ch0 - w, y_to, z_fi, z_bo), box(xb - w, xb, y_ch0 - w, y_to, z_fi, z_bo),
           box(xa, xb, y_ti, y_to, z_fi, zb)]                               # top wall over chamber, back wall and drives
    if xb > xb_card + 0.5:                                                  # chamber overhangs the card end: close it
        man.append(box(xb_card + p.fit, xb, y_ch0 - w, y_to, z_bo, z_bo + w))
        man.append(box(xb_card + p.fit, xb_card + p.fit + w, y_bw, y_to, z_bo, zb))
    for (x, y) in sp:
        man.append(cyl(4.4, p.chamber, "z", (x, y, z_fi)))
    manifold = _union(man)
    mc = [box(xa - 1, xb_card + p.fit, y_ti + 0.6 - p.fit, y_ti + 1.8 + p.fit, zb - 1.5 - p.fit, zb + 1)]   # groove for the cover tongue
    fan_holes = []
    for f in xf:
        mc.append(cyl(fs / 2 - 2.0, w + 2, "z", (f, yc, z_fo - 1)))
        for sx in (-1, 1):
            for sy in (-1, 1):
                fan_holes.append((f + sx * hs / 2, yc + sy * hs / 2))
    mc += [cyl(1.9, w + 2, "z", (x, y, z_fo - 1)) for (x, y) in fan_holes]
    mc += [cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, z_bo - p.insert_depth)) for (x, y) in sp]
    manifold = manifold.cut(_union(mc)).cut(body).cut(keepout)

    fillers = []
    for i, xm in enumerate(mids):
        a, b = drives[i], drives[i + 1]
        gapw = (b["xc"] - a["xc"]) - 2 * W2
        y0 = max(a["y_face"], b["y_face"]) + 6.0
        y1 = min(a["y_top"], b["y_top"])
        bar = box(xm - gapw / 2 + 0.25, xm + gapw / 2 - 0.25, y0, y1 + 3.0, zt + 0.4, zb - 0.4)
        head = box(xm - 6, xm + 6, max(a["y_top"], b["y_top"]) + 0.1, max(a["y_top"], b["y_top"]) + 3.0, zt + 0.4, zb - 0.4)
        fillers.append(bar.union(head))

    def split(wp, x_lo, x_hi, name):
        if x_hi - x_lo <= p.max_len or not mids:
            return {name: wp}
        n = math.ceil((x_hi - x_lo) / p.max_len)
        cuts_x = sorted({min(mids, key=lambda m: abs(m - (x_lo + (x_hi - x_lo) * k / n))) for k in range(1, n)})
        edges = [x_lo - 50] + cuts_x + [x_hi + 50]
        return {f"{name}_{k + 1}": wp.intersect(box(edges[k] + (p.fit / 2 if k else 0), edges[k + 1] - (p.fit / 2 if k < len(edges) - 2 else 0), -100, 300, -200, 200))
                for k in range(len(edges) - 1)}

    printed = {}
    printed.update(split(body, xa, xb_card, "body"))
    printed.update(split(manifold, xa, xb, "manifold"))
    printed.update(split(cover, xa, xb_card, "cover"))
    for i, f in enumerate(fillers):
        printed[f"slot_filler_{i + 1}"] = f

    def T(x=0, y=0, z=0, rx=0, ry=0, rz=0):
        return cq.Location(cq.Vector(x, y, z), (rx, ry, rz))

    hw = [("drive", f"drive_{d['ref']}", parts.drive_u3, (), d["T"]) for d in drives]
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
    for (x, y) in sp:
        hw.append(("M3x8 countersunk screw (body to manifold)", "scr_man", parts.screw_csk, (3.0, 8.0), T(x, y, z_bi)))
        hw.append(("M3 heat-set insert", "ins_man", parts.heat_insert_m3, (), T(x, y, z_bo)))
    for f in xf:
        hw.append((f"{p.fan}x{p.fan}x{int(p.fan_thick)} mm fan", "fan", parts.axial_fan, (p.fan, p.fan_thick), T(f, yc, z_fo - p.fan_thick)))
    for (x, y) in fan_holes:
        hw.append(("M4x12 self-tapping fan screw", "scr_fan", parts.screw_shcs, (4.0, 12.0), T(x, y, z_fo - 4.5, rx=180)))

    info = dict(
        style="top", params=asdict(p), drives=len(drives), fans=nf, card_length=L,
        envelope=dict(length=xb, height_above_finger_bottom=y_to, back_of_card=-(z_fo - p.fan_thick) - t, front_of_card=z_co),
        fan_centres=[(round(f, 2), round(yc, 2)) for f in xf],
        clamp_points=[(round(x, 2), round(y, 2)) for (x, y, _, _) in clamps],
        direct_points=[(round(x, 2), round(y, 2)) for (x, y, _, _) in direct],
        corner_points=[(round(x, 2), round(y, 2)) for (x, y) in corners],
        manifold_points=[(round(x, 2), round(y, 2)) for (x, y) in sp],
    )
    return dict(printed=printed, hardware=hw, info=info, board_solid=pcb)
