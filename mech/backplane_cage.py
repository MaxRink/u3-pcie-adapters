"""Printable 4-drive cage for the cabled U.3 backplane, with an 80 mm fan.

The backplane board is still in layout in its own thread, so this module carries a PLACEHOLDER
board built from the geometry that thread sent (79.6 x 84.5 mm, 20 mm drive pitch, vertical
Amphenol PSAS5F313 receptacles, SlimSAS and power on the back). `BackplaneSpec` holds every
number the cage depends on; when the real board lands, fill the spec from the board file
(receptacle positions, M3 holes) and rebuild.

Frame: x across the drive stack, y up, z = drive insertion axis; the board's drive-side surface
is z = 0 and the drives extend to +z. Air runs from the fan at +z along the drives to the
backplane and leaves through the board's milled openings and the vents next to it: the "facing
stack" layout of docs/thermal.
"""
from dataclasses import dataclass, asdict, field

import cadquery as cq

import parts
from card_shroud import _loft, _union
from parts import box, cyl


@dataclass
class BackplaneSpec:
    """Geometry sent by the backplane thread on 2026-11-13 (layout in progress, not pushed yet),
    converted to this module's frame: y = 84.5 - KiCad y."""
    width: float = 79.6
    height: float = 84.5
    thickness: float = 1.6
    drive_x: tuple = (9.8, 29.8, 49.8, 69.8)      # receptacle centre lines (drive thickness direction)
    drive_y: float = 42.0                         # receptacle centre (drive width direction)
    seat_z: float = 6.5                           # drive end face above the board: UNVERIFIED. 8.15 mm receptacle body,
    #                                               1.7 mm engagement assumed as on the right-angle sibling; the layout assumes 8.2
    holes: tuple = ((3.5, 80.5), (76.1, 80.5), (35.8, 4.0), (74.6, 4.0))   # round 3.2 mm NPTH
    vents: tuple = ((14.6, 20.1, 34.4, 52.5), (34.6, 40.1, 34.4, 52.5), (54.6, 60.1, 34.4, 52.5), (74.6, 78.1, 34.4, 52.5),
                    (17.4, 20.1, 26.0, 34.5), (37.4, 40.1, 26.0, 34.5), (57.4, 60.1, 26.0, 34.5))   # milled air slots (x0, x1, y0, y1)
    slimsas_x: tuple = (15.8, 55.8)               # back side, mating face flush with the bottom edge
    power_x: tuple = (28.0, 52.0)                 # two Mini-Fit Jr 2x4 vertical (12 V in, pass-through), back side, y 79.5
    placeholder: bool = True


def spec6():
    """Concept for the 6-drive board Max asked for on 2026-11-13 (12 drives across two 120 mm fans):
    the 4-drive geometry stretched to six receptacles at 20 mm pitch. Not a real board yet."""
    return BackplaneSpec(width=119.6, drive_x=tuple(9.8 + 20.0 * i for i in range(6)),
                         holes=((3.5, 80.5), (116.1, 80.5), (35.8, 4.0), (114.6, 4.0)),
                         vents=tuple((x0 + 20.0 * k, x1 + 20.0 * k, y0, y1) for k in (0, 1, 2, 3, 4) for (x0, x1, y0, y1) in ((14.6, 20.1, 34.4, 52.5), (17.4, 20.1, 26.0, 34.5))),
                         slimsas_x=(15.8, 55.8, 95.8), power_x=(28.0, 72.0))


@dataclass
class CageParams:
    gap_side: float = 2.5       # air gap between the outer drives and the cage walls (drive-to-drive gap is 5 mm by pitch)
    wall: float = 2.4
    fan: int = 120              # 120x25 by default (Max, 2026-11-13); 80 gives a straight plate without funnel
    fan_thick: float = 25.0
    plenum: float = 14.0        # straight section between the drive ends and the fan or funnel
    funnel_len: float = 30.0    # only used when the fan is larger than the tube
    rail: float = 2.2           # guide rib height
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
        hw.append(("Mini-Fit Jr 2x4 vertical header (PCIe 8-pin)", f"J2{i}", parts.minifit, (4, False), T(x + 6.3, 79.5 + 2.75, -s.thickness, ry=180)))
    return b, hw


def build(spec=None, p=None):
    s, p = spec or BackplaneSpec(), p or CageParams()
    D = parts.DRIVE
    w = p.wall
    H2 = D["H"] / 2
    yd0, yd1 = s.drive_y - D["W"] / 2, s.drive_y + D["W"] / 2
    z0, z1 = s.seat_z, s.seat_z + D["L"]
    xi0, xi1 = s.drive_x[0] - H2 - p.gap_side, s.drive_x[-1] + H2 + p.gap_side
    yi0, yi1 = yd0 - p.fit, yd1 + p.fit
    board, hw = placeholder_board(s)

    def T(x=0, y=0, z=0, rx=0, ry=0, rz=0):
        return cq.Location(cq.Vector(x, y, z), (rx, ry, rz))

    zc1 = z1 + 2.0                                  # cage tube end
    tube = box(xi0 - w, xi1 + w, yi0 - w, yi1 + w, 0, zc1).cut(box(xi0, xi1, yi0, yi1, -1, zc1 + 1))
    add = []
    # guide ribs between drives, top and bottom
    for a, b in zip(s.drive_x[:-1], s.drive_x[1:]):
        xm = (a + b) / 2
        rw = (b - a) - D["H"] - 2 * p.fit
        for (ya, yb) in ((yi0, yi0 + p.rail), (yi1 - p.rail, yi1)):
            add.append(box(xm - rw / 2, xm + rw / 2, ya, yb, 16, zc1))
    for x in (xi0, xi1 - (p.gap_side - p.fit)):
        for (ya, yb) in ((yi0, yi0 + p.rail), (yi1 - p.rail, yi1)):
            add.append(box(x, x + p.gap_side - p.fit, ya, yb, 16, zc1))
    # board mounting: legs to the lower holes, lugs to the upper holes
    bh = min(9.0, s.seat_z - 0.5)                    # bosses stay under the seated drives
    for (x, y) in s.holes:
        if y < yi0 - w:
            add.append(box(x - 4, x + 4, y - 4, yi0 - w + 0.1, 0, bh))
        elif y > yi1 + w - 2:
            add.append(box(x - 4, x + 4, yi1 + w - 0.1, min(y + 4, s.height), 0, bh))
        else:
            add.append(cyl(4, bh, "z", (x, y, 0)).intersect(box(xi0 - w, xi1 + w, 0, s.height, 0, bh)))
    # ledge under the board corner that has no hole (SlimSAS plug in the way on the back)
    add.append(box(xi0 - w, xi0 + 6, 0, yi0 - w + 0.1, 0, 3.0))
    # pads for the fan-plate screws
    pad_y = [(yi0 + yi1) / 2 - 22, (yi0 + yi1) / 2 + 22]
    for y in pad_y:
        add.append(box(xi0 - w - 3.6, xi0 - w + 0.1, y - 5, y + 5, zc1 - 16, zc1 - 4))
        add.append(box(xi1 + w - 0.1, xi1 + w + 3.6, y - 5, y + 5, zc1 - 16, zc1 - 4))
    cage = tube.union(_union(add))
    cuts = [cyl(p.insert_d / 2, bh - 0.4, "z", (x, y, -0.01)) for (x, y) in s.holes]
    # exhaust vents next to the backplane: sides and top
    for k in range(4):
        y = yi0 + 6 + k * 16.5
        cuts.append(box(xi0 - w - 1, xi0 + 0.5, y, y + 11, 9.5, 24))
        cuts.append(box(xi1 - 0.5, xi1 + w + 1, y, y + 11, 9.5, 24))
    for a, b in zip(s.drive_x[:-1], s.drive_x[1:]):
        cuts.append(box((a + b) / 2 - 6, (a + b) / 2 + 6, yi1 - 0.5, yi1 + w + 1, 9.5, 24))
    # drive retention: slotted holes over the drives' side M3 holes (both edges)
    side = []
    for x in s.drive_x:
        hx = x + H2 - D["side_hole_z"]      # drive bottom faces +x
        for dz in D["hole_y"]:
            for (ya, yb) in ((yi0 - w - 1, yi0 + p.rail + 1), (yi1 - p.rail - 1, yi1 + w + 1)):
                cuts.append(cq.Workplane("XZ").slot2D(6.2, p.m3_clear, 90).extrude(-(yb - ya)).translate((hx, ya, z0 + dz)))
            side.append((hx, z0 + dz))
    for y in pad_y:
        cuts.append(cyl(p.insert_d / 2, 5.5, "x", (xi0 - w - 3.61, y, zc1 - 10)))
        cuts.append(cyl(p.insert_d / 2, 5.5, "x", (xi1 + w + 3.61 - 5.5, y, zc1 - 10)))
    cage = cage.cut(_union(cuts)).cut(board)
    for (_, _, fn, args, loc) in hw:                      # connector keep-outs
        for wp, _m in fn(*args):
            bb = wp.val().located(loc).BoundingBox()
            if bb.zmax > 0.5:
                cage = cage.cut(box(bb.xmin - 0.5, bb.xmax + 0.5, bb.ymin - 0.5, bb.ymax + 0.5, max(bb.zmin, 0) - 0.01, bb.zmax + 0.5))

    # fan plate: sleeve over the tube end + plenum + fan flange
    fs, hs, _ = parts.FANS[p.fan]
    cx, cy = (xi0 + xi1) / 2, (yi0 + yi1) / 2
    zs0, zs1 = zc1 - 14, zc1 + p.plenum
    o = w + p.fit
    plate = box(xi0 - o - w, xi1 + o + w, yi0 - o - w, yi1 + o + w, zs0, zs1)
    plate = plate.cut(box(xi0 - o, xi1 + o, yi0 - o, yi1 + o, zs0 - 1, zc1 + p.fit))        # socket for the tube
    plate = plate.cut(box(xi0, xi1, yi0, yi1, zc1, zs1 + 1))                                 # plenum
    r_i = fs / 2 - 2.0
    if fs > min(xi1 - xi0, yi1 - yi0) + 12:            # fan larger than the tube: funnel out to it
        def loft_z(z_a, rect, z_b, circ):
            return _loft(z_a, rect, z_b, circ).rotate((0, 0, 0), (1, 1, 1), -120)
        ro = (xi0 - o - w, xi1 + o + w, yi0 - o - w, yi1 + o + w)
        ri = (xi0, xi1, yi0, yi1)
        funnel = loft_z(zs1 - 0.01, ro, zs1 + p.funnel_len, (cx, cy, r_i + w)).cut(loft_z(zs1 - 0.02, ri, zs1 + p.funnel_len + 0.01, (cx, cy, r_i)))
        zs1 = zs1 + p.funnel_len
        plate = plate.union(funnel)
        flange = cq.Workplane("XY").rect(fs, fs).extrude(4).edges("|Z").fillet(fs * 0.055).translate((cx, cy, zs1))
    else:
        flange = cq.Workplane("XY").rect(max(fs, xi1 - xi0 + 2 * (o + w)), max(fs, yi1 - yi0 + 2 * (o + w))).extrude(4).translate((cx, cy, zs1))
    plate = plate.union(flange.cut(cyl(r_i, 6, "z", (cx, cy, zs1 - 1))))
    fan_holes = [(cx + sx * hs / 2, cy + sy * hs / 2) for sx in (-1, 1) for sy in (-1, 1)]
    pc = [cyl(1.9, 6, "z", (x, y, zs1 - 1)) for (x, y) in fan_holes]
    plate = plate.cut(_union(pc))
    # pockets that slide over the cage's screw pads; one M3 screw through each into the pad's insert
    bumps, pockets = [], []
    for y in pad_y:
        for (xa, xb_) in ((xi0 - w - 3.6 - p.fit - w, xi0 - o), (xi1 + o, xi1 + w + 3.6 + p.fit + w)):
            bumps.append(box(xa, xb_, y - 5.3 - w, y + 5.3 + w, zs0, zc1 - 4 + p.fit + w))
        pockets.append(box(xi0 - w - 3.6 - p.fit, xi0 - o + 0.1, y - 5.3, y + 5.3, zs0 - 1, zc1 - 4 + p.fit))
        pockets.append(box(xi1 + o - 0.1, xi1 + w + 3.6 + p.fit, y - 5.3, y + 5.3, zs0 - 1, zc1 - 4 + p.fit))
        pockets.append(cyl(p.m3_clear / 2, 2 * (xi1 - xi0), "x", (xi0 - 30, y, zc1 - 10)).cut(box(xi0 - o, xi1 + o, y - 3, y + 3, zc1 - 13, zc1 - 7)))
    plate = plate.union(_union(bumps)).cut(_union(pockets))
    xs_out = (xi0 - w - 3.6 - p.fit - w, xi1 + w + 3.6 + p.fit + w)

    for i, x in enumerate(s.drive_x):
        hw.append(("drive", f"drive_{i + 1}", parts.drive_u3, (), _drive_loc(x - H2, s.drive_y, z0)))
    for (x, y) in s.holes:
        hw.append(("M3x8 cap screw (backplane to cage)", "scr_bp", parts.screw_shcs, (3.0, 8.0), T(x, y, -s.thickness, rx=180)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (bh - 0.6,), T(x, y, 0, rx=180)))
    for (hx, hz) in side:
        hw.append(("M3x6 cap screw (drive side hole)", "scr_drv", parts.screw_shcs, (3.0, 6.0), T(hx, yi1 + w, hz, rx=-90)))
        hw.append(("M3x6 cap screw (drive side hole)", "scr_drv", parts.screw_shcs, (3.0, 6.0), T(hx, yi0 - w, hz, rx=90)))
    for y in pad_y:
        hw.append(("M3x8 cap screw (fan plate)", "scr_plate", parts.screw_shcs, (3.0, 8.0), T(xs_out[0], y, zc1 - 10, ry=-90)))
        hw.append(("M3x8 cap screw (fan plate)", "scr_plate", parts.screw_shcs, (3.0, 8.0), T(xs_out[1], y, zc1 - 10, ry=90)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(xi0 - w - 3.6, y, zc1 - 10, ry=-90)))
        hw.append(("M3 heat-set insert", "ins", parts.heat_insert_m3, (), T(xi1 + w + 3.6, y, zc1 - 10, ry=90)))
    zf = zs1 + 4
    hw.append((f"{p.fan}x{p.fan}x{int(p.fan_thick)} mm fan", "fan", parts.axial_fan, (p.fan, p.fan_thick), T(cx, cy, zf + p.fan_thick, rx=180)))
    for (x, y) in fan_holes:
        hw.append(("M4x12 self-tapping fan screw", "scr_fan", parts.screw_shcs, (4.0, 12.0), T(x, y, zf + 4.5)))
    info = dict(spec=asdict(s), params=asdict(p), envelope=dict(x=[xi0 - w - 6, xi1 + w + 6], y=[0, max(s.height, yi1 + w)], z=[-s.thickness, zf + p.fan_thick]),
                board_holes=list(s.holes), drive_side_screws=[(round(a, 2), round(b, 2)) for a, b in side])
    printed = {"cage": cage, "fan_plate": plate}
    return dict(printed=printed, hardware=hw, info=info, board_solid=board)


def _drive_loc(x_bottom, y_c, z_face):
    """Drive frame -> cage frame: plug mating direction (+y) to -z, bottom face (-z) to +x."""
    import numpy as np
    M = np.eye(4)
    # columns = images of the drive's x, y, z axes
    M[:3, 0] = (0, 1, 0)
    M[:3, 1] = (0, 0, -1)
    M[:3, 2] = (-1, 0, 0)       # right-handed: x' x y' = (0,1,0)x(0,0,-1) = (-1,0,0)
    M[:3, 3] = (x_bottom + parts.DRIVE["H"] - parts.DRIVE["plug_z"], y_c, z_face)
    return M
