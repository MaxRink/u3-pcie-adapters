"""Design 1: PCIe x16 card (x4x4x4x4 bifurcation) with four U.3 drives standing upright on their connectors.

Same construction as the x8 card (gen/x8.py): CEM full-height outline, Amphenol SFF-8639 receptacles on the
BOTTOM side (mirrored) so U.3 lane order matches the finger order with no crossings, drives on the card's back
side with their connectors facing the motherboard, the board cut away behind each drive.

Four drives in a row: lanes 0-3 -> A (left of the fingers), 4-7 -> B, 8-11 -> C, 12-15 -> D (all right).
Drive B's own lane pads sit straight above fingers 8-15, and right of the finger span the card edge rises to
12.75 mm, so lanes 8-15 can only pass under B if B (and C, D) sit DZ higher than A: lanes 8-15 stack on a
0.9 mm pitch from 1 mm above the raised edge, band B (lanes 4-7) stacks above them.

Passive variant: drive A is inside the 50 mm direct-attach budget; B is a few mm over, C/D far over
(populate as needed, or use the retimer variant).  Drives C/D run from an optional aux 12 V input (never tied
to slot 12 V): four 25 W drives exceed the 66 W slot budget.

Stackup JLC06161H-3313: L1 HS | L2 GND | L3 LS+GND | L4 12V | L5 GND | L6 HS.
PET (finger side B, F.Cu) run on L1 and drop to L6 next to the receptacle; PER (side A, B.Cu) stay on L6.
Drive lanes 0/1 RX (PER) get 220 nF AC caps (SFF-TA-1001 Rev 1.1 sec. 4.5, Table 4-11).
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbkit import *
from symlib import U3_PINS

OUT = os.path.join(ROOT, "boards", "x16p")
k = Kit(OUT, "u3_x16p")
U3FP = "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD"
DRV = "ABCD"

# ------------------------------------------------------------------ geometry
FX = 45.65                 # finger footprint origin = pin 1 (CEM: 45.65 mm from the bracket-side edge)
XS = {"A": 48.0, "B": 121.0, "C": 194.0, "D": 267.0}     # receptacle centres (73 mm pitch, ~3 mm between drives)
DZ = 5.7                   # drives B-D sit this much higher than A (room for lanes 8-15 under B)
YPD = {d: -24.0 - (0 if d == "A" else DZ) for d in DRV}  # receptacle peg lines
YVTD = {d: YPD[d] + 3.6 for d in DRV}                   # via row between the top pad row and the fingers
YVMD = {d: YPD[d] - 2.5 for d in DRV}                   # via row on the mating side of the bottom pad row
YMD = {d: YPD[d] - 11.75 for d in DRV}                  # mating faces
YE_A, YE_B = YMD["A"] + 1.0, YMD["B"] + 1.0             # window edges (pulled back 1 mm under the housing front)
XSTEP = 84.5               # window step between drive A and drive B
XF = 129.3                 # end of the finger span; the edge rises to -12.75 right of it
XR = 310.0                 # card length (CEM full length is 312)
YTOP = -111.15             # CEM full height
Y0 = -6.0                  # where pairs leave the finger field
Y_REFIN = -14.2            # REFCLK input horizontal (L6), below band A
Y_REFB = -28.8             # REFCLK_B run under receptacle A (L1)
COLW = 12.0                # bracket-side column width
P8 = 0.9                   # pitch of the lane 4-15 stacks


def drv(ln):
    return DRV[ln // 4]


def lvl(ln):
    if ln < 4:
        return {0: -15.2, 1: -16.2, 2: -17.2, 3: -18.2}[ln]
    if ln < 8:
        return -14.0 - P8 * 8 - P8 * (7 - ln)          # band B: lane 7 lowest, right above lane 8
    return -14.0 - P8 * (15 - ln)                       # lanes 8-15: lane 15 lowest, 1 mm off the raised edge


# ------------------------------------------------------------------ CEM x16 edge pinout (side B = F.Cu, side A = B.Cu)
GND_B = [4, 7, 13, 16, 18, 21, 22, 25, 26, 29, 32, 35, 36, 39, 40, 43, 44, 47, 49] + \
        [n for i in range(8) for n in (52 + 4 * i, 53 + 4 * i)][:-1] + [80]
GND_A = [4, 12, 15, 18, 20, 23, 24, 27, 28, 31, 34, 37, 38, 41, 42, 45, 46, 49, 51] + \
        [n for i in range(7) for n in (54 + 4 * i, 55 + 4 * i)] + [82]
GND_B = sorted(set(GND_B) - {81})
fing = {f"B{n}": "GND" for n in GND_B}
fing.update({f"A{n}": "GND" for n in GND_A})
fing.update({"B1": "12V", "B2": "12V", "B3": "12V", "A2": "12V", "A3": "12V",
             "B8": "3V3", "A9": "3V3", "A10": "3V3", "B10": "3V3_AUX", "A11": "PCIE_RST_N",
             "A1": "PRSNT_N", "B81": "PRSNT_N", "A13": "REFCLK_IN_P", "A14": "REFCLK_IN_N"})
PET_PINS = {0: (14, 15), 1: (19, 20), 2: (23, 24), 3: (27, 28), 4: (33, 34), 5: (37, 38), 6: (41, 42), 7: (45, 46)}
PER_PINS = {0: (16, 17), 1: (21, 22), 2: (25, 26), 3: (29, 30), 4: (35, 36), 5: (39, 40), 6: (43, 44), 7: (47, 48)}
for ln in range(8, 16):
    PET_PINS[ln] = (50 + 4 * (ln - 8), 51 + 4 * (ln - 8))
    PER_PINS[ln] = (52 + 4 * (ln - 8), 53 + 4 * (ln - 8))
for ln, (p, n) in PET_PINS.items():
    fing[f"B{p}"], fing[f"B{n}"] = f"PET{ln}_P", f"PET{ln}_N"
for ln, (p, n) in PER_PINS.items():
    fing[f"A{p}"], fing[f"A{n}"] = f"PER{ln}_P", f"PER{ln}_N"
J1 = k.fp("Connector_PCBEdge", "BUS_PCIexpress_x16", "J1", "PCIe x16 edge", FX, -3.45, 0, pads=fing, bom=False)
fpad = lambda n: k.padxy("J1", n)
xpin = lambda n: fpad(f"B{n}")[0]           # A and B pads share x
V12 = {"A": "12V", "B": "12V", "C": "12V_AUX", "D": "12V_AUX"}


# ------------------------------------------------------------------ U.3 receptacles (bottom, mirrored)
def u3net(pin, d):
    n = U3_PINS[pin]
    # PWRDIS tied low (drive always on); DualPortEn# open (drive pull-up = single port); SMBus not wired
    # (all drives share one address, and the slot SMBus is optional per CEM).
    m = {"GND": "GND", "HPT0": "GND", "PWRDIS": "GND", "12V": V12[d], "12V_PRE": V12[d], "3V3_AUX": "3V3_AUX",
         "PERST0#": "PCIE_RST_N", "ACTIVITY#": f"{d}_ACT_N"}
    return m.get(n)


JP = {}
for d in DRV:
    pads = {p: u3net(p, d) for p in U3_PINS if u3net(p, d)}
    pads["MP"] = "GND"
    k.fp("u3adapter", U3FP, f"J{d}", "PSAS4F2130021TR", XS[d], YPD[d], 180, bottom=True, pads=pads, lcsc="C22454449")
    JP[d] = lambda n, d=d: k.padxy(f"J{d}", n)

# ------------------------------------------------------------------ outline
arc = k.arc_pts((43.175, -10.925), 1.825, 180, 360)            # CEM notch between foot and fingers
LEFT = [(0, -4.5), (15.0, -4.5), (15.0, -12.75), (33.35, -12.75), (33.35, -4.5), (41.35, -4.5)] + arc
TOP = [(XR, -12.75), (XR, YTOP), (XR - 8.0, YTOP), (XR - 8.0, YE_B), (XSTEP, YE_B), (XSTEP, YE_A),
       (COLW, YE_A), (COLW, YTOP), (0, YTOP)]
k.outline([(XF, -8.4), (XF, -12.75)] + TOP + LEFT + [(45.0, -8.4)], closed=False)
BOARD = LEFT + [(45.0, 0), (XF, 0), (XF, -12.75)] + TOP
FINGERS = [(44.9, 0.6), (XF + 0.1, 0.6), (XF + 0.1, -5.75), (44.9, -5.75)]
k.rule_area("FINGERS", FINGERS)
k.rule_area("NECKDOWN_FINGERS", [(44.9, 0.6), (XF + 0.1, 0.6), (XF + 0.1, -7.4), (44.9, -7.4)])
for d in DRV:
    xc = XS[d]
    k.rule_area(f"NECKDOWN_J{d}", [(xc - 20.5, YVTD[d] + 0.9), (xc + 20.5, YVTD[d] + 0.9), (xc + 20.5, YVMD[d] - 0.9),
                                   (xc - 20.5, YVMD[d] - 0.9)])
for L in ("L2", "L4", "L5"):
    k.keepout(f"FINGER_VOID_{L}", [(44.8, 0.6), (XF + 0.2, 0.6), (XF + 0.2, -5.9), (44.8, -5.9)], [L])

# ------------------------------------------------------------------ helpers
YKNEE_A = -7.7             # lanes heading left rise straight to here, leaving room for the finger GND vias


def knee(ln, xc, h, pet):
    if ln < 4:
        return YKNEE_A
    if ln < 8:                                          # band B: 45 deg runs end left of lane 8's risers
        xe = (96.2 if pet else 98.2) - (7 - ln) * 0.5
        return h + (xe - xc)
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


def lane_geo(ln, pins, side):
    d = drv(ln); dirn = -1 if d == "A" else 1; h = lvl(ln)
    xc = sum(fpad(f"{side}{p}")[0] for p in pins) / 2
    return d, f"J{d}", ln % 4, dirn, h, xc, knee(ln, xc, h, side == "B")


# ------------------------------------------------------------------ PET lanes (L1 -> via -> L6 into the receptacle)
def pet_lane(ln):
    pins = PET_PINS[ln]
    d, ref, dl, dirn, h, xc, yv = lane_geo(ln, pins, "B")
    YVT, YVM = YVTD[d], YVMD[d]
    if dl == 0:                      # S2/S3 on the bottom (mating-side) row: rise past the top row on L1
        sp = ("S2", "S3")
        xt = sum(JP[d](n)[0] for n in sp) / 2
        res = tpair("L1", band_center(xc, h, xt, YVM + 0.3, dirn, yv), fstarts(pins, "B"),
                    [(None, [(xt + s * 0.4, YVM)]) for s in (-1, 1)])
        v = vias_at(res)
        stub_to_pad(ref, sp, v, "L6", YVM + 0.8)
        k.via("GND", xt, YVM - 0.95)                    # return via for the pair
    else:
        sp = {1: ("S9", "S10"), 2: ("S17", "S18"), 3: ("S23", "S24")}[dl]
        xt = sum(JP[d](n)[0] for n in sp) / 2
        res = k.pair("L1", band_center(xc, h, xt, YVT + 0.32, dirn, yv), fstarts(pins, "B"),
                     [(None, [(JP[d](n)[0], YVT)]) for n in sp])
        v = vias_at(res)
        stub_to_pad(ref, sp, v, "L6", YVT - 1.0)
    return res


# ------------------------------------------------------------------ PER lanes (L6 into the receptacle)
def per_lane(ln):
    pins = PER_PINS[ln]
    d, ref, dl, dirn, h, xc, yv = lane_geo(ln, pins, "A")
    YVT, YVM = YVTD[d], YVMD[d]
    st = fstarts(pins, "A")
    if dl in (2, 3):
        sp = {2: ("S20", "S21"), 3: ("S26", "S27")}[dl]
        xt = sum(JP[d](n)[0] for n in sp) / 2
        res = k.pair("L6", band_center(xc, h, xt, YVT - 0.2, dirn, yv), st,
                     [(None, [(JP[d](n)[0], YVT - 0.75)]) for n in sp])
        name_pads(ref, res, sp)
        return res
    if dl == 1:                      # caps on the bottom side, inline on L6
        sp = ("S12", "S13")
        xt = sum(JP[d](n)[0] for n in sp) / 2
        yc = h - 1.4
        res = k.pair("L6", band_center(xc, h, xt, h - 0.6, dirn, yv, c=0.4), st,
                     [(None, [(xt - 0.5, yc + 0.48)]), (None, [(xt + 0.5, yc + 0.48)])])
        caps = ac_caps(xt, yc, res, True, "L5")
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
    res = k.pair("L6", band_center(xc, h, xt, h - 0.75, dirn, yv, c=0.4), st,
                 [(None, [(JP[d](n)[0], ytr)]) for n in sp])
    v1 = vias_at(res)
    for gx in (xt - 1.59, xt + 1.59):
        k.via("GND", gx, ytr)
    yc = YPD[d] + 1.4
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
for ln in range(16):
    lanes[f"PET{ln}"] = pet_lane(ln)
    lanes[f"PER{ln}"] = per_lane(ln)

# ------------------------------------------------------------------ top-row / bottom-row GND and misc escapes
TOP_ROW = [f"E{i}" for i in range(7, 17)] + [f"S{i}" for i in range(8, 29)] + [f"E{i}" for i in range(17, 26)]
BOT_ROW = [f"S{i}" for i in range(1, 8)] + [f"E{i}" for i in range(1, 7)] + [f"P{i}" for i in range(1, 16)]
for d in DRV:
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
        if not net or net.startswith(("PET", "PER", "C_PER")):
            continue
        w = 0.5 if "12V" in net else (0.3 if net in ("GND", "3V3_AUX") else 0.2)
        dv = (0.6, 0.3) if "12V" in net else (None, None)
        k.track(net, "L6", [(x, y), (x, YVM)], w); k.via(net, x, YVM, *dv)

# ------------------------------------------------------------------ finger GND / power / sideband escapes
YG = -6.75                                   # finger GND via row (between the lane pairs)
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
for m in range(51, 80, 2):                   # lanes 8-15: one via between every two pairs
    finger_gnd(m + 0.5)
finger_gnd(81.5, x=xpin(82), y=-7.6)         # A82, clear of PRSNT2# (B81)
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
# PRSNT1# (A1) -> PRSNT2# x16 (B81) on L3
VPA = (xpin(1), -9.0); VPB = (xpin(81) + 0.75, -9.0)              # via right of PER15 (L6)
k.track("PRSNT_N", "L6", [(xpin(1), -4.6), VPA], 0.2); k.via("PRSNT_N", *VPA)
k.track("PRSNT_N", "L1", [(xpin(81), -5.4), (xpin(81), -8.4), VPB], 0.2); k.via("PRSNT_N", *VPB)
k.track("PRSNT_N", "L3", [VPA, VPB], 0.2)        # crosses the key slot above its 8.4 mm top

# ------------------------------------------------------------------ drive-side low speed: PERST#, 3V3_AUX (L3)
# A: west branches under receptacle A (as on the x8).  B-D: trunks on L3 under the raised housings; PERST# drops
# straight to E5 on L3, 3V3_AUX (outer trunk) drops to E3 on L6.
YB1, YB2 = -28.5, -29.5
XP, X3 = 75.5, 76.5
XT3, XTP = 88.0, 89.0                        # trunk verticals right of the window step
YT3, YTP = -38.0, -37.0                      # trunks under the B-D housings
EP = {d: JP[d]("E5") for d in DRV}; E3 = {d: JP[d]("E3") for d in DRV}
k.track("3V3_AUX", "L3", [VAUX, (X3, VAUX[1]), (X3, YB2), (E3["A"][0], YB2), (E3["A"][0], YVMD["A"])], 0.3)
k.track("3V3_AUX", "L3", [(X3, YB1), (XT3, YB1), (XT3, YT3), (E3["D"][0], YT3)], 0.3)
k.track("PCIE_RST_N", "L3", [VRST, (XP, VRST[1]), (XP, YB1), (EP["A"][0], YB1), (EP["A"][0], YVMD["A"])], 0.2)
k.via("PCIE_RST_N", XP, -13.6); k.via("PCIE_RST_N", 77.5, -13.6)
k.track("PCIE_RST_N", "L6", [(XP, -13.6), (77.5, -13.6)], 0.2)
k.track("PCIE_RST_N", "L3", [(77.5, -13.6), (XTP, -13.6), (XTP, YTP), (EP["D"][0], YTP)], 0.2)
for d in "BCD":
    k.track("PCIE_RST_N", "L3", [(EP[d][0], YTP), (EP[d][0], YVMD[d])], 0.2)
    k.via("3V3_AUX", E3[d][0], YT3)
    k.track("3V3_AUX", "L6", [(E3[d][0], YT3), (E3[d][0], YVMD[d])], 0.3)

# activity LEDs (top side, over the receptacle): 3V3_AUX -> 1k -> LED -> ACT#
for i, d in enumerate(DRV):
    xa = E3[d][0]; xact = JP[d]("P11")[0]; dx = XS[d] - XS["A"]; dz = YPD[d] - YPD["A"]
    xr, xl = 55.1 + dx, 57.7 + dx
    rn = f"R{11 + i}"; ln_ = f"D{1 + i}"
    nr, fr = two(rn, *R0402, "1k", xr, -24.2 + dz, 0, False, (xr - 1, -24.2 + dz), "3V3_AUX", f"{d}_LEDA", "C11702")
    k.fp("LED_SMD", "LED_0603_1608Metric", ln_, "KT-0603YG", xl, -24.2 + dz, 180,
         pads={"1": f"{d}_ACT_N", "2": f"{d}_LEDA"}, lcsc="C2289")
    k.track(f"{d}_LEDA", "L1", [fr, k.padxy(ln_, "2")], 0.2)
    k.track("3V3_AUX", "L1", [(xa, YVMD[d]), (xa, -25.5 + dz), (nr[0] - 0.5, -25.5 + dz), (nr[0] - 0.5, nr[1]), nr], 0.25)
    kp = k.padxy(ln_, "1")
    k.track(f"{d}_ACT_N", "L1", [kp, (xact, kp[1] - 0.4), (xact, YVMD[d])], 0.2)

# 12V bulk at each drive (top side, over the receptacle, next to P13-P15)
for j, d in enumerate(DRV):
    dx = XS[d] - XS["A"]; dz = YPD[d] - YPD["A"]
    for i, x in enumerate((61.6 + dx, 64.6 + dx)):
        ref = f"C{11 + 2 * j + i}"
        n12, ng = two(ref, *C1206, "10uF 25V X5R", x, -23.2 + dz, 90, False, (x, -20.0 + dz), "GND", V12[d], "C13585")
        if i == 0:
            gv = JP[d]("E22")[0], YVTD[d]
        else:
            gv = (x, -20.6 + dz); k.via("GND", *gv)
        k.track("GND", "L1", [n12, gv], 0.5)
        k.track(V12[d], "L1", [ng, (x, -25.6 + dz)], 0.6); k.via(V12[d], x, -25.6 + dz - 0.05, 0.6, 0.3)

# ------------------------------------------------------------------ REFCLK: slot -> 9DBL411B buffer (top) -> drives
# 9DBL411B LP-HCSL outputs need series Rs = Zo - 17 = 33 R for a 100 ohm (50 ohm SE) line (datasheet, Terminations).
UX, UY = 17.9, -20.55
k.fp("Package_SO", "TSSOP-20_4.4x6.5mm_P0.65mm", "U1", "9DBL411BGLF", UX, UY, 0, pads={
    "1": "GND", "2": "REFCLK_IN_N", "3": "REFCLK_IN_P", "4": "3V3", "5": "GND", "6": "GND", "9": "3V3", "10": "GND",
    "7": "U1_REFCLK3_N", "8": "U1_REFCLK3_P", "11": "U1_REFCLK2_N", "12": "U1_REFCLK2_P",
    "13": "GND", "14": "U1_REFCLK1_N", "15": "U1_REFCLK1_P", "16": "GND", "17": "GND", "18": "3V3",
    "19": "U1_REFCLK0_N", "20": "U1_REFCLK0_P"}, lcsc="C1520299")
U = lambda n: k.padxy("U1", str(n))
k.rule_area("NECKDOWN_U1", [(UX - 5.4, UY - 6.0), (UX + 6.0, UY - 6.0), (UX + 6.0, UY + 3.6), (UX - 5.4, UY + 3.6)])
# input: L6 from A13/A14, up, left along Y_REFIN, north on the west side, vias, short L1 into pins 3/2
xin = (xpin(13) + xpin(14)) / 2
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
assert math.dist(r6["REFCLK_IN_P"][0][-1], vP) < 1e-6, "REFCLK_IN polarity L6"
assert math.dist(r1["REFCLK_IN_P"][0][-1], U(3)) < 1e-6, "REFCLK_IN polarity L1"
k.via("REFCLK_IN_P", *vP); k.via("REFCLK_IN_N", *vN)


def series(ref, x, y, rot, n_in, n_out, near):
    return two(ref, *R0402, "33R", x, y, rot, False, near, n_in, n_out, "C25105")


xr = UX + 4.9


def rs(refp, refn, pp, pn, nin, nout, x=None, side=1):
    """Series pair beside pins pp/pn; side +1 = right-hand pin column (resistors east), -1 = left (west)."""
    x = xr if x is None else x
    yc = (U(pp)[1] + U(pn)[1]) / 2; sgn = 1 if U(pn)[1] > U(pp)[1] else -1
    r = {"P": series(refp, x, yc - sgn * 0.475, 0, nin + "_P", nout + "_P", (x - side, 0)),
         "N": series(refn, x, yc + sgn * 0.475, 0, nin + "_N", nout + "_N", (x - side, 0))}
    for pin, key in ((pp, "P"), (pn, "N")):
        k.track(f"{nin}_{key}", "L1", [U(pin), (U(pin)[0] + side * 0.85, U(pin)[1]), r[key][0]], RW)
    return r, yc


RA, yA = rs("R1", "R2", 12, 11, "U1_REFCLK2", "REFCLK_A")      # DIF2 (bottom right) -> A, east then up
RB, yB = rs("R3", "R4", 20, 19, "U1_REFCLK0", "REFCLK_B")      # DIF0 (top right) -> B, north column on L1
RC, yC = rs("R5", "R6", 8, 7, "U1_REFCLK3", "REFCLK_C", x=UX - 4.9, side=-1)   # DIF3 (left) -> C, west column
RD, yD = rs("R7", "R8", 15, 14, "U1_REFCLK1", "REFCLK_D")      # DIF1 (mid right) -> D, north column on L6


def segdist(pt, line):
    best = 1e9
    for p0, p1 in zip(line, line[1:]):
        vx, vy = p1[0] - p0[0], p1[1] - p0[1]; L2 = vx * vx + vy * vy
        t = 0 if L2 == 0 else max(0.0, min(1.0, ((pt[0] - p0[0]) * vx + (pt[1] - p0[1]) * vy) / L2))
        best = min(best, math.dist(pt, (p0[0] + t * vx, p0[1] + t * vy)))
    return best


def clk_pair(d, center, starts, vp, vn, extra=(0.0, 0.0), irange=range(-6, 3), jrange=range(-2, 5)):
    """Route an L1 REFCLK pair to two vias that feed E7/E8 on L6; slide the vias along x so P and N match.
    extra = (P, N) copper already laid for this net elsewhere, so the whole net is matched."""
    pads = (JP[d]("E7")[0], YVTD[d] - 0.8), (JP[d]("E8")[0], YVTD[d] - 0.8)
    best = None
    for i in irange:
        for j in jrange:
            a, b = (vp[0] + 0.05 * i, vp[1]), (vn[0] + 0.05 * j, vn[1])
            if b[0] - a[0] < 0.749:
                continue
            r = k.pair("L1", center, starts, [(None, [a]), (None, [b])], RW, RG, dry=True)
            if min(segdist(b, r[f"REFCLK_{d}_P"][0]), segdist(a, r[f"REFCLK_{d}_N"][0])) < 0.5:
                continue                                        # a line would pass too close to the other via
            lp = plen(r[f"REFCLK_{d}_P"][0]) + math.dist(a, pads[0]) + extra[0]
            ln_ = plen(r[f"REFCLK_{d}_N"][0]) + math.dist(b, pads[1]) + extra[1]
            sc = 10 * max(0.0, abs(lp - ln_) - 0.06) + 1.0 * abs(b[0] - a[0] - 0.75) + 0.05 * (abs(i) + abs(j))
            if best is None or sc < best[0]:
                best = (sc, a, b, lp - ln_)
    _, a, b, skr = best
    print(f"REFCLK_{d} residual skew", round(skr, 3))
    r = k.pair("L1", center, starts, [(None, [a]), (None, [b])], RW, RG)
    assert math.dist(r[f"REFCLK_{d}_P"][0][-1], a) < 1e-6, f"REFCLK_{d} polarity"
    for v, pad, net in ((a, pads[0], f"REFCLK_{d}_P"), (b, pads[1], f"REFCLK_{d}_N")):
        k.via(net, *v); k.track(net, "L6", [v, pad], RW)
    k.setpad(f"J{d}", "E7", f"REFCLK_{d}_P"); k.setpad(f"J{d}", "E8", f"REFCLK_{d}_N")
    k.via("GND", JP[d]("E7")[0] - 1.6, YVTD[d] - 0.9)            # return via beside the clock vias
    return r


def clk_vias(d):
    return (JP[d]("E7")[0], YVTD[d] - 0.25), (JP[d]("E8")[0], YVTD[d] - 0.25)


vAP, vAN = clk_vias("A")
xmA = (vAP[0] + vAN[0]) / 2
cxA = xmA + 0.05                             # arrive off-centre (under the N via): P jogs over, offsetting the left turn
ra = clk_pair("A", [(RA["P"][1][0] + 0.45, yA), (cxA - 0.4, yA), (cxA, yA - 0.4), (cxA, vAP[1] + 0.3)],
              [("REFCLK_A_P", [RA["P"][1]]), ("REFCLK_A_N", [RA["N"][1]])], vAP, vAN,
              irange=range(-10, 7), jrange=range(-6, 7))
# REFCLK_B: east, north past the IC, east under drive A at Y_REFB, then down-right to the raised drive B's E7/E8
XBV = xr + 1.6
vBP, vBN = clk_vias("B")
yBa = YVTD["B"] + 0.4                       # approach level, between band B and B's clock vias
rb = clk_pair("B", [(RB["P"][1][0] + 0.45, yB), (XBV - 0.6, yB), (XBV, yB - 0.6), (XBV, Y_REFB + 0.8), (XBV + 0.8, Y_REFB),
                   (94.5, Y_REFB), (94.5 + (Y_REFB - yBa) * -1, yBa), (vBP[0] - 0.05, yBa), (vBP[0] + 0.3, yBa - 0.35)],
              [("REFCLK_B_P", [RB["P"][1]]), ("REFCLK_B_N", [RB["N"][1]])], vBP, vBN)

# REFCLK_C: west round the buffer, north on the bracket-side column, east under drive A (above REFCLK_B), up under
# the raised B housing, down into drive C like REFCLK_B.  REFCLK_D: east, vias, north on L6 under REFCLK_B's column,
# east under drive A on L6, back to L1 past the window step, then like C (no net winding, so no built-in skew).
# ~190 / ~290 mm of LP-HCSL from the buffer (passive card only).
XC3, YC3, YCB = 10.5, -30.0, -34.5           # C: column, run under A, run under B
YD6, YDB = -31.6, -35.7                      # D: L6 run under A, L1 run under B
vCP, vCN = clk_vias("C"); vDP, vDN = clk_vias("D")
yCa, yDa = YVTD["C"] + 0.4, YVTD["D"] + 0.4
xCd, xDd = 150.0, 222.0                      # where C / D leave the run under the housings
rc = clk_pair("C", [(RC["P"][1][0] - 0.45, yC), (XC3 + 0.6, yC), (XC3, yC - 0.6), (XC3, YC3 + 0.6), (XC3 + 0.6, YC3),
                   (85.0, YC3), (85.0 + (YC3 - YCB), YCB), (xCd, YCB), (xCd + (yCa + 1.6 - YCB), yCa + 1.6),
                   ((vCP[0] + vCN[0]) / 2 - 1.0, yCa + 1.6), ((vCP[0] + vCN[0]) / 2 - 0.4, yCa + 1.0),
                   ((vCP[0] + vCN[0]) / 2 - 0.4, vCP[1] + 0.3)],
              [("REFCLK_C_P", [RC["P"][1]]), ("REFCLK_C_N", [RC["N"][1]])], vCP, vCN,
              irange=range(-14, 5), jrange=range(-4, 3))
yv1 = -21.9
d1 = k.pair("L1", [(RD["P"][1][0] + 0.45, yD), (XBV - 0.4, yD), (XBV, yD - 0.4), (XBV, yv1 + 0.3)],
            [("REFCLK_D_P", [RD["P"][1]]), ("REFCLK_D_N", [RD["N"][1]])],
            [(None, [(XBV - 0.38, yv1)]), (None, [(XBV + 0.38, yv1)])], RW, RG)
assert d1["REFCLK_D_P"][0][-1][0] < XBV, "REFCLK_D polarity (L1 start)"
for n in d1:
    k.via(n, *d1[n][0][-1])
xv2 = 83.4
d6 = k.pair("L6", [(XBV, yv1 - 0.3), (XBV, YD6 + 0.6), (XBV + 0.6, YD6), (xv2 - 0.3, YD6)],
            [(n, [d1[n][0][-1]]) for n in d1],
            [(None, [(xv2, YD6 - 0.38)]), (None, [(xv2, YD6 + 0.38)])], RW, RG)
assert d6["REFCLK_D_P"][0][-1][1] < YD6, "REFCLK_D polarity (L6)"
for n in d6:
    k.via(n, *d6[n][0][-1])
ex = tuple(plen(d1[f"REFCLK_D_{q}"][0]) + plen(d6[f"REFCLK_D_{q}"][0]) for q in "PN")
rd = clk_pair("D", [(xv2 + 0.3, YD6), (xv2 + 1.0, YD6), (xv2 + 1.0 + (YD6 - YDB), YDB), (xDd, YDB),
                   (xDd + (yDa - YDB), yDa), (vDP[0] - 0.05, yDa), (vDP[0] + 0.3, yDa - 0.35)],
              [(n, [d6[n][0][-1]]) for n in d6], vDP, vDN, extra=ex, irange=range(-10, 3), jrange=range(-4, 7))

# buffer power: GND vias under the body (inner column), 3V3 vias in a second inner column; decoupling on the
# bottom over an L6 3V3 pour fed from the finger 3V3 via
for p in (1, 5, 10):
    k.track("GND", "L1", [U(p), (UX - 0.5, U(p)[1])], 0.2); k.via("GND", UX - 0.5, U(p)[1])
for p in (4, 9):
    k.track("3V3", "L1", [U(p), (UX - 1.55, U(p)[1])], 0.2); k.via("3V3", UX - 1.55, U(p)[1])
k.track("GND", "L1", [U(6), (UX - 1.55, U(6)[1])], 0.2); k.via("GND", UX - 1.55, U(6)[1])      # OE3# low = on
k.track("GND", "L1", [U(16), (UX + 1.1, U(16)[1]), (UX + 1.1, U(17)[1]), U(17)], 0.2)
k.via("GND", UX + 1.1, (U(16)[1] + U(17)[1]) / 2)
k.track("3V3", "L1", [U(18), (UX + 1.1, U(18)[1])], 0.2); k.via("3V3", UX + 1.1, U(18)[1])
k.track("GND", "L1", [U(13), (UX + 1.1, U(13)[1])], 0.2); k.via("GND", UX + 1.1, U(13)[1])     # OE2# low = on
k.zone("3V3", "L6", [(UX - 3.0, -15.1), (UX + 8.3, -15.1), (UX + 8.3, -24.6), (UX - 3.0, -24.6)], prio=2)
for i, (ref, val, fpn, lc) in enumerate((("C1", "100nF", C0402, "C1525"), ("C2", "100nF", C0402, "C1525"),
                                         ("C3", "100nF", C0402, "C1525"),
                                         ("C4", "10uF", ("Capacitor_SMD", "C_0603_1608Metric"), "C19702"))):
    x, y = UX - 2.0 + 2.6 * (i % 2), (-16.3 if i < 2 else -23.6)
    if i == 3:
        x = UX + 2.6
    g, v = two(ref, *fpn, val, x, y, 0, True, (x - 2, y), "GND", "3V3", lc)
    gv = (g[0] - 0.75, g[1]); k.via("GND", *gv); k.track("GND", "L6", [g, gv], 0.3)
k.track("3V3", "L1", [V33, (V33[0], -13.6), (UX + 7.7, -13.6), (UX + 7.7, -15.6)], 0.3); k.via("3V3", UX + 7.7, -15.6)

# ------------------------------------------------------------------ aux 12 V for drives C/D (PCIe 6-pin at the card end)
# Molex 45558-0003 / Mini-Fit Jr 2x3 R/A, mating face at the card end: 1-3 +12V, 4-6 GND (5 = sense, tied low).
# Feeds only the L4 12V_AUX plane under C/D; never connected to slot 12 V.  Leave it off when only A/B are fitted.
k.fp("Connector_Molex", "Molex_Mini-Fit_Jr_5569-06A2_2x03_P4.20mm_Horizontal", "J5", "PCIe 6-pin 45558-0003",
     XR - 14.4, -27.0, 270, pads={"1": "12V_AUX", "2": "12V_AUX", "3": "12V_AUX", "4": "GND", "5": "GND", "6": "GND"},
     lcsc="C7545781")
cva, cga = two("C19", *C1206, "22uF 25V X5R", XR - 24.0, -22.0, 90, False, (XR - 24.0, -20.0), "12V_AUX", "GND", "C12891")
k.track("12V_AUX", "L1", [cva, (cva[0], -18.9)], 0.6); k.via("12V_AUX", cva[0], -18.9, 0.6, 0.3)
k.track("GND", "L1", [cga, (cga[0], -25.1)], 0.6); k.via("GND", cga[0], -25.1, 0.6, 0.3)
k.text("AUX 12V", XR - 10.0, -32.6, P.F_SilkS, 1.0)

# ------------------------------------------------------------------ planes
XSPLIT = (XS["B"] + 22.0 + XS["C"] - 22.0) / 2              # L4: slot 12V for A/B, aux 12V for C/D
k.zone("GND", "L2", BOARD, clearance=0.2)
k.zone("GND", "L5", BOARD, clearance=0.2)
k.zone("12V", "L4", [(0, 1), (XSPLIT - 0.3, 1), (XSPLIT - 0.3, YTOP - 1), (0, YTOP - 1)], clearance=0.2)
k.zone("12V_AUX", "L4", [(XSPLIT + 0.3, 1), (XR + 1, 1), (XR + 1, YTOP - 1), (XSPLIT + 0.3, YTOP - 1)], clearance=0.2,
       thermal=False)
k.zone("GND", "L3", BOARD, clearance=0.25)

# ------------------------------------------------------------------ holes: bracket screws + holder slots
k.fp("MountingHole", "MountingHole_3.2mm_M3", "H1", "bracket", 7.5, -94.75, bom=False)
k.fp("MountingHole", "MountingHole_3.2mm_M3", "H2", "bracket", 7.5, -9.35, bom=False)
for i, (x, y) in enumerate(((6.0, -30.0), (6.0, -60.0), (XR - 4.0, -50.0), (XR - 4.0, -80.0))):
    k.fp("u3adapter", "MountingSlot_M3_3.2x6.2", f"H{3 + i}", "M3 slot", x, y, bom=False)

# ------------------------------------------------------------------ silkscreen
k.text("U.3 x16 passive  rev A", 112.0, -37.4, P.F_SilkS, 1.0)
k.text("x4x4x4x4 bifurcation", 112.0, -39.1, P.F_SilkS, 1.0)
for d in DRV:
    k.text(f"DRIVE {d}", XS[d], YPD[d] - 9.0, P.B_SilkS, 1.0, mirror=True)
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
for ln in range(16):
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
(rule "x16 passive: REFCLK_C/D run 190-290 mm with three layer changes; uncoupled <= 5 mm (all at vias/pads)"
    (condition "A.NetClass == 'REFCLK_100' && (A.NetName == 'REFCLK_C_*' || A.NetName == 'REFCLK_D_*')")
    (constraint diff_pair_uncoupled (max 5.0mm)))"""
    bb, rpt = k.fill_and_check(skew + "\n" + extra)
    c, items = drc_summary(rpt)
    print("DRC:", dict(c))
