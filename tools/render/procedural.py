"""Simplified 3D models for parts that have no STEP model in the KiCad library.

Every model is built in the footprint's library frame as KiCad 3D models are: x right,
y up (= -Y of the footprint editor), z up from the board surface, origin at the footprint
anchor. Dimensions come from the footprint Fab layer and public datasheets; they are
appearance models only (good to ~0.5 mm), not mechanical references.
"""
import cadquery as cq

BLACK = (0.08, 0.08, 0.09)
NYLON = (0.12, 0.12, 0.13)
STEEL = (0.72, 0.73, 0.75)
GOLD = (0.85, 0.68, 0.33)
TAN = (0.76, 0.62, 0.42)


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def u3_receptacle():
    """Amphenol PSAS4F213002 SFF-8639 right-angle receptacle. Footprint: body X +-20.215,
    Y -3.2..+11.75 (editor frame, drive mates toward +Y). Height ~7.3 mm (drawing envelope)."""
    y_front, y_back, h = -11.75, 3.2, 7.3
    body = _box(-20.215, 20.215, y_front, y_back, 0, h)
    # mating cavity + tongue (68-position SFF-8639 plug slot)
    cav = _box(-19.0, 19.0, y_front - 0.1, y_front + 6.0, 1.2, h - 1.2)
    body = body.cut(cav)
    tongue = _box(-18.4, 17.6, y_front + 0.6, y_front + 6.0, 3.2, 4.4)
    keys = _box(-19.0, -18.4, y_front, y_front + 6.0, 1.2, h - 1.2).union(
        _box(17.6, 19.0, y_front, y_front + 6.0, 1.2, h - 1.2))
    pegs = _box(-19.6, -18.6, -1.0, 0.0, -1.0, 0.0).union(_box(18.6, 19.6, -1.0, 0.0, -1.0, 0.0))
    return [(body.union(keys).union(pegs), BLACK), (tongue, NYLON)]


def oculink_4i():
    """Amphenol G14A421211112HR OCuLink 4i RA SMT. Shell X +-7.65, Y -4.535..+4.535
    (editor frame, front/mating face at +Y). Height ~6.6 mm."""
    y_front, y_back, h = -4.535, 4.535, 6.6
    shell = _box(-7.65, 7.65, y_front, y_back, 0, h)
    shell = shell.cut(_box(-6.6, 6.6, y_front - 0.1, y_front + 6.0, 1.0, h - 1.0))
    tongue = _box(-5.9, 5.9, y_front + 0.6, y_front + 6.0, 2.9, 3.7)
    latch = _box(-2.0, 2.0, y_front, y_front + 2.5, h - 0.2, h + 0.4)
    return [(shell.union(latch), STEEL), (tongue, NYLON)]


def minifit_6_horizontal():
    """Molex Mini-Fit Jr 2x3 horizontal (PCIe 6-pin). Housing X -2.7..11.1, Y -1.1..-13.9
    in editor frame (mating face at -13.9), so +1.1..+13.9 in model y. Height ~12.4 mm."""
    body = _box(-2.7, 11.1, 1.1, 13.9, 0.0, 12.4)
    for i in range(3):
        for z in (2.6, 6.8):
            body = body.cut(_box(i * 4.2 - 1.5, i * 4.2 + 1.5, 10.0, 14.0, z, z + 3.0))
    latch = _box(2.4, 6.0, 9.0, 13.9, 12.4, 13.6)
    return [(body.union(latch), NYLON)]


def chip(lx, ly, h, color=TAN, cap=0.5):
    body = _box(-lx / 2 + cap, lx / 2 - cap, -ly / 2, ly / 2, 0, h)
    caps = _box(-lx / 2, -lx / 2 + cap, -ly / 2, ly / 2, 0, h).union(_box(lx / 2 - cap, lx / 2, -ly / 2, ly / 2, 0, h))
    return [(body, color), (caps, STEEL)]


REGISTRY = {
    "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD": u3_receptacle,
    "Amphenol_G14A421211112HR_OCuLink_4i_RA_SMD": oculink_4i,
    "Molex_Mini-Fit_Jr_5569-06A2_2x03_P4.20mm_Horizontal": minifit_6_horizontal,
    "Fuse_1812_4532Metric": lambda: chip(4.5, 3.2, 1.6, (0.2, 0.2, 0.22)),
}


def lookup(fpid):
    name = fpid.split(":")[-1]
    for k, f in REGISTRY.items():
        if name.startswith(k):
            return f
    return None


def box_from_fab(fab, h=1.0):
    x0, y0, x1, y1 = fab
    return [(_box(x0, x1, -y1, -y0, 0, h), (0.3, 0.3, 0.32))]


# ---------------------------------------------------------------- 2.5" U.3 drive (appearance model)
DRIVE_L, DRIVE_W = 100.45, 69.85
ALU = (0.70, 0.71, 0.73)
LABEL = (0.16, 0.17, 0.19)


def drive_25(h=15.0, plug_z=4.6):
    """2.5-inch drive, SFF-8201 envelope (100.45 x 69.85 x h). Built so its SFF-8639 plug centre
    sits at the origin and the drive extends toward -y (away from a right-angle receptacle's
    mating face). plug_z = plug centreline above the drive underside (approximate)."""
    y0 = -0.4                      # drive end face, just in front of the receptacle face
    body = _box(-DRIVE_W / 2, DRIVE_W / 2, y0 - DRIVE_L, y0, -plug_z, h - plug_z)
    body = body.edges("|Y").fillet(1.0)
    top = h - plug_z
    recess = _box(-DRIVE_W / 2 + 3, DRIVE_W / 2 - 3, y0 - DRIVE_L + 3, y0 - 6, top - 0.4, top + 0.1)
    body = body.cut(recess)
    label = _box(-DRIVE_W / 2 + 6, DRIVE_W / 2 - 6, y0 - DRIVE_L + 8, y0 - 30, top - 0.4, top - 0.25)
    holes = None
    for yy in (-14.0, -90.6):                       # SFF-8201 side mounting holes (M3)
        for zz in (3.0,):
            for xs in (-1, 1):
                c = cq.Workplane("YZ").circle(1.5).extrude(2.0).translate((xs * DRIVE_W / 2 - (2.0 if xs > 0 else 0) + (0 if xs > 0 else 0), y0 + yy, -plug_z + zz))
                holes = c if holes is None else holes.union(c)
    body = body.cut(holes)
    plug = _box(-19.0 + 0.6, 19.0 - 0.6, y0, y0 + 5.6, -1.6, 1.6).cut(_box(-18.4, 17.6, y0, y0 + 5.7, -0.6, 0.6))
    return [(body, ALU), (label, LABEL), (plug, (0.1, 0.1, 0.11))]
