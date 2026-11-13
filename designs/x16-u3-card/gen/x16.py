"""Design 1: PCIe x16 card with four (x4x4x4x4) or three (x4x4x4 / x8x4x4 host bifurcation) U.3 drives standing
upright on their connectors.  U3_DRIVES=3 python3 gen/x16.py builds the 3-drive card (boards/x16p3).

Same construction as the x8 card (gen/x8.py): CEM full-height outline, Amphenol SFF-8639 receptacles on the
BOTTOM side (mirrored) so U.3 lane order matches the finger order with no crossings, drives on the card's back
side with their connectors facing the motherboard, the board cut away behind each drive.

Four drives in a row: lanes 0-3 -> A (left of the fingers), 4-7 -> B, 8-11 -> C, 12-15 -> D (all right).
Drive B's own lane pads sit straight above fingers 8-15, and right of the finger span the card edge rises to
12.75 mm, so lanes 8-15 can only pass under B if B (and C, D) sit DZ higher than A: lanes 8-15 stack on a
0.9 mm pitch from 1 mm above the raised edge, band B (lanes 4-7) stacks above them.

Passive variant: drive A is inside the 50 mm direct-attach budget; B is a few mm over, C/D far over
(populate as needed, or use the retimer variant).

Every drive has the sideband block of gen/sideband.py (SMBus switch, IO expander for PWRDIS / DualPortEn# /
PRSNT# / IfDet# / IfDet2# / WAKE# / locate LED / reset enable, PERST# AND gate) and a 3-pin 12 V source jumper:
slot 12 V by default, the optional PCIe 6-pin (J5, 12V_AUX) per drive.  The two 12 V nets never meet.
Low-speed trunks (SMCLK, SMDAT, 3V3_AUX, PERST#) run on L3; REFCLK B..D run in channels between the sideband
blocks and the window edges.

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

N = int(os.environ.get("U3_DRIVES", "4"))
assert N in (3, 4)
DRV = "ABCD"[:N]
VAR = "-cdcdb400" if os.environ.get("U3_CLK") == "cdcdb400" else ""     # alternate card versions get their own folder
OUT = os.path.join(ROOT, "boards", ("x16p" if N == 4 else "x16p3") + VAR)
k = Kit(OUT, ("u3_x16p" if N == 4 else "u3_x16p3") + VAR.replace("-", "_"))
U3FP = "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD"

# ------------------------------------------------------------------ geometry
FX = 45.65                 # finger footprint origin = pin 1 (CEM: 45.65 mm from the bracket-side edge)
XS = {d: 48.0 + 73.0 * i for i, d in enumerate(DRV)}    # receptacle centres (73 mm pitch, ~3 mm between drives)
DZ = 5.7                   # drives B-D sit this much higher than A (room for lanes 8-15 under B)
YPD = {d: -24.0 - (0 if d == "A" else DZ) for d in DRV}  # receptacle peg lines
YVTD = {d: YPD[d] + 3.6 for d in DRV}                   # via row between the top pad row and the fingers
YVMD = {d: YPD[d] - 2.5 for d in DRV}                   # via row on the mating side of the bottom pad row
# window edges: 0.65 mm short of the receptacle housing face (10.05 mm from the pegs), as on the x8 card, so a
# seated drive never touches the board (rev D; rev C had the edge 1.35 mm too far out, under the drive)
YEDGE = float(os.environ.get("U3_YEDGE", "-9.9"))   # 9.4 and 9.6 do not route on the 4-drive card (rev E trials)
YE_A, YE_B = YPD["A"] + YEDGE, YPD["B"] + YEDGE
XSTEP = 84.5               # window step between drive A and drive B
XF = 129.3                 # end of the finger span; the edge rises to -12.75 right of it
XL = XS[DRV[-1]]
XR = XL + 45.0             # card length: last drive's sideband block ends 44.3 mm right of its receptacle (312 = CEM max)
YTOP = -111.15             # CEM full height
Y0 = -6.0                  # where pairs leave the finger field
Y_REFIN = -14.2            # REFCLK input horizontal (L6), below band A
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
J1 = k.fp("Connector_PCBEdge", "BUS_PCIexpress_x16", "J1", "PCIe x16 edge", FX, -3.45, 0, pads=fing, bom=False)
fpad = lambda n: k.padxy("J1", n)
xpin = lambda n: fpad(f"B{n}")[0]           # A and B pads share x


# ------------------------------------------------------------------ U.3 receptacles (bottom, mirrored)
def u3net(pin, d):
    n = U3_PINS[pin]
    # sidebands and 12 V come from the drive's sideband block (gen/sideband.py); REFCLK1 / port B stay open
    m = {"GND": "GND", "HPT0": "GND", "3V3_AUX": "3V3_AUX", "ACTIVITY#": f"{d}_ACT_N"}
    return m.get(n)


JP = {}
for d in DRV:
    pads = {p: u3net(p, d) for p in U3_PINS if u3net(p, d)}
    pads["MP"] = "GND"
    k.fp("u3adapter", U3FP, f"J{d}", "PSAS4F2130021TR", XS[d], YPD[d], 180, bottom=True, pads=pads, lcsc="C22454449")
    JP[d] = lambda n, d=d: k.padxy(f"J{d}", n)
R = Router(k)
SB = {d: sideband.block(k, R, d, i, XS[d], YPD[d], JP[d], 10 + 4 * i, 20 + 20 * i, 20 + 10 * i)
      for i, d in enumerate(DRV)}

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
for ln in range(4 * N):
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
        if not net or net.startswith(("PET", "PER", "C_PER", "12V_DRV")):      # 12V_DRV: the L6 pour takes P13-P15
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
k.track("3V3_AUX_SLOT", "L1", [(xpin(10), -5.4), VAUX], 0.3); k.via("3V3_AUX_SLOT", *VAUX)
k.track("PCIE_RST_N", "L6", [(xpin(11), -5.4), VRST], 0.2); k.via("PCIE_RST_N", *VRST)
# PRSNT1# (A1) -> PRSNT2# x16 (B81) on L3
VPA = (xpin(1), -9.0); VPB = (xpin(81) + 0.75, -9.0)              # via right of PER15 (L6)
k.track("PRSNT_N", "L6", [(xpin(1), -4.6), VPA], 0.2); k.via("PRSNT_N", *VPA)
k.track("PRSNT_N", "L1", [(xpin(81), -5.4), (xpin(81), -8.4), VPB], 0.2); k.via("PRSNT_N", *VPB)
k.track("PRSNT_N", "L3", [VPA, VPB], 0.2)        # crosses the key slot above its 8.4 mm top

E3 = {d: JP[d]("E3") for d in DRV}

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

# ------------------------------------------------------------------ aux 12 V: PCIe 6-pin at the card end (opt-in per drive)
# Molex 45558 / Mini-Fit Jr 2x3 R/A, mating face at the card end: 1-3 +12V, 4-6 GND.  Feeds only the L4 12V_AUX plane,
# which reaches every drive's jumper; never connected to slot 12 V.  Fit it only when a jumper is set to aux.
# It sits below the last drive's power area, toward the fingers (placed before routing, so the router avoids it).
J5BOT = os.environ.get('U3_J5_BOTTOM') == '1'      # experimental: J5 on the bottom, the drives' side
J5ROT = int(os.environ.get('U3_J5ROT', '270'))
k.fp("Connector_Molex", "Molex_Mini-Fit_Jr_5569-06A2_2x03_P4.20mm_Horizontal", "J5", "PCIe 6-pin 45558-0003",
     XR - 14.4, -24.15, J5ROT, bottom=J5BOT, pads={"1": "12V_AUX", "2": "12V_AUX", "3": "12V_AUX", "4": "GND", "5": "GND", "6": "GND"},
     lcsc="C7545781")
# bulk cap on the bottom just east of J5's +12V column: +12V straight to pin 2 on L6, GND by a via to the planes
j2 = k.padxy("J5", "2")
cva, cga = two("C19", *C1206, "22uF 25V X5R", j2[0] + 3.8, j2[1], 90, not J5BOT, (j2[0], j2[1] + 5), "12V_AUX", "GND", "C12891")
CL = "L1" if J5BOT else "L6"
k.track("12V_AUX", CL, [cva, (j2[0] + 2.3, cva[1]), j2], 0.6)
k.track("GND", CL, [cga, (cga[0], cga[1] - 1.4)], 0.6); k.via("GND", cga[0], cga[1] - 1.4, 0.6, 0.3)
k.text("AUX 12V", XR - 28.0, -14.2, P.F_SilkS, 1.0)

print("J5 pads", [(q.GetNumber(), round(k.padxy("J5", q.GetNumber())[0], 2), round(k.padxy("J5", q.GetNumber())[1], 2)) for q in k.fps["J5"].Pads()])

# ------------------------------------------------------------------ card-level parts, REFCLK, trunks
import time; T0 = time.time()
YP = YPD["A"]
card = cardkit.Card(k, R, xpin, fpad, [(d, XS[d], YPD[d], JP[d]) for d in DRV], YP)
# REFCLK: the card buffer (DIF3, east face) feeds drive A directly and (DIF2, north face) a chain on L6 under drive A's
# block (the edge-side channel row, as on the x8) to a 9DBL0442 repeater left of drive B.  Each repeater feeds its
# own drive and the next link of the chain, so only one clock pair ever passes under a sideband block (a block's
# vias leave no room for more): 3 drives = repeater at B (-> B, C); 4 drives = repeaters at B (-> B, chain) and C
# (-> C, D).  A 9DBL0442 flips the pair's handedness (top side: input wants P on the left, outputs leave with P on
# the right), so every repeater output turns back through its via pair (a U-turn restores P-left on L6).
card.buffer({"A": 3, "RB": 2})
print("REFCLK_IN skew", round(card.refclk_in(yrun=-13.55, ycross=-14.2, ykneeA=-9.0), 3))
card.parts()
card.wake_clkreq()
card.clock_direct("A", 3)
REPS = ["B"] if N == 3 else ["B", "C"]
RXC = {d: XS[d] - 27.0 for d in REPS}                  # repeater centres (top side, rot 270; DIF3 clears the MP pad)
TAPDX = 5.0                                              # 3V3_AUX trunk tap this far left of a repeater
XSTEPC = XSTEP + 1.0                                     # channel step (trunks and clock row) just past the window step
# slot SMBus: B5/B6 -> vias -> the TCA9548A upstream port
VSC, VSD = (xpin(5), -10.0), (xpin(6), -10.6)
k.track("SMCLK_SLOT", "L1", [(xpin(5), -5.4), VSC], 0.2); k.via("SMCLK_SLOT", *VSC)
k.track("SMDAT_SLOT", "L1", [(xpin(6), -5.4), VSD], 0.2); k.via("SMDAT_SLOT", *VSD)
first = card.trunks({"SMCLK": 13.5, "SMDAT": 14.5, "3V3_AUX": 15.5, "PCIE_RST_N": 27.45, "PCIE_WAKE_N": 28.3},
                   steps=[(XSTEPC, XSTEPC)], aux_taps=[RXC[d] - TAPDX for d in REPS])
# ------------------------------------------------------------------ REFCLK repeaters and the clock chain (L6)
from cardkit import refclk, approach, RW, RG
CD = (RW + RG) / 2                                       # line offset from the pair centre
CO = 0.6                                                 # via offset from the pair centre (vias 1.2 mm apart)
VIA_H = 1.5784
FAN = 0.8                                                # via fan length along the pair: fans steeper than 45 deg, so
                                                         # DRC never takes a fan and a 45 deg bend of the other line as a pair
QFN = ("Package_DFN_QFN", "VQFN-32-1EP_5x5mm_P0.5mm_EP3.15x3.15mm")
C0603 = ("Capacitor_SMD", "C_0603_1608Metric")
REP = {}


def rep_place_cdc(d, nxt):
    """CDCDB400 repeater (U3_CLK=cdcdb400): same land and orientation, input on pins 3/4, CK2 (22/23) south -> drive
    d, CK3 (27/28) east -> nxt.  Fan-out only, so every stage is a plain buffer (no ZDB stage, no PLL filter)."""
    cx, cy = RXC[d], YPD[d] - 2.0
    ref = f"U{40 + REPS.index(d)}"
    pads = {"33": "GND", "3": f"REFCLK_R{d}_P", "4": f"REFCLK_R{d}_N",
            "22": f"REFCLK_{d}_P", "23": f"REFCLK_{d}_N", "27": f"REFCLK_{nxt}_P", "28": f"REFCLK_{nxt}_N", "24": "GND"}
    for p in (1, 2, 6, 7, 12, 15, 16, 18, 21, 25, 29, 31, 32):   # VDD/VDDR, CKPWRGD and SMBus high, OE0#/OE1# high
        pads[str(p)] = "3V3_AUX"
    k.fp(*QFN, ref, cardkit.CLK_VALUE, cx, cy, 270, pads=pads, lcsc="")
    U = lambda n: k.padxy(ref, str(n))
    assert abs(U(3)[1] - (cy - 2.438)) < 0.01 and U(3)[0] > U(4)[0], "repeater orientation"
    k.rule_area(f"NECKDOWN_{ref}", [(cx - 5.0, cy - 5.2), (cx + 6.2, cy - 5.2), (cx + 6.2, cy + 5.0), (cx - 5.0, cy + 5.0)])
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            k.via("GND", cx + i, cy + j)
    x, y = U(24); k.track("GND", "L1", [(x, y), (x, y - 0.55), (x - 0.4, y - 0.95)], 0.2)
    V = {}
    V["w"] = (cx - 3.3, cy - 1.0); k.track("3V3_AUX", "L1", [U(12), (cx - 2.9, U(12)[1]), V["w"]], 0.2)
    V["w2"] = (cx - 3.3, cy + 1.25); k.track("3V3_AUX", "L1", [U(15), U(16), V["w2"]], 0.2)
    V["n"] = (cx - 1.0, cy - 3.3)                        # SMBus pins 6/7 (tied high), west of the input pair
    k.track("3V3_AUX", "L1", [U(6), (U(6)[0], cy - 2.95), V["n"]], 0.2)
    k.track("3V3_AUX", "L1", [U(7), (U(7)[0], cy - 2.95), V["n"]], 0.2)
    V["s"] = (cx - 1.75, cy + 3.4)                       # below pin 17 (NC)
    k.track("3V3_AUX", "L1", [U(21), (U(21)[0], cy + 3.15), (cx - 1.5, cy + 3.15), V["s"]], 0.2)
    k.track("3V3_AUX", "L1", [U(18), (U(18)[0], cy + 3.15)], 0.2)
    V["e"] = (cx + 2.7, cy - 3.0)                        # VDDR (2), CKPWRGD (1), 32 (NC, any level), 31, 29
    k.track("3V3_AUX", "L1", [U(2), (U(2)[0], cy - 2.95), (cx + 2.35, cy - 2.95), V["e"]], 0.2)
    k.track("3V3_AUX", "L1", [U(1), (U(1)[0], cy - 2.95)], 0.2)
    k.track("3V3_AUX", "L1", [U(29), (cx + 3.05, U(29)[1]), (cx + 3.05, cy - 2.65), V["e"]], 0.15)
    k.track("3V3_AUX", "L1", [U(31), (cx + 3.05, U(31)[1])], 0.15)
    k.track("3V3_AUX", "L1", [U(32), (cx + 3.05, U(32)[1])], 0.15)
    V["se"] = (cx + 2.9, cy + 2.2); k.track("3V3_AUX", "L1", [U(25), (cx + 2.9, U(25)[1]), V["se"]], 0.2)
    for v in V.values():
        k.via("3V3_AUX", *v)
    # ring on L3; the VDDR/CKPWRGD via (e) reaches the 100 nF at n between the input vias and the pad row
    k.track("3V3_AUX", "L3", [V["w"], V["w2"], (cx - 2.4, cy + 2.15), (cx - 2.4, cy + 3.0), V["s"],
                              (cx + 2.9, cy + 3.4), V["se"], (cx + 2.9, cy - 2.8), V["e"], (cx + 2.6, cy - 2.9),
                              (cx - 0.6, cy - 2.9), V["n"]], 0.25)
    caps = [("w", (cx - 3.3, cy - 2.0), 90, "100nF", C0402, (0.65, 0.0)), ("w2", (cx - 3.3, cy + 2.0), 90, "10uF", C0603, (0, 0.8)),
            ("s", (cx - 1.75, cy + 4.1), 90, "100nF", C0402, (0, 0.75)), ("n", (cx - 1.0, cy - 4.1), 90, "100nF", C0402, (-0.65, 0.0))]
    for i, (key, (x, y), rot, val, fp, gd) in enumerate(caps):
        cref = f"C{60 + 4 * REPS.index(d) + i}"
        vp, gp = two(cref, *fp, val, x, y, rot, True, V[key], "3V3_AUX", "GND", "C1525" if val == "100nF" else "C19702")
        k.track("3V3_AUX", "L6", [V[key], vp], 0.25)
        gv = (gp[0] + gd[0], gp[1] + gd[1]); k.track("GND", "L6", [gp, gv], 0.25); k.via("GND", *gv)
    REP[d] = dict(cx=cx, cy=cy, U=U, V=V, ref=ref)
    return REP[d]


def rep_place(d, nxt):
    if cardkit.CDC:
        return rep_place_cdc(d, nxt)
    """9DBL0442 on the top side left of drive d's receptacle, rot 270: input (pins 5/6) on the north face, DIF2
    (22/23) south -> drive d, DIF3 (27/28) east -> nxt.  DIF0/DIF1 unused (OE# tied high = off)."""
    cx, cy = RXC[d], YPD[d] - 2.0
    ref = f"U{40 + REPS.index(d)}"
    # pin 1 (HIBW_BYPM_LOBW#): open = bypass (fan-out).  The last stage of the 4-drive chain (U41 -> C, D) runs as a
    # zero-delay buffer instead (pin 1 low = low-BW PLL), so no drive sees more than two buffer delays (12 ns
    # common-clock transport budget); its PLL jitter (<= 0.48 ps) only reaches the Gen3 drives C and D
    zdb = nxt == "D"
    pads = {"8": "GND", "33": "GND", "5": f"REFCLK_R{d}_P", "6": f"REFCLK_R{d}_N",
            "22": f"REFCLK_{d}_P", "23": f"REFCLK_{d}_N", "27": f"REFCLK_{nxt}_P", "28": f"REFCLK_{nxt}_N",
            "24": "GND", "29": "GND"}
    for p in (4, 21, 9, 10, 11, 12, 15, 19, 25, 31):    # VDD/VDDA/SMBus/CKPWRGD high, OE0#/OE1# high
        pads[str(p)] = "3V3_AUX"
    if zdb:                                             # PLL in use: pin 1 strapped hard to GND (latched input),
        pads["1"] = "GND"; pads["21"] = "3V3_PLL"       # VDDA behind its own ferrite + 100 nF
    k.fp(*QFN, ref, "PI6CB33401ZHIEX", cx, cy, 270, pads=pads, lcsc="")
    U = lambda n: k.padxy(ref, str(n))
    assert abs(U(5)[1] - (cy - 2.438)) < 0.01 and U(5)[0] > U(6)[0], "repeater orientation"
    k.rule_area(f"NECKDOWN_{ref}", [(cx - 5.0, cy - 5.2), (cx + 6.2, cy - 5.2), (cx + 6.2, cy + 5.0), (cx - 5.0, cy + 5.0)])
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            k.via("GND", cx + i, cy + j)
    # GND pins into the exposed pad (L1)
    for p, sx in (((1, -1), (8, 1)) if zdb else ((8, 1),)):
        x, y = U(p); k.track("GND", "L1", [(x, y), (x, y + 0.55), (x + sx * 0.4, y + 0.95)], 0.2)
    x, y = U(24); k.track("GND", "L1", [(x, y), (x, y - 0.55), (x - 0.4, y - 0.95)], 0.2)
    x, y = U(29); k.track("GND", "L1", [(x, y), (cx + 1.2, y)], 0.2)
    # supply escapes -> vias (L1), decoupling on the bottom right at the vias
    V = {}
    k.track("3V3_AUX", "L1", [U(9), U(12)], 0.2)
    V["w"] = (cx - 3.3, cy - 1.0); k.track("3V3_AUX", "L1", [U(10), (cx - 2.9, U(10)[1]), V["w"]], 0.2)
    V["w2"] = (cx - 3.3, cy + 1.25); k.track("3V3_AUX", "L1", [U(15), V["w2"]], 0.2)
    V["n"] = (cx + 1.0, cy - 3.3); k.track("3V3_AUX", "L1", [U(4), (U(4)[0], cy - 2.95), V["n"]], 0.2)
    V["s"] = (cx - 1.75, cy + 3.4)                      # below pin 17 (no net), 0.26 clear
    if zdb:
        VP = (cx - 0.1, cy + 3.5)
        k.track("3V3_PLL", "L1", [U(21), (U(21)[0], cy + 3.15), VP], 0.2); k.via("3V3_PLL", *VP)
        k.track("3V3_AUX", "L1", [U(19), (U(19)[0], cy + 3.15), (cx - 1.5, cy + 3.15), V["s"]], 0.2)
    else:
        k.track("3V3_AUX", "L1", [U(21), (U(21)[0], cy + 3.15), (cx - 1.5, cy + 3.15), V["s"]], 0.2)
        k.track("3V3_AUX", "L1", [U(19), (U(19)[0], cy + 3.15)], 0.2)
    V["e"] = (cx + 2.7, cy - 3.0)                       # east past pin 32's tip, then north (DIF3 pair further east)
    k.track("3V3_AUX", "L1", [U(31), (cx + 3.05, U(31)[1]), (cx + 3.05, cy - 2.65), V["e"]], 0.15)
    V["se"] = (cx + 2.9, cy + 2.2); k.track("3V3_AUX", "L1", [U(25), (cx + 2.9, U(25)[1]), V["se"]], 0.2)
    for v in V.values():
        k.via("3V3_AUX", *v)
    # the supply vias joined on L3 around the part (w is fed from the trunk's aux tap)
    south = [(cx - 1.0, cy + 4.15), (cx + 1.4, cy + 4.15), (cx + 2.15, cy + 3.4)] if zdb else []   # around the PLL via
    k.track("3V3_AUX", "L3", [V["w"], V["w2"], (cx - 2.4, cy + 2.15), (cx - 2.4, cy + 3.0), V["s"], *south,
                              (cx + 2.9, cy + 3.4), V["se"], (cx + 2.9, cy - 2.8), V["e"], V["n"]], 0.25)
    caps = [("w", (cx - 3.3, cy - 2.0), 90, "100nF", C0402, (0.65, 0.0)), ("w2", (cx - 3.3, cy + 2.0), 90, "10uF", C0603, (0, 0.8)),
            ("s", (cx - 1.75, cy + 4.1), 90, "100nF", C0402, (0, 0.75)), ("n", (cx + 1.0, cy - 4.1), 90, "100nF", C0402, (0.65, 0.0))]
    if zdb:                                             # bottom: via s -> ferrite -> 100 nF -> PLL via; pin 19's 100 nF west
        caps[2] = ("s", (cx - 3.4, cy + 5.3), 90, "100nF", C0402, (0, 0.75))
        f1, f2 = two(f"FB{ref[1:]}", "Inductor_SMD", "L_0603_1608Metric", "600R@100MHz", cx - 1.35, cy + 4.3, 0, True, V["s"],
                     "3V3_AUX", "3V3_PLL", "C19330")
        k.track("3V3_AUX", "L6", [V["s"], (f1[0] + 0.15, cy + 4.0)], 0.25)
        k.track("3V3_AUX", "L6", [(f1[0], cy + 4.5), (cx - 2.9, cy + 4.82), (cx - 3.4, cy + 4.82)], 0.25)
        k.track("3V3_PLL", "L6", [VP, (f2[0], cy + 4.0)], 0.25)
        pp, pg = two(f"C{60 + 4 * REPS.index(d) + 4}", *C0402, "100nF", cx - 0.55, cy + 6.05, 90, True, f2, "3V3_PLL", "GND", "C1525")
        k.track("3V3_PLL", "L6", [f2, pp], 0.25)
        k.track("GND", "L6", [pg, (pg[0] - 0.75, pg[1])], 0.25); k.via("GND", pg[0] - 0.75, pg[1])
    for i, (key, (x, y), rot, val, fp, gd) in enumerate(caps):
        cref = f"C{60 + 4 * REPS.index(d) + i}"
        vp, gp = two(cref, *fp, val, x, y, rot, True, V[key], "3V3_AUX", "GND", "C1525" if val == "100nF" else "C19702")
        if not (zdb and key == "s"):
            k.track("3V3_AUX", "L6", [V[key], vp], 0.25)
        gv = (gp[0] + gd[0], gp[1] + gd[1]); k.track("GND", "L6", [gp, gv], 0.25); k.via("GND", *gv)
    REP[d] = dict(cx=cx, cy=cy, U=U, V=V, ref=ref)
    return REP[d]


PIN_P, PIN_N = cardkit.CLKIN


def pins_in(r, xin, yv, net):
    """L1: input via pair (side by side at yv, P east) -> pins 5/6 (heading south)."""
    vP, vN = (xin + CO, yv), (xin - CO, yv)
    res = k.pair("L1", [(xin, yv + CO - CD), (xin, r["U"](PIN_P)[1] - 0.45)], [(f"{net}_P", [vP]), (f"{net}_N", [vN])],
                 [(None, [r["U"](PIN_P)]), (None, [r["U"](PIN_N)])], RW, RG)
    assert math.dist(res[f"{net}_P"][0][-1], r["U"](PIN_P)) < 1e-6, f"{net}: P must reach pin 5"
    k.via(f"{net}_P", *vP); k.via(f"{net}_N", *vN)
    return {n: plen(v[0]) for n, v in res.items()}


def chain_in(r, net, cen6, starts, extra0=None):
    """L6 from starts along cen6 (ending heading south over the repeater input) -> via pair -> L1 -> pins 5/6."""
    xin = r["cx"] + (0.5 if cardkit.CDC else -0.5)
    yv = r["cy"] - 3.6
    l1 = pins_in(r, xin, yv, net)
    ex = {n: l1[n] + 2 * VIA_H + (extra0 or {}).get(n, 0.0) for n in l1}
    cen = cen6 + [(xin, yv - FAN)]
    res = refclk(k, "L6", cen, starts, [(None, [(xin + CO, yv)]), (None, [(xin - CO, yv)])], extra=ex)
    assert math.dist(res[f"{net}_P"][0][-1], (xin + CO, yv)) < 1e-6, f"{net}: P must land on the east via"
    tot = {n: plen(res[n][0]) + ex[n] for n in res}
    print(f"{net}: {tot[net + '_P']:.2f} / {tot[net + '_N']:.2f} mm, skew {tot[net + '_P'] - tot[net + '_N']:+.3f}")


def out_local(r, d):
    """DIF2 (south face, P west) -> L1 south -> vias (P west) -> L6 U-turn north, east, south, east into E7/E8."""
    U = r["U"]; cx, cy = r["cx"], r["cy"]
    xm = (U(22)[0] + U(23)[0]) / 2
    yv = cy + 4.9                                         # 1 mm leg before the U-turn (fan and bend not parallel)
    vP, vN = (xm - CO, yv), (xm + CO, yv)
    l1 = k.pair("L1", [(xm, U(22)[1] + 0.45), (xm, yv - CO + CD)], [(f"REFCLK_{d}_P", [U(22)]), (f"REFCLK_{d}_N", [U(23)])],
                [(None, [vP]), (None, [vN])], RW, RG)
    assert math.dist(l1[f"REFCLK_{d}_P"][0][-1], vP) < 1e-6, f"REFCLK_{d}: P must reach the west via"
    k.via(f"REFCLK_{d}_P", *vP); k.via(f"REFCLK_{d}_N", *vN)
    cend, ends = approach(JP[d], d, YPD[d])
    xa = XS[d] - 23.0
    y1 = cy + 2.9
    cen = [(xm, yv - FAN), (xm, y1 + 0.5), (xm + 0.5, y1), (xa - 0.6, y1), (xa, y1 + 0.6), (xa, cend[1] - 0.6),
           (xa + 0.6, cend[1]), cend]
    ex = {n: plen(l1[n][0]) + 2 * VIA_H for n in l1}
    res = refclk(k, "L6", cen, [(f"REFCLK_{d}_P", [vP]), (f"REFCLK_{d}_N", [vN])], ends, extra=ex)
    card._check(d, res, JP[d])


def out_chain(r, nxt):
    """DIF3 (east face, P south) -> L1 east, north -> vias (P east) -> L6 U-turn south, east, north to the edge-side
    row, east.  Returns (L6 start entries, centre so far, lengths so far) for the next link."""
    U = r["U"]; cx, cy = r["cx"], r["cy"]
    ym = (U(27)[1] + U(28)[1]) / 2
    xl = cx + 3.7
    yv = cy - 4.2
    vP, vN = (xl + CO, yv), (xl - CO, yv)
    l1 = k.pair("L1", [(U(27)[0] + 0.45, ym), (xl - 0.4, ym), (xl, ym - 0.4), (xl, yv + CO - CD)],
                [(f"REFCLK_{nxt}_P", [U(27)]), (f"REFCLK_{nxt}_N", [U(28)])], [(None, [vP]), (None, [vN])], RW, RG)
    assert math.dist(l1[f"REFCLK_{nxt}_P"][0][-1], vP) < 1e-6, f"REFCLK_{nxt}: P must reach the east via"
    k.via(f"REFCLK_{nxt}_P", *vP); k.via(f"REFCLK_{nxt}_N", *vN)
    yr = r["cy"] + 2.0 + sideband.CLK_Y[0]
    xu = xl + 2.2
    cen = [(xl, yv + FAN), (xl, yv + 1.4), (xl + 0.5, yv + 1.9), (xu - 0.5, yv + 1.9), (xu, yv + 1.4),
           (xu, yr + 0.6), (xu + 0.6, yr)]
    ex = {n: plen(l1[n][0]) + 2 * VIA_H for n in l1}
    return [(f"REFCLK_{nxt}_P", [vP]), (f"REFCLK_{nxt}_N", [vN])], cen, ex


# link 1: card buffer DIF2 (north face) -> column north -> edge-side row under drive A -> step -> repeater B input
U1 = card.U
a_, b_ = U1(22), U1(23)
xc1 = (a_[0] + b_[0]) / 2
yrA, yrB = YPD["A"] + sideband.CLK_Y[0], YPD["B"] + sideband.CLK_Y[0]
rB = rep_place("B", "C" if N == 3 else "RC")
xin = rB["cx"] - 0.5
chain_in(rB, "REFCLK_RB", [(xc1, a_[1] - 0.7), (xc1, yrA + 0.6), (xc1 + 0.6, yrA), (XSTEPC - 0.6, yrA), (XSTEPC, yrA - 0.6),
                           (XSTEPC, yrB + 0.6), (XSTEPC + 0.6, yrB), (xin - 0.6, yrB), (xin, yrB + 0.6)],
         [("REFCLK_RB_P", [a_]), ("REFCLK_RB_N", [b_])])
out_local(rB, "B")
st, cen, ex = out_chain(rB, "C" if N == 3 else "RC")
if N == 3:                                     # B's repeater -> under B's block -> drop left of C -> C
    cend, ends = approach(JP["C"], "C", YPD["C"])
    xdrop = XS["C"] - 25.0
    cen += [(xdrop - 0.6, yrB), (xdrop, yrB + 0.6), (xdrop, cend[1] - 0.6), (xdrop + 0.6, cend[1]), cend]
    card._check("C", refclk(k, "L6", cen, st, ends, extra=ex), JP["C"])
else:
    rC = rep_place("C", "D")
    xin = rC["cx"] - 0.5
    chain_in(rC, "REFCLK_RC", cen + [(xin - 0.6, yrB), (xin, yrB + 0.6)], st, extra0=ex)
    out_local(rC, "C")
    st, cen, ex = out_chain(rC, "D")
    cend, ends = approach(JP["D"], "D", YPD["D"])
    xdrop = XS["D"] - 25.0
    cen += [(xdrop - 0.6, yrB), (xdrop, yrB + 0.6), (xdrop, cend[1] - 0.6), (xdrop + 0.6, cend[1]), cend]
    card._check("D", refclk(k, "L6", cen, st, ends, extra=ex), JP["D"])
# 3V3_AUX for the repeaters: the trunk's extra tap (left of the repeater) -> L1 -> the repeater's west supply via
for d, r in REP.items():
    tv = [t for t in card.aux_taps if abs(t[0] - (r["cx"] - TAPDX)) < 1e-6][0]
    k.track("3V3_AUX", "L1", [tv, (tv[0], r["V"]["w"][1]), r["V"]["w"]], 0.25)

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
for j, d in enumerate(DRV if os.environ.get("STAGE") != "card" else ""):
    SB[d]["taps"] = {net: tv[j] for net, tv in card.taps.items()}
    sideband.route_block(k, R, d, SB[d], JP[d], YVMD[d], YVTD[d])
    card.after_block(j)
    print("t block", d, round(time.time() - T0))

# ------------------------------------------------------------------ rev F: bring-up and service features (gen/extras.py)
EX = extras.Extras(k, R, P)
EX.column()
EX.foot()
for i, d in enumerate(DRV):
    EX.drive(d, i, XS[d], YPD[d], last=d == DRV[-1], dy=-1.0)
EX.fan(XL + 12.45, -16.0, "net", "via", (XL + 20.47, -22.0), default="aux")
EX.holes(XR, (-65.0, -104.0), -92.0)
GAPH = EX.gap_holes([(XS[a] + XS[b]) / 2 for a, b in zip(DRV, DRV[1:])], 11)
print("t extras", round(time.time() - T0), "fails", len(EX.fails))

# ------------------------------------------------------------------ planes
# L4: slot 12 V (fingers -> every jumper's slot pin) in the band next to the fingers, 12V_AUX everywhere else
# (window-side band -> every jumper's aux pin, the 6-pin and its bulk cap).  12 V has priority; the aux plane fills
# around it.
YSPL_A, YSPL_B = YPD["A"] + sideband.YSPLIT, YPD["B"] + sideband.YSPLIT
k.zone("GND", "L2", BOARD, clearance=0.2)
k.zone("GND", "L5", BOARD, clearance=0.2)
k.zone("12V", "L4", [(0, 1), (XL + 21.5, 1), (XL + 21.5, YPD[DRV[-1]] + 2.3), (XL + 27.6, YPD[DRV[-1]] + 2.3), (XL + 27.6, YSPL_B + 0.3),
                     (XSTEP, YSPL_B + 0.3), (XSTEP, YSPL_A + 0.3), (0, YSPL_A + 0.3)], prio=1, clearance=0.3)
k.zone("12V_AUX", "L4", [(0, 1), (XR + 1, 1), (XR + 1, YTOP - 1), (0, YTOP - 1)], clearance=0.3, thermal=False)
k.zone("GND", "L3", BOARD, clearance=0.25)

# ------------------------------------------------------------------ holes: bracket screws + holder slots
# bracket screw holes: keep the L4 12 V planes 1.1 mm off the hole wall (a screw must never reach 12 V)
for hn, (hx, hy) in (("H1", (7.5, -94.75)), ("H2", (7.5, -9.35))):
    k.keepout(f"{hn}_L4_VOID", [(hx + 2.7 * math.cos(math.radians(a)), hy + 2.7 * math.sin(math.radians(a)))
                                for a in range(0, 360, 30)], ["L4"])
k.fp("MountingHole", "MountingHole_3.2mm_M3", "H1", "bracket", 7.5, -94.75, bom=False)
k.fp("MountingHole", "MountingHole_3.2mm_M3", "H2", "bracket", 7.5, -9.35, bom=False)
for i, (x, y) in enumerate(((6.0, -30.0), (6.0, -60.0), (XR - 4.0, -50.0), (XR - 4.0, -80.0))):
    k.fp("u3adapter", "MountingSlot_M3_3.2x6.2", f"H{3 + i}", "M3 slot", x, y, bom=False)

# ------------------------------------------------------------------ silkscreen
k.text(f"U.3 x16 passive {N} drives  rev F", 112.0, -21.0, P.F_SilkS, 1.0)
k.text("C/D: PCIe Gen3 only" if N == 4 else "C: PCIe Gen3 only", 112.0, -24.2, P.F_SilkS, 1.0)
k.text("x4x4x4x4 bifurcation" if N == 4 else "x4x4x4 / x8x4x4 bifurcation", 112.0, -22.6, P.F_SilkS, 1.0)
for d in DRV:
    k.text(f"DRIVE {d}", XS[d], YPD[d] - 8.2, P.B_SilkS, 1.0, mirror=True)
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
    (constraint length (max 300mm)))"""
    extra += "\n" + cardkit.DRU
    extra += """
(rule "REFCLK100 x16: repeater links <= 12 mm uncoupled (two via fans, two QFN pin fan-outs, turn-skew bumps)"
    (condition "A.NetClass == 'REFCLK_100' && (A.NetName == 'REFCLK_R*' || A.NetName == 'REFCLK_B_*' || A.NetName == 'REFCLK_C_*' || A.NetName == 'REFCLK_D_*')")
    (constraint diff_pair_uncoupled (max 12.0mm)))"""
    bb, rpt = k.fill_and_check(skew + "\n" + extra)
    c, items = drc_summary(rpt)
    print("DRC:", dict(c))
