"""Footprint generators for the cabled U.3 backplane and its host cards (KiCad 7 file format).

Dimensions are transcribed from the vendor drawings, see ../docs/reference-data.md:
  * Amphenol PSAS5F313002xxx rev 3 sheet 2 (vertical SMT SFF-8639 receptacle, U.3 rated)
  * Amphenol U10A474xxxT (SlimSAS 8i, SFF-8654, right angle SMT)
  * TI NJX0064A (DS160PR810, 64-pin WQFN 5.5 x 10, 0.4 mm pitch)
Footprint coordinates are KiCad's: x right, y down.
"""
import os, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "lib", "u3adapter.pretty")


def u():
    return str(uuid.uuid4())


def pad_smd(num, x, y, w, h, layers='"F.Cu" "F.Paste" "F.Mask"', shape="roundrect", rr=0.15, extra=""):
    r = f" (roundrect_rratio {rr})" if shape == "roundrect" else ""
    return (f'  (pad "{num}" smd {shape} (at {x:.4f} {y:.4f}) (size {w:.3f} {h:.3f}) '
            f'(layers {layers}){r}{extra} (tstamp "{u()}"))\n')


def pad_npth(x, y, d):
    return (f'  (pad "" np_thru_hole circle (at {x:.4f} {y:.4f}) (size {d:.3f} {d:.3f}) (drill {d:.3f}) '
            f'(layers "*.Cu" "*.Mask") (tstamp "{u()}"))\n')


def pad_pth(num, x, y, d, drill):
    return (f'  (pad "{num}" thru_hole circle (at {x:.4f} {y:.4f}) (size {d:.3f} {d:.3f}) (drill {drill:.3f}) '
            f'(layers "*.Cu" "*.Mask") (tstamp "{u()}"))\n')


def line(x1, y1, x2, y2, layer, w=0.12):
    return (f'  (fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width {w}) (type solid)) '
            f'(layer "{layer}") (tstamp "{u()}"))\n')


def rect(x1, y1, x2, y2, layer, w=0.05):
    return "".join([line(x1, y1, x2, y1, layer, w), line(x2, y1, x2, y2, layer, w),
                    line(x2, y2, x1, y2, layer, w), line(x1, y2, x1, y1, layer, w)])


def text(kind, val, x, y, layer, hide=False):
    h = " hide" if hide else ""
    return (f'  (fp_text {kind} "{val}" (at {x:.3f} {y:.3f}) (layer "{layer}"){h} (tstamp "{u()}")\n'
            f'    (effects (font (size 1 1) (thickness 0.15))))\n')


def header(name, descr, tags, attr="smd"):
    return (f'(footprint "{name}" (version 20221018) (generator pcbnew)\n  (layer "F.Cu")\n'
            f'  (descr "{descr}")\n  (tags "{tags}")\n  (attr {attr})\n')


def write(name, body):
    os.makedirs(LIB, exist_ok=True)
    with open(os.path.join(LIB, name + ".kicad_mod"), "w") as f:
        f.write(body + ")\n")


# ---------------------------------------------------------------- U.3 vertical receptacle
# Origin = connector centreline on the peg line.  Row 1 (40 pads) is drawn above the peg line in the
# drawing, so it is at negative y here.
U3_ROW1 = [f"E{i}" for i in range(7, 17)] + [f"S{i}" for i in range(8, 29)] + [f"E{i}" for i in range(17, 26)]
U3V = "Amphenol_PSAS5F313002_SFF-8639_U3_Vertical_SMD"


def u3v_pads():
    """{pin: (x, y, w, h)}"""
    pos = {}
    for i, n in enumerate(U3_ROW1):
        pos[n] = (-15.48 + 0.80 * i, -2.32, 0.50, 1.60)
    for i in range(7):
        pos[f"S{i + 1}"] = (-15.87 + 1.27 * i, 1.71, 0.60, 1.70)
    for i in range(6):
        pos[f"E{i + 1}"] = (-7.075 + 0.80 * i, 2.29, 0.50, 2.20)
    for i in range(15):
        pos[f"P{i + 1}"] = (-1.905 + 1.27 * i, 1.71, 0.60, 1.70)
    return pos


def u3v():
    s = header(U3V, "Amphenol PSAS5F3130021TR vertical SMT SFF-8639 receptacle, U.3 (SFF-TA-1001) 32 GT/s, "
               "8.15 mm high; drawing PSAS5F313002XXX rev 3", "U.3 U.2 SFF-8639 SFF-TA-1001 NVMe backplane")
    s += text("reference", "REF**", 0, -5.0, "F.SilkS")
    s += text("value", U3V, 0, 5.2, "F.Fab")
    pos = u3v_pads()
    assert abs(pos["E25"][0] - 15.72) < 1e-6 and abs(pos["P15"][0] - 15.875) < 1e-6 and len(pos) == 68
    for n, (x, y, w, h) in pos.items():
        s += pad_smd(n, x, y, w, h, rr=0.2)
    s += pad_npth(-18.58, 0, 0.90) + pad_npth(18.58, 0, 1.30)
    for x in (-21.80, 21.80):                       # SMT retainer clips
        s += pad_smd("MP", x, 0, 2.60, 2.40, rr=0.1)
    s += rect(-22.725, -2.75, 22.725, 2.75, "F.Fab", 0.1)
    s += rect(-23.4, -3.4, 23.4, 3.0, "F.CrtYd")          # body +-2.75; the E1-E6 pad tips reach 3.39
    for x1, x2 in ((-22.725, -16.2), (16.4, 22.725)):
        s += line(x1, -2.86, x2, -2.86, "F.SilkS")
    s += line(-22.84, -2.86, -22.84, -1.5, "F.SilkS") + line(22.84, -2.86, 22.84, -1.5, "F.SilkS")
    s += line(-16.9, 3.0, -16.9, 3.6, "F.SilkS", 0.2)           # S1 marker
    write(U3V, s)


# ---------------------------------------------------------------- SlimSAS 8i right angle
# Origin = midpoint of the two dia 1.30 pegs.  Mating face at y = -10.30, tails at +y (row A, then row B).
SS8 = "Amphenol_U10A474_SlimSAS_8i_SFF-8654_RA_SMD"
SS8_FRONT = -10.30


def ss8_pads():
    pos = {}
    for i in range(37):
        x = 10.80 - 0.60 * i
        pos[f"A{i + 1}"] = (x, 2.70, 0.35, 1.30)
        pos[f"B{i + 1}"] = (x, 5.05, 0.35, 1.30)
    return pos


def ss8():
    s = header(SS8, "Amphenol U10A474240T SlimSAS 8i (SFF-8654 74 pos) right angle SMT receptacle, 2.2 mm latch pins; "
               "drawing U10A474XXXT", "SlimSAS SFF-8654 8i PCIe SFF-9402")
    s += text("reference", "REF**", 0, 7.4, "F.SilkS")
    s += text("value", SS8, 0, -11.5, "F.Fab")
    for n, (x, y, w, h) in ss8_pads().items():
        s += pad_smd(n, x, y, w, h, shape="rect")
    s += pad_npth(-10.95, 0, 1.30) + pad_npth(10.95, 0, 1.30)
    for x in (-11.63, 11.63):
        for y in (-5.15, -8.15):
            s += pad_pth("SH", x, y, 1.15, 0.70)
    s += rect(-11.75, SS8_FRONT, 11.75, 5.5, "F.Fab", 0.1)
    s += rect(-12.4, SS8_FRONT - 0.2, 12.4, 6.1, "F.CrtYd")
    s += line(-11.87, -9.2, -11.87, -10.42, "F.SilkS") + line(-11.87, -10.42, 11.87, -10.42, "F.SilkS")
    s += line(11.87, -10.42, 11.87, -9.2, "F.SilkS")
    s += line(-11.87, -4.0, -11.87, -1.0, "F.SilkS") + line(11.87, -4.0, 11.87, -1.0, "F.SilkS")
    s += line(11.5, 2.0, 11.5, 3.3, "F.SilkS", 0.2)             # A1 marker
    write(SS8, s)


# ---------------------------------------------------------------- DS160PR810 WQFN-64 (NJX0064A)
NJX = "TI_NJX0064A_WQFN-64_5.5x10mm_P0.4mm_EP4.1x8.6mm"


def njx_pads():
    pos = {}
    for i in range(23):                                # 1..23 left side, top to bottom
        pos[str(1 + i)] = (-2.65, -4.4 + 0.4 * i, 0.60, 0.20)
        pos[str(55 - i)] = (2.65, -4.4 + 0.4 * i, 0.60, 0.20)   # 55 top right .. 33 bottom right
    for i in range(9):                                 # 24..32 bottom, left to right; 64..56 top
        pos[str(24 + i)] = (-1.6 + 0.4 * i, 4.9, 0.20, 0.60)
        pos[str(64 - i)] = (-1.6 + 0.4 * i, -4.9, 0.20, 0.60)
    return pos


def njx():
    s = header(NJX, "TI NJX0064A WQFN-64, 5.5 x 10 mm, 0.4 mm pitch, exposed pad 4.1 x 8.6 (DS160PR810)",
               "WQFN QFN redriver")
    s += text("reference", "REF**", 0, -6.3, "F.SilkS")
    s += text("value", NJX, 0, 6.3, "F.Fab")
    for n, (x, y, w, h) in njx_pads().items():
        s += pad_smd(n, x, y, w, h, rr=0.25)
    # exposed pad: copper + mask whole, paste split into 8 windows (about 60 % coverage)
    s += pad_smd("65", 0, 0, 4.10, 8.60, layers='"F.Cu" "F.Mask"', shape="rect")
    for ix in (-1, 1):
        for iy in (-1.5, -0.5, 0.5, 1.5):
            s += pad_smd("65", ix * 1.0, iy * 2.1, 1.55, 1.65, layers='"F.Paste"', shape="roundrect", rr=0.1)
    s += rect(-2.75, -5.0, 2.75, 5.0, "F.Fab", 0.1)
    s += rect(-3.3, -5.55, 3.3, 5.55, "F.CrtYd")
    for sx in (-1, 1):
        for sy in (-1, 1):
            s += line(sx * 2.86, sy * 5.11, sx * 2.86, sy * 4.75, "F.SilkS")
            s += line(sx * 2.86, sy * 5.11, sx * 1.95, sy * 5.11, "F.SilkS")
    s += line(-3.2, -4.9, -3.2, -4.3, "F.SilkS", 0.2)           # pin 1 marker
    write(NJX, s)


# ---------------------------------------------------------------- TI TPS25982 eFuse, RGE0024M VQFN 4x4
RGE = "TI_RGE0024M_VQFN-24_4x4mm_P0.5mm_SplitEP"


def rge():
    """TI drawing RGE0024M (4223975/B): 24 x 0.24 x 0.575 lands, 0.5 pitch; split exposed pad 2.7 wide:
    IN pad 1.45 tall at -0.625 (IN/OUT half: pins 1-3, 16-24), GND pad 0.85 tall at +0.925 (GND pins 4/5/14 half).
    VERIFY against the TI land pattern before ordering (pad split orientation inferred from the pin map)."""
    name = RGE
    b = header(name, "TI RGE0024M VQFN-24 4x4 mm, 0.5 mm pitch, split exposed pad (25 = IN, 26 = GND), TPS25982",
               "TPS25982 eFuse VQFN RGE")
    b += text("reference", "REF**", 0, -3.0, "F.SilkS")
    b += text("value", name, 0, 3.0, "F.Fab")
    c, L, W = 1.8125, 0.575, 0.24
    for i in range(6):
        o = -1.25 + 0.5 * i
        b += pad_smd(str(1 + i), -c, o, L, W, rr=0.25)          # left, top -> bottom
        b += pad_smd(str(7 + i), o, c, W, L, rr=0.25)           # bottom, left -> right
        b += pad_smd(str(13 + i), c, -o, L, W, rr=0.25)         # right, bottom -> top
        b += pad_smd(str(19 + i), -o, -c, W, L, rr=0.25)        # top, right -> left
    b += pad_smd("25", 0, -0.625, 2.7, 1.45, rr=0.05)
    b += pad_smd("26", 0, 0.925, 2.7, 0.85, rr=0.05)
    b += rect(-2.0, -2.0, 2.0, 2.0, "F.Fab", 0.1)
    b += rect(-2.4, -2.4, 2.4, 2.4, "F.CrtYd", 0.05)
    b += line(-2.1, -2.1, -1.5, -2.1, "F.SilkS")
    write(name, b)


if __name__ == "__main__":
    u3v(); ss8(); njx(); rge()
    print("wrote footprints to", os.path.normpath(LIB))
