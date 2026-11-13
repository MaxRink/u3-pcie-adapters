"""Top-loading hot-plug cage for the cabled U.3 backplane, hung on a 120 mm front case fan.

Max, 2026-11-13: the drives go in from the top with the connector facing down, the cage is
anchored to the front 120 mm case fans, and there is a 6-drive version so that two cages behind
two fans hold 12 drives.

The backplane lies flat at the bottom, receptacles up, cable connectors on its underside. The
drives stand on it side by side at 20 mm pitch (5 mm air gaps); six drives are exactly 120 mm, one
fan wide. The fan blows horizontally through the gaps, across the drives' 70 mm width.

Frame: X across the drive stack, Y = air direction (fan rear face at Y = 0, fan in front of it),
Z up, Z = 0 at the cage's underside.

Printed parts, all printable flat without supports:
  fan_duct     flange on the fan's rear holes (105 mm pattern) and a short duct to the cage
  base         floor with the standoffs for the backplane
  comb_front, comb_rear   posts, bars in front of every drive and two guide shelves with a notch per drive
  side_left, side_right   thin side plates
  lid          drop-on cover that keeps the air in the gaps; lift it off to swap a drive

The backplane board is still in layout in its own thread, so this module carries a PLACEHOLDER
board built from the geometry that thread sent. `BackplaneSpec` holds every number the cage
depends on; when the real board lands, fill the spec from the board file and rebuild.
"""
from dataclasses import dataclass, asdict, field

import cadquery as cq

import parts
from card_shroud import _loft, _union
from parts import box, cyl


@dataclass
class BackplaneSpec:
    """Geometry sent by the backplane thread on 2026-11-13 20:35 (placement DRC clean, routing in
    progress, not pushed yet), converted to this module's frame: y = height - KiCad y."""
    width: float = 79.6
    height: float = 90.5
    thickness: float = 1.6
    drive_x: tuple = (9.8, 29.8, 49.8, 69.8)      # receptacle centre lines (drive thickness direction)
    drive_y: float = 42.0                         # receptacle centre (drive width direction)
    seat_z: float = 6.5                           # drive end face above the board: UNVERIFIED. 8.15 mm receptacle body,
    #                                               1.7 mm engagement assumed as on the right-angle sibling; the layout assumes 8.2
    holes: tuple = ((3.2, 75.0), (76.4, 75.0), (36.0, 4.2), (76.0, 4.2))   # round 3.2 mm
    vents: tuple = tuple((17.05 + 20.0 * k, 22.55 + 20.0 * k, 28.75, 55.25) for k in range(3))   # milled air slots (x0, x1, y0, y1)
    slimsas_x: tuple = (15.8, 55.8)               # underside, right angle, plug leaves over the y = 0 edge
    power_x: tuple = (28.0, 52.0)                 # two Mini-Fit Jr 2x4 right angle (12 V in, 12 V out), underside, plug leaves over the y = height edge
    placeholder: bool = True


def spec6():
    """The 6-drive board (12 drives in two cages behind two 120 mm fans), same source."""
    return BackplaneSpec(width=119.6, drive_x=tuple(9.8 + 20.0 * i for i in range(6)),
                         holes=((3.2, 75.0), (116.4, 75.0), (36.0, 4.2), (76.0, 4.2), (116.0, 4.2)),
                         vents=tuple((17.05 + 20.0 * k, 22.55 + 20.0 * k, 28.75, 55.25) for k in range(5)),
                         slimsas_x=(15.8, 55.8, 95.8), power_x=(48.0, 72.0))


@dataclass
class CageParams:
    gap_side: float = 2.5       # air gap between the outer drives and the side plates (drive-to-drive gap is 5 mm by pitch)
    max_width: float = 0.0      # > 0: shrink gap_side so that the cage is no wider than this (120 for cages on neighbouring fans)
    side: float = 1.6           # side plate thickness
    floor: float = 2.4
    under: float = 15.0         # clear height under the board for the right-angle cable connectors
    fan: int = 120
    fan_thick: float = 25.0
    duct: float = 34.0          # fan rear face to the cage; also the room for the cable plugs on the fan-side board edge
    duct_wall: float = 2.0
    post: float = 8.0
    bar: float = 3.0            # thickness of the bars in front of the drives
    shelf: float = 2.0          # guide shelf thickness
    grip: float = 6.0           # drive length that stands above the combs, to pull a drive by hand
    fit: float = 0.3
    insert_d: float = 4.0
    insert_depth: float = 6.5
    m3_clear: float = 3.4


def placeholder_board(s):
    """Board solid + connector models from the spec (stand-in until the board file is pushed)."""
    b = box(0, s.width, 0, s.height, -s.thickness, 0)
    cuts = [cyl(1.6, s.thickness + 2, "z", (x, y, -s.thickness - 1)) for (x, y) in s.holes]
    for (x0, x1, y0, y1) in s.vents:
        cuts.append(box(x0, x1, y0, y1, -s.thickness - 1, 1).edges("|Z").fillet(1.0))
    b = b.cut(_union(cuts))
    hw = []

    def T(x=0, y=0, z=0, rx=0, ry=0, rz=0):
        return cq.Location(cq.Vector(x, y, z), (rx, ry, rz))
    for i, x in enumerate(s.drive_x):
        hw.append(("U.3 vertical receptacle PSAS5F3130021TR", f"J{i + 1}", parts.u3_receptacle_vertical, (), T(x, s.drive_y, 0, rz=90)))
    for i, x in enumerate(s.slimsas_x):
        hw.append(("SlimSAS 8i right-angle receptacle U10A474240T", f"J1{i}", parts.slimsas_8i_ra, (), T(x, 7.9, -s.thickness, ry=180)))
    for i, x in enumerate(s.power_x):
        hw.append(("Mini-Fit Jr 2x4 right-angle header (PCIe 8-pin)", f"J2{i}", parts.minifit, (4, True), T(x + 6.3, s.height - 13.9, -s.thickness, ry=180)))
    return b, hw


def _rect_loft(y0, r0, y1, r1):
    """Ruled solid between two rectangles (x0, x1, z0, z1) at y0 and y1."""
    def wire(y, r):
        x0, x1, z0, z1 = r
        return cq.Wire.makePolygon([cq.Vector(x0, y, z0), cq.Vector(x1, y, z0), cq.Vector(x1, y, z1), cq.Vector(x0, y, z1)], close=True)
    return cq.Workplane("XY").add(cq.Solid.makeLoft([wire(y0, r0), wire(y1, r1)], True))


def build(spec=None, p=None):
    import numpy as np
    s, p = spec or BackplaneSpec(), p or CageParams()
    D = parts.DRIVE
    H2, fit = D["H"] / 2, p.fit
    span = s.drive_x[-1] - s.drive_x[0] + D["H"]
    gs = p.gap_side
    if p.max_width and span + 2 * (gs + p.side) > p.max_width:
        gs = (p.max_width - span - 2 * p.side) / 2
    assert gs >= 0.5, "no room for the drives between the side plates"
    Wc = max(span + 2 * (gs + p.side), 0.0)
    xs_in0, xs_in1 = p.side, Wc - p.side                 # inner faces of the side plates
    zb = p.floor + p.under + s.thickness                 # board top
    zd0, zd1 = zb + s.seat_z, zb + s.seat_z + D["L"]     # drive ends
    fs, hs, _hub = parts.FANS[p.fan]
    xf, zf = Wc / 2, fs / 2                              # fan centre: bottom edge level with the cage's underside
    ztop = max(zd1 - p.grip, 2 * zf)                     # top of combs and side plates
    Yc0 = p.duct                                         # front comb starts here
    Yb0 = Yc0 + p.post + 0.5                             # fan-side board edge
    Xb0 = (Wc - s.width) / 2

    def bx(x):                                           # board frame -> cage frame (board turned 180 deg: power edge to the fan)
        return Xb0 + s.width - x

    def by(y):
        return Yb0 + s.height - y

    Yd = by(s.drive_y)
    Yle, Yte = Yd - D["W"] / 2, Yd + D["W"] / 2          # drive leading / trailing edge
    Yend = 2 * Yd - Yc0                                  # rear comb is the front comb mirrored about the drives
    Xd = [bx(x) for x in s.drive_x]

    def T(x=0, y=0, z=0, rx=0, ry=0, rz=0):
        return cq.Location(cq.Vector(x, y, z), (rx, ry, rz))

    Lb = T(Xb0 + s.width, Yb0 + s.height, zb, rz=180)
    board0, bhw = placeholder_board(s)
    board = board0.rotate((0, 0, 0), (0, 0, 1), 180).translate((Xb0 + s.width, Yb0 + s.height, zb))
    hw = [(d, nm, fn, args, Lb * loc) for (d, nm, fn, args, loc) in bhw]

    # ------------------------------------------------------------ base
    pc = p.post / 2
    post_xy = [(xs_in0 + pc, Yc0 + pc), (xs_in1 - pc, Yc0 + pc), (xs_in0 + pc, Yend - pc), (xs_in1 - pc, Yend - pc)]
    base = [box(0, Wc, Yc0, Yend, 0, p.floor)]
    holes_w = [(bx(x), by(y)) for (x, y) in s.holes]
    for (x, y) in holes_w:
        base.append(cyl(4.0, p.under, "z", (x, y, p.floor)).intersect(box(0, Wc, Yc0, Yend, 0, 100)))
    base = _union(base)
    bcut = [cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, p.floor + p.under - p.insert_depth)) for (x, y) in holes_w]
    for (x, y) in post_xy:
        bcut.append(cyl(p.m3_clear / 2, p.floor + 2, "z", (x, y, -1)))
        bcut.append(cq.Workplane("XY").circle(3.1).workplane(offset=1.5).circle(1.6).loft(combine=True).translate((x, y, -0.01)))
    base = base.cut(_union(bcut))

    # ------------------------------------------------------------ combs
    z_sh = [zd0 + 28.0, ztop - p.shelf]                  # guide shelves
    yb0, yb1 = Yc0 + p.post - p.bar, Yc0 + p.post        # bars: the rear 3 mm of the comb
    comb = [box(xs_in0, xs_in0 + p.post, Yc0, Yc0 + p.post, p.floor, ztop), box(xs_in1 - p.post, xs_in1, Yc0, Yc0 + p.post, p.floor, ztop),
            box(xs_in0, xs_in1, Yc0, Yc0 + p.post, ztop - 7.0, ztop),                         # top rail
            box(xs_in0, xs_in1, yb0, yb1, zb + 0.5, zb + 5.0)]                                # low rail, above the cable plugs
    for x in Xd:
        comb.append(box(x - 5.0, x + 5.0, yb0, yb1, zb + 0.5, ztop))
    for z in z_sh:
        comb.append(box(xs_in0, xs_in1, yb1 - 0.1, Yle + 4.0, z, z + p.shelf))
    comb = _union(comb)
    ccut = [box(x - H2 - 0.35, x + H2 + 0.35, Yle - 0.4, Yle + 5.0, zb, ztop + 1) for x in Xd]
    side_z = [zb + 30.0, ztop - 22.0]
    for (x, y) in post_xy[:2]:
        ccut.append(cyl(p.insert_d / 2, p.insert_depth, "z", (x, y, p.floor - 0.01)))          # base screw
        ccut.append(cyl(2.1, 5.0, "z", (x, y, ztop - 5.0)))                                     # lid peg
        sx = 1 if x < Wc / 2 else -1
        for z in side_z:
            ccut.append(cyl(p.insert_d / 2, 5.9, "x", ((xs_in0 if sx > 0 else xs_in1 - 5.9), y, z)))
    tongue_x = [Wc / 2 - (Wc / 2 - 26.0), Wc / 2 + (Wc / 2 - 26.0)]
    comb_r = comb.cut(_union(ccut)).mirror("XZ", (0, Yd, 0))
    ccut += [cyl(p.insert_d / 2, p.insert_depth, "z", (x, Yc0 + pc, ztop - p.insert_depth)) for x in tongue_x]
    comb_f = comb.cut(_union(ccut))

    # ------------------------------------------------------------ side plates
    def side_plate(x0):
        sp = box(x0, x0 + p.side, Yc0, Yend, zb + 1.0, ztop)
        cuts = []
        for y in (Yc0 + pc, Yend - pc):
            for z in side_z:
                cuts.append(cyl(p.m3_clear / 2, p.side + 2, "x", (x0 - 1, y, z)))
        return sp.cut(_union(cuts))
    side_l, side_r = side_plate(0.0), side_plate(Wc - p.side)

    # ------------------------------------------------------------ fan duct
    dw = p.duct_wall
    y_f1, y_d1 = 3.0, Yc0 - fit
    r_fan = (xf - fs / 2, xf + fs / 2, zf - fs / 2, zf + fs / 2)
    r_cage = (0.0, Wc, 0.0, ztop)
    ins = lambda r: (r[0] + dw, r[1] - dw, r[2] + dw, r[3] - dw)
    shell = _rect_loft(y_f1 - 0.01, r_fan, y_d1, r_cage).cut(_rect_loft(y_f1 - 0.02, ins(r_fan), y_d1 + 0.01, ins(r_cage)))
    flange = box(r_fan[0], r_fan[1], 0, y_f1, r_fan[2], r_fan[3]).cut(cyl(fs / 2 - 2.0, y_f1 + 2, "y", (xf, -1, zf)))
    fan_holes = [(xf + sx * hs / 2, zf + sz * hs / 2) for sx in (-1, 1) for sz in (-1, 1)]
    flange = flange.cut(_union([cyl(2.25, y_f1 + 2, "y", (x, -1, z)) for (x, z) in fan_holes]))
    tongue = box(tongue_x[0] - 8, tongue_x[1] + 8, y_d1 - 0.1, Yc0 + p.post, ztop, ztop + 2.4)
    tcut = [cyl(p.m3_clear / 2, 5, "z", (x, Yc0 + pc, ztop - 1)) for x in tongue_x]
    tcut += [cq.Workplane("XY").circle(1.6).workplane(offset=1.5).circle(3.1).loft(combine=True).translate((x, Yc0 + pc, ztop + 0.91)) for x in tongue_x]
    duct = shell.union(flange).union(tongue.cut(_union(tcut)))
    duct = duct.cut(box(-100, Wc + 100, y_d1 - 22.0, y_d1 - 4.0, p.floor + 1.0, p.floor + p.under - 1.0))    # cable exits, both sides

    # ------------------------------------------------------------ lid
    zl = zd1 + 0.8
    lid = [box(0, Wc, Yc0, Yend, zl, zl + 1.6),
           box(0, p.side, Yc0, Yend, ztop + 0.1, zl), box(Wc - p.side, Wc, Yc0, Yend, ztop + 0.1, zl),
           box(0, Wc, Yend - 3.0, Yend, ztop + 0.1, zl), box(0, Wc, Yc0, Yc0 + 3.0, ztop + 2.6, zl)]
    for (x, y) in post_xy:
        lid.append(box(x - pc - (p.side if x < Wc / 2 else 0), x + pc + (p.side if x > Wc / 2 else 0), y - pc, y + pc, ztop + 0.1, zl))
        lid.append(cyl(1.8, 4.5, "z", (x, y, ztop - 4.3)))
    lid = _union(lid)

    printed = {"fan_duct": duct, "base": base, "comb_front": comb_f, "comb_rear": comb_r, "side_left": side_l, "side_right": side_r, "lid": lid}

    # ------------------------------------------------------------ bought parts
    for i, x in enumerate(Xd):
        M = np.eye(4)
        M[:3, 0], M[:3, 1], M[:3, 2] = (0, 1, 0), (0, 0, -1), (-1, 0, 0)      # mating direction down, bottom face to +X
        M[:3, 3] = (x + H2 - D["plug_z"], Yd, zd0)
        hw.append(("drive", f"drive_{i + 1}", parts.drive_u3, (), M))
    for (x, y) in holes_w:
        hw.append(("M3x6 cap screw (backplane to base)", "scr_bp", parts.screw_shcs, (3.0, 6.0), T(x, y, zb)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(x, y, p.floor + p.under)))
    for (x, y) in post_xy:
        hw.append(("M3x8 countersunk screw (base to comb)", "scr_base", parts.screw_csk, (3.0, 8.0), T(x, y, 0, rx=180)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(x, y, p.floor, rx=180)))
        left = x < Wc / 2
        for z in side_z:
            hw.append(("M3x6 countersunk screw (side plate)", "scr_side", parts.screw_csk, (3.0, 6.0), T(0.0 if left else Wc, y, z, ry=-90 if left else 90)))
            hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(xs_in0 if left else xs_in1, y, z, ry=-90 if left else 90)))
    for x in tongue_x:
        hw.append(("M3x8 countersunk screw (duct to cage)", "scr_duct", parts.screw_csk, (3.0, 8.0), T(x, Yc0 + pc, ztop + 2.4)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(x, Yc0 + pc, ztop)))
    hw.append((f"{p.fan}x{p.fan}x{int(p.fan_thick)} mm fan (the case's front fan)", "fan", parts.axial_fan, (p.fan, p.fan_thick), T(xf, -p.fan_thick, zf, rx=-90)))
    for (x, z) in fan_holes:
        hw.append(("M4x12 self-tapping fan screw", "scr_fan", parts.screw_shcs, (4.0, 12.0), T(x, y_f1, z, rx=-90)))
    info = dict(spec=asdict(s), params=asdict(p), drives=len(Xd), width=Wc, gap_side=round(gs, 2),
                envelope=dict(x=[min(0, r_fan[0]), max(Wc, r_fan[1])], y=[-p.fan_thick, Yend], z=[0, zl + 1.6]),
                board=dict(top_z=zb, origin_corner=[Xb0 + s.width, Yb0 + s.height], turned_deg=180, clear_under=p.under,
                           plug_room_fan_side=round(Yb0 - y_f1, 1)),
                fan_centre=dict(x=xf, z=zf), drive_x=[round(x, 2) for x in Xd], drive_z=[round(zd0, 2), round(zd1, 2)],
                guide_shelves_z=[round(z, 1) for z in z_sh], comb_top_z=ztop)
    return dict(printed=printed, hardware=hw, info=info, board_solid=board)
