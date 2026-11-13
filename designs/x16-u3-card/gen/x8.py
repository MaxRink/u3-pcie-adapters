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
from router import Router

OUT = os.path.join(ROOT, "boards", "x8")
k = Kit(OUT, "u3_x8")
U3FP = "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD"

# ------------------------------------------------------------------ geometry
FX = 45.65                 # finger footprint origin = pin 1 (CEM: 45.65 mm from the bracket-side edge)
XA, XB = 48.0, 121.0       # receptacle centres (drive A / drive B)
YP = -24.0                 # receptacle peg line
YE = YP + sideband.YEDGE   # window edge: 0.65 mm short of the housing face (10.05 mm from the pegs)
XR = 190.0                 # card length (room for drive B's sideband block and the aux 12 V plug)
YTOP = -111.15             # CEM full height
YVT = -20.4                # via row between the top pad row and the fingers
YVM = -26.5                # via row on the mating side of the bottom pad row
Y0 = -6.0                 # where pairs leave the finger field
LVL_A = {0: -15.2, 1: -16.2, 2: -17.2, 3: -18.2}      # band A horizontals (lane 0 lowest)
LVL_B = {7: -15.2, 6: -16.2, 5: -17.2, 4: -18.2}      # band B horizontals (lane 7 lowest)
Y_REFIN = -14.2            # REFCLK input horizontal (L6), below band A
COLW = 12.0                # bracket-side column width

# ------------------------------------------------------------------ CEM x8 edge pinout (side B = F.Cu, side A = B.Cu)
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
J1 = k.fp("Connector_PCBEdge", "BUS_PCIexpress_x8", "J1", "PCIe x8 edge", FX, -3.45, 0, pads=fing, bom=False)
fpad = lambda n: k.padxy("J1", n)


# ------------------------------------------------------------------ U.3 receptacles (bottom, mirrored)
def u3net(pin, d):
    n = U3_PINS[pin]
    # sidebands (SMBus, PERST0/1#, PWRDIS, DualPortEn#, PRSNT#, IfDet#, IfDet2#, WAKE#, 12 V) come from the
    # drive's sideband block (gen/sideband.py); REFCLK1 / port B lanes stay open (single-port x4)
    m = {"GND": "GND", "HPT0": "GND", "3V3_AUX": "3V3_AUX", "ACTIVITY#": f"{d}_ACT_N"}
    return m.get(n)          # lanes and REFCLK get their nets from the router; U.2/port-B/5V/HPT1 etc. open


JP = {}
for d, xc in (("A", XA), ("B", XB)):
    pads = {p: u3net(p, d) for p in U3_PINS if u3net(p, d)}
    pads["MP"] = "GND"
    k.fp("u3adapter", U3FP, f"J{d}", "PSAS4F2130021TR", xc, YP, 180, bottom=True, pads=pads, lcsc="C22454449")
    JP[d] = lambda n, d=d: k.padxy(f"J{d}", n)
R = Router(k)
SB = {d: sideband.block(k, R, d, i, xc, YP, JP[d], 10 + 4 * i, 20 + 20 * i, 20 + 10 * i)
      for i, (d, xc) in enumerate((("A", XA), ("B", XB)))}

# ------------------------------------------------------------------ outline
arc = k.arc_pts((43.175, -10.925), 1.825, 180, 360)            # CEM notch between foot and fingers
outline = ([(96.3, -8.4), (96.3, -12.75), (XR, -12.75), (XR, YTOP), (XR - 8.0, YTOP), (XR - 8.0, YE),
            (COLW, YE), (COLW, YTOP), (0, YTOP), (0, -4.5), (15.0, -4.5), (15.0, -12.75), (33.35, -12.75),
            (33.35, -4.5), (41.35, -4.5)] + arc + [(45.0, -8.4)])
k.outline(outline, closed=False)
BOARD = ([(0, -4.5), (15, -4.5), (15, -12.75), (33.35, -12.75), (33.35, -4.5), (41.35, -4.5)] + arc +
         [(45.0, 0), (96.3, 0), (96.3, -12.75), (XR, -12.75), (XR, YTOP), (XR - 8, YTOP), (XR - 8, YE),
          (COLW, YE), (COLW, YTOP), (0, YTOP)])
FINGERS = [(44.9, 0.6), (96.4, 0.6), (96.4, -5.75), (44.9, -5.75)]
k.rule_area("FINGERS", FINGERS)
k.rule_area("NECKDOWN_FINGERS", [(44.9, 0.6), (96.4, 0.6), (96.4, -7.4), (44.9, -7.4)])
for d, xc in (("A", XA), ("B", XB)):
    k.rule_area(f"NECKDOWN_J{d}", [(xc - 20.5, YVT + 0.9), (xc + 20.5, YVT + 0.9), (xc + 20.5, YVM - 0.9),
                                   (xc - 20.5, YVM - 0.9)])
# finger field: void L2/L4/L5 under the pads, L3 stays GND (design-rules README sec. 6)
for L in ("L2", "L4", "L5"):
    k.keepout(f"FINGER_VOID_{L}", [(44.8, 0.6), (96.5, 0.6), (96.5, -5.9), (44.8, -5.9)], [L])

# ------------------------------------------------------------------ helpers
d_pair = (PCIE_W + PCIE_G) / 2
hs_len_extra = {}


YKNEE_B = -11.6            # lanes heading right rise straight first, to clear the raised edge behind the fingers (x 96.3)


YKNEE_A = -7.7             # lanes heading left rise straight to here, leaving room for the finger GND vias


def band_center(xc, h, xt, yend, dirn, c=0.8):
    yv = YKNEE_A if dirn < 0 else YKNEE_B
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


# ------------------------------------------------------------------ PET lanes (L1 -> via -> L6 into the receptacle)
def pet_lane(ln):
    d = "A" if ln < 4 else "B"; ref = f"J{d}"; dl = ln % 4
    dirn = -1 if d == "A" else 1
    h = (LVL_A if d == "A" else LVL_B)[ln]
    pins = PET_PINS[ln]
    xc = sum(fpad(f"B{p}")[0] for p in pins) / 2
    if dl == 0:                      # S2/S3 on the bottom (mating-side) row: rise past the top row on L1
        sp = ("S2", "S3")
        xt = sum(JP[d](n)[0] for n in sp) / 2
        res = tpair("L1", band_center(xc, h, xt, YVM + 0.3, dirn), fstarts(pins, "B"),
                    [(None, [(xt + s * 0.4, YVM)]) for s in (-1, 1)])
        v = vias_at(res)
        stub_to_pad(ref, sp, v, "L6", YVM + 0.8)
        k.via("GND", xt, YVM - 0.95)                    # return via for the pair
    else:
        sp = {1: ("S9", "S10"), 2: ("S17", "S18"), 3: ("S23", "S24")}[dl]
        xt = sum(JP[d](n)[0] for n in sp) / 2
        res = k.pair("L1", band_center(xc, h, xt, YVT + 0.32, dirn), fstarts(pins, "B"),
                     [(None, [(JP[d](n)[0], YVT)]) for n in sp])
        v = vias_at(res)
        stub_to_pad(ref, sp, v, "L6", YVT - 1.0)
    return res


# ------------------------------------------------------------------ PER lanes (L6 into the receptacle)
def per_lane(ln):
    d = "A" if ln < 4 else "B"; ref = f"J{d}"; dl = ln % 4
    dirn = -1 if d == "A" else 1
    h = (LVL_A if d == "A" else LVL_B)[ln]
    pins = PER_PINS[ln]
    xc = sum(fpad(f"A{p}")[0] for p in pins) / 2
    st = fstarts(pins, "A")
    if dl in (2, 3):
        sp = {2: ("S20", "S21"), 3: ("S26", "S27")}[dl]
        xt = sum(JP[d](n)[0] for n in sp) / 2
        res = k.pair("L6", band_center(xc, h, xt, YVT - 0.2, dirn), st,
                     [(None, [(JP[d](n)[0], YVT - 0.75)]) for n in sp])
        name_pads(ref, res, sp)
        return res
    if dl == 1:                      # caps on the bottom side, inline on L6
        sp = ("S12", "S13")
        xt = sum(JP[d](n)[0] for n in sp) / 2
        yc = h - 1.4
        res = k.pair("L6", band_center(xc, h, xt, h - 0.6, dirn, c=0.4), st,
                     [(None, [(xt - 0.5, yc + 0.48)]), (None, [(xt + 0.5, yc + 0.48)])])
        caps = ac_caps(xt, yc, res, True, "L5")
        # make sure each cap's near pad sits on the line that reached it
        for net, (full, sn, en) in res.items():
            refc, near, far = caps[net]
            if math.dist(near, full[-1]) > 0.05:
                raise SystemExit(f"cap/net mismatch on {net}")
        starts = [("C_" + net, [caps[net][2], (caps[net][2][0], caps[net][2][1] - 0.35)]) for net in res]
        res2 = k.pair("L6", [(xt, yc - 1.05), (xt, YVT - 0.2)], starts,
                      [(None, [(JP[d](n)[0], YVT - 0.75)]) for n in sp])
        name_pads(ref, res2, sp)
        return {**res, **res2}
    # dl == 0: L6 -> via -> L1 (caps on top) -> via -> L6 stub into the bottom-row pads S5/S6
    sp = ("S5", "S6")
    xt = sum(JP[d](n)[0] for n in sp) / 2
    ytr = h - 1.2
    res = k.pair("L6", band_center(xc, h, xt, h - 0.75, dirn, c=0.4), st,
                 [(None, [(JP[d](n)[0], ytr)]) for n in sp])
    v1 = vias_at(res)
    for gx in (xt - 1.59, xt + 1.59):
        k.via("GND", gx, ytr)
    yc = -22.6
    starts = [(net, [v1[net]]) for net in v1]
    res2 = k.pair("L1", [(xt, ytr - 0.6), (xt, yc + 0.9)], starts,
                  [(None, [(xt - 0.5, yc + 0.48)]), (None, [(xt + 0.5, yc + 0.48)])])
    caps = ac_caps(xt, yc, res2, False, "L2")
    for net, (full, sn, en) in res2.items():
        if math.dist(caps[net][1], full[-1]) > 0.05:
            raise SystemExit(f"cap/net mismatch on {net}")
    starts = [("C_" + net, [caps[net][2], (caps[net][2][0], caps[net][2][1] - 0.1)]) for net in res2]
    res3 = k.pair("L1", [(xt, yc - 1.05), (xt, YVM + 0.3)], starts,
                  [(None, [(xt + s * 0.4, YVM)]) for s in (-1, 1)])
    v2 = vias_at(res3)
    stub_to_pad(ref, sp, v2, "L6", YVM + 0.8)
    k.via("GND", xt, YVM - 0.95)
    return {**res, **res2, **res3}


lanes = {}
for ln in range(8):
    lanes[f"PET{ln}"] = pet_lane(ln)
    lanes[f"PER{ln}"] = per_lane(ln)

# ------------------------------------------------------------------ top-row / bottom-row GND and misc escapes
TOP_ROW = [f"E{i}" for i in range(7, 17)] + [f"S{i}" for i in range(8, 29)] + [f"E{i}" for i in range(17, 26)]
BOT_ROW = [f"S{i}" for i in range(1, 8)] + [f"E{i}" for i in range(1, 7)] + [f"P{i}" for i in range(1, 16)]
for d in ("A", "B"):
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
YG = -6.75                                   # finger GND via row (between the lane pairs)
xpin = lambda n: fpad(f"B{n}")[0]           # A and B pads share x
RW, RG = 0.128, 0.254                        # REFCLK 100 ohm geometry


def finger_gnd(m, x=None, y=YG):
    lo, hi = math.floor(m), math.ceil(m)
    x = x if x is not None else (xpin(lo) + xpin(hi)) / 2
    k.via("GND", x, y)
    for side, L in (("B", "L1"), ("A", "L6")):
        for n in sorted({lo, hi}):
            if fing.get(f"{side}{n}") == "GND":
                px = xpin(n)
                k.track("GND", L, [(px, -5.4), (px, -5.9), (x, y)], 0.3)


for m in (15.5, 18, 20.5, 22.5, 24.5, 26.5, 28.5, 31.5, 34.5, 36.5, 38.5, 40.5, 42.5, 44.5, 46.5, 4, 7):
    finger_gnd(m)
finger_gnd(12.5, x=xpin(12) + 0.4)           # keep 0.5 mm off REFCLK_IN
finger_gnd(49, y=-6.85)

# 12V: B1-B3 / A2-A3 -> four vias into the L4 plane
for x, y in ((xpin(2), -6.8), (xpin(3), -6.8), (xpin(2), -7.8), (xpin(3), -7.8)):
    k.via("12V", x, y, 0.6, 0.3)
k.track("12V", "L1", [(xpin(1), -5.4), (xpin(1), -5.9), (xpin(2), -6.8)], 0.5)
for n in (2, 3):
    k.track("12V", "L1", [(xpin(n), -5.4), (xpin(n), -7.8)], 0.5)
    k.track("12V", "L6", [(xpin(n), -5.4), (xpin(n), -7.8)], 0.5)
# 3V3: B8 (L1), A9/A10 (L6) -> via, then L1 to the clock buffer
V33 = (xpin(9), -6.8)
k.via("3V3", *V33)
k.track("3V3", "L1", [(xpin(8), -5.4), (xpin(8), -5.9), V33], 0.3)
k.track("3V3", "L6", [(xpin(9), -5.4), V33], 0.3)
k.track("3V3", "L6", [(xpin(10), -5.4), (xpin(10), -5.9), V33], 0.3)
# 3V3_AUX (B10, L1) and PERST# (A11, L6)
VAUX = (xpin(10), -9.6); VRST = (xpin(11), -10.2)
k.track("3V3_AUX_SLOT", "L1", [(xpin(10), -5.4), VAUX], 0.3); k.via("3V3_AUX_SLOT", *VAUX)
k.track("PCIE_RST_N", "L6", [(xpin(11), -5.4), VRST], 0.2); k.via("PCIE_RST_N", *VRST)
# PRSNT1# (A1) -> PRSNT2# x8 (B48) on L3
VPA = (xpin(1), -9.0); VPB = (95.6, -8.0)
k.track("PRSNT_N", "L6", [(xpin(1), -4.6), VPA], 0.2); k.via("PRSNT_N", *VPA)
k.track("PRSNT_N", "L1", [(xpin(48), -5.4), (xpin(48), -7.3), VPB], 0.2); k.via("PRSNT_N", *VPB)
k.track("PRSNT_N", "L3", [VPA, (95.0, VPA[1]), VPB], 0.2)        # crosses the key slot above its 8.4 mm top

# activity LEDs (top side, over the receptacle): 3V3_AUX -> 1k -> LED -> ACT#
E3 = {d: JP[d]("E3") for d in "AB"}
for d in "AB":
    xa = E3[d][0]; xact = JP[d]("P11")[0]; dx = XB - XA if d == "B" else 0
    xr, xl = 55.1 + dx, 57.7 + dx
    rn = "R11" if d == "A" else "R12"; ln_ = "D1" if d == "A" else "D2"
    nr, fr = two(rn, *R0402, "1k", xr, -24.2, 0, False, (xr - 1, -24.2), "3V3_AUX", f"{d}_LEDA", "C11702")
    k.fp("LED_SMD", "LED_0603_1608Metric", ln_, "KT-0603YG", xl, -24.2, 180, pads={"1": f"{d}_ACT_N", "2": f"{d}_LEDA"},
         lcsc="C2289")
    k.track(f"{d}_LEDA", "L1", [fr, k.padxy(ln_, "2")], 0.2)
    k.track("3V3_AUX", "L1", [(xa, YVM), (xa, -25.5), (nr[0] - 0.5, -25.5), (nr[0] - 0.5, nr[1]), nr], 0.25)
    kp = k.padxy(ln_, "1")
    k.track(f"{d}_ACT_N", "L1", [kp, (xact, kp[1] - 0.4), (xact, YVM)], 0.2)

# ------------------------------------------------------------------ card-level parts, REFCLK, trunks
import time; T0 = time.time()
card = cardkit.Card(k, R, xpin, fpad, [(d, xc, YP, JP[d]) for d, xc in (("A", XA), ("B", XB))], YP)
card.buffer({"A": 3, "B": 2})
print("REFCLK_IN skew", round(card.refclk_in(yrun=-13.55, ycross=-14.2, ykneeA=-9.0), 3))
card.parts()
card.wake_clkreq()
card.clock_direct("A", 3)
card.clock_channel("B", 2, row=YP + sideband.CLK_Y[0], xdrop=XB - 25.0)
# slot SMBus: B5/B6 -> vias -> the TCA9548A upstream port
VSC, VSD = (xpin(5), -10.0), (xpin(6), -10.6)
k.track("SMCLK_SLOT", "L1", [(xpin(5), -5.4), VSC], 0.2); k.via("SMCLK_SLOT", *VSC)
k.track("SMDAT_SLOT", "L1", [(xpin(6), -5.4), VSD], 0.2); k.via("SMDAT_SLOT", *VSD)
first = card.trunks({"SMCLK": 13.5, "SMDAT": 14.5, "3V3_AUX": 15.5, "PCIE_RST_N": 27.45, "PCIE_WAKE_N": 28.3})
# slot PERST#/WAKE#: west on L3 under the REFCLK_IN run (clear of the CEM notch), north up the left side of drive A's
# receptacle to the trunk starts; the router only does the short hop from the finger vias
# (diagonals on x - y = 58.54 / 59.18: >= 0.9 mm from the REFCLK_IN via at (47.5, -12.95), clear of the notch)
RW_ = {"PCIE_RST_N": [(48.34, -10.2), (45.24, -13.3), (27.45, -13.3), first["PCIE_RST_N"]],
       # WAKE# passes 0.2 from the peg hole (29, -24), then steps east to leave room for the PERST# tap via
       "PCIE_WAKE_N": [(47.88, -11.3), (45.43, -13.75), (27.8, -13.75), (27.8, -26.0), (28.3, -26.5),
                       first["PCIE_WAKE_N"]]}
for net, pts in RW_.items():
    k.track(net, "L3", pts, sideband.TRK_W)
# drive A's reset gate / WAKE buffer tap these verticals (1.05 mm apart, room for a via on each)
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
risers = [("PCIE_RST_N", ("all", *VRST), ("L3", *RW_["PCIE_RST_N"][0])),
          ("PCIE_WAKE_N", ("all", *card.vwake), ("L3", *RW_["PCIE_WAKE_N"][0])),
          ("3V3", ("all", *V33), U3("3V3")), ("3V3_AUX", U3("3V3_AUX"), ("L3", *first["3V3_AUX"])),
          ("SMCLK_SLOT", ("all", *VSC), U2("22")), ("SMDAT_SLOT", ("all", *VSD), U2("23")),
          ("3V3_AUX_SLOT", ("all", *VAUX), U3("3V3_AUX_SLOT"))]
card.seed_trunks()
for net, a, b in risers:
    try:
        w_ = 0.25 if "3V3" in net else 0.15
        out = R.route(net, a, b, w=w_, **LCOST)
        if net in ("3V3", "3V3_AUX"):              # root these supplies: later to_net calls must reach the source
            R.seed(net, [(L, "seg", (p[0], p[1], q[0], q[1], w_ / 2)) for L, xy in out for p, q in zip(xy, xy[1:])] +
                   [("all" if a[0] == "all" else a[0], "circle", (a[1], a[2], 0.1)),
                    ("all" if b[0] == "all" else b[0], "circle", (b[1], b[2], 0.1))])
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
import time
print("t card", round(time.time() - T0))
for j, d in enumerate("AB" if os.environ.get("STAGE") != "card" else ""):
    SB[d]["taps"] = {net: tv[j] for net, tv in card.taps.items()}
    sideband.route_block(k, R, d, SB[d], JP[d], YVM, YVT)
    card.after_block(j)
    print("t block", d, round(time.time() - T0))

# ------------------------------------------------------------------ aux 12 V: PCIe 6-pin at the card end (opt-in per drive)
# Molex 45558 / Mini-Fit Jr 2x3 R/A, 1-3 +12V, 4-6 GND.  Feeds only the L4 12V_AUX plane, which reaches each
# drive's jumper; never connected to slot 12 V.  Fit it only when a drive's jumper is set to aux.
k.fp("Connector_Molex", "Molex_Mini-Fit_Jr_5569-06A2_2x03_P4.20mm_Horizontal", "J5", "PCIe 6-pin 45558-0003",
     XR - 14.4, -24.6, 270, pads={"1": "12V_AUX", "2": "12V_AUX", "3": "12V_AUX", "4": "GND", "5": "GND", "6": "GND"},
     lcsc="C7545781")
cva, cga = two("C19", *C1206, "22uF 25V X5R", XR - 24.0, -20.0, 90, False, (XR - 24.0, -18.0), "12V_AUX", "GND", "C12891")
k.track("12V_AUX", "L1", [cva, (cva[0], cva[1] + 1.3)], 0.6); k.via("12V_AUX", cva[0], cva[1] + 1.3, 0.6, 0.3)
k.track("GND", "L1", [cga, (cga[0], cga[1] - 1.3)], 0.6); k.via("GND", cga[0], cga[1] - 1.3, 0.6, 0.3)
k.text("AUX 12V", XR - 10.0, -30.0, P.F_SilkS, 1.0)

# ------------------------------------------------------------------ planes
# L4: slot 12 V toward the fingers (to each jumper's SLOT via), 12V_AUX toward the window and at the card end (J5)
YSPL = YP + sideband.YSPLIT
XAUX = XB + 30.5
k.zone("GND", "L2", BOARD, clearance=0.2)
k.zone("GND", "L5", BOARD, clearance=0.2)
k.zone("12V", "L4", [(0, 1), (XAUX - 0.3, 1), (XAUX - 0.3, YSPL + 0.3), (0, YSPL + 0.3)], clearance=0.2)
k.zone("12V_AUX", "L4", [(0, YSPL - 0.3), (XAUX + 0.3, YSPL - 0.3), (XAUX + 0.3, 1), (XR + 1, 1), (XR + 1, YTOP - 1),
                         (0, YTOP - 1)], clearance=0.2, thermal=False)
k.zone("GND", "L3", BOARD, clearance=0.25)
# ------------------------------------------------------------------ holes: bracket screws + holder slots
# bracket screw holes: keep the L4 12 V planes 1.1 mm off the hole wall (a screw must never reach 12 V)
for hn, (hx, hy) in (("H1", (7.5, -94.75)), ("H2", (7.5, -9.35))):
    k.keepout(f"{hn}_L4_VOID", [(hx + 2.7 * math.cos(math.radians(a)), hy + 2.7 * math.sin(math.radians(a)))
                                for a in range(0, 360, 30)], ["L4"])
k.fp("MountingHole", "MountingHole_3.2mm_M3", "H1", "bracket", 7.5, -94.75, bom=False)
k.fp("MountingHole", "MountingHole_3.2mm_M3", "H2", "bracket", 7.5, -9.35, bom=False)
for i, (x, y) in enumerate(((6.0, -30.0), (6.0, -60.0), (XR - 4.0, -38.0), (XR - 4.0, -68.0))):
    k.fp("u3adapter", "MountingSlot_M3_3.2x6.2", f"H{3 + i}", "M3 slot", x, y, bom=False)

# ------------------------------------------------------------------ silkscreen
k.text("U.3 x8  rev D", 146.0, -14.0, P.F_SilkS, 1.0)
k.text("x4x4 bifurcation", 146.0, -15.6, P.F_SilkS, 1.0)
k.text("DRIVE A", XA, -32.2, P.B_SilkS, 1.0, mirror=True)
k.text("DRIVE B", XB, -32.2, P.B_SilkS, 1.0, mirror=True)
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
    extra += "\n" + cardkit.DRU
    bb, rpt = k.fill_and_check(skew + "\n" + extra)
    c, items = drc_summary(rpt)
    print("DRC:", dict(c))
