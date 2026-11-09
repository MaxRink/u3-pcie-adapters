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

OUT = os.path.join(ROOT, "boards", "x8")
k = Kit(OUT, "u3_x8")
U3FP = "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD"

# ------------------------------------------------------------------ geometry
FX = 45.65                 # finger footprint origin = pin 1 (CEM: 45.65 mm from the bracket-side edge)
XA, XB = 48.0, 121.0       # receptacle centres (drive A / drive B)
YP = -24.0                 # receptacle peg line
YM = YP - 11.75            # mating face
YE = YM + 1.0              # board edge in the drive windows (pulled back 1 mm under the housing front)
XR = 165.0                 # card length (half-length card is 167.65)
YTOP = -111.15             # CEM full height
YVT = -20.4                # via row between the top pad row and the fingers
YVM = -26.5                # via row on the mating side of the bottom pad row
Y0 = -6.0                 # where pairs leave the finger field
LVL_A = {0: -15.2, 1: -16.2, 2: -17.2, 3: -18.2}      # band A horizontals (lane 0 lowest)
LVL_B = {7: -15.2, 6: -16.2, 5: -17.2, 4: -18.2}      # band B horizontals (lane 7 lowest)
Y_REFIN = -14.2            # REFCLK input horizontal (L6), below band A
Y_REFB = -28.8             # REFCLK_B run under receptacle A (L1)
COLW = 12.0                # bracket-side column width

# ------------------------------------------------------------------ CEM x8 edge pinout (side B = F.Cu, side A = B.Cu)
GND_B = [4, 7, 13, 16, 18, 21, 22, 25, 26, 29, 32, 35, 36, 39, 40, 43, 44, 47, 49]
GND_A = [4, 12, 15, 18, 20, 23, 24, 27, 28, 31, 34, 37, 38, 41, 42, 45, 46, 49]
fing = {f"B{n}": "GND" for n in GND_B}
fing.update({f"A{n}": "GND" for n in GND_A})
fing.update({"B1": "12V", "B2": "12V", "B3": "12V", "A2": "12V", "A3": "12V", "B5": "SMBCLK", "B6": "SMBDAT",
             "B8": "3V3", "A9": "3V3", "A10": "3V3", "B10": "3V3_AUX", "A11": "PCIE_RST_N",
             "A1": "PRSNT_N", "B48": "PRSNT_N", "A13": "REFCLK_IN_P", "A14": "REFCLK_IN_N"})
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
    m = {"GND": "GND", "HPT0": "GND", "12V": "12V", "12V_PRE": "12V", "3V3_AUX": "3V3_AUX",
         "PERST0#": "PCIE_RST_N", "SMBCLK": f"{d}_SMBCLK", "SMBDAT": f"{d}_SMBDAT",
         "DUALPORTEN#": f"{d}_DPE_N", "PWRDIS": f"{d}_PWRDIS", "ACTIVITY#": f"{d}_ACT_N"}
    return m.get(n)          # lanes and REFCLK get their nets from the router; U.2/port-B/5V/HPT1 etc. open


JP = {}
for d, xc in (("A", XA), ("B", XB)):
    pads = {p: u3net(p, d) for p in U3_PINS if u3net(p, d)}
    pads["MP"] = "GND"
    k.fp("u3adapter", U3FP, f"J{d}", "PSAS4F2130021TR", xc, YP, 180, bottom=True, pads=pads, lcsc="C22454449")
    JP[d] = lambda n, d=d: k.padxy(f"J{d}", n)

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


def band_center(xc, h, xt, yend, dirn, c=0.8):
    yv = Y0 if dirn < 0 else YKNEE_B
    xd = xc + dirn * (yv - h)
    pts = [(xc, Y0)] + ([(xc, yv)] if yv != Y0 else [])
    return pts + [(xd, h), (xt - dirn * c, h), (xt, h - c), (xt, yend)]


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
        res = k.pair("L1", band_center(xc, h, xt, YVM + 0.3, dirn), fstarts(pins, "B"),
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
        w = 0.5 if net == "12V" else (0.3 if net in ("GND", "3V3_AUX") else 0.2)
        dv = (0.6, 0.3) if net == "12V" else (None, None)
        k.track(net, "L6", [(x, y), (x, YVM)], w); k.via(net, x, YVM, *dv)

k.save()
with open(os.path.join(OUT, "bom_raw.json"), "w") as f:
    json.dump(k.bom, f, indent=1)

if __name__ == "__main__":
    import subprocess
    skew = subprocess.run([sys.executable, os.path.join(RULES, "gen_pair_skew_rules.py"), k.pcb],
                          capture_output=True, text=True).stdout
    bb, rpt = k.fill_and_check(skew)
    c, items = drc_summary(rpt)
    print("DRC:", dict(c))
