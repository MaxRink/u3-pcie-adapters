"""Footprint generators for the U.3 adapter project (KiCad 7 file format).

Sources:
  * PSAS4F213002xxx: Amphenol customer drawing PSAS4F213002XXX rev 3 (docs/ref/psas4f213002xxx.pdf),
    sheet 2 "Recommended PCB layout (top view)".
  * G14A421211112HR: pad geometry from Antmicro hardware-components (Apache-2.0),
    kicad-footprints/amphenol-g14a421211112hr, re-emitted in KiCad 7 format.
"""
import os, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "lib", "u3adapter.pretty")


def u():
    return str(uuid.uuid4())


def pad_smd(num, x, y, w, h, layers='"F.Cu" "F.Paste" "F.Mask"', shape="roundrect", rr=0.15):
    extra = f" (roundrect_rratio {rr})" if shape == "roundrect" else ""
    return (f'  (pad "{num}" smd {shape} (at {x:.4f} {y:.4f}) (size {w:.3f} {h:.3f}) '
            f'(layers {layers}){extra} (tstamp "{u()}"))\n')


def pad_npth(x, y, d):
    return (f'  (pad "" np_thru_hole circle (at {x:.4f} {y:.4f}) (size {d:.3f} {d:.3f}) (drill {d:.3f}) '
            f'(layers "*.Cu" "*.Mask") (tstamp "{u()}"))\n')


def pad_slot(num, x, y, w, h, dw, dh):
    return (f'  (pad "{num}" thru_hole oval (at {x:.4f} {y:.4f}) (size {w:.3f} {h:.3f}) (drill oval {dw:.3f} {dh:.3f}) '
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


# ---------------------------------------------------------------- U.3 receptacle
# Drawing datum: left locating peg = (0,0); right peg at x=38.00. Drawing "up" (tail side) = -y.
# We re-centre so the footprint origin is midway between the pegs (datum B).
U3_TOP = [f"E{i}" for i in range(7, 17)] + [f"S{i}" for i in range(8, 29)] + [f"E{i}" for i in range(17, 26)]
assert len(U3_TOP) == 40
U3_MATING_Y = 13.20 - 3.15   # housing front face from the peg line: 13.20 deep, pegs 3.15 from the tail end (rev C)
U3_POST_Y = U3_MATING_Y + 1.70  # alignment posts protrude 1.70 past the face (into the drive)


def u3_pad_positions():
    """Return {pin: (x, y, w, h)} in footprint coordinates (origin = datum B, y down)."""
    cx = 19.0
    pos = {}
    for i, n in enumerate(U3_TOP):
        pos[n] = (3.52 + 0.80 * i - cx, -1.95, 0.60, 2.00)
    for i in range(7):
        pos[f"S{i+1}"] = (3.125 + 1.27 * i - cx, 0.83, 0.65, 2.05)
    for i in range(6):
        pos[f"E{i+1}"] = (11.92 + 0.80 * i - cx, 1.24, 0.50, 2.00)
    for i in range(15):
        pos[f"P{i+1}"] = (17.095 + 1.27 * i - cx, 0.83, 0.65, 2.05)
    assert len(pos) == 68
    return pos


def gen_u3():
    name = "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD"
    b = header(name, "Amphenol PSAS4F213002xxx SAS/PCIe 4.0 (U.2/U.3) SFF-8639 68p right-angle SMT receptacle; "
               "PCB layout per Amphenol drawing PSAS4F213002XXX rev3 sheet 2. Drive mates toward +Y; keep board "
               "material clear beyond the mating line (Edge.Cuts/window at Y=+11.75).",
               "SFF-8639 U.2 U.3 SAS PCIe receptacle")
    b += text("reference", "REF**", 0, -4.6, "F.SilkS")
    b += text("value", name, 0, 13.0, "F.Fab")
    for n, (x, y, w, h) in u3_pad_positions().items():
        b += pad_smd(n, x, y, w, h)
    cx = 19.0
    b += pad_npth(0 - cx, 0, 1.78)
    b += pad_npth(38.0 - cx, 0, 1.78)
    # solder clips (DIP retainers): 0.80 x 1.90 PTH slots, tied to GND (pad name "MP")
    b += pad_slot("MP", -3.0 - cx, 2.35, 1.40, 2.50, 0.80, 1.90)
    b += pad_slot("MP", 41.0 - cx, 2.35, 1.40, 2.50, 0.80, 1.90)
    # fab outline: housing 47.00 wide incl. clips; 40.43 body; depth from tail row to mating face
    my = U3_MATING_Y
    b += rect(-20.215, -3.2, 20.215, my, "F.Fab", 0.1)
    b += line(-23.5, my, 23.5, my, "Dwgs.User", 0.1)
    b += line(-20.2, U3_POST_Y, 20.2, U3_POST_Y, "Dwgs.User", 0.05)
    b += (f'  (fp_text user "MATING FACE: board edge/window >= 0.65 mm inside this line" (at 0 {my + 0.8:.2f}) '
          f'(layer "Dwgs.User") (tstamp "{u()}")\n    (effects (font (size 0.6 0.6) (thickness 0.08))))\n')
    b += rect(-23.6, -3.6, 23.6, my + 0.2, "F.CrtYd", 0.05)
    b += line(-20.4, -3.4, -15.8, -3.4, "F.SilkS")
    b += line(20.4, -3.4, 15.8, -3.4, "F.SilkS")
    b += line(-20.4, -3.4, -20.4, 1.0, "F.SilkS")
    b += line(20.4, -3.4, 20.4, 1.0, "F.SilkS")
    # pin-1 style marker next to S1
    s1x = 3.125 - cx
    b += line(s1x - 0.5, 2.6, s1x + 0.5, 2.6, "F.SilkS")
    write(name, b)
    return name


# ---------------------------------------------------------------- OCuLink 4i R/A
def oculink_pad_positions():
    pos = {}
    for i in range(21):
        pos[f"A{i+1}"] = (-4.75 + 0.5 * i, -2.115, 0.31, 0.91)
        pos[f"B{i+1}"] = (-5.25 + 0.5 * i, -4.305, 0.31, 0.91)
    return pos


OCULINK_EDGE_Y = 3.065  # receptacle front face / board edge line (Antmicro F.Fab line)


def gen_oculink():
    name = "Amphenol_G14A421211112HR_OCuLink_4i_RA_SMD"
    b = header(name, "Amphenol G14A421211112HR OCuLink 4i (SFF-8611/8612) 42p receptacle, right angle SMT. "
               "Pad geometry from Antmicro hardware-components (Apache-2.0). Front face at Y=+3.065 = board edge.",
               "OCuLink SFF-8612 PCIe 4i")
    b += text("reference", "REF**", 0, -6.0, "F.SilkS")
    b += text("value", name, 0, 5.6, "F.Fab")
    for n, (x, y, w, h) in oculink_pad_positions().items():
        b += pad_smd(n, x, y, w, h, rr=0.25)
    for (x, y, w, h) in [(-6.91, -3.915, 1.81, 1.38), (-6.91, 0.805, 1.8, 1.81),
                         (6.91, -3.915, 1.81, 1.38), (6.91, 0.805, 1.8, 1.81)]:
        b += pad_smd("SH", x, y, w, h, rr=0.1)
    b += pad_npth(-5.42, -1.395, 1.0)
    b += pad_npth(5.95, -1.395, 1.0)
    b += rect(-7.65, -4.535, 7.65, 4.535, "F.Fab", 0.1)
    b += line(-8.5, OCULINK_EDGE_Y, 8.5, OCULINK_EDGE_Y, "Dwgs.User", 0.1)
    b += rect(-8.22, -5.22, 8.22, 4.94, "F.CrtYd", 0.05)
    b += line(-6.8, -0.4, -6.8, -3.0, "F.SilkS")
    b += line(6.8, -3.0, 6.8, -0.4, "F.SilkS")
    b += (f'  (fp_circle (center -5.58 -4.91) (end -5.53 -4.91) (stroke (width 0.15) (type solid)) (fill solid) '
          f'(layer "F.SilkS") (tstamp "{u()}"))\n')
    write(name, b)
    return name


# ---------------------------------------------------------------- slotted M3 mounting hole
def gen_slot(length=6.2):
    """M3 NPTH slot, elongated along footprint Y (rotate so Y = drive insertion axis); 0.6 mm copper keepout."""
    name = f"MountingSlot_M3_3.2x{length:.1f}"
    b = header(name, f"M3 mounting slot 3.2 x {length} mm NPTH, elongated along Y for drive/holder tolerance",
               "mounting hole slot M3", attr="exclude_from_pos_files exclude_from_bom")
    b += text("reference", "REF**", 0, -length / 2 - 1.2, "F.SilkS", hide=True)
    b += text("value", name, 0, length / 2 + 1.2, "F.Fab")
    b += (f'  (pad "" np_thru_hole oval (at 0 0) (size 3.2 {length:.2f}) (drill oval 3.2 {length:.2f}) '
          f'(layers "*.Cu" "*.Mask") (clearance 0.6) (tstamp "{u()}"))\n')
    b += rect(-2.4, -length / 2 - 0.8, 2.4, length / 2 + 0.8, "F.CrtYd", 0.05)
    write(name, b)
    return name


# ---------------------------------------------------------------- TI TPS25982 eFuse, RGE0024M VQFN 4x4
def gen_tps25982():
    """TI drawing RGE0024M (4223975/B): 24 x 0.24 x 0.575 lands, 0.5 pitch; split exposed pad 2.7 wide:
    IN pad 1.45 tall at -0.625 (IN/OUT half: pins 1-3, 16-24), GND pad 0.85 tall at +0.925 (GND pins 4/5/14 half).
    VERIFY against the TI land pattern before ordering (pad split orientation inferred from the pin map)."""
    name = "TI_RGE0024M_VQFN-24_4x4mm_P0.5mm_SplitEP"
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
    return name


if __name__ == "__main__":
    print(gen_tps25982())
    print(gen_slot())
    print(gen_u3())
    print(gen_oculink())
