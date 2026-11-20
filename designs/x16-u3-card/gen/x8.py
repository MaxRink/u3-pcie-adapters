"""Design 2: PCIe x8 card (x4x4 bifurcation) with two U.3 drives standing upright on their connectors.

Board frame: x from the bracket-side card edge (CEM datum), y up = negative (KiCad y down), y=0 is the
finger edge.  CEM outline numbers come from lucanastasio/PCIexpress-KiCad (CEM r1.2 templates): pin 1 at
x=45.65, outside the finger span the bottom edge is 12.75 mm above the finger edge, full height 111.15.

The two Amphenol SFF-8639 receptacles sit on the BOTTOM side (mirrored), mating face toward the card top,
so U.3 lane order matches the finger lane order with no crossings: drives stand on the card's back side
with their connectors facing the motherboard.  Lanes 0-3 -> drive A (left), lanes 4-7 -> drive B (right).
Stackup JLC06161H-3313: L1 HS | L2 GND | L3 LS+GND | L4 12V | L5 GND | L6 HS.
PET (finger side B, F.Cu) run on L1 and drop to L6 next to the receptacle; PER (side A, B.Cu) stay on L6.
Drive lanes 0/1 RX (PER) get 220 nF AC caps (SFF-TA-1001 Rev 1.1 sec. 4.5, Table 4-11).
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbkit import *
from symlib import U3_PINS
import sideband
import cardkit
import extras
from router import Router

VAR = "-cdcdb400" if os.environ.get("U3_CLK") == "cdcdb400" else ""     # alternate card versions get their own folder
UNX = os.environ.get("U3_LANES") == "uncrossed"                         # lanes crossed back on the board
VAR += "-uncrossed" if UNX else ""
OUT = os.path.join(ROOT, "boards", "x8" + VAR)
k = Kit(OUT, "u3_x8" + VAR.replace("-", "_"))
U3FP = "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD"

# ------------------------------------------------------------------ frames
# Rev G: the drives sit on the card FRONT (CEM component side).  The card is generated in a mirrored frame and flipped
# once when it is saved (Kit.mirror_all): in this frame the receptacles are bottom-side parts and the drive blocks,
# trunks and clocks are the proven rev F ones.  Mirrored x = XM - physical x, so the bracket is at x = XM and the
# card's free end at x = -TAB; layer names here are mirrored too (L1 = physical L6 ... L3 = physical L4).
# Only the finger field is laid out in the physical frame (through kf).
XM = 169.0                 # bracket-side card edge (drive nearest the bracket: 48 mm from it, as the CEM tab needs)
TAB, YTAB = 22.6, -38.0    # tail tab beyond the last drive's column: aux 12 V plug, bulk cap, TVS
k.xm = XM
kf = Phys(k, XM)
M = lambda x: XM - x
cardkit.allow_refclk_in_l3(k)

# ------------------------------------------------------------------ geometry (mirrored frame)
FX = 45.65                 # finger footprint origin = pin 1 (CEM: 45.65 mm from the bracket-side edge), physical
XB, XA = 48.0, 121.0       # receptacle centres: drive A is the one next to the bracket (lanes 0-3)
DRV = (("B", XB), ("A", XA))                # west to east in this frame
IDX = {"A": 0, "B": 1}
YP = -24.0                 # receptacle peg line
YE = YP + sideband.YEDGE   # window edge: 0.65 mm short of the housing face (10.05 mm from the pegs)
YTOP = -111.15             # CEM full height
YVT = -20.4                # via row between the top pad row and the fingers
YVM = -26.5                # via row on the mating side of the bottom pad row
Y0 = -6.0                  # where pairs leave the finger field
LVL = {0: -15.2, 1: -16.2, 2: -17.2, 3: -18.2, 7: -15.2, 6: -16.2, 5: -17.2, 4: -18.2}   # band horizontals
COLW = 12.0                # column width at both card ends

# ------------------------------------------------------------------ CEM x8 edge pinout (side B = front, side A = back)
GND_B = [4, 7, 13, 16, 18, 21, 22, 25, 26, 29, 32, 35, 36, 39, 40, 43, 44, 47, 49]
GND_A = [4, 12, 15, 18, 20, 23, 24, 27, 28, 31, 34, 37, 38, 41, 42, 45, 46, 49]
fing = {f"B{n}": "GND" for n in GND_B}
fing.update({f"A{n}": "GND" for n in GND_A})
fing.update({"B1": "12V", "B2": "12V", "B3": "12V", "A2": "12V", "A3": "12V",
             "B8": "3V3", "A9": "3V3", "A10": "3V3", "B10": "3V3_AUX_SLOT", "A11": "PCIE_RST_N",
             "A1": "PRSNT_N", "B48": "PRSNT_N", "A13": "REFCLK_IN_P", "A14": "REFCLK_IN_N",
             "B5": "SMCLK_SLOT", "B6": "SMDAT_SLOT", "B11": "PCIE_WAKE_N", "B12": "CLKREQ_N"})
PET_PINS = {0: (14, 15), 1: (19, 20), 2: (23, 24), 3: (27, 28), 4: (33, 34), 5: (37, 38), 6: (41, 42), 7: (45, 46)}
PER_PINS = {0: (16, 17), 1: (21, 22), 2: (25, 26), 3: (29, 30), 4: (35, 36), 5: (39, 40), 6: (43, 44), 7: (47, 48)}
for ln, (p, n) in PET_PINS.items():
    fing[f"B{p}"], fing[f"B{n}"] = f"PET{ln}_P", f"PET{ln}_N"
for ln, (p, n) in PER_PINS.items():
    fing[f"A{p}"], fing[f"A{n}"] = f"PER{ln}_P", f"PER{ln}_N"
# placed pre-flipped, so the final flip puts it on the front with pin 1 at FX
J1 = k.fp("Connector_PCBEdge", "BUS_PCIexpress_x8", "J1", "PCIe x8 edge", M(FX), -3.45, 0, bottom=True, pads=fing, bom=False)
fpad = lambda n: k.padxy("J1", n)
assert abs(fpad("B1")[0] - M(FX)) < 1e-6 and k.fps["J1"].IsFlipped()


# ------------------------------------------------------------------ U.3 receptacles (drive side; bottom in this frame)
def u3net(pin, d):
    n = U3_PINS[pin]
    # sidebands (SMBus, PERST0/1#, PWRDIS, DualPortEn#, PRSNT#, IfDet#, IfDet2#, WAKE#, 12 V) come from the
    # drive's sideband block (gen/sideband.py); REFCLK1 / port B lanes stay open (single-port x4)
    m = {"GND": "GND", "HPT0": "GND", "3V3_AUX": "3V3_AUX", "ACTIVITY#": f"{d}_ACT_N"}
    return m.get(n)          # lanes and REFCLK get their nets from the router; U.2/port-B/5V/HPT1 etc. open


JP = {}
for d, xc in DRV:
    pads = {p: u3net(p, d) for p in U3_PINS if u3net(p, d)}
    pads["MP"] = "GND"
    k.fp("u3adapter", U3FP, f"J{d}", "PSAS4F2130021TR", xc, YP, 180, bottom=True, pads=pads, lcsc="C22454449")
    JP[d] = lambda n, d=d: k.padxy(f"J{d}", n)
R = Router(k)
SB = {d: sideband.block(k, R, d, IDX[d], xc, YP, JP[d], 10 + 4 * IDX[d], 20 + 20 * IDX[d], 20 + 10 * IDX[d])
      for d, xc in DRV}

# ------------------------------------------------------------------ outline (physical points, mirrored)
arc = k.arc_pts((43.175, -10.925), 1.825, 180, 360)            # CEM notch between foot and fingers
XT = XM + TAB
tail = [(96.3, -12.75), (XT, -12.75), (XT, YTAB), (XM, YTAB), (XM, YTOP), (XM - COLW, YTOP), (XM - COLW, YE),
        (COLW, YE), (COLW, YTOP), (0, YTOP)]
foot = [(0, -4.5), (15.0, -4.5), (15.0, -12.75), (33.35, -12.75), (33.35, -4.5), (41.35, -4.5)] + arc
MP = lambda pts: [(M(x), y) for x, y in pts]
k.outline(MP([(96.3, -8.4)] + tail + foot + [(45.0, -8.4)]), closed=False)
BOARD = MP(foot + [(45.0, 0), (96.3, 0)] + tail)
RECT = lambda x0, x1, y0, y1: MP([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
k.rule_area("FINGERS", RECT(44.9, 96.4, 0.6, -5.75))
k.rule_area("NECKDOWN_FINGERS", RECT(44.9, 96.4, 0.6, -7.4))
for d, xc in DRV:
    k.rule_area(f"NECKDOWN_J{d}", [(xc - 20.5, YVT + 0.9), (xc + 20.5, YVT + 0.9), (xc + 20.5, YVM - 0.9),
                                   (xc - 20.5, YVM - 0.9)])
# finger field: void L2/L4/L5 under the pads, L3 stays GND (design-rules README sec. 6; the stack is symmetric)
for L in ("L2", "L4", "L5"):
    k.keepout(f"FINGER_VOID_{L}", RECT(44.8, 96.5, 0.6, -5.9), [L])

# ------------------------------------------------------------------ helpers
d_pair = (PCIE_W + PCIE_G) / 2
hs_len_extra = {}


YKNEE = -11.6              # lanes rise straight to here: clears the raised edge behind the fingers (lanes heading
#                            away from the bracket) and the slot clock / sideband vias next to lane 0 (the others)


def band_center(xc, h, xt, yend, dirn, c=0.8):
    yv = YKNEE
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
# In this frame the fingers' side B (PET) is L6, the receptacle's layer, and side A (PER) is L1.  Finger lanes 0-3 go
# to drive A, 4-7 to drive B.  Inside a drive the receptacle's lane order runs against the fingers' (front mounting):
#   default      finger lane n -> drive lane 3 - n % 4, straight through; the x4 port trains lane-reversed
#   U3_LANES=uncrossed   finger lane n -> drive lane n % 4 (see uncross below)
# Drive lanes 0/1 RX (PER) get 220 nF AC caps (SFF-TA-1001 Rev 1.1 sec. 4.5, Table 4-11).
SP_PET = {0: ("S2", "S3"), 1: ("S9", "S10"), 2: ("S17", "S18"), 3: ("S23", "S24")}
SP_PER = {0: ("S5", "S6"), 1: ("S12", "S13"), 2: ("S20", "S21"), 3: ("S26", "S27")}


def lane_of(ln):
    d = "A" if ln < 4 else "B"
    return d, f"J{d}", 3 - ln % 4, (1 if d == "A" else -1), LVL[ln]


def pet_lane(ln):
    """L6 from the fingers straight into the top-row pads; drive lane 0 (bottom row) hops over the top row on L1."""
    d, ref, dl, dirn, h = lane_of(ln)
    pins = PET_PINS[ln]; sp = SP_PET[dl]
    xc = sum(fpad(f"B{p}")[0] for p in pins) / 2
    xt = sum(JP[d](n)[0] for n in sp) / 2
    st = fstarts(pins, "B")
    if dl:
        res = k.pair("L6", band_center(xc, h, xt, YVT - 0.2, dirn), st,
                     [(None, [(JP[d](n)[0], YVT - 0.75)]) for n in sp])
        name_pads(ref, res, sp)
        return res
    ytr = YVT + 1.0                            # same row on both drives: the L3 slot feeders pass south of it
    res = k.pair("L6", band_center(xc, h, xt, ytr + 0.45, dirn, c=0.4), st, [(None, [(JP[d](n)[0], ytr)]) for n in sp])
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
    d, ref, dl, dirn, h = lane_of(ln)
    pins = PER_PINS[ln]; sp = SP_PER[dl]
    xc = sum(fpad(f"A{p}")[0] for p in pins) / 2
    xt = sum(JP[d](n)[0] for n in sp) / 2
    st = fstarts(pins, "A")
    if dl >= 2:
        res = k.pair("L1", band_center(xc, h, xt, YVT + 0.32, dirn), st, [(None, [(JP[d](n)[0], YVT)]) for n in sp])
        stub_to_pad(ref, sp, vias_at(res), "L6", YVT - 1.0)
        return res
    yc = h - 1.4 if dl else -22.6            # caps: just above the band (lane 1) / over the receptacle (lane 0)
    res = k.pair("L1", band_center(xc, h, xt, (h - 0.6) if dl else (yc + 0.9), dirn, c=0.4), st,
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
for ln in range(8):
    lanes[f"PET{ln}"] = pet_lane(ln)
    lanes[f"PER{ln}"] = per_lane(ln)

# ------------------------------------------------------------------ top-row / bottom-row GND and misc escapes
TOP_ROW = [f"E{i}" for i in range(7, 17)] + [f"S{i}" for i in range(8, 29)] + [f"E{i}" for i in range(17, 26)]
BOT_ROW = [f"S{i}" for i in range(1, 8)] + [f"E{i}" for i in range(1, 7)] + [f"P{i}" for i in range(1, 16)]
for d, _ in DRV:
    ref = f"J{d}"
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

# ------------------------------------------------------------------ finger GND / power / sideband escapes
# physical frame (kf): the same field as on the back-drive cards
YG = -6.75                                   # finger GND via row (between the lane pairs)
xpin = lambda n: fpad(f"B{n}")[0]           # A and B pads share x (mirrored frame)
xP = lambda n: M(xpin(n))                   # physical


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
finger_gnd(12.5, x=xP(12) + 0.4)             # keep 0.5 mm off REFCLK_IN
finger_gnd(49, y=-6.85)

# 12V: B1-B3 / A2-A3 -> four vias into the 12 V plane
for x, y in ((xP(2), -6.8), (xP(3), -6.8), (xP(2), -7.8), (xP(3), -7.8)):
    kf.via("12V", x, y, 0.6, 0.3)
kf.track("12V", "L1", [(xP(1), -5.4), (xP(1), -5.9), (xP(2), -6.8)], 0.5)
for n in (2, 3):
    kf.track("12V", "L1", [(xP(n), -5.4), (xP(n), -7.8)], 0.5)
    kf.track("12V", "L6", [(xP(n), -5.4), (xP(n), -7.8)], 0.5)
# 3V3: B8 (front), A9/A10 (back) -> one via north of the PRSNT# row, so its L3 feeder does not cross that row
V33 = (xP(9), -10.4)
kf.via("3V3", *V33)
kf.track("3V3", "L1", [(xP(8), -5.4), (xP(8), -9.4), V33], 0.3)
kf.track("3V3", "L6", [(xP(9), -5.4), V33], 0.3)
kf.track("3V3", "L6", [(xP(10), -5.4), (xP(10), -5.9), (xP(9), -6.9)], 0.3)
# 3V3_AUX (B10) and PERST# (A11)
VAUX = (xP(10), -9.6); VRST = (xP(11), -10.2)
kf.track("3V3_AUX_SLOT", "L1", [(xP(10), -5.4), VAUX], 0.3); kf.via("3V3_AUX_SLOT", *VAUX)
kf.track("PCIE_RST_N", "L6", [(xP(11), -5.4), VRST], 0.2); kf.via("PCIE_RST_N", *VRST)
# PRSNT1# (A1) -> PRSNT2# x8 (B48) on L3
VPA = (xP(1), -9.0); VPB = (95.6, -8.0)
kf.track("PRSNT_N", "L6", [(xP(1), -4.6), VPA], 0.2); kf.via("PRSNT_N", *VPA)
kf.track("PRSNT_N", "L1", [(xP(48), -5.4), (xP(48), -7.3), VPB], 0.2); kf.via("PRSNT_N", *VPB)
kf.track("PRSNT_N", "L3", [VPA, (95.0, VPA[1]), VPB], 0.2)        # crosses the key slot above its 8.4 mm top
# B11 WAKE# -> via; B12 CLKREQ# tied low (clock always requested): joins the B13 GND via of the finger GND row
x11, x12 = xP(11), xP(12)
VWK = (x11 + 0.55, -11.3)
kf.track("PCIE_WAKE_N", "L1", [(x11, -5.4), (x11, -9.4), (x11 + 0.55, -9.95), VWK], 0.2); kf.via("PCIE_WAKE_N", *VWK)
k.setpad("J1", "B11", "PCIE_WAKE_N"); k.setpad("J1", "B12", "GND")
kf.track("GND", "L1", [(x12, -5.4), (x12, -6.35), (x12 + 0.4, -6.75)], 0.2)
# slot SMBus: B5/B6 -> vias
VSC, VSD = (xP(5), -10.0), (xP(6), -10.6)
kf.track("SMCLK_SLOT", "L1", [(xP(5), -5.4), VSC], 0.2); kf.via("SMCLK_SLOT", *VSC)
kf.track("SMDAT_SLOT", "L1", [(xP(6), -5.4), VSD], 0.2); kf.via("SMDAT_SLOT", *VSD)

# activity LEDs (over the receptacle, on the side away from the drive): 3V3_AUX -> 1k -> LED -> ACT#
E3 = {d: JP[d]("E3") for d, _ in DRV}
for d, xc in DRV:
    xa = E3[d][0]; xact = JP[d]("P11")[0]; dx = xc - 48.0
    xr, xl = 55.1 + dx, 57.7 + dx
    rn = f"R{11 + IDX[d]}"; ln_ = f"D{1 + IDX[d]}"
    nr, fr = two(rn, *R0402, "1k", xr, -24.2, 0, False, (xr - 1, -24.2), "3V3_AUX", f"{d}_LEDA", "C11702")
    k.fp("LED_SMD", "LED_0603_1608Metric", ln_, "KT-0603YG", xl, -24.2, 180, pads={"1": f"{d}_ACT_N", "2": f"{d}_LEDA"},
         lcsc="C2289")
    k.track(f"{d}_LEDA", "L1", [fr, k.padxy(ln_, "2")], 0.2)
    k.track("3V3_AUX", "L1", [(xa, YVM), (xa, -25.5), (nr[0] - 0.5, -25.5), (nr[0] - 0.5, nr[1]), nr], 0.25)
    kp = k.padxy(ln_, "1")
    k.track(f"{d}_ACT_N", "L1", [kp, (xact, kp[1] - 0.4), (xact, YVM)], 0.2)

# ------------------------------------------------------------------ card-level parts, REFCLK, trunks
# all at the card's free end (west in this frame), as on the back-drive cards; the slot nets come over on L3
import time; T0 = time.time()
card = cardkit.Card(k, R, xpin, fpad, [(d, xc, YP, JP[d]) for d, xc in DRV], YP)
card.buffer({DRV[0][0]: 3, DRV[1][0]: 2})
YROW = -13.45              # REFCLK_IN on L3; the slot nets run north of it
print("REFCLK_IN skew", round(card.refclk_in_l3(yrow=YROW), 3))
card.parts(dy=-0.4)          # the tail edge is 12.75 mm up: lift the TPS2116 group clear of it
card.vwake = kf.X(VWK)
card.clock_direct(DRV[0][0], 3)
card.clock_channel(DRV[1][0], 2, row=YP + sideband.CLK_Y[0], xdrop=DRV[1][1] - 25.0)
first = card.trunks({"SMCLK": 13.5, "SMDAT": 14.5, "3V3_AUX": 15.5, "PCIE_RST_N": 27.45, "PCIE_WAKE_N": 28.3})
# slot feeders on L3 under the lane field: each rises north from its finger via (PERST# first steps west of the
# WAKE# via, so it ends up the southern line as the trunk starts need it) to its row, then runs west.
# PERST# / WAKE# go all the way to their trunk starts; the others end short of drive B's lane vias, the router
# takes them on to the TCA9548A and the TPS2116.
V = kf.X
(xr_, yr_), (xw_, yw_) = V(VRST), V(VWK)
FEED = {
    "PCIE_RST_N": (0.15, [(xr_, yr_), (xr_ - 1.15, yr_), (xr_ - 1.15, -13.9), (xr_ - 1.55, -14.3), (27.85, -14.3),
                          (27.45, -14.7), first["PCIE_RST_N"]]),
    # WAKE# passes 0.2 from the peg hole (29, -24), then steps east to leave room for the PERST# tap via
    "PCIE_WAKE_N": (0.15, [(xw_, yw_), (xw_, -14.3), (xw_ - 0.4, -14.7), (28.2, -14.7), (27.8, -15.1),
                           (27.8, -26.0), (28.3, -26.5), first["PCIE_WAKE_N"]]),
}
ENDS = {}
# rows south to north; each ends in a via in the pocket between the PERST#/WAKE# verticals and drive B's lane 0
for i, (net, v, yrow, w_) in enumerate((("3V3_AUX_SLOT", V(VAUX), -15.1, 0.15), ("3V3", V(V33), -15.6, 0.3),
                                        ("SMDAT_SLOT", V(VSD), -16.1, 0.15), ("SMCLK_SLOT", V(VSC), -16.5, 0.15))):
    xv, yv = 28.9 + 1.0 * i, -16.3 - 0.55 * i
    FEED[net] = (w_, [v, (v[0], yrow + 0.4), (v[0] - 0.4, yrow), (xv + 0.4, yrow), (xv, yrow - 0.4), (xv, yv)])
    k.via(net, xv, yv)
    ENDS[net] = ("all", xv, yv)
for net, (w_, pts) in FEED.items():
    k.track(net, "L3", pts, w_)
# drive B's reset gate / WAKE buffer tap these verticals (1.05 mm apart, room for a via on each)
for net, tv in (("PCIE_RST_N", (27.45, YP - 6.3)), ("PCIE_WAKE_N", (28.3, YP - 5.0))):
    k.via(net, *tv); card.taps[net].append(tv)
LCOST = dict(layer_cost={"L1": 2.5, "L6": 2.5}, via_cost=1.0, maxpad=12.0)
U2 = lambda q: ("L1", *k.padxy("U2", q))
U3 = lambda net: ("L1", *card.u3t[net])
# local bus risers (hand-laid): U2 SC0/SD0 east -> vias -> L3 north along the column edge -> trunk starts
for net, q, xv in (("SMCLK", "5", 10.6), ("SMDAT", "4", 11.4)):
    pq = k.padxy("U2", q); f0 = first[net]
    k.track(net, "L1", [pq, (xv, pq[1])], 0.15); k.via(net, xv, pq[1])
    k.track(net, "L3", [(xv, pq[1]), (xv, f0[1]), f0], sideband.TRK_W)
for net in ("PCIE_RST_N", "PCIE_WAKE_N"):          # root the hand-laid slot lines for the router
    pts = FEED[net][1]
    R.seed(net, [("L3", "seg", (p[0], p[1], q[0], q[1], 0.075)) for p, q in zip(pts, pts[1:])] +
           [("all", "circle", (pts[0][0], pts[0][1], 0.1))])
risers = [("3V3", ENDS["3V3"], U3("3V3")), ("3V3_AUX", U3("3V3_AUX"), ("L3", *first["3V3_AUX"])),
          ("SMCLK_SLOT", ENDS["SMCLK_SLOT"], U2("22")), ("SMDAT_SLOT", ENDS["SMDAT_SLOT"], U2("23")),
          ("3V3_AUX_SLOT", ENDS["3V3_AUX_SLOT"], U3("3V3_AUX_SLOT"))]
card.seed_trunks()
if cardkit.CDC:      # CDCDB400 version: the slot SMBus risers box in the mux reset pull-up; wire it first
    qr = [q.GetNumber() for q in k.fps["RN10"].Pads() if q.GetNetname() == "MUX_RST_N"][0]
    R.route("MUX_RST_N", ("L1", *k.padxy("U2", "3")), ("L1", *k.padxy("RN10", qr)), w=0.15, **LCOST)
for net, a, b in risers:
    try:
        w_ = 0.25 if "3V3" in net else 0.15
        out = R.route(net, a, b, w=w_, **LCOST)
        if net in ("3V3", "3V3_AUX"):              # root these supplies: later to_net calls must reach the source
            R.seed(net, [(L, "seg", (p[0], p[1], q[0], q[1], w_ / 2)) for L, xy in out for p, q in zip(xy, xy[1:])] +
                   [(a[0], "circle", (a[1], a[2], 0.1)), (b[0], "circle", (b[1], b[2], 0.1))])
            if net in FEED:
                pts = FEED[net][1]
                R.seed(net, [("L3", "seg", (p[0], p[1], q[0], q[1], 0.15)) for p, q in zip(pts, pts[1:])] +
                       [("all", "circle", (pts[0][0], pts[0][1], 0.1))])
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
    sideband.route_block(k, R, d, SB[d], JP[d], YVM, YVT)
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
    EX.drive(d, IDX[d], xc, YP, last=d == DRV[-1][0])
EX.tvs(-14.0, -33.4)
EX.fan_front(XA + 26.2, -15.4, XA + 27.8, -20.5, ((XA + 34.2, -20.4), (XA + 36.6, -20.4)))
EX.holes(XM, (-76.0, -106.0), -53.0)
GAPH = EX.gap_holes([84.5], 11)
print("t extras", round(time.time() - T0), "fails", len(EX.fails))

# ------------------------------------------------------------------ planes
# L4: slot 12 V toward the fingers (to each jumper's SLOT via), 12V_AUX toward the window, at the bracket end (fan
# jumper) and on the tail tab (J5).  Under the slot clock's L3 run and in the finger field the layer is GND.
YSPL = YP + sideband.YSPLIT
XAUX = XA + 30.5
k.zone("GND", "L2", BOARD, clearance=0.2)
k.zone("GND", "L5", BOARD, clearance=0.2)
k.zone("12V", "L4", [(0, 1), (XAUX - 0.3, 1), (XAUX - 0.3, YSPL + 0.3), (0, YSPL + 0.3)], clearance=0.2)
k.zone("12V_AUX", "L4", [(-TAB - 1, 1), (-0.3, 1), (-0.3, YSPL - 0.3), (XAUX + 0.3, YSPL - 0.3), (XAUX + 0.3, 1),
                         (XM + 1, 1), (XM + 1, YTOP - 1), (-TAB - 1, YTOP - 1)], clearance=0.2, thermal=False)
xk = M(xP(12)) + 1.9                           # east end: just short of the key slot / pins 1-11
k.zone("GND", "L4", [(23.0, -12.6), (M(96.3) + 0.3, -12.6), (M(96.3) + 0.3, -5.9), (xk, -5.9), (xk, YROW - 0.65),
                     (23.0, YROW - 0.65)], prio=2, clearance=0.2, name="REFCLK_IN_REF")
k.zone("GND", "L3", BOARD, clearance=0.25)
# ------------------------------------------------------------------ holes: bracket screws + holder slots
# bracket screw holes: keep the L4 12 V planes 1.1 mm off the hole wall (a screw must never reach 12 V)
for hn, (hx, hy) in (("H1", (M(7.5), -94.75)), ("H2", (M(7.5), -9.35))):
    k.keepout(f"{hn}_L4_VOID", [(hx + 2.7 * math.cos(math.radians(a)), hy + 2.7 * math.sin(math.radians(a)))
                                for a in range(0, 360, 30)], ["L4"])
    k.fp("MountingHole", "MountingHole_3.2mm_M3", hn, "bracket", hx, hy, bom=False)
for i, (x, y) in enumerate(((6.0, -30.0), (6.0, -60.0), (XM - 4.0, -38.0), (XM - 4.0, -68.0))):
    k.fp("u3adapter", "MountingSlot_M3_3.2x6.2", f"H{3 + i}", "M3 slot", x, y, bom=False)

# ------------------------------------------------------------------ silkscreen
FRONT = lambda s_, x, y: k.text(s_, x, y, P.B_SilkS, 1.0, mirror=True)       # reads on the card front after the flip
FRONT("U.3 x8  rev G" + ("  uncrossed" if UNX else ""), 46.0, -13.9)
FRONT("x4x4 bifurcation", 64.0, -13.9)
for d, xc in DRV:
    FRONT(f"DRIVE {d}", xc, -32.2)
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
VIA_H = 1.5784
lens = {}
for net, segs in k.lines.items():
    if net.startswith(("PET", "PER", "C_PER", "REFCLK")):
        lens[net] = round(sum(plen(p) for _, p, _ in segs) + VIA_H * len(k.vias_by_net.get(net, [])), 3)
lane = {}
for ln in range(8):                         # finger -> receptacle copper per lane (PER lanes 0/1 include the cap)
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
    (constraint silk_clearance (min 0mm)))"""
    extra += "\n" + cardkit.DRU + """
(rule "x8 front drives: drive B sits 8 mm further from its fingers than on the back (its lane pins are on the far half of the receptacle), lanes 4-7 run up to 66 mm"
    (condition "A.NetClass == 'PCIe_85' && (A.NetName == '*PE?4_*' || A.NetName == '*PE?5_*' || A.NetName == '*PE?6_*' || A.NetName == '*PE?7_*')")
    (constraint length (max 70mm)))
(rule "PCIe85 front drives: drive lane 0 TX hops over the top pad row (two via pairs on one net), 3 mm uncoupled in total"
    (condition "A.NetClass == 'PCIe_85' && A.intersectsArea('NECKDOWN*')")
    (constraint diff_pair_uncoupled (max 3.0mm)))"""
    bb, rpt = k.fill_and_check(skew + "\n" + extra)
    c, items = drc_summary(rpt)
    print("DRC:", dict(c))
