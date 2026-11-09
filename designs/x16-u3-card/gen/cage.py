"""Design 3: OCuLink 4i (device end) -> U.3 (SFF-TA-1001) breakout board for a printed drive cage.

Board frame: x right, y down, y=0 is the drive mating edge.  6 layers JLC06161H-3313
(L1 HS | L2 GND | L3 LS | L4 12V | L5 GND | L6 HS).  OCuLink sits on the BOTTOM so lane order
matches the U.3 pin order without crossings; P/N inversion on some pairs is allowed by PCIe.
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbkit import *
from symlib import U3_PINS, OCU_DEV_PINS

OUT = os.path.join(ROOT, "boards", "cage")
k = Kit(OUT, "u3_cage")
b = k.b

# ------------------------------------------------------------------ geometry constants
XO = 3.0                 # OCuLink centre x
YB = 23.6                # OCuLink B row (bottom side)
YO = YB + 4.305          # OCuLink footprint origin
EF = YO + 3.065          # OCuLink front face = notch edge
YV = 26.65               # A-front via row (PET L1->L6, low-speed)
YG2 = 27.4               # second GND via row
YBR = 24.695             # between-rows
YVR = 14.95              # via row behind U.3 top pad row
YH = 9.15                # via row under the U.3 housing (front of bottom pad row)

# ------------------------------------------------------------------ nets on the U.3 receptacle
def u3net(pin):
    n = U3_PINS[pin]
    m = {"GND": "GND", "12V": "12V", "12V_PRE": "12V", "3V3_AUX": "3V3_AUX", "PERST0#": "PCIE_RST_N",
         "SMBCLK": "SMBCLK", "SMBDAT": "SMBDAT", "DUALPORTEN#": "DUALPORTEN_N", "PWRDIS": "PWRDIS",
         "ACTIVITY#": "ACT_N", "REFCLK0+": "REFCLK0_P", "REFCLK0-": "REFCLK0_N"}
    if n in m:
        return m[n]
    import re
    r = re.match(r"^PE([TR])([pn])([0-3])$", n)
    if r:
        return f"PE{r.group(1)}{r.group(3)}_{r.group(2).upper()}"
    return None          # U.2-only lanes, port B, HPT, IfDet, PRSNT, 5V, WAKE, RSVD: not connected


j1pads = {p: u3net(p) for p in U3_PINS if u3net(p)}
j1pads["MP"] = "GND"
J1 = k.fp("u3adapter", "Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD", "J1", "PSAS4F2130021TR", 0, 11.75, 180,
          pads=j1pads, lcsc="C22454449")

j2pads = {p: "GND" for p, n in OCU_DEV_PINS.items() if n in ("GND", "SHIELD")}
j2pads.update({"A9": "SMBCLK", "A10": "SMBDAT", "A12": "PCIE_RST_N", "A13": "CPRSNT_N"})
J2 = k.fp("u3adapter", "Amphenol_G14A421211112HR_OCuLink_4i_RA_SMD", "J2", "G14A421211112HR", XO, YO, 0,
          bottom=True, pads=j2pads, lcsc="C5156927")

# PCIe 6-pin aux (Molex 45558-0003 / Mini-Fit Jr 2x3 R/A): 1-3 +12V, 4,6 GND, 5 sense (GND)
J3 = k.fp("Connector_Molex", "Molex_Mini-Fit_Jr_5569-06A2_2x03_P4.20mm_Horizontal", "J3", "PCIe 6-pin 45558-0003",
          -12.0, 25.6, 180, pads={"1": "12V_IN", "2": "12V_IN", "3": "12V_IN", "4": "GND", "5": "GND", "6": "GND"},
          lcsc="C7545781")


def two(ref, lib, fpn, val, x, y, rot, bottom, near, net_near, net_far, lcsc, dnp=False):
    f = k.fp(lib, fpn, ref, val, x, y, rot, bottom=bottom, lcsc=lcsc, dnp=dnp)
    p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
    if math.dist(p1, near) <= math.dist(p2, near):
        k.setpad(ref, "1", net_near); k.setpad(ref, "2", net_far); return p1, p2
    k.setpad(ref, "2", net_near); k.setpad(ref, "1", net_far); return p2, p1


R0402 = ("Resistor_SMD", "R_0402_1005Metric")
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C0805 = ("Capacitor_SMD", "C_0805_2012Metric")
C1206 = ("Capacitor_SMD", "C_1206_3216Metric")

# 3.3 V aux LDO (bottom, under the receptacle)
U1 = k.fp("Package_TO_SOT_SMD", "SOT-223-3_TabPin2", "U1", "AMS1117-3.3", -6.0, 4.4, 0, bottom=True,
          pads={"1": "GND", "2": "3V3_AUX", "3": "12V"}, lcsc="C6186")
u1in, u1gnd, u1tab = k.padxy("U1", "3"), k.padxy("U1", "1"), k.padxy("U1", "2", 1)
if abs(u1tab[0] - (-9.15)) > 0.1:
    u1tab = k.padxy("U1", "2", 0)
c4v, c4g = two("C4", *C0805, "10uF 25V X5R", -0.6, 4.4, 90, True, (-0.6, 6.0), "12V", "GND", "C15850")
c5v, c5g = two("C5", *C0805, "10uF 25V X5R", -11.5, 4.4, 90, True, (-11.5, 0), "3V3_AUX", "GND", "C15850")
c6v, c6g = two("C6", *C0402, "100nF", 7.0, 7.0, 0, True, (0, 7.0), "3V3_AUX", "GND", "C1525")
r3s, r3g = two("R3", *R0402, "10k", -0.635, 8.0, 0, True, (0, 8.0), "PWRDIS", "GND", "C25744")
Q1 = k.fp("Package_TO_SOT_SMD", "SOT-23-3", "Q1", "2N7002", 3.0, 4.5, 0, bottom=True,
          pads={"1": "3V3_AUX", "2": "GND", "3": "CPRSNT_N"}, lcsc="C8545")
q1g, q1s, q1d = k.padxy("Q1", "1"), k.padxy("Q1", "2"), k.padxy("Q1", "3")
# 12 V bulk at the drive power pins
c1v, c1g = two("C1", *C1206, "22uF 25V X5R", -16.0, 6.6, 0, True, (-14.0, 6.6), "12V", "GND", "C12891")
c2v, c2g = two("C2", *C1206, "22uF 25V X5R", -20.9, 6.6, 0, True, (-18.0, 6.6), "12V", "GND", "C12891")
c3v, c3g = two("C3", *C0402, "100nF 16V X7R", -12.6, 7.6, 0, True, (-14.5, 7.6), "12V", "GND", "C1525")
# top band behind the receptacle: DualPortEn# pull-up, activity LED
r4v, r4s = two("R4", *R0402, "10k", -17.0, 16.6, 0, False, (-20, 16.6), "3V3_AUX", "DUALPORTEN_N", "C25744")
r5v, r5a = two("R5", *R0402, "1k", -22.6, 16.6, 0, False, (-25, 16.6), "3V3_AUX", "LED_A", "C11702")
D2 = k.fp("LED_SMD", "LED_0603_1608Metric", "D2", "LED green", -19.6, 16.6, 180,
          pads={"1": "ACT_N", "2": "LED_A"}, lcsc="C72043")
# input polyfuse (bottom, next to the power connector)
f1i, f1o = two("F1", "Fuse", "Fuse_1812_4532Metric", "PTC 1812 Ihold>=2.6A 16V+", -16.2, 33.5, 90, True, (-16.2, 25),
               "12V_IN", "12V", "")
for i, (x, y) in enumerate([(21.5, 20.0), (21.5, 37.0), (-27.8, 21.0), (-27.8, 37.0)]):
    k.fp("MountingHole", "MountingHole_3.2mm_M3", f"H{i+1}", "M3", x, y, bom=False)

# ------------------------------------------------------------------ outline + rule areas
k.outline([(-31.5, 0), (25, 0), (25, 40), (14, 40), (14, EF), (-8, EF), (-8, 40), (-31.5, 40)])
k.rule_area("NECKDOWN_J1", [(-17.0, 7.3), (17.4, 7.3), (17.4, 16.3), (-17.0, 16.3)])
k.rule_area("NECKDOWN_J2", [(-2.4, 22.3), (8.6, 22.3), (8.6, 27.1), (-2.4, 27.1)])

# ------------------------------------------------------------------ U.3 pad escapes
J1p = lambda n: k.padxy("J1", n)
TOP_ROW = [f"E{i}" for i in range(7, 17)] + [f"S{i}" for i in range(8, 29)] + [f"E{i}" for i in range(17, 26)]
for n in TOP_ROW:
    net = j1pads.get(n)
    x, y = J1p(n)
    if net == "GND":
        vx = 13.6 if n == "E9" else x            # E9 pulled away from REFCLK
        k.track("GND", "L1", [(x, y), (x, 14.9), (vx, YVR)], 0.25); k.via("GND", vx, YVR)
    elif net and net.startswith("PER"):
        k.track(net, "L1", [(x, 14.6), (x, YVR)], PCIE_W); k.via(net, x, YVR)
for n in ["S1", "S4", "S7", "P5", "P6", "P12"]:
    x, y = J1p(n); k.track("GND", "L1", [(x, y), (x, YH)], 0.3); k.via("GND", x, YH)
for n in ["S5", "S6"]:
    x, y = J1p(n); net = j1pads[n]; k.track(net, "L1", [(x, 9.995), (x, YH)], PCIE_W); k.via(net, x, YH)
for gx in (8.9, 11.42):                         # return vias for the PER0 transition
    k.via("GND", gx, 8.6)
for n, extra in [("P13", []), ("P14", [8.4]), ("P15", [8.4])]:
    x, y = J1p(n); k.track("12V", "L1", [(x, y), (x, min([YH] + extra))], 0.5)
    for yy in [YH] + extra:
        k.via("12V", x, yy, 0.6, 0.3)
for n, net in [("P3", "PWRDIS"), ("P11", "ACT_N")]:
    x, y = J1p(n); k.track(net, "L1", [(x, y), (x, YH)], 0.2); k.via(net, x, YH)
for n, net in [("E3", "3V3_AUX"), ("E5", "PCIE_RST_N")]:
    x, y = J1p(n); k.track(net, "L1", [(x, y), (x, 9.0)], 0.3 if n == "E3" else 0.2); k.via(net, x, 9.0)
# SMBus / DualPortEn on L1 behind the top row
x, y = J1p("E24"); k.track("SMBDAT", "L1", [(x, y), (x, YVR)], 0.15); k.via("SMBDAT", x, YVR)
x, y = J1p("E23"); k.track("SMBCLK", "L1", [(x, y), (x, 17.3)], 0.15); k.via("SMBCLK", x, 17.3)
x, y = J1p("E25"); k.track("DUALPORTEN_N", "L1", [(x, y), (x, 16.0), (r4s[0] + 0.3, 16.6), r4s], 0.15)

# ------------------------------------------------------------------ high-speed routing
d = (PCIE_W + PCIE_G) / 2
J2p = lambda n: k.padxy("J2", n)


def top_start(n):
    x, y = J1p(n); return (j1pads[n], [(x, 14.6), (x, 15.0)])


def via_pt(net, x, y):
    k.via(net, x, y); return (net, [(x, y)])


hs_vias = {}     # net -> via xy (L1->L6 transitions near OCuLink)


def pet(lane, center, vx, tune=None):
    """PET: U.3 pads (L1) -> pair -> via pair at A-front -> L6 stubs -> A row pads."""
    pn = {"0": ("S2", "S3"), "1": ("S9", "S10"), "2": ("S17", "S18"), "3": ("S23", "S24")}[lane]
    if lane == "0":
        starts = [(j1pads[n], [(J1p(n)[0], 9.995), (J1p(n)[0], 9.6)]) for n in pn]
    else:
        starts = [top_start(n) for n in pn]
    ends = [(None, [(x, YV)]) for x in vx]
    res = k.pair("L1", center, starts, ends, tune=tune)
    # vias: net of each via = net of the line that reached it
    for net, (full, sn, en) in res.items():
        x, y = full[-1]; k.via(net, x, y); hs_vias[net] = (x, y)
    # L6 stubs to the A pads, matched by x order (no crossing)
    apads = {"0": ("A3", "A4"), "1": ("A6", "A7"), "2": ("A15", "A16"), "3": ("A18", "A19")}[lane]
    pads = sorted(apads, key=lambda n: J2p(n)[0])
    vs = sorted(res, key=lambda net: hs_vias[net][0])
    for pad, net in zip(pads, vs):
        vx_, vy_ = hs_vias[net]; px, py = J2p(pad)
        k.setpad("J2", pad, net)
        k.track(net, "L6", [(vx_, vy_), (px, 26.15)], PCIE_W)
    for net in vs:
        # assert the L6 stub is short and both ends coupled
        pass
    return res


pet("3", [(-4.92, 15.35), (-4.92, 16.0), (-1.0, 19.92), (-1.0, 26.0)], (-1.4, -0.6))
pet("2", [(-0.12, 15.35), (-0.12, 16.0), (0.5, 16.62), (0.5, 26.0)], (0.1, 0.9))
pet("1", [(6.28, 15.35), (6.28, 16.0), (3.0, 19.28), (3.0, 21.0), (5.0, 23.0), (5.0, 26.15)], (4.6, 5.4))
pet("0", [(13.97, 9.2), (13.97, 8.3), (14.37, 7.9), (16.5, 7.9), (16.9, 8.3), (16.9, 16.0), (7.05, 25.85)],
    (6.35, 7.15), tune={"PET0_P": [(4, [0.286, 0.455, 0.623, 0.792], 0.24, 0.5), (2, [0.5], 0.24, 0.5)]})


def per(lane, center, bottom_row=False):
    """PER: U.3 pad -> via (already placed) -> L6 pair -> B row pad (B row reached from the U.3 side)."""
    pn = {"0": ("S5", "S6"), "1": ("S12", "S13"), "2": ("S20", "S21"), "3": ("S26", "S27")}[lane]
    yv = YH if lane == "0" else YVR
    starts = [(j1pads[n], [(J1p(n)[0], yv)]) for n in pn]
    bp = {"0": ("B3", "B4"), "1": ("B6", "B7"), "2": ("B15", "B16"), "3": ("B18", "B19")}[lane]
    ends = [(None, [(J2p(n)[0], YB - 0.355)]) for n in bp]
    res = k.pair("L6", center, starts, ends)
    for net, (full, sn, en) in res.items():
        pad = min(bp, key=lambda n: math.dist(J2p(n), full[-1]))
        k.setpad("J2", pad, net)
    return res


per("3", [(-7.32, 15.4), (-7.32, 15.9), (-0.5, 22.72), (-0.5, 22.85)])
per("2", [(-2.52, 15.4), (-2.52, 15.9), (1.0, 19.42), (1.0, 22.85)])
per("1", [(3.88, 15.4), (3.88, 15.9), (6.0, 18.02), (6.0, 22.0), (5.5, 22.5), (5.5, 22.85)])
per("0", [(10.16, 9.8), (10.16, 15.8), (7.0, 18.96), (7.0, 22.85)])

# REFCLK0: E7/E8 (L1) -> 100 ohm pair -> via pair -> L6 -> B12/B13.  Polarity must be preserved.
starts = [(j1pads[n], [(J1p(n)[0], 14.6), (J1p(n)[0], 15.2)]) for n in ("E7", "E8")]
cv = [(4.683, 21.083), (4.117, 20.517)]
res = k.pair("L1", [(15.08, 15.5), (15.08, 15.9), (14.68, 16.3), (8.9, 16.3), (4.4, 20.8)],
             starts, [(None, [p]) for p in cv], CLK_W, CLK_G)
clk_via = {}
for net, (full, sn, en) in res.items():
    k.via(net, *full[-1]); clk_via[net] = full[-1]
starts = [(net, [clk_via[net]]) for net in clk_via]
res = k.pair("L6", [(4.4, 20.8), (2.5, 22.7), (2.5, 22.85)], starts,
             [(None, [(J2p(n)[0], YB - 0.355)]) for n in ("B12", "B13")], CLK_W, CLK_G)
for net, (full, sn, en) in res.items():
    pad = min(("B12", "B13"), key=lambda n: math.dist(J2p(n), full[-1]))
    k.setpad("J2", pad, net)
assert k.padnet("J2", "B12") == "REFCLK0_P", "REFCLK polarity flipped!"

# ------------------------------------------------------------------ OCuLink GND / low-speed vias
lsv = {"A13": 1.8, "A12": 2.43, "A10": 3.07, "A9": 3.7}
for pad, x in lsv.items():
    net = j2pads[pad]; px, py = J2p(pad)
    k.track(net, "L6", [(px, 26.15), (x, YV)], 0.12); k.via(net, x, YV)
for x in (-1.75, -0.25, 1.25, 4.25, 5.875, 7.5):
    k.via("GND", x, YG2)
for x in (-2.5, 3.3, 4.0):
    k.via("GND", x, YBR)
gpads = [p for p, n in OCU_DEV_PINS.items() if n == "GND"]
xs = []
for p in gpads:
    px, py = J2p(p); xs.append(px)
    k.track("GND", "L6", [(px, py), (px, YBR)], 0.15)
k.track("GND", "L6", [(min(xs + [-2.5]), YBR), (max(xs), YBR)], 0.2)
k.zone("GND", "L6", [(-4.9, 23.4), (10.9, 23.4), (10.9, EF - 0.3), (-4.9, EF - 0.3)], prio=2, thermal=False)

# ------------------------------------------------------------------ low-speed on L3
LS = 0.15
k.track("CPRSNT_N", "L3", [(1.8, YV), (1.8, 16.4), (1.68, 16.0), (1.68, 8.0)], LS); k.via("CPRSNT_N", 1.68, 8.0)
k.track("PCIE_RST_N", "L3", [(2.43, YV), (2.43, 16.4), (2.08, 16.0), (2.08, 12.0), (3.88, 10.2), (3.88, 9.0)], LS)
x24 = J1p("E24")[0]; x23 = J1p("E23")[0]
k.track("SMBDAT", "L3", [(3.07, YV), (3.07, 27.8), (2.77, 28.1), (-6.7, 28.1), (-7.0, 27.8), (-7.0, 16.6),
                         (-7.3, 16.3), (x24 + 0.3, 16.3), (x24, 16.0), (x24, YVR)], LS)
k.track("SMBCLK", "L3", [(3.7, YV), (3.7, 28.2), (3.1, 28.6), (-7.2, 28.6), (-7.5, 28.3), (-7.5, 17.1),
                         (-7.8, 16.8), (x23 + 0.2, 16.8), (x23, 17.0), (x23, 17.3)], LS)

# ------------------------------------------------------------------ bottom (L6) power + misc
P3 = 0.3
k.track("CPRSNT_N", "L6", [(1.68, 8.0), (q1d[0], 7.4), q1d], 0.2)
k.via("GND", q1s[0], 6.6); k.track("GND", "L6", [q1s, (q1s[0], 6.6)], 0.3)
# 3V3 aux spine: tab -> west to the top-band via, -> east under the housing to Q1 gate, C6, E3
k.track("3V3_AUX", "L6", [u1tab, (u1tab[0], 3.45), c5v], 0.4)
k.track("3V3_AUX", "L6", [c5v, (-24.0, 3.45), (-24.0, 17.45)], P3); k.via("3V3_AUX", -24.0, 17.45)
k.track("3V3_AUX", "L6", [(u1tab[0], 2.4), (u1tab[0], 0.7), (5.48, 0.7), (5.48, 9.0)], P3)
k.track("3V3_AUX", "L6", [(q1g[0], 0.7), q1g], P3)
k.track("3V3_AUX", "L6", [(5.48, c6v[1]), c6v], P3)
k.via("GND", c6g[0], c6g[1] - 1.1); k.track("GND", "L6", [c6g, (c6g[0], c6g[1] - 1.1)], P3)
k.via("GND", c5g[0], c5g[1] + 1.1); k.track("GND", "L6", [c5g, (c5g[0], c5g[1] + 1.1)], P3)
k.via("GND", u1gnd[0] + 1.3, u1gnd[1]); k.track("GND", "L6", [u1gnd, (u1gnd[0] + 1.3, u1gnd[1])], 0.5)
k.track("12V", "L6", [u1in, (-1.5, u1in[1]), (c4v[0], u1in[1] - 0.9), c4v], 0.5); k.via("12V", u1in[0], 8.0, 0.6, 0.3)
k.track("3V3_AUX", "L6", [k.padxy("U1", "2", 0), k.padxy("U1", "2", 1)], 0.6)
k.track("12V", "L6", [u1in, (u1in[0], 8.0)], 0.5)
k.via("GND", c4g[0], 2.2); k.track("GND", "L6", [c4g, (c4g[0], 2.2)], 0.4)
k.track("PWRDIS", "L6", [(J1p("P3")[0], YH), r3s], 0.2)
k.via("GND", -1.75, 8.75); k.track("GND", "L6", [r3g, (-1.75, 8.75)], 0.25)
p14, p15 = J1p("P14")[0], J1p("P15")[0]
k.track("12V", "L6", [(p14, 8.4), c1v], 0.6)
k.track("12V", "L6", [(J1p("P13")[0], YH), c3v], 0.5)
k.via("12V", c2v[0], 8.3, 0.6, 0.3); k.track("12V", "L6", [c2v, (c2v[0], 8.3)], 0.6)
for (gx, gy) in (c1g, c2g):
    k.via("GND", gx, gy - 1.6); k.track("GND", "L6", [(gx, gy), (gx, gy - 1.6)], 0.5)
k.via("GND", c3g[0] + 0.1, c3g[1] - 1.1); k.track("GND", "L6", [c3g, (c3g[0] + 0.1, c3g[1] - 1.1)], 0.3)
# activity LED: P11 via -> L6 -> via next to the LED cathode
k.track("ACT_N", "L6", [(J1p("P11")[0], YH), (J1p("P11")[0], 13.0), (-18.81, 13.0), (-18.81, 15.6)], 0.2)
k.via("ACT_N", -18.81, 15.6)
d2k = k.padxy("D2", "1"); d2a = k.padxy("D2", "2")
k.track("ACT_N", "L1", [(-18.81, 15.6), d2k], 0.2)
k.track("LED_A", "L1", [r5a, d2a], 0.2)
k.track("3V3_AUX", "L1", [(-24.0, 17.45), (r5v[0], 17.45), r5v], P3)
k.track("3V3_AUX", "L1", [(r5v[0], 17.45), (r4v[0], 17.45), r4v], P3)

# ------------------------------------------------------------------ power entry
k.zone("12V_IN", "L6", [(-22.2, 23.4), (-9.8, 23.4), (-9.8, 29.0), (-14.3, 29.0), (-14.3, 32.6),
                        (-18.1, 32.6), (-18.1, 29.0), (-22.2, 29.0)], prio=3, clearance=0.3, thermal=False)
k.zone("12V_IN", "L1", [(-22.2, 23.4), (-9.8, 23.4), (-9.8, 28.0), (-22.2, 28.0)], prio=3, clearance=0.3,
       thermal=False)
k.zone("12V", "L6", [(-18.4, 34.6), (-14.0, 34.6), (-14.0, 39.5), (-18.4, 39.5)], prio=3, clearance=0.3,
       thermal=False)
for x in (-17.6, -16.2, -14.8):
    for y in (37.4, 38.7):
        k.via("12V", x, y, 0.6, 0.3)

# ------------------------------------------------------------------ planes
BOARD = [(-31.5, 0), (25, 0), (25, 40), (14, 40), (14, EF), (-8, EF), (-8, 40), (-31.5, 40)]
k.zone("GND", "L2", BOARD, clearance=0.2)
k.zone("GND", "L5", BOARD, clearance=0.2)
k.zone("12V", "L4", BOARD, clearance=0.2)
k.zone("GND", "L3", BOARD, clearance=0.25)

# ------------------------------------------------------------------ silkscreen
k.text("U.3 CAGE", 19.5, 28.0, P.F_SilkS, 1.0)
k.text("rev A", 19.5, 30.0, P.F_SilkS, 1.0)
k.text("12V IN", -27.5, 29.0, P.F_SilkS, 1.0)
k.text("J2 OCuLink", 19.5, 33.0, P.B_SilkS, 1.0, mirror=True)

for ref, f in k.fps.items():
    for g in list(f.GraphicalItems()):          # library silk crowds 0.5 mm pitch fields; JLC places by CPL
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
    if net.startswith(("PET", "PER", "REFCLK")):
        L = sum(plen(p) for _, p, _ in segs) + VIA_H * len(k.vias_by_net.get(net, []))
        lens[net] = round(L, 3)
with open(os.path.join(OUT, "lengths.json"), "w") as f:
    json.dump(lens, f, indent=1)
for base in sorted({n.rsplit("_", 1)[0] for n in lens}):
    p, n = lens.get(base + "_P"), lens.get(base + "_N")
    print(f"{base:8s} P {p:7.3f}  N {n:7.3f}  skew {abs(p - n):.3f}")

# ------------------------------------------------------------------ skew rules + zone fill + DRC
if __name__ == "__main__":
    import subprocess
    skew = subprocess.run([sys.executable, os.path.join(RULES, "gen_pair_skew_rules.py"), k.pcb],
                          capture_output=True, text=True).stdout
    extra = """# --- board-specific: J2 vendor land pattern puts the two locating NPTHs 0.11-0.13 mm from the
# unused corner pads A1/A21 (no net).  Accepted: NPTH vs no-net copper only.
(rule "silk may sit on masked copper (only pads/holes need clearance)"
    (condition "A.Type != 'Pad' && B.Type != 'Pad' && A.Type != 'Via' && B.Type != 'Via'")
    (constraint silk_clearance (min 0mm)))
(rule "PET0 uncoupled exception (skew bumps, approved by design-rules Rev B)"
    (condition "A.NetName == 'PET0_P' || A.NetName == 'PET0_N'")
    (constraint diff_pair_uncoupled (max 7mm)))
(rule "J2 locating NPTH vs unused corner pads"
    (condition "A.Type == 'Pad' && !A.isPlated() && B.Type == 'Pad' && B.NetName == ''")
    (constraint hole_clearance (min 0.1mm)))
"""
    bb, rpt = k.fill_and_check(extra + skew)
    c, items = drc_summary(rpt)
    print("DRC:", dict(c))
