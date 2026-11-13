"""Parametric CadQuery models of the bought parts: drive, connectors, fans, bracket, screws.

Every function returns a list of (cq.Workplane, material) pairs in the part's own frame, which is
documented per function. Materials are names from MATERIALS (colour + render finish).

Dimensions are from the form-factor specs and public datasheets as far as they are known;
values marked "approx" are appearance-level and must be checked against the real part before
relying on them for fit. See mech/README.md, "What is verified".
"""
import math

import cadquery as cq

# name -> (r, g, b, metallic, roughness)
MATERIALS = {
    "alu": (0.78, 0.79, 0.80, 1.0, 0.38),
    "alu_dark": (0.30, 0.31, 0.33, 1.0, 0.45),
    "steel": (0.72, 0.73, 0.75, 1.0, 0.30),
    "zinc": (0.62, 0.64, 0.66, 1.0, 0.35),
    "gold": (0.95, 0.72, 0.30, 1.0, 0.25),
    "black_plastic": (0.035, 0.035, 0.04, 0.0, 0.45),
    "lcp": (0.06, 0.06, 0.065, 0.0, 0.55),
    "nylon": (0.86, 0.85, 0.80, 0.0, 0.55),
    "label": (0.93, 0.93, 0.91, 0.0, 0.6),
    "label_dark": (0.10, 0.11, 0.13, 0.0, 0.5),
    "petg": (0.93, 0.36, 0.08, 0.0, 0.42),          # printed parts (orange)
    "petg_grey": (0.33, 0.35, 0.38, 0.0, 0.45),
    "petg_clear": (0.80, 0.86, 0.90, 0.0, 0.15),
    "fan_black": (0.03, 0.03, 0.035, 0.0, 0.35),
    "fr4": (0.05, 0.05, 0.055, 0.0, 0.5),
    "tpu": (0.08, 0.08, 0.09, 0.0, 0.8),
    "brass": (0.80, 0.62, 0.25, 1.0, 0.35),
}


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(r, h, axis="z", at=(0, 0, 0)):
    """Cylinder of radius r starting at `at` and extending +h along axis."""
    c = cq.Workplane("XY").circle(r).extrude(h)
    if axis == "x":
        c = c.rotate((0, 0, 0), (0, 1, 0), 90)
    elif axis == "y":
        c = c.rotate((0, 0, 0), (1, 0, 0), -90)
    return c.translate(at)


# ------------------------------------------------------------------ 2.5" U.3 drive (PM1735, 15 mm)
DRIVE = dict(
    L=100.45,          # SFF-8201 max length incl. connector
    W=69.85,           # SFF-8201 width
    H=15.0,            # 15 mm class (PM1735: 14.8 +- 0.2 nominal)
    plug_z=3.5,        # connector tongue centreline above the bottom face (SFF-8223, approx)
    hole_y=(14.0, 90.6),   # mounting hole rows, from the connector end (SFF-8201)
    hole_dx=61.72,     # bottom hole lateral spacing (SFF-8201)
    side_hole_z=3.0,   # side holes above the bottom face (SFF-8201)
    mass_g=210,
)


def drive_u3(h=None):
    """2.5" U.3 drive. Frame: plug (SFF-8639) centre at the origin, mating direction +y, the body
    extends to -y; z up, bottom face at z = -plug_z; x across the 69.85 mm width, centred.
    Bottom face = the side with the four M3 holes, top face = label side."""
    D = DRIVE
    h = h or D["H"]
    pz, W, L = D["plug_z"], D["W"], D["L"]
    y1, y0 = 0.0, -L
    body = box(-W / 2, W / 2, y0, y1, -pz, h - pz).edges("|Y").fillet(1.2)
    body = body.faces("<Y").edges().chamfer(0.6)
    top = h - pz
    # shallow label recess on top, ribbed heat-spreader strip near the connector end
    body = body.cut(box(-W / 2 + 4, W / 2 - 4, y0 + 5, y1 - 22, top - 0.3, top + 1))
    for i in range(9):
        yy = y1 - 19 + i * 1.9
        body = body.cut(box(-W / 2 + 4, W / 2 - 4, yy, yy + 0.9, top - 0.8, top + 1))
    # connector bay cut-out at the plug end
    body = body.cut(box(-21.5, 21.5, y1 - 5.2, y1 + 1, -pz - 1, -pz + 7.2))
    # mounting holes: 4 bottom, 4 side (M3)
    for yy in D["hole_y"]:
        for s in (-1, 1):
            body = body.cut(cyl(1.25, 4.0, "z", (s * D["hole_dx"] / 2, y1 - yy, -pz - 0.01)))
            body = body.cut(cyl(1.25, 4.0, "x", (s * W / 2 - (4.0 if s > 0 else 0) + (0.01 if s > 0 else -0.01), y1 - yy, -pz + D["side_hole_z"])))
    label = box(-W / 2 + 7, W / 2 - 7, y0 + 9, y1 - 26, top - 0.3, top - 0.2)
    bar = box(-W / 2 + 10, -W / 2 + 34, y0 + 12, y0 + 20, top - 0.2, top - 0.15)
    # SFF-8639 plug: housing with two tongue levels (approx 42.7 mm wide, 5 mm proud of the bay floor)
    plug = box(-21.0, 21.0, y1 - 5.2, y1 - 0.2, -2.6, 2.6)
    plug = plug.cut(box(-19.9, 19.9, y1 - 4.6, y1, -1.9, 1.9))
    tongue = box(-19.3, 12.0, y1 - 4.6, y1 - 0.3, -0.6, 0.6).union(box(13.2, 19.3, y1 - 4.6, y1 - 0.3, -0.6, 0.6))
    pins = None
    for i in range(30):
        x = -18.6 + i * 1.27
        if 11.6 < x < 13.4:
            continue
        p = box(x - 0.3, x + 0.3, y1 - 4.2, y1 - 0.6, 0.6, 0.66).union(box(x - 0.3, x + 0.3, y1 - 4.2, y1 - 0.6, -0.66, -0.6))
        pins = p if pins is None else pins.union(p)
    pcb = box(-W / 2 + 3, W / 2 - 3, y1 - 5.2, y1 - 5.0, -pz + 1.0, -pz + 6.5)
    return [(body, "alu"), (label, "label"), (bar, "label_dark"), (plug.union(tongue), "lcp"), (pins, "gold"), (pcb, "fr4")]


# ------------------------------------------------------------------ connectors
def u3_receptacle_ra():
    """Amphenol PSAS4F213002 right-angle SFF-8639 receptacle, KiCad 3D-model frame of the project
    footprint (x right, y up = -editor Y, z up from the board). Body X +-20.215, rear at y +3.2,
    mating face at y -11.75; drive plug centre 3.5 mm above the board (approx, see README)."""
    yf, yb, h = -11.75, 3.2, 5.3
    body = box(-20.215, 20.215, yf, yb, 0.15, h)
    body = body.cut(box(-19.6, 19.6, yf - 0.1, yf + 6.2, 1.5, h - 0.1 + 1))     # open-top mating bay
    floor = box(-19.6, 19.6, yf, yf + 6.2, 0.15, 1.5)
    wall = box(-19.3, 19.3, yf + 0.5, yf + 5.6, 2.75, 4.25).cut(box(-18.9, 18.9, yf + 0.4, yf + 5.0, 3.05, 3.95))
    ears = box(-23.5, -20.2, yb - 4.2, yb, 0.15, 3.4).union(box(20.2, 23.5, yb - 4.2, yb, 0.15, 3.4))
    pegs = cyl(0.85, 1.5, "z", (-19.0, 0, -1.4)).union(cyl(0.85, 1.5, "z", (19.0, 0, -1.4)))
    tails = None
    for i in range(34):
        x = -16.5 + i * 1.0
        t = box(x - 0.15, x + 0.15, yb, yb + 1.3, 0.0, 0.25)
        tails = t if tails is None else tails.union(t)
    return [(body.union(floor).union(wall).union(ears).union(pegs), "lcp"), (tails, "gold")]


def u3_receptacle_vertical():
    """Amphenol PSAS5F313002 vertical SMT SFF-8639 receptacle (backplane). Frame: footprint
    centre at origin, z up from the board, long axis x; 8.15 mm tall (datasheet), body approx 44 x 6.3."""
    h = 8.15
    body = box(-22.0, 22.0, -3.15, 3.15, 0.15, h)
    body = body.cut(box(-20.0, 20.0, -2.0, 2.0, 2.5, h + 1))
    tongue = box(-19.3, 12.0, -0.6, 0.6, 2.5, h - 0.6).union(box(13.2, 19.3, -0.6, 0.6, 2.5, h - 0.6))
    tails = None
    for i in range(34):
        x = -16.5 + i * 1.0
        t = box(x - 0.15, x + 0.15, -4.3, 4.3, 0.0, 0.25)
        tails = t if tails is None else tails.union(t)
    pegs = cyl(0.85, 1.5, "z", (-21.0, 0, -1.4)).union(cyl(0.85, 1.5, "z", (21.0, 0, -1.4)))
    return [(body.union(tongue).union(pegs), "lcp"), (tails, "gold")]


def oculink_4i_ra():
    """Amphenol G14A421211112HR OCuLink 4i right-angle receptacle, project footprint frame.
    Shell X +-7.65, Y -4.535..+4.535 (mating face at -y in the model frame), 5.6 mm tall (approx)."""
    yf, yb, h = -4.535, 4.535, 5.6
    shell = box(-7.65, 7.65, yf, yb, 0.1, h).edges("|Y").fillet(0.5)
    shell = shell.cut(box(-6.9, 6.9, yf - 0.1, yf + 6.5, 0.9, h - 0.6))
    tongue = box(-6.0, 6.0, yf + 0.8, yf + 6.5, 2.4, 3.2)
    insul = box(-6.9, 6.9, yf + 6.4, yb - 0.3, 0.9, h - 0.6)
    latch = box(-3.2, -1.6, yf + 0.5, yf + 2.5, h - 0.05, h + 0.25).union(box(1.6, 3.2, yf + 0.5, yf + 2.5, h - 0.05, h + 0.25))
    legs = cyl(0.5, 1.6, "z", (-5.685, 1.4, -1.5)).union(cyl(0.5, 1.6, "z", (5.685, 1.4, -1.5)))
    return [(shell.union(latch).union(legs), "steel"), (tongue.union(insul), "lcp")]


def slimsas_8i_ra():
    """SlimSAS 8i (SFF-8654) right-angle receptacle, Amphenol U10A474240T. Frame: centre of the
    body, mating face at -y, z up. Envelope 23.5 x 15.8 x 6.7 mm (from the backplane layout's
    reading of the drawing); the plug needs 26 mm of width."""
    w, d, h = 23.5, 15.8, 6.7
    shell = box(-w / 2, w / 2, -d / 2, d / 2, 0.1, h).edges("|Y").fillet(0.5)
    shell = shell.cut(box(-w / 2 + 0.8, w / 2 - 0.8, -d / 2 - 0.1, -d / 2 + 8.0, 0.9, h - 0.7))
    tongue = box(-w / 2 + 2.0, w / 2 - 2.0, -d / 2 + 0.8, -d / 2 + 8.0, 2.9, 3.8)
    insul = box(-w / 2 + 0.8, w / 2 - 0.8, -d / 2 + 7.9, d / 2 - 0.3, 0.9, h - 0.7)
    return [(shell, "steel"), (tongue.union(insul), "lcp")]


def minifit(rows=3, horizontal=True):
    """Molex Mini-Fit Jr 2 x rows header (PCIe 6-pin: rows=3, 8-pin: rows=4), KiCad library frame
    of Molex_Mini-Fit_Jr_5569 horizontal: pin 1 at origin, pins along +x at 4.2 mm, housing toward
    +y in the model frame (mating face at y = 13.9). 12.4 mm tall (approx: datasheet 12.8 max)."""
    x0, x1 = -2.7, (rows - 1) * 4.2 + 2.7
    if not horizontal:
        body = box(x0, x1, -7.9, 2.4, 0.0, 12.8)
        for i in range(rows):
            for j in range(2):
                body = body.cut(box(i * 4.2 - 1.6, i * 4.2 + 1.6, -5.5 * j - 1.6 + 0.0, -5.5 * j + 1.6, 3.0, 13.0))
        return [(body, "nylon")]
    body = box(x0, x1, 1.1, 13.9, 0.0, 12.4)
    pins = None
    for i in range(rows):
        for z in (1.6, 7.1):
            body = body.cut(box(i * 4.2 - 1.75, i * 4.2 + 1.75, 4.0, 14.0, z, z + 3.6))
            p = box(i * 4.2 - 0.5, i * 4.2 + 0.5, 4.0, 11.5, z + 1.3, z + 2.3)
            pins = p if pins is None else pins.union(p)
    latch = box((x0 + x1) / 2 - 1.8, (x0 + x1) / 2 + 1.8, 8.5, 13.9, 12.4, 13.9)
    return [(body.union(latch), "nylon"), (pins, "gold")]


def pin_header(n=3, pitch=2.54, shunt_at=None):
    """Vertical 1xN 2.54 mm header, centred, pins along x. Optional shunt over pins (i, i+1)."""
    w = n * pitch
    base = box(-w / 2, w / 2, -1.25, 1.25, 0.0, 2.5)
    pins = None
    for i in range(n):
        x = -w / 2 + pitch / 2 + i * pitch
        p = box(x - 0.32, x + 0.32, -0.32, 0.32, 0.0, 8.5)
        pins = p if pins is None else pins.union(p)
    out = [(base, "black_plastic"), (pins, "gold")]
    if shunt_at is not None:
        x = -w / 2 + pitch * (shunt_at + 1)
        out.append((box(x - 2.5, x + 2.5, -1.2, 1.2, 2.5, 8.6), "black_plastic"))
    return out


# ------------------------------------------------------------------ fans
FANS = {   # size: (frame, hole spacing, thickness options, hub dia)
    40: (40.0, 32.0, 14.0), 60: (60.0, 50.0, 26.0), 80: (80.0, 71.5, 36.0),
    92: (92.0, 82.5, 40.0), 120: (120.0, 105.0, 46.0),
}


def axial_fan(size=92, thick=38.0, blades=7):
    """Axial fan. Frame: centred on the rotor axis, axis = z, frame from z=0 (intake side) to
    z=thick (exhaust side, with the struts)."""
    s, hs, hub = FANS[size]
    frame = cq.Workplane("XY").rect(s, s).extrude(thick).edges("|Z").fillet(s * 0.055)
    frame = frame.cut(cyl(s / 2 - 1.6, thick + 2, "z", (0, 0, -1)))
    # open-flange style: relieve the frame between the two flanges
    web = cq.Workplane("XY").rect(s + 2, s + 2).extrude(thick - 9).translate((0, 0, 4.5))
    keep = cyl(s / 2 + 0.9, thick, "z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            keep = keep.union(cyl(4.2, thick, "z", (sx * hs / 2, sy * hs / 2, 0)))
    frame = frame.cut(web.cut(keep))
    for sx in (-1, 1):
        for sy in (-1, 1):
            frame = frame.cut(cyl(2.15, thick + 2, "z", (sx * hs / 2, sy * hs / 2, -1)))
    struts = cyl(hub / 2, 3.0, "z", (0, 0, thick - 3.0))
    for k in range(4):
        st = box(0, s / 2 - 1.0, -1.6, 1.6, thick - 3.0, thick - 0.3).rotate((0, 0, 0), (0, 0, 1), 45 + 90 * k + 12)
        struts = struts.union(st)
    rotor = cyl(hub / 2, thick - 6.5, "z", (0, 0, 1.5)).faces("<Z").edges().fillet(2.0)
    r_tip = s / 2 - 2.6
    span = r_tip - hub / 2 + 1.0
    chord = thick - 9.0
    for k in range(blades):
        bl = (cq.Workplane("XY").box(span, 1.4, chord / math.cos(math.radians(38)), centered=(False, True, True))
              .rotate((0, 0, 0), (1, 0, 0), 38).translate((hub / 2 - 1.0, 0, 1.5 + (thick - 6.5) / 2)))
        bl = bl.intersect(cyl(r_tip, thick - 7.0, "z", (0, 0, 1.6)))
        rotor = rotor.union(bl.rotate((0, 0, 0), (0, 0, 1), k * 360.0 / blades))
    sticker = cyl(hub / 2 - 2, 0.1, "z", (0, 0, thick - 0.05))
    return [(frame.union(struts), "fan_black"), (rotor, "black_plastic"), (sticker, "label")]


# ------------------------------------------------------------------ PCIe bracket
BRACKET = dict(t=0.86, w=18.42, z0=-4.11, y0=-9.2, y1=112.75, x=-0.9)


BRACKET_TAB_Y = (9.35, 94.75)      # bracket tab holes on a full-height card, above the bottom of the gold fingers


def pcie_bracket(tab_y=(9.35, 94.75), tab_x=7.5):
    """Full-height PCI/PCIe bracket in the card frame (x along the card from its bracket-end edge,
    y up from the bottom of the gold fingers, z = 0 on the component side). Appearance-level: the
    plate position follows the CEM drawing to about +-1 mm. Two tabs screw to the card's bracket
    holes from the component side."""
    B = BRACKET
    t, x, z0, z1 = B["t"], B["x"], B["z0"], B["z0"] + B["w"]
    plate = box(x - t, x, B["y0"] + 6, B["y1"], z0, z1)
    tongue = box(x - t, x, B["y0"], B["y0"] + 6.5, z0 + 3.8, z1 - 3.8)
    lip = box(x - t - 11.4, x, B["y1"] - t, B["y1"], z0, z1 + 3.0)
    lip = lip.cut(cyl(2.2, 3, "y", (x - t - 6.4, B["y1"] - 2, z1 - 1.4)))
    lip = lip.cut(box(x - t - 6.4 - 2.2, x - t - 6.4 + 2.2, B["y1"] - 2, B["y1"] + 1, z1 - 1.4, z1 + 4))
    out = plate.union(tongue).union(lip)
    for ty in tab_y:
        tab = box(x - t, tab_x + 4.5, ty - 4.0, ty + 4.0, 0.0, t)
        tab = tab.cut(cyl(1.6, 3, "z", (tab_x, ty, -1)))
        out = out.union(tab)
    return [(out, "zinc")]


# ------------------------------------------------------------------ fasteners
def screw_shcs(d=3.0, length=10.0):
    """Socket head cap screw (ISO 4762). Frame: under-head plane at z=0, shank toward -z."""
    hd, hh = d * 1.83, d
    head = cyl(hd / 2, hh, "z").faces(">Z").edges().chamfer(0.25)
    head = head.cut(cq.Workplane("XY").polygon(6, d * 0.96).extrude(d * 0.6).translate((0, 0, hh - d * 0.6 + 0.01)))
    shank = cyl(d / 2, length, "z", (0, 0, -length))
    return [(head.union(shank), "steel")]


def screw_csk(d=3.0, length=8.0):
    """Countersunk screw (ISO 10642). Frame: head top at z=0, shank toward -z."""
    hd = d * 2.0
    head = cq.Workplane("XY").circle(hd / 2).workplane(offset=-(hd - d) / 2).circle(d / 2).loft(combine=True)
    shank = cyl(d / 2, length, "z", (0, 0, -length))
    return [(head.union(shank), "steel")]


def screw_632_hex(length=6.0):
    """6-32 hex washer-head case screw (bracket screw). Under-head plane at z=0."""
    head = cq.Workplane("XY").polygon(6, 7.3).extrude(2.6).union(cyl(4.1, 0.6, "z"))
    return [(head.union(cyl(1.75, length, "z", (0, 0, -length))), "zinc")]


def heat_insert_m3(length=5.7):
    """M3 brass heat-set insert (Ruthex/CNC Kitchen style, 4.6 OD x 5.7). Top at z=0, body toward -z."""
    return [(cyl(2.3, length, "z", (0, 0, -length)).cut(cyl(1.25, length + 1, "z", (0, 0, -length - 0.5))), "brass")]
