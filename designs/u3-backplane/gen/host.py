"""Host card for the cabled U.3 backplane: PCIe x16 edge (x4x4x4x4 bifurcation) -> two SlimSAS 8i (SFF-9402).

Card frame (same as the x16 U.3 card): x right from the bracket-side edge, y down, y = 0 at the finger edge.
  * J1 = CEM x16 fingers.  Side B (F.Cu) carries PET, side A (B.Cu) carries PER and REFCLK.
  * J2 / J3 = Amphenol U10A474240T on the BOTTOM side at the top edge, mating face flush with the edge.  Bottom
    mounting puts pin 1 on the left, so the lane order of the fingers and of the connectors is the same.
    J2 = lanes 0-7, J3 = lanes 8-15.  Host connector: row B = PET + 2W + PERST# + CPRSNT#, row A = PER + REFCLK +
    BP_TYPE + CWAKE# (SFF-9402 Table 6-2, see ../docs/reference-data.md).
  * PET: L1 from the finger to a via pair, then L6 straight into row B (1 via).
    PER: L6 from the finger to a via pair, L1 over both pad rows, via pair beyond row A, short L6 stub (2 vias).
  * REFCLK: finger A13/A14 -> L6 -> via -> 9DBL0442 1:4 buffer (top side, bypass mode) -> four L1 pairs along the
    strip above the connectors -> via pair beyond row A -> pads 11/12 and 29/30.  Every pair is skew matched by
    where its far vias sit.
  * Low speed (L3, maze router): TCA9546A SMBus switch (0x77, one channel per x4 port), TCA9554 (0x27) reading
    CPRSNT# and BP_TYPE of the four ports, PERST# through 33R per port, CWAKE# wire-OR to WAKE#.
Stackup JLC06161H-3313: L1 HS | L2 GND | L3 low speed + GND | L4 3V3 | L5 GND | L6 HS.
"""
import os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew as P
import pcbkit
from pcbkit import Kit, PCIE_W, PCIE_G, CLK_W, CLK_G, plen
from router import Router
import fplib

HERE = os.path.dirname(os.path.abspath(__file__))
VAR = os.environ.get("VARIANT", "passive")
OUT = os.environ.get("OUTDIR") or os.path.join(HERE, "..", "boards", f"host_{VAR}")
NAME = f"u3_host_{VAR}"
STAGE = os.environ.get("STAGE", "all")

FX, XF, XR, YTOP = 45.65, 129.3, 131.0, -44.0
XCN = [77.6, 112.2]                 # connector centres
YP = YTOP + 10.30                   # peg line
YA, YB = YP + 2.70, YP + 5.05       # row A (nearer the mating face) and row B
YV1, YV2, YD = -8.6, -10.2, -11.8   # PET via row, PER via row, start of the diagonals
LP = {0: (2, 3), 1: (5, 6), 2: (14, 15), 3: (17, 18), 4: (20, 21), 5: (23, 24), 6: (32, 33), 7: (35, 36)}
SSG = [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37]
LSW = 0.15
R0402 = ("Resistor_SMD", "R_0402_1005Metric")
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C0805 = ("Capacitor_SMD", "C_0805_2012Metric")
RN = ("Resistor_SMD", "R_Array_Convex_4x0603")
LC = {"10k": "C25744", "100nF": "C1525", "10uF": "C15850", "4.7k x4": "C1980", "33R x4": "", "0R": "C17168",
      "FB": "C19330"}

# ---------------------------------------------------------------- CEM x16 edge (side B = F.Cu, side A = B.Cu)
GND_B = sorted(set([4, 7, 13, 16, 18, 21, 22, 25, 26, 29, 32, 35, 36, 39, 40, 43, 44, 47, 49] +
                   [n for i in range(8) for n in (52 + 4 * i, 53 + 4 * i)][:-1] + [80]) - {81})
WAKE_V = []
GND_A = [4, 12, 15, 18, 20, 23, 24, 27, 28, 31, 34, 37, 38, 41, 42, 45, 46, 49, 51] + \
        [n for i in range(7) for n in (54 + 4 * i, 55 + 4 * i)] + [82]
fing = {f"B{n}": "GND" for n in GND_B}
fing.update({f"A{n}": "GND" for n in GND_A})
fing.update({"B8": "3V3", "A9": "3V3", "A10": "3V3", "A11": "PCIE_RST_N", "A1": "PRSNT_N", "B81": "PRSNT_N",
             "A13": "REFCLK_IN_P", "A14": "REFCLK_IN_N", "B5": "SMCLK", "B6": "SMDAT", "B11": "PCIE_WAKE_N",
             "B12": "CLKREQ_N"})
PET_PINS = {0: (14, 15), 1: (19, 20), 2: (23, 24), 3: (27, 28), 4: (33, 34), 5: (37, 38), 6: (41, 42), 7: (45, 46)}
PER_PINS = {0: (16, 17), 1: (21, 22), 2: (25, 26), 3: (29, 30), 4: (35, 36), 5: (39, 40), 6: (43, 44), 7: (47, 48)}
for ln in range(8, 16):
    PET_PINS[ln] = (50 + 4 * (ln - 8), 51 + 4 * (ln - 8))
    PER_PINS[ln] = (52 + 4 * (ln - 8), 53 + 4 * (ln - 8))
for ln, (p, n) in PET_PINS.items():
    fing[f"B{p}"], fing[f"B{n}"] = f"PET{ln}_P", f"PET{ln}_N"
for ln, (p, n) in PER_PINS.items():
    fing[f"A{p}"], fing[f"A{n}"] = f"PER{ln}_P", f"PER{ln}_N"

ROOT = {}                # net -> hand-laid via the router starts from
HS_LOG = []


def solve(fn):
    """fn(x, dry) -> signed skew of a pair whose geometry depends on x; find the x that zeroes it, then lay it."""
    x0, s0 = 0.0, fn(0.0, True)
    x = 0.0
    if abs(s0) > 0.004:
        x1 = 0.2 if s0 < 0 else -0.2
        s1 = fn(x1, True)
        for _ in range(14):
            if abs(s1) < 0.004:
                break
            x2 = x1 - s1 * (x1 - x0) / (s1 - s0)
            x0, s0, x1 = x1, s1, x2
            s1 = fn(x1, True)
        assert abs(s1) < 0.02, ("skew solve failed", s1)
        x = x1
    fn(x, False)
    return x


def two(k, ref, fp, val, x, y, rot, na, nb, near, lcsc="", bottom=False):
    k.fp(*fp, ref, val, x, y, rot, lcsc=lcsc, bottom=bottom)
    p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
    a, b_ = ("1", "2") if math.dist(p1, near) <= math.dist(p2, near) else ("2", "1")
    k.setpad(ref, a, na); k.setpad(ref, b_, nb)
    return k.padxy(ref, a), k.padxy(ref, b_)


def build():
    fplib.ss8()
    k = Kit(OUT, NAME)
    k.fp("Connector_PCBEdge", "BUS_PCIexpress_x16", "J1", "PCIe x16 edge", FX, -3.45, 0, pads=fing, bom=False)
    fpad = lambda n: k.padxy("J1", n)
    fx = lambda n: fpad(f"B{n}")[0]
    # ---------------- outline, finger rule areas, plane voids under the fingers
    arc = k.arc_pts((43.175, -10.925), 1.825, 180, 360)
    LEFT = [(0, -4.5), (15.0, -4.5), (15.0, -12.75), (33.35, -12.75), (33.35, -4.5), (41.35, -4.5)] + arc
    TOP = [(XR, -12.75), (XR, YTOP), (0, YTOP)]
    k.outline([(XF, -8.4), (XF, -12.75)] + TOP + LEFT + [(45.0, -8.4)], closed=False)
    board = LEFT + [(45.0, 0), (XF, 0), (XF, -12.75)] + TOP
    k.rule_area("FINGERS", [(44.9, 0.6), (XF + 0.1, 0.6), (XF + 0.1, -5.75), (44.9, -5.75)])
    for L in ("L2", "L3", "L4", "L5"):           # no plane copper under the fingers
        k.keepout(f"FINGER_VOID_{L}", [(44.8, 0.6), (XF + 0.2, 0.6), (XF + 0.2, -5.9), (44.8, -5.9)], [L])
    k.rule_area("NECKDOWN_FINGERS", [(44.9, 0.6), (XF + 0.1, 0.6), (XF + 0.1, -7.4), (44.9, -7.4)])
    for L in ("L2", "L4", "L5"):
        k.keepout(f"FINGER_VOID_{L}", [(44.8, 0.6), (XF + 0.2, 0.6), (XF + 0.2, -5.9), (44.8, -5.9)], [L])
    # ---------------- SlimSAS connectors (bottom side, mating face on the top edge)
    for c, xc in enumerate(XCN):
        jc = f"J{c + 2}"
        pads = {"SH": "GND"}
        for n in SSG:
            pads[f"A{n}"] = pads[f"B{n}"] = "GND"
        k.fp("u3adapter", fplib.SS8, jc, "U10A474240T", xc, YP, rot=0, bottom=True, pads=pads)
        assert abs(k.padxy(jc, "A1")[0] - (xc - 10.8)) < 1e-6 and abs(k.padxy(jc, "B1")[1] - YB) < 1e-6
        k.rule_area(f"NECKDOWN_{jc}", [(xc - 11.4, YA - 3.4), (xc + 11.4, YA - 3.4), (xc + 11.4, YB + 2.6),
                                       (xc - 11.4, YB + 2.6)])
        for n in SSG:
            a, b_ = k.padxy(jc, f"A{n}"), k.padxy(jc, f"B{n}")
            k.track("GND", "L6", [a, b_], 0.25); k.via("GND", a[0], (a[1] + b_[1]) / 2)

    def tail(layer, nets, starts, center, jc, pins, w, g, tag):
        """Pair on `layer` that ends on a via pair beyond row A and L6 stubs into the row A pads `pins` (left, right).
        The far vias slide along y until both lines are equally long."""
        pads = [(f"A{p}", k.padxy(jc, f"A{p}")) for p in pins]
        t = (pads[0][1][0] + pads[1][1][0]) / 2

        def fn(x, dry):
            vl, vr = (t - 0.45, YA - 1.0 - max(x, 0)), (t + 0.45, YA - 1.0 - max(-x, 0))
            res = k.pair(layer, center + [(t, YA - 0.5)], starts, [(None, [vl]), (None, [vr])], w, g, dry=dry)
            L = {}
            for net, (full, sn, en) in res.items():
                side = 0 if math.dist(full[-1], vl) < 1e-6 else 1
                vxy = (vl, vr)[side]; pname, pxy = pads[side]
                st = [vxy, (pxy[0], pxy[1] - 0.5)]
                L[side] = plen(full) + plen(st)
                if not dry:
                    k.via(net, *vxy); k.setpad(jc, pname, net); k.track(net, "L6", st, w)
                    if tag:
                        assert net.endswith("_P") == (side == 0), ("polarity", net, side)
            return L[0] - L[1]
        HS_LOG.append((tag or nets, round(solve(fn), 3)))

    # ---------------- lanes
    for ln in range(16):
        c, L = divmod(ln, 8); jc = f"J{c + 2}"
        tx = sum(k.padxy(jc, f"B{p}")[0] for p in LP[L]) / 2
        # PET: finger (L1) -> vias -> L6 -> row B
        p, n = PET_PINS[ln]; xf = (fx(p) + fx(n)) / 2
        np_, nn = f"PET{ln}_P", f"PET{ln}_N"
        yv, yd = (YV1, YD) if ln else (-11.8, -13.0)        # lane 0: vias north of the REFCLK input's west turn
        k.pair("L1", [(xf, -6.4), (xf, yv + 0.45)], [(np_, [(fx(p), -5.45)]), (nn, [(fx(n), -5.45)])],
               [(None, [(xf - 0.45, yv)]), (None, [(xf + 0.45, yv)])])
        k.via(np_, xf - 0.45, yv); k.via(nn, xf + 0.45, yv)
        dx = tx - xf
        cen = [(xf, yv - 0.45), (xf, yd), (tx, yd - abs(dx)), (tx, YB + 1.3)]
        res = k.pair("L6", cen, [(np_, [(xf - 0.45, yv)]), (nn, [(xf + 0.45, yv)])],
                     [(None, [(k.padxy(jc, f"B{q}")[0], YB + 0.58)]) for q in LP[L]])
        for net, (full, sn, en) in res.items():
            q = min(LP[L], key=lambda q: abs(k.padxy(jc, f"B{q}")[0] - full[-1][0]))
            assert (q == LP[L][0]) == net.endswith("_P"), ("polarity", net)
            k.setpad(jc, f"B{q}", net)
        # PER: finger (L6) -> vias -> L1 over the rows -> vias beyond row A -> L6 stub
        p, n = PER_PINS[ln]; xf = (fpad(f"A{p}")[0] + fpad(f"A{n}")[0]) / 2
        np_, nn = f"PER{ln}_P", f"PER{ln}_N"
        k.pair("L6", [(xf, -6.4), (xf, YV2 + 0.45)], [(np_, [(fpad(f"A{p}")[0], -5.45)]), (nn, [(fpad(f"A{n}")[0], -5.45)])],
               [(None, [(xf - 0.45, YV2)]), (None, [(xf + 0.45, YV2)])])
        k.via(np_, xf - 0.45, YV2); k.via(nn, xf + 0.45, YV2)
        dx = tx - xf
        cen = [(xf, YV2 - 0.45), (xf, YD), (tx, YD - abs(dx))]
        tail("L1", None, [(np_, [(xf - 0.45, YV2)]), (nn, [(xf + 0.45, YV2)])], cen, jc, LP[L], PCIE_W, PCIE_G, f"PER{ln}")
    # ---------------- finger GND vias: one via between the lane pairs, joined to the GND fingers of both sides
    def finger_gnd(m, x=None, y=-6.75):
        lo, hi = math.floor(m), math.ceil(m)
        x = x if x is not None else (fx(lo) + fx(hi)) / 2
        k.via("GND", x, y)
        for side, L in (("B", "L1"), ("A", "L6")):
            for n in sorted({lo, hi}):
                if fing.get(f"{side}{n}") == "GND":
                    k.track("GND", L, [(fx(n), -5.4), (fx(n), -5.9), (x, y)], 0.3)

    for m in (15.5, 18, 20.5, 22.5, 24.5, 26.5, 28.5, 31.5, 34.5, 36.5, 38.5, 40.5, 42.5, 44.5, 46.5, 4, 7):
        finger_gnd(m)
    for m in range(51, 80, 2):                   # lanes 8-15: one via between every two pairs
        finger_gnd(m + 0.5)
    finger_gnd(81.5, x=fx(82), y=-7.6)           # A82, clear of PRSNT2# (B81)
    finger_gnd(12.5, x=fx(12) + 0.4)             # keep off REFCLK_IN
    finger_gnd(49, y=-6.85)
    # WAKE# (B11): stub out of the finger zone to a via, the router continues from there
    xw = fx(11)
    k.track("PCIE_WAKE_N", "L1", [(xw, -5.3), (xw, -7.9)], 0.2); k.via("PCIE_WAKE_N", xw, -7.9)
    WAKE_V.append((xw, -7.9))
    # ---------------- REFCLK buffer (top side, rotated so CLK_IN faces the fingers)
    UX, UY = 50.0, -28.0
    pads = {"8": "GND", "33": "GND", "4": "3V3_A", "21": "3V3_A", "11": "3V3", "15": "3V3", "25": "3V3", "9": "3V3",
            "10": "3V3", "31": "3V3", "5": "REFCLK_IN_P", "6": "REFCLK_IN_N", "12": "GND", "19": "GND", "24": "GND",
            "29": "GND"}
    DIF = {0: (13, 14), 1: (17, 18), 2: (22, 23), 3: (27, 28)}
    DEST = {0: (0, (11, 12)), 1: (0, (29, 30)), 2: (1, (11, 12)), 3: (1, (29, 30))}     # output -> (connector, pins)
    for i, (a, b_) in DIF.items():
        pads[str(a)], pads[str(b_)] = f"REFCLK{i}_P", f"REFCLK{i}_N"
    k.fp("Package_DFN_QFN", "VQFN-32-1EP_5x5mm_P0.5mm_EP3.15x3.15mm", "U1", "9DBL0442BKILF", UX, UY, 90, pads=pads,
         lcsc="C1540554")
    U = lambda n: k.padxy("U1", str(n))
    assert U(5)[1] > UY + 2 and U(5)[0] < U(6)[0] and U(13)[0] > UX + 2 and U(13)[1] > U(14)[1], "buffer orientation"
    k.rule_area("NECKDOWN_U1", [(UX - 4.1, UY - 4.1), (UX + 4.1, UY - 4.1), (UX + 4.1, UY + 4.6), (UX - 4.1, UY + 4.6)])
    for i in (-1, 1):
        for j in (-1, 1):
            k.via("GND", UX + 0.9 * i, UY + 0.9 * j)
    # 0.5 mm pitch pins are wired by hand: GND pins run into the exposed pad, supply pins get a stub and a via
    for p in (8, 12, 19, 24, 29):
        x, y = U(p)
        if abs(y - UY) > 2:
            sy = -math.copysign(1, y - UY); pts = [(x, y), (x, y + sy * 0.55)]
            pts = pts + [(x - math.copysign(0.4, x - UX), y + sy * 0.95)] if abs(x - UX) > 1.35 else [(x, y), (x, UY - sy * 1.2)]
        else:
            sx = -math.copysign(1, x - UX); pts = [(x, y), (x + sx * 0.55, y)]
            pts = pts + [(x + sx * 0.95, y - math.copysign(0.4, y - UY))] if abs(y - UY) > 1.35 else [(x, y), (UX - sx * 1.2, y)]
        k.track("GND", "L1", pts, 0.2)
    sv = {}
    for p in (11, 15, 25, 31, 21):
        x, y = U(p)
        v = (x, y + math.copysign(1.0, y - UY)) if abs(y - UY) > 2 else (x + math.copysign(1.0, x - UX), y)
        net = k.padnet("U1", str(p)); k.track(net, "L1", [(x, y), v], 0.2); k.via(net, *v); sv[p] = v
    x9, x10, x11 = U(9), U(10), U(11)
    k.track("3V3", "L1", [x9, (x9[0] + 0.7, x9[1]), (x11[0] + 0.7, x11[1])], 0.2)
    k.track("3V3", "L1", [x10, (x10[0] + 0.7, x10[1])], 0.2)
    x4 = U(4); sv[4] = (x4[0] - 0.9, x4[1] + 1.3)
    k.track("3V3_A", "L1", [x4, (x4[0], x4[1] + 0.75), sv[4]], 0.2); k.via("3V3_A", *sv[4])
    info_sv = sv
    # input: A13/A14 on L6 west along y -7.9, north under the buffer's south face, vias, L1 into pins 5/6
    x13, x14 = fpad("A13")[0], fpad("A14")[0]
    xin = (x13 + x14) / 2; xi = (U(5)[0] + U(6)[0]) / 2; yv = U(5)[1] + 1.3
    k.pair("L6", [(xin, -6.4), (xin, -9.7), (xin - 0.6, -10.3), (xi + 0.6, -10.3), (xi, -10.9), (xi, yv + 0.5)],
           [("REFCLK_IN_P", [(x13, -5.45)]), ("REFCLK_IN_N", [(x14, -5.45)])],
           [(None, [(xi - 0.45, yv)]), (None, [(xi + 0.45, yv)])], CLK_W, CLK_G)
    for net, vx, pin in (("REFCLK_IN_P", xi - 0.45, 5), ("REFCLK_IN_N", xi + 0.45, 6)):
        k.via(net, vx, yv); k.track(net, "L1", [(vx, yv), (U(pin)[0], yv - 0.5), U(pin)], CLK_W)
    # outputs: columns next to the buffer, channels in the strip above the connectors, drop to the far vias
    CH = {0: -35.4, 1: -36.6, 2: -40.35, 3: -43.2}
    for i, (a, b_) in DIF.items():
        c, pins = DEST[i]; jc = f"J{c + 2}"
        t = (k.padxy(jc, f"A{pins[0]}")[0] + k.padxy(jc, f"A{pins[1]}")[0]) / 2
        pa, pb = U(a), U(b_); m = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
        ch = CH[i]; r = 0.6
        if i == 0:                                   # east face
            cen = [(m[0] + 0.7, m[1]), (UX + 4.6 - r, m[1]), (UX + 4.6, m[1] - r), (UX + 4.6, ch + r), (UX + 4.6 + r, ch)]
        elif i in (1, 2):                            # north face
            cen = [(m[0], m[1] - 0.7), (m[0], ch + r), (m[0] + r, ch)]
        else:                                        # west face
            cen = [(m[0] - 0.7, m[1]), (UX - 4.6 + r, m[1]), (UX - 4.6, m[1] - r), (UX - 4.6, ch + r), (UX - 4.6 + r, ch)]
        cen += [(t - r, ch), (t, ch + r)]
        tail("L1", None, [(f"REFCLK{i}_P", [pa]), (f"REFCLK{i}_N", [pb])], cen, jc, pins, CLK_W, CLK_G, f"REFCLK{i}")
    # ---------------- sideband pins of the four ports: stubs + vias (the router continues on L3)
    port = {}
    for pt in range(4):
        c, hb = divmod(pt, 2); jc = f"J{c + 2}"; base = 18 * hb
        nets = {"B8": f"P{pt}_SCL", "B9": f"P{pt}_SDA", "B11": f"P{pt}_PERST_N", "B12": f"P{pt}_CPRSNT_N",
                "A8": f"P{pt}_BPTYPE", "A9": "PCIE_WAKE_N"}
        port[pt] = {}
        for pin, net in nets.items():
            row, o = pin[0], int(pin[1:]); name = f"{row}{base + o}"
            x, y = k.padxy(jc, name); k.setpad(jc, name, net)
            far = o in (9, 12)
            vy = (YB + (2.1 if far else 1.4)) if row == "B" else (YA - (1.75 if far else 1.0))
            k.track(net, "L6", [(x, y), (x, vy)], LSW); k.via(net, x, vy)
            port[pt][pin] = (x, vy)
    # ---------------- card logic (top side, left of the lanes)
    info = {}
    k.fp("Package_SO", "TSSOP-16_4.4x5mm_P0.65mm", "U2", "TCA9546APWR", 27.0, -21.0, 0, pads={
        "1": "3V3", "2": "3V3", "13": "3V3", "3": "PCIE_RST_N", "8": "GND", "14": "SMCLK", "15": "SMDAT", "16": "3V3",
        "4": "P0_SDA", "5": "P0_SCL", "6": "P1_SDA", "7": "P1_SCL", "9": "P2_SDA", "10": "P2_SCL", "11": "P3_SDA",
        "12": "P3_SCL"}, lcsc="")
    ex = {"1": "3V3", "2": "3V3", "3": "3V3", "8": "GND", "14": "SMCLK", "15": "SMDAT", "16": "3V3"}
    for pt in range(4):
        ex[str(4 + pt)] = f"P{pt}_CPRSNT_N"; ex[str(9 + pt)] = f"P{pt}_BPTYPE"
    k.fp("Package_SO", "TSSOP-16_4.4x5mm_P0.65mm", "U3", "TCA9554PWR", 27.0, -35.0, 0, pads=ex, lcsc="")
    arr = []

    def array(ref, val, x, y, rot, pairs):
        k.fp(*RN, ref, val, x, y, rot, lcsc=LC[val])
        for i, (na, nb) in enumerate(pairs):
            k.setpad(ref, str(i + 1), na); k.setpad(ref, str(8 - i), nb)
            arr.append((ref, str(i + 1), na)); arr.append((ref, str(8 - i), nb))
    array("RN1", "4.7k x4", 35.0, -18.5, 0, [("P0_SDA", "3V3"), ("P0_SCL", "3V3"), ("P1_SDA", "3V3"), ("P1_SCL", "3V3")])
    array("RN2", "4.7k x4", 35.0, -23.5, 0, [("P2_SDA", "3V3"), ("P2_SCL", "3V3"), ("P3_SDA", "3V3"), ("P3_SCL", "3V3")])
    array("RN3", "33R x4", 40.0, -21.0, 0, [(f"P{pt}_PERST_N", "PCIE_RST_N") for pt in range(4)])
    caps = [two(k, "C1", C0402, "100nF", 21.5, -21.0, 90, "3V3", "GND", (21.5, -24), LC["100nF"]),
            two(k, "C2", C0402, "100nF", 21.5, -35.0, 90, "3V3", "GND", (21.5, -38), LC["100nF"]),
            two(k, "C3", C0805, "10uF 25V X5R", 40.0, -37.0, 0, "3V3", "GND", (38, -37), LC["10uF"]),
            two(k, "C4", C0402, "100nF", UX + 3.3, UY + 4.9, 0, "3V3", "GND", (UX, UY + 4.9), LC["100nF"]),
            two(k, "C5", C0402, "100nF", UX - 6.4, UY - 2.6, 90, "3V3", "GND", (UX - 6.4, UY), LC["100nF"])]
    acap = [two(k, "C6", C0402, "100nF", UX - 2.6, UY + 5.2, 0, "3V3_A", "GND", (UX, UY + 5.2), LC["100nF"]),
            two(k, "C7", C0805, "10uF 25V X5R", UX - 6.0, UY + 5.4, 0, "3V3_A", "GND", (UX, UY + 5.4), LC["10uF"])]
    fb = two(k, "FB1", ("Inductor_SMD", "L_0603_1608Metric"), "ferrite 600R@100MHz", UX - 6.0, UY + 7.6, 0, "3V3_A", "3V3",
             (UX, UY + 7.6), LC["FB"])
    rq = two(k, "R1", R0402, "0R", 44.5, -14.5, 0, "CLKREQ_N", "GND", (47, -14.5), LC["0R"])
    k.fp("MountingHole", "MountingHole_3.2mm_M3", "H1", "bracket", 7.5, -9.35, bom=False)
    info.update(sv=info_sv, port=port, arr=arr, caps=caps, acap=acap, fb=fb, rq=rq, board=board, fpad=fpad)
    return k, info


def route(k, info):
    R = Router(k)
    T = lambda ref, p: ("L6" if k.fps[ref].IsFlipped() else "L1", *k.padxy(ref, p))
    L3 = dict(layer_cost={"L1": 1.5, "L6": 1.5}, via_cost=1.0)
    PW = ("GND", "3V3")
    tasks = []
    add = lambda f, *a, **kw: tasks.append((f, a, kw))
    fpad = info["fpad"]
    # buffer: analog supply island, supplies, OE#
    add(R.route, "3V3_A", ("all", *info["sv"][4]), ("L1", *info["acap"][0][0]), w=0.2)
    add(R.route, "3V3_A", ("L1", *info["acap"][0][0]), ("L1", *info["acap"][1][0]), w=0.3)
    add(R.route, "3V3_A", ("L1", *info["acap"][1][0]), ("L1", *info["fb"][0]), w=0.3)
    add(R.to_net, "3V3_A", ("all", *info["sv"][21]), w=0.2, maxpad=24.0, **L3)
    for pa, pb in info["acap"]:
        add(R.to_via, "GND", ("L1", *pb))
    add(R.to_via, "3V3", ("L1", *info["fb"][1]), w=0.3)
    for ref in ("U2", "U3"):
        for p in k.fps[ref].Pads():
            if p.GetNetname() in PW:
                add(R.to_via, p.GetNetname(), T(ref, p.GetNumber()))
    for pa, pb in info["caps"]:
        add(R.to_via, "3V3", ("L1", *pa)); add(R.to_via, "GND", ("L1", *pb))
    for ref, p, net in info["arr"]:
        if net in PW:
            add(R.to_via, net, T(ref, p))
    add(R.to_via, "GND", ("L1", *info["rq"][1]))
    for n in ("B8",):
        add(R.to_via, "3V3", ("L1", fpad(n)[0], -5.3), w=0.4)
    for n in ("A9", "A10"):
        add(R.to_via, "3V3", ("L6", fpad(n)[0], -5.3), w=0.4)
    fails = R.run_tasks(tasks)
    print("stage 1 fails:", fails)
    tasks.clear()
    # signals
    add(R.route, "CLKREQ_N", ("L1", fpad("B12")[0], -5.3), ("L1", *info["rq"][0]), w=LSW)
    add(R.route, "SMCLK", ("L1", fpad("B5")[0], -5.3), T("U2", "14"), w=LSW)
    add(R.route, "SMDAT", ("L1", fpad("B6")[0], -5.3), T("U2", "15"), w=LSW)
    add(R.to_net, "SMCLK", T("U3", "14"), w=LSW, maxpad=32.0, **L3)
    add(R.to_net, "SMDAT", T("U3", "15"), w=LSW, maxpad=32.0, **L3)
    add(R.route, "PCIE_RST_N", ("L6", fpad("A11")[0], -5.3), T("U2", "3"), w=LSW, **L3)
    add(R.route, "PRSNT_N", ("L6", fpad("A1")[0], -5.0), ("L1", fpad("B81")[0], -5.0), w=LSW, **L3)
    for ref, p, net in info["arr"]:
        if net not in PW:
            add(R.to_net, net, T(ref, p), w=LSW, maxpad=48.0, **L3)
    for ref in ("U2", "U3"):
        for p in k.fps[ref].Pads():
            net = p.GetNetname()
            if net and net not in PW and net not in ("SMCLK", "SMDAT", "PCIE_RST_N"):
                add(R.to_net, net, T(ref, p.GetNumber()), w=LSW, maxpad=48.0, **L3)
    for pt in range(4):
        for pin, (x, y) in info["port"][pt].items():
            net = k.padnet(f"J{pt // 2 + 2}", f"{pin[0]}{18 * (pt % 2) + int(pin[1:])}")
            if net == "PCIE_WAKE_N":
                continue
            add(R.to_net, net, ("all", x, y), w=LSW, maxpad=110.0, **L3)
    wk = [info["port"][pt]["A9"] for pt in range(4)]
    add(R.route, "PCIE_WAKE_N", ("all", *WAKE_V[0]), ("all", *wk[0]), w=LSW, **L3)
    for a in wk[1:]:
        add(R.to_net, "PCIE_WAKE_N", ("all", *a), w=LSW, maxpad=110.0, **L3)
    fails += R.run_tasks(tasks)
    return fails


EXTRA_DRU = """
(rule "silk may sit on masked copper (only pads/holes need clearance)"
    (condition "A.Type != 'Pad' && B.Type != 'Pad' && A.Type != 'Via' && B.Type != 'Via'")
    (constraint silk_clearance (min 0mm)))
(rule "REFCLK100: uncoupled length incl. via and QFN pin fan-outs <= 8 mm (100 MHz HCSL)"
    (condition "A.NetClass == 'REFCLK_100'")
    (constraint diff_pair_uncoupled (max 8.0mm)))
"""


def finish(k, info):
    k.zone("GND", "L2", info["board"], clearance=0.2, thermal=False)
    k.zone("GND", "L5", info["board"], clearance=0.2, thermal=False)
    k.zone("GND", "L3", info["board"], clearance=0.2, thermal=False)
    k.zone("3V3", "L4", info["board"], clearance=0.25, thermal=False)
    k.text(f"U.3 host card {VAR}  x16 -> 2x SlimSAS 8i", 26.0, -42.0, P.F_SilkS, 1.0)
    k.text("x4x4x4x4 bifurcation", 26.0, -40.2, P.F_SilkS, 1.0)
    for ref, f in k.fps.items():
        for g in list(f.GraphicalItems()):
            if g.GetLayer() in (P.F_SilkS, P.B_SilkS) and g.GetClass() != "FP_TEXT":
                f.Remove(g)
        f.Value().SetVisible(False); f.Reference().SetVisible(False)
    with open(os.path.join(OUT, "bom_raw.json"), "w") as f:
        json.dump(k.bom, f, indent=1)
    import subprocess
    k.save()
    skew = subprocess.run([sys.executable, os.path.join(pcbkit.RULES, "gen_pair_skew_rules.py"), k.pcb],
                          capture_output=True, text=True).stdout
    bb, rpt = k.fill_and_check(EXTRA_DRU + skew)
    c, items = pcbkit.drc_summary(rpt)
    print("DRC:", dict(c))


if __name__ == "__main__":
    k, info = build()
    print(HS_LOG)
    if STAGE != "place":
        for f_ in route(k, info):
            print("FAIL", f_)
    finish(k, info)
