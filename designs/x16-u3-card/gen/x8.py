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
from router import Router

OUT = os.path.join(ROOT, "boards", "x8")
k = Kit(OUT, "u3_x8")
U3FP = "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD"

# ------------------------------------------------------------------ geometry
FX = 45.65                 # finger footprint origin = pin 1 (CEM: 45.65 mm from the bracket-side edge)
XA, XB = 48.0, 121.0       # receptacle centres (drive A / drive B)
YP = -24.0                 # receptacle peg line
YM = YP - 11.75            # mating face
YE = YM + 1.0              # board edge in the drive windows (pulled back 1 mm under the housing front)
XR = 190.0                 # card length (room for drive B's sideband block and the aux 12 V plug)
YTOP = -111.15             # CEM full height
YVT = -20.4                # via row between the top pad row and the fingers
YVM = -26.5                # via row on the mating side of the bottom pad row
Y0 = -6.0                 # where pairs leave the finger field
LVL_A = {0: -15.2, 1: -16.2, 2: -17.2, 3: -18.2}      # band A horizontals (lane 0 lowest)
LVL_B = {7: -15.2, 6: -16.2, 5: -17.2, 4: -18.2}      # band B horizontals (lane 7 lowest)
Y_REFIN = -14.2            # REFCLK input horizontal (L6), below band A
Y_REFB = -34.0             # REFCLK_B run over drive A's mating end (L1), above the sideband blocks
COLW = 12.0                # bracket-side column width

# ------------------------------------------------------------------ CEM x8 edge pinout (side B = F.Cu, side A = B.Cu)
GND_B = [4, 7, 13, 16, 18, 21, 22, 25, 26, 29, 32, 35, 36, 39, 40, 43, 44, 47, 49]
GND_A = [4, 12, 15, 18, 20, 23, 24, 27, 28, 31, 34, 37, 38, 41, 42, 45, 46, 49]
fing = {f"B{n}": "GND" for n in GND_B}
fing.update({f"A{n}": "GND" for n in GND_A})
fing.update({"B1": "12V", "B2": "12V", "B3": "12V", "A2": "12V", "A3": "12V",
             "B8": "3V3", "A9": "3V3", "A10": "3V3", "B10": "3V3_AUX", "A11": "PCIE_RST_N",
             "A1": "PRSNT_N", "B48": "PRSNT_N", "A13": "REFCLK_IN_P", "A14": "REFCLK_IN_N",
             "B5": "SMCLK", "B6": "SMDAT"})
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
SB = {d: sideband.block(k, R, d, i, xc, YP, JP[d], 10 + 3 * i, 20 + 20 * i, 20 + 10 * i)
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
        if not net or net.startswith(("PET", "PER", "C_PER")):
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
k.track("3V3_AUX", "L1", [(xpin(10), -5.4), VAUX], 0.3); k.via("3V3_AUX", *VAUX)
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

# ------------------------------------------------------------------ REFCLK: slot -> 9DBL411B buffer (top) -> drives
# 9DBL411B LP-HCSL outputs need series Rs = Zo - 17 = 33 R for a 100 ohm (50 ohm SE) line (datasheet, Terminations).
UX, UY = 17.9, -20.55
k.fp("Package_SO", "TSSOP-20_4.4x6.5mm_P0.65mm", "U1", "9DBL411BGLF", UX, UY, 0, pads={
    "1": "GND", "2": "REFCLK_IN_N", "3": "REFCLK_IN_P", "4": "3V3", "5": "GND", "6": "3V3", "9": "3V3", "10": "GND",
    "13": "3V3", "14": "U1_REFCLK1_N", "15": "U1_REFCLK1_P", "16": "GND", "17": "GND", "18": "3V3",
    "19": "U1_REFCLK0_N", "20": "U1_REFCLK0_P"}, lcsc="C1520299")
U = lambda n: k.padxy("U1", str(n))
k.rule_area("NECKDOWN_U1", [(UX - 5.4, UY - 6.0), (UX + 6.0, UY - 6.0), (UX + 6.0, UY + 3.6), (UX - 5.4, UY + 3.6)])
# input: L6 from A13/A14, up, left along Y_REFIN, north on the west side, vias, short L1 into pins 3/2
xin = (xpin(13) + xpin(14)) / 2
XW = UX - 4.3
ym = (U(2)[1] + U(3)[1]) / 2
XW = UX - 4.4
yv = U(1)[1] - 0.9                     # via pair north of the pin row: L6 runs north, L1 comes back south (U-turn)
cen6 = [(xin, -5.76), (xin, YKNEE_A), (xin - (YKNEE_A - Y_REFIN), Y_REFIN), (XW + 1.0, Y_REFIN),
        (XW, Y_REFIN - 1.0), (XW, yv + 0.22)]
cen1 = [(XW, yv + 0.22), (XW, ym - 0.4), (XW + 0.4, ym), (UX - 3.75, ym)]
st = [("REFCLK_IN_P", [(xpin(13), -5.62)]), ("REFCLK_IN_N", [(xpin(14), -5.62)])]
best = None
for i in range(-6, 7):
    for j in range(-6, 7):
        vP, vN = (XW - 0.355, yv + 0.05 * i), (XW + 0.355, yv + 0.05 * j)
        r6 = k.pair("L6", cen6, st, [(None, [vP]), (None, [vN])], RW, RG, dry=True)
        r1 = k.pair("L1", cen1, [("REFCLK_IN_P", [vP]), ("REFCLK_IN_N", [vN])], [(None, [U(3)]), (None, [U(2)])], RW, RG, dry=True)
        sk = sum(plen(r[n][0]) * (1 if n.endswith("P") else -1) for r in (r6, r1) for n in r)
        sc = 10 * max(0.0, abs(sk) - 0.06) + 0.05 * (abs(i) + abs(j))
        if best is None or sc < best[0]:
            best = (sc, vP, vN, sk)
_, vP, vN, sk = best
print("REFCLK_IN residual skew", round(sk, 3))
r6 = k.pair("L6", cen6, st, [(None, [vP]), (None, [vN])], w=RW, g=RG)
r1 = k.pair("L1", cen1, [("REFCLK_IN_P", [vP]), ("REFCLK_IN_N", [vN])], [(None, [U(3)]), (None, [U(2)])], w=RW, g=RG)
assert math.dist(r6["REFCLK_IN_P"][0][-1], vP) < 1e-6, ("REFCLK_IN polarity L6", r6["REFCLK_IN_P"][0][-2:], vP, vN)
assert math.dist(r1["REFCLK_IN_P"][0][-1], U(3)) < 1e-6, ("REFCLK_IN polarity L1", r1["REFCLK_IN_P"][0][:2], r1["REFCLK_IN_P"][0][-2:], U(3), U(2))
k.via("REFCLK_IN_P", *vP); k.via("REFCLK_IN_N", *vN)


def series(ref, x, y, rot, n_in, n_out, near):
    return two(ref, *R0402, "33R", x, y, rot, False, near, n_in, n_out, "C25105")


# outputs: 33R series resistors stacked 1.0 mm apart right at the pins (DIF1 15/14 -> A, DIF0 20/19 -> B)
xr = UX + 4.9


def rs(refp, refn, pp, pn, nin, nout):
    yc = (U(pp)[1] + U(pn)[1]) / 2; sgn = 1 if U(pn)[1] > U(pp)[1] else -1
    r = {"P": series(refp, xr, yc - sgn * 0.475, 0, nin + "_P", nout + "_P", (xr - 1, 0)),
         "N": series(refn, xr, yc + sgn * 0.475, 0, nin + "_N", nout + "_N", (xr - 1, 0))}
    for pin, key in ((pp, "P"), (pn, "N")):
        k.track(f"{nin}_{key}", "L1", [U(pin), (U(pin)[0] + 0.85, U(pin)[1]), r[key][0]], RW)
    return r, yc


RA, yA = rs("R1", "R2", 15, 14, "U1_REFCLK1", "REFCLK_A")
RB, yB = rs("R3", "R4", 20, 19, "U1_REFCLK0", "REFCLK_B")
E7A, E8A = JP["A"]("E7"), JP["A"]("E8")
vAP, vAN = (E7A[0], -20.65), (E8A[0], -20.65)
xmA = (vAP[0] + vAN[0]) / 2


def clk_pair(d, center, starts, vp, vn):
    """Route an L1 REFCLK pair to two vias that feed E7/E8 on L6; slide the vias along x so P and N match."""
    pads = (JP[d]("E7")[0], -21.2), (JP[d]("E8")[0], -21.2)
    best = None
    for i in range(-6, 3):
        for j in range(-2, 5):
            a, b = (vp[0] + 0.05 * i, vp[1]), (vn[0] + 0.05 * j, vn[1])
            if b[0] - a[0] < 0.749:
                continue
            r = k.pair("L1", center, starts, [(None, [a]), (None, [b])], RW, RG, dry=True)
            lp = plen(r[f"REFCLK_{d}_P"][0]) + math.dist(a, pads[0])
            ln_ = plen(r[f"REFCLK_{d}_N"][0]) + math.dist(b, pads[1])
            sc = 10 * max(0.0, abs(lp - ln_) - 0.06) + 1.0 * abs(b[0] - a[0] - 0.75) + 0.05 * (abs(i) + abs(j))
            if best is None or sc < best[0]:
                best = (sc, a, b)
    _, a, b = best
    r = k.pair("L1", center, starts, [(None, [a]), (None, [b])], RW, RG)
    assert math.dist(r[f"REFCLK_{d}_P"][0][-1], a) < 1e-6, f"REFCLK_{d} polarity"
    for v, pad, net in ((a, pads[0], f"REFCLK_{d}_P"), (b, pads[1], f"REFCLK_{d}_N")):
        k.via(net, *v); k.track(net, "L6", [v, pad], RW)
    k.setpad(f"J{d}", "E7", f"REFCLK_{d}_P"); k.setpad(f"J{d}", "E8", f"REFCLK_{d}_N")
    k.via("GND", JP[d]("E7")[0] - 1.6, -21.3)                    # return via beside the clock vias
    return r


ra = clk_pair("A", [(RA["P"][1][0] + 0.45, yA), (xmA - 0.4, yA), (xmA, yA - 0.4)],
              [("REFCLK_A_P", [RA["P"][1]]), ("REFCLK_A_N", [RA["N"][1]])], vAP, vAN)
# REFCLK_B: east, north past the IC, east under drive A at Y_REFB, south at x 97, east to drive B's E7/E8
XBV = xr + 1.6
E7B, E8B = JP["B"]("E7"), JP["B"]("E8")
vBP, vBN = (E7B[0], -20.65), (E8B[0], -20.65)
rb = clk_pair("B", [(RB["P"][1][0] + 0.45, yB), (XBV - 0.6, yB), (XBV, yB - 0.6), (XBV, Y_REFB + 0.8), (XBV + 0.8, Y_REFB),
                   (96.0, Y_REFB), (96.8, Y_REFB + 0.8), (96.8, -21.0), (97.8, -20.0), (vBP[0] - 0.05, -20.0),
                   (vBP[0] + 0.3, -20.35)],
              [("REFCLK_B_P", [RB["P"][1]]), ("REFCLK_B_N", [RB["N"][1]])], vBP, vBN)

# buffer power: GND vias under the body (inner column), 3V3 vias in a second inner column; decoupling on the
# bottom over an L6 3V3 pour fed from the finger 3V3 via
for p in (1, 5, 10):
    k.track("GND", "L1", [U(p), (UX - 0.5, U(p)[1])], 0.2); k.via("GND", UX - 0.5, U(p)[1])
for p in (4, 6, 9):
    k.track("3V3", "L1", [U(p), (UX - 1.55, U(p)[1])], 0.2); k.via("3V3", UX - 1.55, U(p)[1])
k.track("GND", "L1", [U(16), (UX + 1.1, U(16)[1]), (UX + 1.1, U(17)[1]), U(17)], 0.2)
k.via("GND", UX + 1.1, (U(16)[1] + U(17)[1]) / 2)
for p in (13, 18):
    k.track("3V3", "L1", [U(p), (UX + 1.1, U(p)[1])], 0.2); k.via("3V3", UX + 1.1, U(p)[1])
k.zone("3V3", "L6", [(UX - 3.0, -15.1), (UX + 4.4, -15.1), (UX + 4.4, -24.6), (UX - 3.0, -24.6)], prio=2)
for i, (ref, val, fpn, lc) in enumerate((("C1", "100nF", C0402, "C1525"), ("C2", "100nF", C0402, "C1525"),
                                         ("C3", "100nF", C0402, "C1525"),
                                         ("C4", "10uF", ("Capacitor_SMD", "C_0603_1608Metric"), "C19702"))):
    x, y = UX - 2.0 + 2.6 * (i % 2), (-16.3 if i < 2 else -23.6)
    if i == 3:
        x = UX + 2.6
    g, v = two(ref, *fpn, val, x, y, 0, True, (x - 2, y), "GND", "3V3", lc)
    gv = (g[0] - 0.75, g[1]); k.via("GND", *gv); k.track("GND", "L6", [g, gv], 0.3)
# 3V3 feed: L1 north from the finger via, west at -13.6, via into the pour
k.track("3V3", "L1", [V33, (V33[0], -13.6), (UX + 4.0, -13.6), (UX + 4.0, -15.6)], 0.3); k.via("3V3", UX + 4.0, -15.6)

# ------------------------------------------------------------------ slot SMBus + management trunks (L3)
# B5/B6 -> vias north of the PRSNT# run; east on L3 above the lane fan-out, north at x ~94 (between the drive A
# block and REFCLK_B's descent), then east in the channel over the drive B mating end.  3V3_AUX and PERST# join.
VSC, VSD = (xpin(5), -10.0), (xpin(6), -10.6)
k.track("SMCLK", "L1", [(xpin(5), -5.4), VSC], 0.2); k.via("SMCLK", *VSC)
k.track("SMDAT", "L1", [(xpin(6), -5.4), VSD], 0.2); k.via("SMDAT", *VSD)
TR = [("SMCLK", VSC, -12.6, 93.4, YE + 0.65, 0.2, 39.4), ("SMDAT", VSD, -12.15, 94.1, YE + 1.25, 0.2, 38.6),
      ("3V3_AUX", VAUX, -11.7, 94.8, YE + 1.85, 0.25, 37.8), ("PCIE_RST_N", VRST, -11.25, 95.5, YE + 2.45, 0.2, 37.0)]
TRUNK = {}
for i, (net, v0, ylow, xr_, ych, w, xtap) in enumerate(TR):
    tA = (xr_, -26.0 - 0.8 * i)                                              # drive A tap (trunk vertex)
    pts = [v0, (v0[0], ylow), (xr_, ylow), tA, (xr_, ych), (XB + xtap, ych)]  # channel ends at drive B's tap
    k.track(net, "L3", pts, w)
    TRUNK[net] = [("L3", "seg", (p[0], p[1], q[0], q[1], w / 2)) for p, q in zip(pts, pts[1:])]
    # tap points are trunk vertices (no vias: blocks end on the vertex on L3, or drop their own via onto it)
    R.seed(net, [("L3", "circle", (XB + xtap, ych, w / 2)), ("L3", "circle", (*tA, w / 2))])
# DNP option: bridge 3V3 -> 3V3_AUX for slots that do not supply 3.3 Vaux (fit only then)
k.fp(*R0402, "R9", "0R DNP (no 3.3Vaux)", 45.6, -12.0, 90, lcsc="C17168", dnp=True)
pa, pb = sorted(("1", "2"), key=lambda q: k.padxy("R9", q)[1])          # pa: toward the 3V3 feed at -13.6
k.setpad("R9", pa, "3V3"); k.setpad("R9", pb, "3V3_AUX")
k.track("3V3", "L1", [k.padxy("R9", pa), (45.6, -13.6)], 0.3)
R9AUX = ("L1", *k.padxy("R9", pb))

# ------------------------------------------------------------------ aux 12 V: PCIe 6-pin at the card end (opt-in per drive)
# Molex 45558 / Mini-Fit Jr 2x3 R/A, 1-3 +12V, 4-6 GND.  Feeds only the L4 12V_AUX plane, which reaches each
# drive's jumper; never connected to slot 12 V.  Fit it only when a drive's jumper is set to aux.
YJ5 = -21.0
k.fp("Connector_Molex", "Molex_Mini-Fit_Jr_5569-06A2_2x03_P4.20mm_Horizontal", "J5", "PCIe 6-pin 45558-0003",
     XR - 14.4, -24.6, 270, pads={"1": "12V_AUX", "2": "12V_AUX", "3": "12V_AUX", "4": "GND", "5": "GND", "6": "GND"},
     lcsc="C7545781")
cva, cga = two("C19", *C1206, "22uF 25V X5R", XR - 24.0, -20.0, 90, False, (XR - 24.0, -18.0), "12V_AUX", "GND", "C12891")
k.track("12V_AUX", "L1", [cva, (cva[0], cva[1] + 1.3)], 0.6); k.via("12V_AUX", cva[0], cva[1] + 1.3, 0.6, 0.3)
k.track("GND", "L1", [cga, (cga[0], cga[1] - 1.3)], 0.6); k.via("GND", cga[0], cga[1] - 1.3, 0.6, 0.3)
k.text("AUX 12V", XR - 10.0, -30.0, P.F_SilkS, 1.0)

# ------------------------------------------------------------------ sideband blocks: route
for d in "AB":
    sideband.route_block(k, R, d, SB[d], JP[d], YVM, YVT)
R.seed("3V3_AUX", TRUNK["3V3_AUX"])
R.to_net("3V3_AUX", R9AUX, maxpad=12.0, via_cost=1.0)

# ------------------------------------------------------------------ planes
# L4: slot 12 V in the lower band (fingers -> each drive's jumper pin 1), aux 12 V above it (6-pin -> pin 3)
YSPL = YP - 3.3
XAUX = XB + 30.5
k.zone("GND", "L2", BOARD, clearance=0.2)
k.zone("GND", "L5", BOARD, clearance=0.2)
k.zone("12V", "L4", [(0, 1), (XAUX - 0.3, 1), (XAUX - 0.3, YSPL + 0.3), (0, YSPL + 0.3)], clearance=0.2)
k.zone("12V_AUX", "L4", [(0, YSPL - 0.3), (XAUX + 0.3, YSPL - 0.3), (XAUX + 0.3, 1), (XR + 1, 1), (XR + 1, YTOP - 1),
                         (0, YTOP - 1)], clearance=0.2, thermal=False)
k.zone("GND", "L3", BOARD, clearance=0.25)

# ------------------------------------------------------------------ holes: bracket screws + holder slots
k.fp("MountingHole", "MountingHole_3.2mm_M3", "H1", "bracket", 7.5, -94.75, bom=False)
k.fp("MountingHole", "MountingHole_3.2mm_M3", "H2", "bracket", 7.5, -9.35, bom=False)
for i, (x, y) in enumerate(((6.0, -30.0), (6.0, -60.0), (XR - 4.0, -38.0), (XR - 4.0, -68.0))):
    k.fp("u3adapter", "MountingSlot_M3_3.2x6.2", f"H{3 + i}", "M3 slot", x, y, bom=False)

# ------------------------------------------------------------------ silkscreen
k.text("U.3 x8  rev B", 146.0, -14.0, P.F_SilkS, 1.0)
k.text("x4x4 bifurcation", 146.0, -15.6, P.F_SilkS, 1.0)
k.text("DRIVE A", XA, -33.0, P.B_SilkS, 1.0, mirror=True)
k.text("DRIVE B", XB, -33.0, P.B_SilkS, 1.0, mirror=True)
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
    if net.startswith(("PET", "PER", "C_PER", "REFCLK", "U1_REFCLK")):
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
    extra += """
(rule "x8: REFCLK_B 100 MHz HCSL, ~120 mm with 8 bends and via/pin fan-outs; uncoupled <= 4 mm (bends + ends)"
    (condition "A.NetClass == 'REFCLK_100' && A.NetName == 'REFCLK_B_*'")
    (constraint diff_pair_uncoupled (max 4.0mm)))"""
    bb, rpt = k.fill_and_check(skew + "\n" + extra)
    c, items = drc_summary(rpt)
    print("DRC:", dict(c))
