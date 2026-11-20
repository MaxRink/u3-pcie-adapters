"""Design 1: PCIe x16 card with four (x4x4x4x4) or three (x4x4x4 / x8x4x4 host bifurcation) U.3 drives standing
upright on their connectors.  U3_DRIVES=3 python3 gen/x16.py builds the 3-drive card (boards/x16p3).

Rev G: the drives stand on the card FRONT (CEM component side).  Same method as gen/x8.py: the card is generated in a
mirrored frame and flipped once when it is saved (Kit.mirror_all), so the receptacles are bottom-side parts here and
the drive blocks (gen/sideband.py) and the management trunks are the proven ones.  Mirrored x = XM - physical x: the
bracket is at x = XM, the card's free end at x = -TAB; layer names here are mirrored too (L1 = physical L6 ...
L3 = physical L4).

Drives west to east in this frame: D C B A (C B A on the 3-drive card); A is next to the bracket and takes finger
lanes 0-3.  The drive at the free end sits on the low peg line, the others DZ higher: lanes 8-15 pass under B (and C).
Inside a drive the receptacle's lane order runs against the fingers' (front mounting):
  default              finger lane n -> drive lane 3 - n % 4, straight through; each x4 port trains lane-reversed
  U3_LANES=uncrossed   finger lane n -> drive lane n % 4 (not built yet)

REFCLK: one buffer (U1) at the bracket end next to the fingers feeds every drive through its own pair, so each drive
sits behind exactly one buffer stage.  The slot clock reaches U1 on L3 (40 mm); each output drops to L3 at the buffer,
runs west in the channel between the finger field and the receptacles and comes up left of its receptacle.
The card-end cluster (TCA9548A, TPS2116) stays at the free end; the slot's SMBus, PERST#, WAKE# and 3.3 V lines run
there on L3 south of the clock pairs.

Passive variant: drive A is inside the 50 mm direct-attach budget; B is close to it, C/D far over (Gen3).
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbkit import *
from symlib import U3_PINS
import sideband
import cardkit
import extras
from cardkit import refclk, approach, RW, RG
from router import Router

N = int(os.environ.get("U3_DRIVES", "4"))
assert N in (3, 4)
NAMES = "ABCD"[:N]
VAR = "-cdcdb400" if os.environ.get("U3_CLK") == "cdcdb400" else ""     # alternate card versions get their own folder
UNX = os.environ.get("U3_LANES") == "uncrossed"                         # lanes crossed back on the board
VAR += "-uncrossed" if UNX else ""
assert not cardkit.CDC, "front-drive x16: the CDCDB400 version is not laid out (output 0 / OE0# wiring)"
OUT = os.path.join(ROOT, "boards", ("x16p" if N == 4 else "x16p3") + VAR)
k = Kit(OUT, ("u3_x16p" if N == 4 else "u3_x16p3") + VAR.replace("-", "_"))
U3FP = "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD"

# ------------------------------------------------------------------ geometry (mirrored frame)
FX = 45.65                 # finger footprint origin = pin 1 (CEM: 45.65 mm from the bracket-side edge), physical
XF = 129.3                 # end of the finger span (physical); the edge rises to -12.75 beyond it
DRV = [(d, 48.0 + 73.0 * i) for i, d in enumerate(NAMES[::-1])]   # west to east; 73 mm pitch
XS = dict(DRV)
IDX = {d: i for i, d in enumerate(NAMES)}                          # address / reference index: A = 0
LOW = DRV[0][0]            # the drive at the free end
XM = XS["A"] + 45.0        # bracket-side card edge: A's block ends 44.3 mm east of its receptacle
TAB, YTAB = 22.6, -38.0    # tail tab beyond the last drive's column: aux 12 V plug, bulk cap, TVS
k.xm = XM
kf = Phys(k, XM)
M = lambda x: XM - x
cardkit.allow_refclk_in_l3(k, every=True)
DZ = 5.7                   # the other drives sit this much higher than the low one (room for lanes 8-15 under B)
YPD = {d: -24.0 - (0 if d == LOW else DZ) for d in NAMES}          # receptacle peg lines
YVTD = {d: YPD[d] + 3.6 for d in NAMES}                 # via row between the top pad row and the fingers
YVMD = {d: YPD[d] - 2.5 for d in NAMES}                 # via row on the mating side of the bottom pad row
YEDGE = float(os.environ.get("U3_YEDGE", "-9.9"))   # window edge 0.15 mm short of the housing face (rev E trials)
YE_LO, YE_HI = YPD[LOW] + YEDGE, YPD["A"] + YEDGE
XSTEP = 84.5               # window step between the low drive and its neighbour
YTOP = -111.15             # CEM full height
Y0 = -6.0                  # where pairs leave the finger field
COLW = 12.0                # column width at both card ends
P8 = 0.9                   # pitch of the lane 4-15 stacks
UXR, UYR = XM - 15.0, -20.0     # REFCLK buffer U1 (bottom here = drive side), between drive A and the bracket


def lvl(ln):
    if ln < 4:
        return {0: -15.2, 1: -16.2, 2: -17.2, 3: -18.2}[ln]
    last = 4 * N - 1
    if ln < 8:
        return -14.0 - P8 * (last - 7) - P8 * (7 - ln)  # band B: lane 7 lowest, right above lane 8
    return -14.0 - P8 * (last - ln)                     # lanes 8 up: the last lane lowest, 1 mm off the raised edge


# ------------------------------------------------------------------ CEM x16 edge pinout (side B = F.Cu, side A = B.Cu)
GND_B = [4, 7, 13, 16, 18, 21, 22, 25, 26, 29, 32, 35, 36, 39, 40, 43, 44, 47, 49] + \
        [n for i in range(8) for n in (52 + 4 * i, 53 + 4 * i)][:-1] + [80]
GND_A = [4, 12, 15, 18, 20, 23, 24, 27, 28, 31, 34, 37, 38, 41, 42, 45, 46, 49, 51] + \
        [n for i in range(7) for n in (54 + 4 * i, 55 + 4 * i)] + [82]
GND_B = sorted(set(GND_B) - {81})
fing = {f"B{n}": "GND" for n in GND_B}
fing.update({f"A{n}": "GND" for n in GND_A})
fing.update({"B1": "12V", "B2": "12V", "B3": "12V", "A2": "12V", "A3": "12V",
             "B8": "3V3", "A9": "3V3", "A10": "3V3", "B10": "3V3_AUX_SLOT", "A11": "PCIE_RST_N",
             "A1": "PRSNT_N", "B81": "PRSNT_N", "A13": "REFCLK_IN_P", "A14": "REFCLK_IN_N",
             "B5": "SMCLK_SLOT", "B6": "SMDAT_SLOT", "B11": "PCIE_WAKE_N", "B12": "CLKREQ_N"})
PET_PINS = {0: (14, 15), 1: (19, 20), 2: (23, 24), 3: (27, 28), 4: (33, 34), 5: (37, 38), 6: (41, 42), 7: (45, 46)}
PER_PINS = {0: (16, 17), 1: (21, 22), 2: (25, 26), 3: (29, 30), 4: (35, 36), 5: (39, 40), 6: (43, 44), 7: (47, 48)}
for ln in range(8, 16):
    PET_PINS[ln] = (50 + 4 * (ln - 8), 51 + 4 * (ln - 8))
    PER_PINS[ln] = (52 + 4 * (ln - 8), 53 + 4 * (ln - 8))
for ln, (p, n) in PET_PINS.items():
    if ln < 4 * N:                           # 3-drive card: lanes 12-15 stay open
        fing[f"B{p}"], fing[f"B{n}"] = f"PET{ln}_P", f"PET{ln}_N"
for ln, (p, n) in PER_PINS.items():
    if ln < 4 * N:
        fing[f"A{p}"], fing[f"A{n}"] = f"PER{ln}_P", f"PER{ln}_N"
# placed pre-flipped, so the final flip puts it on the front with pin 1 at FX
J1 = k.fp("Connector_PCBEdge", "BUS_PCIexpress_x16", "J1", "PCIe x16 edge", M(FX), -3.45, 0, bottom=True, pads=fing, bom=False)
fpad = lambda n: k.padxy("J1", n)
assert abs(fpad("B1")[0] - M(FX)) < 1e-6 and k.fps["J1"].IsFlipped()
xpin = lambda n: fpad(f"B{n}")[0]           # A and B pads share x (mirrored frame)
xP = lambda n: M(xpin(n))                   # physical


# ------------------------------------------------------------------ U.3 receptacles (drive side; bottom in this frame)
def u3net(pin, d):
    n = U3_PINS[pin]
    # sidebands and 12 V come from the drive's sideband block (gen/sideband.py); REFCLK1 / port B stay open
    m = {"GND": "GND", "HPT0": "GND", "3V3_AUX": "3V3_AUX", "ACTIVITY#": f"{d}_ACT_N"}
    return m.get(n)


JP = {}
for d, xc in DRV:
    pads = {p: u3net(p, d) for p in U3_PINS if u3net(p, d)}
    pads["MP"] = "GND"
    k.fp("u3adapter", U3FP, f"J{d}", "PSAS4F2130021TR", xc, YPD[d], 180, bottom=True, pads=pads, lcsc="C22454449")
    JP[d] = lambda n, d=d: k.padxy(f"J{d}", n)
R = Router(k)
SB = {d: sideband.block(k, R, d, IDX[d], xc, YPD[d], JP[d], 10 + 4 * IDX[d], 20 + 20 * IDX[d], 20 + 10 * IDX[d])
      for d, xc in DRV}

# ------------------------------------------------------------------ outline (physical points, mirrored)
arc = k.arc_pts((43.175, -10.925), 1.825, 180, 360)            # CEM notch between foot and fingers
XT = XM + TAB
tail = [(XF, -12.75), (XT, -12.75), (XT, YTAB), (XM, YTAB), (XM, YTOP), (XM - COLW, YTOP), (XM - COLW, YE_LO),
        (XM - XSTEP, YE_LO), (XM - XSTEP, YE_HI), (COLW, YE_HI), (COLW, YTOP), (0, YTOP)]
foot = [(0, -4.5), (15.0, -4.5), (15.0, -12.75), (33.35, -12.75), (33.35, -4.5), (41.35, -4.5)] + arc
MP = lambda pts: [(M(x), y) for x, y in pts]
k.outline(MP([(XF, -8.4)] + tail + foot + [(45.0, -8.4)]), closed=False)
BOARD = MP(foot + [(45.0, 0), (XF, 0)] + tail)
RECT = lambda x0, x1, y0, y1: MP([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
k.rule_area("FINGERS", RECT(44.9, XF + 0.1, 0.6, -5.75))
k.rule_area("NECKDOWN_FINGERS", RECT(44.9, XF + 0.1, 0.6, -7.4))
for d, xc in DRV:
    k.rule_area(f"NECKDOWN_J{d}", [(xc - 20.5, YVTD[d] + 0.9), (xc + 20.5, YVTD[d] + 0.9), (xc + 20.5, YVMD[d] - 0.9),
                                   (xc - 20.5, YVMD[d] - 0.9)])
for L in ("L2", "L4", "L5"):
    k.keepout(f"FINGER_VOID_{L}", RECT(44.8, XF + 0.2, 0.6, -5.9), [L])

# ------------------------------------------------------------------ helpers
YKNEE_A = -11.6            # lanes 0-3 rise straight to here: clears the slot clock vias next to lane 0


def knee(ln, xc, h, side):
    if ln < 4:
        return YKNEE_A
    if ln < 8:                                          # band B: 45 deg runs end short of lane 8's risers
        xe = (96.2 if side == "B" else 98.2) - (7 - ln) * 0.5 - (1.5 if N == 3 else 0)     # physical; the 3-drive
        # card's band B sits 3.6 mm lower, so its knees start nearer the fingers: keep lane 4's above the GND via row
        return h + (xe - M(xc))
    return h + 0.8


def band_center(xc, h, xt, yend, dirn, yv, c=0.8):
    xd = xc + dirn * (yv - h)
    pts = [(xc, Y0)] + ([(xc, yv)] if yv != Y0 else [])
    return pts + [(xd, h), (xt - dirn * c, h), (xt, h - c), (xt, yend)]


def tpair(layer, center, starts, ends, w=PCIE_W, g=PCIE_G, h=0.2, L=0.4, extra=None):
    """k.pair with automatic length matching: trapezoid bumps on the shorter line, longest centre segment."""
    res = k.pair(layer, center, starts, ends, w, g, dry=True)
    ln = {n: plen(v[0]) + (extra or {}).get(n, 0) for n, v in res.items()}
    (short, ls), (_, ll) = sorted(ln.items(), key=lambda kv: kv[1])
    nb = math.ceil((ll - ls) / (2 * h * (math.sqrt(2) - 1)) - 0.25)
    if nb <= 0:
        return k.pair(layer, center, starts, ends, w, g)
    si = max(range(len(center) - 1), key=lambda i: math.dist(center[i], center[i + 1]))
    seg = math.dist(center[si], center[si + 1]); pitch = L + 2 * h + 0.4
    assert nb * pitch < seg - 1.0, ("no room to deskew", short, nb, seg)
    fr = [0.5 + (i - (nb - 1) / 2) * pitch / seg for i in range(nb)]
    return k.pair(layer, center, starts, ends, w, g, tune={short: [(si, fr, h, L)]})


def fstarts(pins, side):
    return [(fing[f"{side}{p}"], [(fpad(f"{side}{p}")[0], -5.45)]) for p in pins]


def vias_at(res, ref=None):
    out = {}
    for net, (full, sn, en) in res.items():
        x, y = full[-1]; k.via(net, x, y); out[net] = (x, y)
    return out


def stub_to_pad(ref, pads_xy, vias, layer, ystop):
    """Connect each via (net) to the receptacle pad straight above/below it (same x) and name the pad."""
    for net, (vx, vy) in vias.items():
        pad = min(pads_xy, key=lambda n: abs(k.padxy(ref, n)[0] - vx))
        px, py = k.padxy(ref, pad)
        k.track(net, layer, [(vx, vy), (px, ystop)], PCIE_W)
        k.setpad(ref, pad, net)


def name_pads(ref, res, pads):
    for net, (full, sn, en) in res.items():
        pad = min(pads, key=lambda n: math.dist(k.padxy(ref, n), full[-1]))
        k.setpad(ref, pad, net)


R0402 = ("Resistor_SMD", "R_0402_1005Metric")
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C1206 = ("Capacitor_SMD", "C_1206_3216Metric")


def two(ref, lib, fpn, val, x, y, rot, bottom, near, net_near, net_far, lcsc, dnp=False):
    k.fp(lib, fpn, ref, val, x, y, rot, bottom=bottom, lcsc=lcsc, dnp=dnp)
    p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
    if math.dist(p1, near) <= math.dist(p2, near):
        k.setpad(ref, "1", net_near); k.setpad(ref, "2", net_far); return p1, p2
    k.setpad(ref, "2", net_near); k.setpad(ref, "1", net_far); return p2, p1


capn = [0]


def ac_caps(xt, yc, res, bottom, layer_void):
    """Two 0402 220 nF caps (vertical) at xt +- 0.5, centre y yc, one on the end of each line in res.
    Returns {finger_net: (ref, near_pad_xy, far_pad_xy)} with near = toward the fingers (larger y)."""
    out = {}
    for fn, (full, sn, en) in sorted(res.items(), key=lambda kv: kv[1][0][-1][0]):
        dn = "C_" + fn
        capn[0] += 1; ref = f"C{100 + capn[0]}"
        x = xt + (-0.5 if full[-1][0] < xt else 0.5)
        near, far = two(ref, *C0402, "220nF 16V X7R", x, yc, 90, bottom, (x, yc + 1), fn, dn, "C16772")
        k.void_under(ref, layer_void)
        out[fn] = (ref, near, far)
    return out


# ------------------------------------------------------------------ lanes
# In this frame the fingers' side B (PET) is L6, the receptacle's layer, and side A (PER) is L1.
# Drive lanes 0/1 RX (PER) get 220 nF AC caps (SFF-TA-1001 Rev 1.1 sec. 4.5, Table 4-11).
SP_PET = {0: ("S2", "S3"), 1: ("S9", "S10"), 2: ("S17", "S18"), 3: ("S23", "S24")}
SP_PER = {0: ("S5", "S6"), 1: ("S12", "S13"), 2: ("S20", "S21"), 3: ("S26", "S27")}
assert not UNX, "U3_LANES=uncrossed is not built yet for the x16 cards"


def lane_of(ln, pins, side):
    d = NAMES[ln // 4]; h = lvl(ln)
    xc = sum(fpad(f"{side}{p}")[0] for p in pins) / 2
    return d, f"J{d}", 3 - ln % 4, (1 if d == "A" else -1), h, xc, knee(ln, xc, h, side)


def pet_lane(ln):
    """L6 from the fingers straight into the top-row pads; drive lane 0 (bottom row) hops over the top row on L1."""
    pins = PET_PINS[ln]
    d, ref, dl, dirn, h, xc, yv = lane_of(ln, pins, "B")
    YVT, YVM = YVTD[d], YVMD[d]
    sp = SP_PET[dl]
    xt = sum(JP[d](n)[0] for n in sp) / 2
    st = fstarts(pins, "B")
    if dl:
        res = k.pair("L6", band_center(xc, h, xt, YVT - 0.2, dirn, yv), st,
                     [(None, [(JP[d](n)[0], YVT - 0.75)]) for n in sp])
        name_pads(ref, res, sp)
        return res
    ytr = YVT + 1.0
    res = k.pair("L6", band_center(xc, h, xt, ytr + 0.45, dirn, yv, c=0.4), st, [(None, [(JP[d](n)[0], ytr)]) for n in sp])
    v1 = vias_at(res)
    for gx in (xt - 1.59, xt + 1.59):
        k.via("GND", gx, ytr)
    res2 = tpair("L1", [(xt, ytr - 0.6), (xt, YVM + 0.3)], [(net, [v1[net]]) for net in v1],
                 [(None, [(xt + s * 0.4, YVM)]) for s in (-1, 1)])
    v2 = vias_at(res2)
    stub_to_pad(ref, sp, v2, "L6", YVM + 0.8)
    k.via("GND", xt, YVM - 0.95)
    return {**res, **res2}


def per_lane(ln):
    """L1 from the fingers, one via pair down to the receptacle pads; AC caps inline on L1 for drive lanes 0/1."""
    pins = PER_PINS[ln]
    d, ref, dl, dirn, h, xc, yv = lane_of(ln, pins, "A")
    YVT, YVM = YVTD[d], YVMD[d]
    sp = SP_PER[dl]
    xt = sum(JP[d](n)[0] for n in sp) / 2
    st = fstarts(pins, "A")
    if dl >= 2:
        res = k.pair("L1", band_center(xc, h, xt, YVT + 0.32, dirn, yv), st, [(None, [(JP[d](n)[0], YVT)]) for n in sp])
        stub_to_pad(ref, sp, vias_at(res), "L6", YVT - 1.0)
        return res
    yc = h - 1.4 if dl else YPD[d] + 1.4      # caps: just above the band (lane 1) / over the receptacle (lane 0)
    res = k.pair("L1", band_center(xc, h, xt, (h - 0.6) if dl else (yc + 0.9), dirn, yv, c=0.4), st,
                 [(None, [(xt - 0.5, yc + 0.48)]), (None, [(xt + 0.5, yc + 0.48)])])
    caps = ac_caps(xt, yc, res, False, "L2")
    for net, (full, sn, en) in res.items():
        if math.dist(caps[net][1], full[-1]) > 0.05:
            raise SystemExit(f"cap/net mismatch on {net}")
    starts = [("C_" + net, [caps[net][2], (caps[net][2][0], caps[net][2][1] - (0.1 if dl == 0 else 0.3))]) for net in res]
    if dl:
        res2 = k.pair("L1", [(xt, yc - 1.05), (xt, YVT + 0.32)], starts, [(None, [(JP[d](n)[0], YVT)]) for n in sp])
        stub_to_pad(ref, sp, vias_at(res2), "L6", YVT - 1.0)
    else:
        res2 = k.pair("L1", [(xt, yc - 1.05), (xt, YVM + 0.3)], starts, [(None, [(xt + s * 0.4, YVM)]) for s in (-1, 1)])
        stub_to_pad(ref, sp, vias_at(res2), "L6", YVM + 0.8)
        k.via("GND", xt, YVM - 0.95)
    return {**res, **res2}


lanes = {}
for ln in range(4 * N):
    lanes[f"PET{ln}"] = pet_lane(ln)
    lanes[f"PER{ln}"] = per_lane(ln)

# ------------------------------------------------------------------ top-row / bottom-row GND and misc escapes
TOP_ROW = [f"E{i}" for i in range(7, 17)] + [f"S{i}" for i in range(8, 29)] + [f"E{i}" for i in range(17, 26)]
BOT_ROW = [f"S{i}" for i in range(1, 8)] + [f"E{i}" for i in range(1, 7)] + [f"P{i}" for i in range(1, 16)]
for d, _ in DRV:
    ref = f"J{d}"; YVT, YVM = YVTD[d], YVMD[d]
    for n in TOP_ROW:
        net = k.padnet(ref, n)
        x, y = JP[d](n)
        if net == "GND":
            if n == "E9":                 # under the PET0 riser: join E12's via on L6
                x12 = JP[d]("E12")[0]
                k.track("GND", "L6", [(x, y), (x, YVT - 0.25), (x12, YVT - 0.25)], 0.2)
                continue
            if n == "S15":                # HPT0 (tie low = SFF-TA-1001 x4)
                k.track("GND", "L6", [(x, y), (x, YVT - 0.25), (x + 0.8, YVT)], 0.2)
                continue
            k.track("GND", "L6", [(x, y), (x, YVT)], 0.25); k.via("GND", x, YVT)
        elif net and not net.startswith(("PET", "PER", "C_PER", "REFCLK")) and net != "":
            k.track(net, "L6", [(x, y), (x, YVT)], 0.2); k.via(net, x, YVT)
    for n in BOT_ROW:
        net = k.padnet(ref, n)
        x, y = JP[d](n)
        if not net or net.startswith(("PET", "PER", "C_PER", "12V_DRV")):      # 12V_DRV: the L6 pour takes P13-P15
            continue
        w = 0.5 if "12V" in net else (0.3 if net in ("GND", "3V3_AUX") else 0.2)
        dv = (0.6, 0.3) if "12V" in net else (None, None)
        k.track(net, "L6", [(x, y), (x, YVM)], w); k.via(net, x, YVM, *dv)

# ------------------------------------------------------------------ finger GND / power escapes (physical frame, kf)
YG = -6.75                                   # finger GND via row (between the lane pairs)


def finger_gnd(m, x=None, y=YG):
    lo, hi = math.floor(m), math.ceil(m)
    x = x if x is not None else (xP(lo) + xP(hi)) / 2
    kf.via("GND", x, y)
    for side, L in (("B", "L1"), ("A", "L6")):
        for n in sorted({lo, hi}):
            if fing.get(f"{side}{n}") == "GND":
                px = xP(n)
                kf.track("GND", L, [(px, -5.4), (px, -5.9), (x, y)], 0.3)


for m in (15.5, 18, 20.5, 22.5, 24.5, 26.5, 28.5, 31.5, 34.5, 36.5, 38.5, 40.5, 42.5, 44.5, 46.5, 4, 7):
    finger_gnd(m)
for m in range(51, 80, 2):                   # lanes 8-15: one via between every two pairs
    finger_gnd(m + 0.5)
finger_gnd(81.5, x=xP(82), y=-7.6)           # A82, clear of PRSNT2# (B81)
finger_gnd(12.5, x=xP(12) + 0.4)             # keep 0.5 mm off REFCLK_IN
finger_gnd(49, y=-6.85)

# 12V: B1-B3 / A2-A3 -> four vias into the 12 V plane
for x, y in ((xP(2), -6.8), (xP(3), -6.8), (xP(2), -7.8), (xP(3), -7.8)):
    kf.via("12V", x, y, 0.6, 0.3)
kf.track("12V", "L1", [(xP(1), -5.4), (xP(1), -5.9), (xP(2), -6.8)], 0.5)
for n in (2, 3):
    kf.track("12V", "L1", [(xP(n), -5.4), (xP(n), -7.8)], 0.5)
    kf.track("12V", "L6", [(xP(n), -5.4), (xP(n), -7.8)], 0.5)
# PRSNT1# (A1) -> PRSNT2# x16 (B81) on L3
VPA = (xP(1), -9.0); VPB = (xP(81) + 0.75, -9.0)              # via beyond PER15
kf.track("PRSNT_N", "L6", [(xP(1), -4.6), VPA], 0.2); kf.via("PRSNT_N", *VPA)
kf.track("PRSNT_N", "L1", [(xP(81), -5.4), (xP(81), -8.4), VPB], 0.2); kf.via("PRSNT_N", *VPB)
kf.track("PRSNT_N", "L3", [VPA, VPB], 0.2)        # crosses the key slot above its 8.4 mm top
# B12 CLKREQ# tied low (clock always requested): joins the B13 GND via of the finger GND row
k.setpad("J1", "B11", "PCIE_WAKE_N"); k.setpad("J1", "B12", "GND")
kf.track("GND", "L1", [(xP(12), -5.4), (xP(12), -6.35), (xP(12) + 0.4, -6.75)], 0.2)

# ------------------------------------------------------------------ slot sidebands and 3.3 V (this frame)
# The slot pins sit east of the clock pins, their loads (TCA9548A, TPS2116, trunk starts) at the free end, and the
# clock goes east to U1: every line has to cross the clock.  They do it on L3 south of the clock's via pair, where
# the clock still runs on L1: via north of the row band, stub south into its row, west under the clock, north again
# west of the clock vias and then west along the channel rows.  West to east pin order = north to south row order,
# so no stub crosses a row.
YCV = -12.55               # slot clock via row
SLOT = [  # net, pin layer, pin, via xy, band row, column x, channel row, width
    ("PCIE_WAKE_N", "L6", 11, (xpin(11) - 0.55, -13.0), -11.55, 252.3 - 312.0 + XM, -16.7, 0.15),
    ("PCIE_RST_N", "L1", 11, (xpin(11), -12.3), -11.25, 251.9 - 312.0 + XM, -16.3, 0.15),
    ("3V3_AUX_SLOT", "L6", 10, (xpin(10), -12.3), -10.9, 251.4 - 312.0 + XM, -15.8, 0.25),
    ("3V3", "L1", 9, (xpin(9), -12.3), -10.35, 250.8 - 312.0 + XM, -15.25, 0.4),
    ("SMDAT_SLOT", "L6", 6, (xpin(6), -12.3), -9.8, 250.25 - 312.0 + XM, -14.7, 0.15),
    ("SMCLK_SLOT", "L6", 5, (xpin(5), -12.3), -9.4, 249.85 - 312.0 + XM, -14.3, 0.15)]
SLOTV = {}
ROWS = {}
for net, L, pin, (vx, vy), yb, xcol, yrow, w_ in SLOT:
    px = xpin(pin)
    pts = [(px, -5.4), (px, -9.4), (vx, -9.4 - abs(px - vx)), (vx, vy)] if abs(px - vx) > 1e-6 else [(px, -5.4), (vx, vy)]
    k.track(net, L, pts, 0.3 if "3V3" in net else 0.2)
    k.via(net, vx, vy)
    SLOTV[net] = (vx, vy)
    ROWS[net] = (w_, [(vx, vy), (vx, yb - 0.3), (vx - 0.3, yb), (xcol + 0.3, yb), (xcol, yb - 0.3), (xcol, yrow + 0.3),
                      (xcol - 0.3, yrow)])
# 3.3 V: B8 and A10 join A9's line
k.track("3V3", "L6", [(xpin(8), -5.4), (xpin(8), -9.4), (xpin(9), -10.4), (xpin(9), -12.3)], 0.3)
k.track("3V3", "L1", [(xpin(10), -5.4), (xpin(10), -5.9), (xpin(9), -6.9)], 0.3)

# ------------------------------------------------------------------ activity LEDs (side away from the drive)
E3 = {d: JP[d]("E3") for d, _ in DRV}
for d, xc in DRV:
    xa = E3[d][0]; xact = JP[d]("P11")[0]; dx = xc - 48.0; dz = YPD[d] + 24.0
    xr, xl = 55.1 + dx, 57.7 + dx
    rn = f"R{11 + IDX[d]}"; ln_ = f"D{1 + IDX[d]}"
    nr, fr = two(rn, *R0402, "1k", xr, -24.2 + dz, 0, False, (xr - 1, -24.2 + dz), "3V3_AUX", f"{d}_LEDA", "C11702")
    k.fp("LED_SMD", "LED_0603_1608Metric", ln_, "KT-0603YG", xl, -24.2 + dz, 180,
         pads={"1": f"{d}_ACT_N", "2": f"{d}_LEDA"}, lcsc="C2289")
    k.track(f"{d}_LEDA", "L1", [fr, k.padxy(ln_, "2")], 0.2)
    k.track("3V3_AUX", "L1", [(xa, YVMD[d]), (xa, -25.5 + dz), (nr[0] - 0.5, -25.5 + dz), (nr[0] - 0.5, nr[1]), nr], 0.25)
    kp = k.padxy(ln_, "1")
    k.track(f"{d}_ACT_N", "L1", [kp, (xact, kp[1] - 0.4), (xact, YVMD[d])], 0.2)

# ------------------------------------------------------------------ REFCLK: buffer at the bracket end, one pair per drive
import time; T0 = time.time()
YPL = YPD[LOW]
card = cardkit.Card(k, R, xpin, fpad, [(d, xc, YPD[d], JP[d]) for d, xc in DRV], YPL)
USED = {d: i for (d, _), i in zip(DRV, (0, 1, 2, 3) if N == 4 else (0, 2, 3))}       # drive -> U1 output
card.buffer(USED, at=(UXR, UYR))
U = card.U
N_IN = ("REFCLK_IN_P", "REFCLK_IN_N")
O = 0.6                                          # via offset from the pair centre (vias 1.2 mm apart)
D1 = (RW + RG) / 2; D3 = (CLK3_W + CLK3_G) / 2
VIA_H = 1.5784


def clock_in(yrow=-14.8, xjog=2.05):
    """A13/A14 (L1) north, stepping east clear of the PET0 riser, to two vias side by side; L3 north and east along
    yrow to two stacked vias west of U1; L6 east and north into the input pins.  P stays the east / south / east line:
    no crossing, two vias per line."""
    x13, x14 = xpin(13), xpin(14)
    assert x13 > x14
    xin = (x13 + x14) / 2; xc1 = xin + xjog; yv = YCV
    r1 = k.pair("L1", [(xin, -5.76), (xin, -7.5), (xc1, -7.5 - xjog), (xc1, yv + 1.0)],
                [(N_IN[0], [(x13, -5.62)]), (N_IN[1], [(x14, -5.62)])],
                [(None, [(xc1 + O, yv), (xc1 + D1, yv + O - D1)]), (None, [(xc1 - O, yv), (xc1 - D1, yv + O - D1)])], RW, RG)
    assert r1[N_IN[0]][0][-1][0] > xc1, "REFCLK_IN: P should take the east via"
    k.via(N_IN[0], xc1 + O, yv); k.via(N_IN[1], xc1 - O, yv)
    p5, p6 = U(cardkit.CLKIN[0]), U(cardkit.CLKIN[1])
    assert p5[0] > p6[0]
    xc = (p5[0] + p6[0]) / 2; xvw = xc - 2.8
    r6 = k.pair("L6", [(xvw + 1.0, yrow), (xc - 0.6, yrow), (xc, yrow - 0.6), (xc, yrow - 1.0)],
                [(N_IN[0], [(xvw, yrow + O), (xvw + O - D1, yrow + D1)]), (N_IN[1], [(xvw, yrow - O), (xvw + O - D1, yrow - D1)])],
                [(None, [p5, (p5[0], yrow - 1.4)]), (None, [p6, (p6[0], yrow - 1.4)])], RW, RG)
    assert math.dist(r6[N_IN[0]][0][-1], p5) < 1e-6, "REFCLK_IN: P should end on the east pin"
    k.via(N_IN[0], xvw, yrow + O); k.via(N_IN[1], xvw, yrow - O)
    ex = {n: plen(r1[n][0]) + plen(r6[n][0]) + 2 * VIA_H for n in N_IN}
    r3 = refclk(k, "L3", [(xc1, yv - 1.0), (xc1, yrow + 0.85), (xc1 + 0.85, yrow), (xvw - 1.0, yrow)],
                [(N_IN[0], [(xc1 + O, yv), (xc1 + D3, yv - O + D3)]), (N_IN[1], [(xc1 - O, yv), (xc1 - D3, yv - O + D3)])],
                [(None, [(xvw, yrow + O), (xvw - O + D3, yrow + D3)]), (None, [(xvw, yrow - O), (xvw - O + D3, yrow - D3)])],
                extra=ex, RW=CLK3_W, RG=CLK3_G)
    assert r3[N_IN[0]][0][-1][1] > yrow, "REFCLK_IN: P should take the south via"
    lp, ln = (plen(r3[n][0]) + ex[n] for n in N_IN)
    print(f"REFCLK_IN: {lp:.2f} / {ln:.2f} mm, of it {plen(r3[N_IN[0]][0]):.2f} on L3")
    return (xc1, xvw, yrow)


XC1, XVW, YIN = clock_in()
YROW = {d: -17.6 - 1.4 * i for i, (d, _) in enumerate(DRV)}        # L3 channel rows, the far drive's southmost
XCOL = {i: UXR - 9.0 - 1.4 * i for i in range(4)}                  # where each output's L3 pair turns south to its row


def clock_out(d):
    """U1 output -> L6 -> via pair -> L3: round to the west, south down its column to the drive's channel row (P on
    the south line), west under the receptacles, north at the receptacle's west end to a via pair, L6 north and east
    into E7/E8.  One buffer stage and two via pairs per drive."""
    dif = USED[d]; pp, pn = cardkit.DIF[dif]
    NP, NN = f"REFCLK_{d}_P", f"REFCLK_{d}_N"
    a, b = U(pp), U(pn)
    yr, xcol = YROW[d], XCOL[dif]
    if dif == 0:                               # west face: straight west, vias stacked (P south)
        ym = (a[1] + b[1]) / 2; xv = UXR - 7.2
        l6 = k.pair("L6", [(a[0] - 0.45, ym), (xv + O, ym)], [(NP, [a]), (NN, [b])],
                    [(None, [(xv, ym + O)]), (None, [(xv, ym - O)])], RW, RG)
        vP, vN = (xv, ym + O), (xv, ym - O)
        st = [(NP, [vP, (xv - O + D3, ym + D3)]), (NN, [vN, (xv - O + D3, ym - D3)])]
        cen = [(xv - O, ym), (xcol + 0.6, ym), (xcol, ym + 0.6)]
    else:
        if dif == 3:                           # east face: east, then north (P west)
            ym = (a[1] + b[1]) / 2; xc = UXR + 6.6; yv = UYR - 4.0; yt = UYR - 7.3
            c6 = [(a[0] + 0.45, ym), (xc - 0.6, ym), (xc, ym - 0.6), (xc, yv + O)]
        else:                                  # north face: straight north (P west)
            xc = (a[0] + b[0]) / 2
            yv, yt = (UYR - 4.2, UYR - 5.5) if dif == 1 else (UYR - 5.1, UYR - 6.4)
            c6 = [(xc, a[1] - 0.45), (xc, yv + O)]
        l6 = k.pair("L6", c6, [(NP, [a]), (NN, [b])], [(None, [(xc - O, yv)]), (None, [(xc + O, yv)])], RW, RG)
        vP, vN = (xc - O, yv), (xc + O, yv)
        st = [(NP, [vP, (xc - D3, yv - O + D3)]), (NN, [vN, (xc + D3, yv - O + D3)])]
        if dif == 3:        # drive A's eFuse parts (GND vias at y -27.0) sit north-east of U1: pass south of them,
            ya = UYR - 6.0  # then step up to the outermost row once west of them
            cen = [(xc, yv - O), (xc, ya + 0.6), (xc - 0.6, ya), (UXR + 3.6, ya), (UXR + 3.6 + (yt - ya), yt)]
        else:
            cen = [(xc, yv - O), (xc, yt + 0.6), (xc - 0.6, yt)]
        cen += [(xcol + 0.6, yt), (xcol, yt + 0.6)]
    assert math.dist(l6[NP][0][-1], vP) < 1e-6, f"REFCLK_{d}: P must reach its via at U1"
    k.via(NP, *vP); k.via(NN, *vN)
    # drive end
    cend, ends = approach(JP[d], d, YPD[d])
    xr = cend[0] - 1.95; yvd = cend[1] + 1.56
    wP, wN = (xr - O, yvd), (xr + O, yvd)
    k.via(NP, *wP); k.via(NN, *wN)
    d6 = k.pair("L6", [(xr, yvd - O), (xr, cend[1] + 0.6), (xr + 0.6, cend[1]), cend],
                [(NP, [wP, (xr - D1, yvd - O + D1)]), (NN, [wN, (xr + D1, yvd - O + D1)])], ends, RW, RG)
    assert math.dist(d6[NP][0][-1], JP[d]("E7")) < 1e-6, f"REFCLK_{d}: P does not end on E7"
    k.setpad(f"J{d}", "E7", NP); k.setpad(f"J{d}", "E8", NN)
    ex = {n: plen(l6[n][0]) + plen(d6[n][0]) + 2 * VIA_H for n in (NP, NN)}
    cen += [(xcol, yr - 0.6), (xcol - 0.6, yr), (xr + 0.6, yr), (xr, yr - 0.6), (xr, yvd + O)]
    r3 = refclk(k, "L3", cen, st, [(None, [wP, (xr - D3, yvd + O - D3)]), (None, [wN, (xr + D3, yvd + O - D3)])],
                extra=ex, RW=CLK3_W, RG=CLK3_G)
    assert math.dist(r3[NP][0][-1], wP) < 1e-6, f"REFCLK_{d}: P must take the west via at the drive"
    lp, ln = (plen(r3[n][0]) + ex[n] for n in (NP, NN))
    print(f"REFCLK_{d}: {lp:.2f} / {ln:.2f} mm, skew {lp - ln:+.3f}")


for d, _ in DRV:
    clock_out(d)

# ------------------------------------------------------------------ card-end cluster, trunks, slot rows
card.parts(dy=-0.4, fb=(UXR + 5.8, UYR + 4.4))          # the tail edge is 12.75 mm up: lift the TPS2116 group clear
XSTEPC = XSTEP + 1.0                                     # channel step (trunks) just past the window step
first = card.trunks({"SMCLK": 13.5, "SMDAT": 14.5, "3V3_AUX": 15.5, "PCIE_RST_N": 27.45, "PCIE_WAKE_N": 28.3},
                   steps=[(XSTEPC, XSTEPC)])
# channel rows west to the free end.  PERST# / WAKE# (northmost) run on to their trunk starts; the others end in a
# via east of those two verticals, the router takes them on to the TCA9548A and the TPS2116
ENDS = {}
for i, net in enumerate(("3V3_AUX_SLOT", "3V3", "SMDAT_SLOT", "SMCLK_SLOT")):
    w_, pts = ROWS[net]
    yrow = pts[-1][1]
    xv = 28.8 + 1.2 * i
    if net == "SMCLK_SLOT":                    # southmost row: its via steps south, clear of the SMDAT row passing it
        pts += [(xv + 0.7, yrow), (xv, yrow + 0.7)]; yrow += 0.7
    else:
        pts += [(xv, yrow)]
    k.via(net, xv, yrow)
    ENDS[net] = ("all", xv, yrow)
w_, pts = ROWS["PCIE_RST_N"]
pts += [(27.85, pts[-1][1]), (27.45, pts[-1][1] - 0.4), first["PCIE_RST_N"]]
w_, pts = ROWS["PCIE_WAKE_N"]
# WAKE# passes 0.2 from the peg hole (29, -24), then steps east to leave room for the PERST# tap via
pts += [(28.2, pts[-1][1]), (27.8, pts[-1][1] - 0.4), (27.8, -26.0), (28.3, -26.5), first["PCIE_WAKE_N"]]
for net, (w_, pts) in ROWS.items():
    k.track(net, "L3", pts, w_)
# 3.3 V for U1: east from the 3.3 V via along the raised edge, south of the slot clock, to a via past the edge step
V33 = SLOTV["3V3"]
XE33 = M(15.0) + 1.0
F33 = [V33, (V33[0], -12.9), (V33[0] + 0.35, -13.25), (XE33 - 0.7, -13.25), (XE33, -12.55), (XE33, -11.9)]
k.track("3V3", "L3", F33, 0.3); k.via("3V3", *F33[-1])
# the low drive's reset gate / WAKE buffer tap these verticals (1.05 mm apart, room for a via on each)
for net, tv in (("PCIE_RST_N", (27.45, YPL - 6.3)), ("PCIE_WAKE_N", (28.3, YPL - 5.0))):
    k.via(net, *tv); card.taps[net].append(tv)
LCOST = dict(layer_cost={"L1": 2.5, "L6": 2.5}, via_cost=1.0, maxpad=12.0)
U2 = lambda q: ("L1", *k.padxy("U2", q))
U3 = lambda net: ("L1", *card.u3t[net])
# local bus risers (hand-laid): U2 SC0/SD0 east -> vias -> L3 north along the column edge -> trunk starts
for net, q, xv in (("SMCLK", "5", 10.6), ("SMDAT", "4", 11.4)):
    pq = k.padxy("U2", q); f0 = first[net]
    k.track(net, "L1", [pq, (xv, pq[1])], 0.15); k.via(net, xv, pq[1])
    k.track(net, "L3", [(xv, pq[1]), (xv, f0[1]), f0], sideband.TRK_W)


def seed_line(net, pts, w_, layer="L3"):
    R.seed(net, [(layer, "seg", (p[0], p[1], q[0], q[1], w_ / 2)) for p, q in zip(pts, pts[1:])] +
           [("all", "circle", (pts[0][0], pts[0][1], 0.1)), ("all", "circle", (pts[-1][0], pts[-1][1], 0.1))])


for net in ("PCIE_RST_N", "PCIE_WAKE_N", "3V3"):          # root the hand-laid slot lines for the router
    seed_line(net, ROWS[net][1], ROWS[net][0])
seed_line("3V3", F33, 0.3)
risers = [("3V3", ENDS["3V3"], U3("3V3")), ("3V3_AUX", U3("3V3_AUX"), ("L3", *first["3V3_AUX"])),
          ("SMCLK_SLOT", ENDS["SMCLK_SLOT"], U2("22")), ("SMDAT_SLOT", ENDS["SMDAT_SLOT"], U2("23")),
          ("3V3_AUX_SLOT", ENDS["3V3_AUX_SLOT"], U3("3V3_AUX_SLOT"))]
card.seed_trunks()
for net, a, b in risers:
    try:
        w_ = 0.25 if "3V3" in net else 0.15
        out = R.route(net, a, b, w=w_, **LCOST)
        if net in ("3V3", "3V3_AUX"):              # root these supplies: later to_net calls must reach the source
            R.seed(net, [(L, "seg", (p[0], p[1], q[0], q[1], w_ / 2)) for L, xy in out for p, q in zip(xy, xy[1:])] +
                   [(a[0], "circle", (a[1], a[2], 0.1)), (b[0], "circle", (b[1], b[2], 0.1))])
        if net == "3V3_AUX":                       # C9 first: the slot lines routed next would box its pad in
            c9 = [q.GetNumber() for q in k.fps["C9"].Pads() if q.GetNetname() == "3V3_AUX"][0]
            R.to_net("3V3_AUX", ("L1", *k.padxy("C9", c9)), w=0.25, **LCOST)
    except RuntimeError as e:
        print("FAIL riser", net, e)
for net, v in card.supply_vias.items():
    nn = k.padnet("U1", str(net))
    if nn in ("3V3", "3V3_A"):
        try:
            R.to_net(nn, ("all", *v), w=0.25, **LCOST)
        except RuntimeError as e:
            if not ("no target copper" in str(e) and nn not in R.conn):
                print("FAIL buffer supply", net, e)
card.wire()
print("t card", round(time.time() - T0))
for j, (d, xc) in enumerate(DRV if os.environ.get("STAGE") != "card" else ()):
    SB[d]["taps"] = {net: tv[j] for net, tv in card.taps.items()}
    sideband.route_block(k, R, d, SB[d], JP[d], YVMD[d], YVTD[d])
    card.after_block(j)
    print("t block", d, round(time.time() - T0))

# ------------------------------------------------------------------ aux 12 V: PCIe 6-pin on the tail tab (opt-in per drive)
# Molex 45558 / Mini-Fit Jr 2x3 R/A, 1-3 +12V, 4-6 GND, on the drive side, plug toward the card end.  Feeds only the
# 12V_AUX plane, which reaches each drive's jumper; never connected to slot 12 V.
k.fp("Connector_Molex", "Molex_Mini-Fit_Jr_5569-06A2_2x03_P4.20mm_Horizontal", "J5", "PCIe 6-pin 45558-0003",
     -8.0, -24.6, 270, bottom=True, pads={"1": "12V_AUX", "2": "12V_AUX", "3": "12V_AUX", "4": "GND", "5": "GND", "6": "GND"},
     lcsc="C7545781")
cva, cga = two("C19", *C1206, "22uF 25V X5R", -4.0, -33.0, 90, False, (-4.0, -31.0), "12V_AUX", "GND", "C12891")
k.track("12V_AUX", "L1", [cva, (cva[0] - 1.6, cva[1])], 0.6); k.via("12V_AUX", cva[0] - 1.6, cva[1], 0.6, 0.3)
k.track("GND", "L1", [cga, (cga[0] - 1.6, cga[1])], 0.6); k.via("GND", cga[0] - 1.6, cga[1], 0.6, 0.3)
k.text("AUX 12V", -11.0, -29.6, P.B_SilkS, 1.0, mirror=True)

# ------------------------------------------------------------------ rev F: bring-up and service features (gen/extras.py)
EX = extras.Extras(k, R, P)
EX.column()
EX.foot(XM)
for d, xc in DRV:
    EX.drive(d, IDX[d], xc, YPD[d], last=d == "A", dy=-1.0)
EX.tvs(-11.5, -28.4)
# fan header on the tail tab next to the aux plug, drive side.  The fan is fed from the aux 12 V plane only: the slot
# cannot spare a 92x38 fan's 3 A next to three or four drives, and no slot 12 V copper reaches the tab.  Pin 1 (GND)
# and pin 2 (12 V) are through-hole pins straight into their planes.
k.fp("Connector", "FanPinHeader_1x04_P2.54mm_Vertical", "J7", "fan 4-pin PWM (fed from the aux 12 V plug)", -15.5, -33.5,
     180, bottom=True, pads={"1": "GND", "2": "12V_AUX", "3": "FAN_TACH", "4": "FAN_PWM"}, lcsc="C240840")
assert k.padxy("J7", "1")[0] < k.padxy("J7", "4")[0]
k.text("FAN", -17.2, -36.6, P.B_SilkS, 1.0, mirror=True)
for net, txy, q in (("FAN_TACH", (-19.8, -31.4), "3"), ("FAN_PWM", (-19.8, -35.4), "4")):
    EX.R_route(net, EX.tp(net, *txy), k.padxy("J7", q))
EX.holes(XM, (-76.0, -106.0), -53.0)
GAPH = EX.gap_holes([(a[1] + b[1]) / 2 for a, b in zip(DRV, DRV[1:])], 11)
print("t extras", round(time.time() - T0), "fails", len(EX.fails))

# ------------------------------------------------------------------ planes
# L4: slot 12 V (fingers -> every jumper's slot via) in the band next to the fingers, 12V_AUX everywhere else
# (window-side band -> every jumper's aux via, the tail tab with the 6-pin).  12 V has priority.
YSPL_LO, YSPL_HI = YPL + sideband.YSPLIT, YPD["A"] + sideband.YSPLIT
k.zone("GND", "L2", BOARD, clearance=0.2)
k.zone("GND", "L5", BOARD, clearance=0.2)
k.zone("12V", "L4", [(0, 1), (XM + 1, 1), (XM + 1, YSPL_HI + 0.3), (XSTEP, YSPL_HI + 0.3), (XSTEP, YSPL_LO + 0.3),
                     (0, YSPL_LO + 0.3)], prio=1, clearance=0.3)
k.zone("12V_AUX", "L4", [(-TAB - 1, 1), (XM + 1, 1), (XM + 1, YTOP - 1), (-TAB - 1, YTOP - 1)], clearance=0.3, thermal=False)
k.zone("GND", "L3", BOARD, clearance=0.25)

# ------------------------------------------------------------------ holes: bracket screws + holder slots
for hn, (hx, hy) in (("H1", (M(7.5), -94.75)), ("H2", (M(7.5), -9.35))):
    k.keepout(f"{hn}_L4_VOID", [(hx + 2.7 * math.cos(math.radians(a)), hy + 2.7 * math.sin(math.radians(a)))
                                for a in range(0, 360, 30)], ["L4"])
    k.fp("MountingHole", "MountingHole_3.2mm_M3", hn, "bracket", hx, hy, bom=False)
for i, (x, y) in enumerate(((6.0, -30.0), (6.0, -60.0), (XM - 4.0, -46.0), (XM - 4.0, -68.0))):
    k.fp("u3adapter", "MountingSlot_M3_3.2x6.2", f"H{3 + i}", "M3 slot", x, y, bom=False)

# ------------------------------------------------------------------ silkscreen
FRONT = lambda s_, x, y: k.text(s_, x, y, P.B_SilkS, 1.0, mirror=True)       # reads on the card front after the flip
XTX = XS["B"] + 34.0
FRONT(f"U.3 x16 passive {N} drives  rev G", XTX, -25.4)
FRONT("x4x4x4x4 bifurcation" if N == 4 else "x4x4x4 / x8x4x4 bifurcation", XTX, -27.0)
FRONT("C/D: PCIe Gen3 only" if N == 4 else "C: PCIe Gen3 only", XTX, -28.6)
for d, xc in DRV:
    FRONT(f"DRIVE {d}", xc, YPD[d] - 8.2)
for ref, f in k.fps.items():
    for g in list(f.GraphicalItems()):          # library silk crowds the dense fields; JLC places by CPL
        if g.GetLayer() in (P.F_SilkS, P.B_SilkS) and g.GetClass() != "FP_TEXT":
            f.Remove(g)
    f.Value().SetVisible(False)
    f.Reference().SetVisible(False)
k.save()
with open(os.path.join(OUT, "bom_raw.json"), "w") as f:
    json.dump(k.bom, f, indent=1)

# ------------------------------------------------------------------ lengths (PCB copper incl. via height)
lens = {}
for net, segs in k.lines.items():
    if net.startswith(("PET", "PER", "C_PER", "REFCLK")):
        lens[net] = round(sum(plen(p) for _, p, _ in segs) + VIA_H * len(k.vias_by_net.get(net, [])), 3)
lane = {}
for ln in range(4 * N):
    for kind in ("PET", "PER"):
        tot = {pn: lens.get(f"{kind}{ln}_{pn}", 0) + lens.get(f"C_{kind}{ln}_{pn}", 0) for pn in "PN"}
        lane[f"{kind}{ln}"] = tot
with open(os.path.join(OUT, "lengths.json"), "w") as f:
    json.dump({"nets": lens, "lanes_finger_to_U3": lane}, f, indent=1)
for k_, v in lane.items():
    print(f"{k_:6s} P {v['P']:7.3f}  N {v['N']:7.3f}  skew {abs(v['P'] - v['N']):.3f}" + ("  OVER 50 mm" if max(v.values()) > 50 else ""))

if __name__ == "__main__":
    import subprocess
    skew = subprocess.run([sys.executable, os.path.join(RULES, "gen_pair_skew_rules.py"), k.pcb],
                          capture_output=True, text=True).stdout
    extra = """(rule "silk may sit on masked copper (only pads/holes need clearance)"
    (condition "A.Type != 'Pad' && B.Type != 'Pad' && A.Type != 'Via' && B.Type != 'Via'")
    (constraint silk_clearance (min 0mm)))
(rule "x16 passive: drives B-D exceed the 50.8 mm direct-attach cap by design (populate as needed)"
    (condition "A.NetClass == 'PCIe_85' && (A.NetName == '*PE?4_*' || A.NetName == '*PE?5_*' || A.NetName == '*PE?6_*' || A.NetName == '*PE?7_*' || A.NetName == '*PE?8_*' || A.NetName == '*PE?9_*' || A.NetName == '*PE?1?_*')")
    (constraint length (max 300mm)))
(rule "PCIe85 front drives: drive lane 0 TX hops over the top pad row (two via pairs on one net), 3 mm uncoupled in total"
    (condition "A.NetClass == 'PCIe_85' && A.intersectsArea('NECKDOWN*')")
    (constraint diff_pair_uncoupled (max 3.0mm)))"""
    extra += "\n" + cardkit.DRU + "\n" + cardkit.DRU_L3
    bb, rpt = k.fill_and_check(skew + "\n" + extra)
    c, items = drc_summary(rpt)
    print("DRC:", dict(c))
