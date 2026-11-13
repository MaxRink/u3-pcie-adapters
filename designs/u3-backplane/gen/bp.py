"""Cabled 4-drive U.3 backplane: 4x vertical U.3 receptacle (drive side), 2x SlimSAS 8i + PCIe 8-pin (back).

Board frame: x right, y down, seen from the drive side (L1).  Units mm.
  * receptacles at x = XD[i], centre y = YC, S1 end down, 20 mm pitch
  * SlimSAS 8i right angle on the back, mating face on the bottom edge (y = H)
  * J_A (left) port B (lanes 4-7) -> drive 0, port A (lanes 0-3) -> drive 1; J_B the same for drives 2, 3
  * PET (host transmit) runs on L1, PER (drive transmit) on L6
"""
import os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew as P
import pcbkit
from router import Router
from pcbkit import Kit, PCIE_W, PCIE_G, CLK_W, CLK_G, plen
import fplib

HERE = os.path.dirname(os.path.abspath(__file__))
ND = int(os.environ.get("ND", "4"))          # drives per module: 4 (two 8i cables) or 6 (three, one 120 mm fan wide)
NP = ND // 2
OUT = os.environ.get("OUTDIR") or os.path.join(HERE, "..", "boards", "backplane" if ND == 4 else f"backplane{ND}")
NAME = "u3_backplane" if ND == 4 else f"u3_backplane{ND}"
STAGE = os.environ.get("STAGE", "all")

W, H = 20.0 * ND - 0.4, 90.5
XD = [9.8 + 20.0 * i for i in range(ND)]
YC = 48.5
XC = [15.8 + 40.0 * i for i in range(NP)]
YJ = H - 10.30                      # SlimSAS peg line (mating face flush with the bottom edge)
YA, YBR = YJ - 2.70, YJ - 5.05      # tail rows A and B (y)
# U.3 pin -> signal (SFF-TA-1001), host-centric names
U3 = {"S2": "PET0_P", "S3": "PET0_N", "S5": "PER0_N", "S6": "PER0_P", "S9": "PET1_P", "S10": "PET1_N",
      "S12": "PER1_N", "S13": "PER1_P", "S17": "PET2_P", "S18": "PET2_N", "S20": "PER2_N", "S21": "PER2_P",
      "S23": "PET3_P", "S24": "PET3_N", "S26": "PER3_N", "S27": "PER3_P", "E7": "REFCLK_P", "E8": "REFCLK_N"}
U3_GND = ["S1", "S4", "S7", "S8", "S11", "S14", "S15", "S16", "S19", "S22", "S25", "S28", "E9", "E12", "E15", "E19",
          "E22", "P5", "P6", "P12"]          # S15 = HPT0 tied to GND: selects the SFF-TA-1001 lane map
U3_SB = {"E3": "3V3_AUX", "E5": "PRST_N", "E6": "IFDET2_N", "E23": "SCL", "E24": "SDA",
         "E25": "DPEN_N", "P1": "WAKE_N", "P3": "PWRDIS", "P4": "IFDET_N", "P10": "PRSNT_N", "P11": "ACT_N",
         "P13": "12V", "P14": "12V", "P15": "12V"}
SS_GND = [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37]


SS = lambda c: f"J{ND + 1 + c}"                 # SlimSAS connector of drive pair c
JPI, JPO, JFI, JF = (f"J{ND + NP + i}" for i in (1, 2, 3, 4))   # 12 V in, 12 V out, fan control in, fan + out


def port_of(d):
    """drive index -> (connector index, first pin of the port)"""
    return d // 2, (20 if d % 2 == 0 else 2) - 1


def ss_pin(d, lane):
    """SlimSAS pin numbers (p, n order as in SFF-9402) of a drive's lane 0..3"""
    base = 1 if d % 2 else 19
    off = {0: 1, 1: 4, 2: 13, 3: 16}[lane]
    return base + off, base + off + 1


def ss_sb(d):
    """sideband pin numbers of a drive's port: (pin8, pin9, pin11, pin12)"""
    base = 1 if d % 2 else 19
    return base + 7, base + 8, base + 10, base + 11



# ---------------------------------------------------------------- helpers
def solve(fn):
    """fn(x, dry) -> signed skew of a pair whose geometry depends on x; find the x that zeroes it, then lay it."""
    x0, s0 = 0.0, fn(0.0, True)
    x = 0.0
    if abs(s0) > 0.004:
        x1 = 0.2 if s0 < 0 else -0.2
        s1 = fn(x1, True)
        for _ in range(12):
            if abs(s1) < 0.004:
                break
            x2 = x1 - s1 * (x1 - x0) / (s1 - s0)
            x0, s0, x1 = x1, s1, x2
            s1 = fn(x1, True)
        assert abs(s1) < 0.02, ("skew solve failed", s1)
        x = x1
    fn(x, False)
    return x


HS_LOG = []
VB, VA, VV = 26.65, 29.0, 30.0           # local v of SlimSAS row B, row A and the PET via row
BASE = {3: -3.9, 2: -2.1, "clk": -0.3, 1: 3.3, 0: 5.1}      # local u of a port's pin pairs (even drives)
LANE_PINS = {0: (1, 2), 1: (4, 5), 2: (13, 14), 3: (16, 17), "clk": (10, 11)}     # offsets from the port base
PN_POL = {"S5": "N", "S6": "P", "S12": "N", "S13": "P"}


def drive_hs(k, d):
    """All PCIe pairs of drive d.  No serpentines: every pair is matched by where its two vias sit (the copper
    doubles back at a via, so moving one via by x adds 2x to that line)."""
    xd = XD[d]; c = d // 2; even = d % 2 == 0
    off = 0.0 if even else -9.2
    jc = SS(c); jd = f"J{d + 1}"
    base = 19 if even else 1
    Bp = lambda u, v: (xd + u, YC + v)
    Bl = lambda pts: [Bp(*p) for p in pts]
    T = lambda key: BASE[key] + off
    N = lambda s_: f"D{d}_{s_}"
    PD = lambda pn: (k.padxy(jd, pn)[0] - xd, k.padxy(jd, pn)[1] - YC)

    def cpad(row, key):
        return [(f"{row}{base + o}", k.padxy(jc, f"{row}{base + o}")) for o in LANE_PINS[key]]

    for key in BASE:                                     # sanity: pads sit where the plan says
        (n1, p1), (n2, p2) = cpad("B", key)
        assert abs((p1[0] + p2[0]) / 2 - xd - T(key)) < 1e-6 and abs(p1[1] - YC - VB) < 1e-6, (d, key, p1, p2)

    # ------------------------------------------------ PET: receptacle pads (L1) -> via pair -> L6 stub -> row A
    def pet(lane, pins, center):
        t = T(lane)
        starts = []
        for pn in pins:
            u, v = PD(pn)
            starts.append((k.padnet(jd, pn), [Bp(-2.95 if u < 0 else 2.4, v)]))
        pads = sorted(cpad("A", lane), key=lambda e: e[1][0])          # left, right

        def fn(x, dry):
            vl, vr = Bp(t - 0.45, VV + max(x, 0)), Bp(t + 0.45, VV + max(-x, 0))
            res = k.pair("L1", Bl(center + [(t, VV - 0.4)]), starts, [(None, [vl]), (None, [vr])], dry=dry)
            L = {}
            for net, (full, sn, en) in res.items():
                side = 0 if math.dist(full[-1], vl) < 1e-6 else 1
                vxy = (vl, vr)[side]; pname, pxy = pads[side]
                st = [vxy, (pxy[0], pxy[1] + 0.5)]
                L[side] = plen(full) + plen(st)
                if not dry:
                    k.via(net, *vxy); k.setpad(jc, pname, net); k.track(net, "L6", st, PCIE_W)
            return L[0] - L[1]
        HS_LOG.append((N(f"PET{lane}"), round(solve(fn), 3)))

    ch = 0.4; P3, P2 = -7.9, -7.0
    if even:
        pet(3, ("S23", "S24"), [(-3.5, -4.92), (P3 + ch, -4.92), (P3, -4.92 + ch), (P3, 16.5),
                                (T(3), 16.5 + T(3) - P3)])
        pet(2, ("S17", "S18"), [(-3.5, -0.12), (P2 + ch, -0.12), (P2, -0.12 + ch), (P2, 16.0),
                                (T(2), 16.0 + T(2) - P2)])
        pet(1, ("S9", "S10"), [(-3.5, 6.28), (-5.3 + ch, 6.28), (-5.3, 6.28 + ch), (-5.3, 15.86), (-1.5, 19.66),
                               (1.64, 19.66), (3.3, 21.32)])
        pet(0, ("S2", "S3"), [(3.0, 13.965), (3.6, 13.965), (4.0, 14.365), (4.0, 15.5), (5.1, 16.6)])
    else:
        pet(3, ("S23", "S24"), [(-3.5, -4.92), (P3 + ch, -4.92), (P3, -4.92 + ch), (P3, 17.0),
                                (T(3), 17.0 + (P3 - T(3)))])
        pet(2, ("S17", "S18"), [(-3.5, -0.12), (P2 + ch, -0.12), (P2, -0.12 + ch), (P2, 17.4),
                                (T(2), 17.4 + (P2 - T(2)))])
        pet(1, ("S9", "S10"), [(-3.5, 6.28), (-5.3 + ch, 6.28), (-5.3, 6.28 + ch), (-5.3, 18.0), (T(1), 18.6)])
        pet(0, ("S2", "S3"), [(3.0, 13.965), (3.6, 13.965), (4.0, 14.365), (4.0, 17.3), (1.64, 19.66),
                              (-1.64, 19.66), (T(0), 19.66 + (-1.64 - T(0)))])

    # ------------------------------------------------ PER / REFCLK: receptacle pad (L1) [-> 220 nF] -> via -> L6 -> row B
    def l6(key, vias, center, w, g, dry):
        """L6 pair from the two vias [(net, (u, v))] to the row B pads; returns {net: length}"""
        t = T(key)
        ends = [(None, [(pxy[0], pxy[1] - 0.58)]) for _, pxy in cpad("B", key)]
        res = k.pair("L6", Bl(center + [(t, VB - 1.0)]), [(n, [Bp(*p)]) for n, p in vias], ends, w, g, dry=dry)
        if not dry:
            for net, (full, sn, en) in res.items():
                pname = min(cpad("B", key), key=lambda e: math.dist(e[1], full[-1]))[0]
                k.setpad(jc, pname, net)
        return {net: plen(full) for net, (full, sn, en) in res.items()}

    def direct(lane, pins, center):
        """lanes 2 and 3: staggered vias left of the pads, the pair leaves them straight down.
        pins = (upper pad, lower pad); the lower pad's via is the far one and gets tuned."""
        up, lo = pins
        (uu, vu), (ul, vl) = PD(up), PD(lo)

        def fn(x, dry):
            vias = [(k.padnet(jd, up), (-3.42, vu)), (k.padnet(jd, lo), (-4.12 - x, vl))]
            st = {n: [Bp(-3.1, p[1]), Bp(*p)] for n, p in vias}
            L = l6(lane, vias, center, PCIE_W, PCIE_G, dry)
            if not dry:
                for n, p in vias:
                    k.track(n, "L1", st[n], PCIE_W); k.via(n, *Bp(*p))
            a, b_ = vias[0][0], vias[1][0]
            return (L[a] + plen(st[a])) - (L[b_] + plen(st[b_]))
        HS_LOG.append((N(f"PER{lane}"), round(solve(fn), 3)))

    def capped(lane, pins, side, vs, center):
        """drive TX lanes 0 and 1: pad -> 220 nF 0402 -> via, the L6 pair doubles back under the caps.
        side = -1 left of the receptacle, +1 right."""
        uc = -4.43 if side < 0 else 4.7
        info = []
        for pn, v in zip(pins, vs):
            u0, v0 = PD(pn); pol = PN_POL[pn]
            nd, nc = f"D{d}C_PER{lane}_{pol}", N(f"PER{lane}_{pol}")
            k.setpad(jd, pn, nd)
            ref = f"C{d + 1}{lane}{1 if pol == 'P' else 2}"
            k.fp("Capacitor_SMD", "C_0402_1005Metric", ref, "220nF", *Bp(uc, v), 0, lcsc="C16772")
            p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
            near, far = (("1", "2") if abs(p1[0] - xd - u0) < abs(p2[0] - xd - u0) else ("2", "1"))
            k.setpad(ref, near, nd); k.setpad(ref, far, nc)
            k.track(nd, "L1", [Bp(-2.95 if side < 0 else 2.4, v0), (k.padxy(ref, near)[0] - side * 0.1, v + YC)], PCIE_W)
            k.void_under(ref, "L2")
            info.append((nc, k.padxy(ref, far), v))

        def fn(x, dry):
            sh = (max(x, 0), max(-x, 0))
            vias = [(nc, (uc + side * (1.27 + sh[i]), v)) for i, (nc, pf, v) in enumerate(info)]
            st = {nc: [pf, Bp(*vias[i][1])] for i, (nc, pf, v) in enumerate(info)}
            L = l6(lane, vias, center, PCIE_W, PCIE_G, dry)
            if not dry:
                for n, p in vias:
                    k.track(n, "L1", st[n], PCIE_W); k.via(n, *Bp(*p))
            a, b_ = vias[0][0], vias[1][0]
            return (L[a] + plen(st[a])) - (L[b_] + plen(st[b_]))
        HS_LOG.append((N(f"PER{lane}"), round(solve(fn), 3)))

    def clk(center):
        np_, nn = k.padnet(jd, "E7"), k.padnet(jd, "E8")
        (_, vp), (_, vn) = PD("E7"), PD("E8")

        def fn(x, dry):
            vias = [(np_, (-0.35 + x, vp)), (nn, (-1.05, vn))]
            st = {n: [Bp(-1.6, p[1]), Bp(*p)] for n, p in vias}
            L = l6("clk", vias, center, CLK_W, CLK_G, dry)
            if not dry:
                for n, p in vias:
                    k.track(n, "L1", st[n], CLK_W); k.via(n, *Bp(*p))
            return (L[np_] + plen(st[np_])) - (L[nn] + plen(st[nn]))
        HS_LOG.append((N("REFCLK"), round(solve(fn), 3)))

    c1 = [(-5.2, 3.88), (1.0 - ch, 3.88), (1.0, 3.88 + ch)]
    c0 = [(5.2, 10.155), (5.0, 10.155), (4.6, 10.555)]
    v1, v0 = (3.88 + 0.53, 3.88 - 0.53), (10.79, 9.52)
    if even:
        direct(3, ("S27", "S26"), [(-3.77, -6.35), (-3.77, -6.1), (-8.4, -1.45), (-8.4, 16.4), (T(3), 20.9)])
        direct(2, ("S21", "S20"), [(-3.77, -1.55), (-3.77, -1.3), (-7.4, 2.35), (-7.4, 16.0), (T(2), 21.3)])
        clk([(-0.7, 15.95), (-0.7, 16.3), (-1.05, 16.65), (-1.05, 19.6), (T("clk"), 20.35)])
        capped(1, ("S12", "S13"), -1, v1, c1 + [(1.0, 19.2), (T(1), 21.5)])
        capped(0, ("S5", "S6"), +1, v0, c0 + [(4.6, 20.0), (T(0), 20.5)])
    else:
        direct(3, ("S27", "S26"), [(-3.77, -6.35), (-3.77, -6.1), (-8.4, -1.45), (-8.4, 20.5), (T(3), 25.2)])
        direct(2, ("S21", "S20"), [(-3.77, -1.55), (-3.77, -1.3), (-7.4, 2.35), (-7.4, 21.0), (T(2), 24.9)])
        clk([(-0.7, 15.95), (-0.7, 16.2), (T("clk"), 16.2 + 8.8)])
        capped(1, ("S12", "S13"), -1, v1, c1 + [(1.0, 16.2), (T(1), 16.2 + 6.9)])
        capped(0, ("S5", "S6"), +1, v0, c0 + [(4.6, 15.7), (T(0), 15.7 + 8.7)])
    assert k.padnet(jc, f"B{base + 10}") == N("REFCLK_P"), "REFCLK polarity"



R0402 = ("Resistor_SMD", "R_0402_1005Metric")
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C0805 = ("Capacitor_SMD", "C_0805_2012Metric")
C1206 = ("Capacitor_SMD", "C_1206_3216Metric")
RN = ("Resistor_SMD", "R_Array_Convex_4x0603")
SOT = "Package_TO_SOT_SMD"
LC = {"10k": "C25744", "1k": "C11702", "100nF": "C1525", "22uF": "C12891", "10uF": "C15850", "100k": "C25741",
      "24k": "", "10k x4": "C29718", "4.7k x4": "C1980"}
LSW = 0.15                    # low-speed track width
SLOTS = []                    # air slot polygons (board coords)
TRUNK = {}                    # net -> L3 trunk polyline (router root copper)
ROOT = {}                     # net -> root via (x, y)


def two(k, ref, fp, val, x, y, rot, na, nb, near, lcsc="", dnp=False):
    """two-pad part; the pad nearer to `near` gets net na.  Returns (xy of pad a, xy of pad b)."""
    k.fp(*fp, ref, val, x, y, rot, lcsc=lcsc, dnp=dnp)
    p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
    a, b_ = ("1", "2") if math.dist(p1, near) <= math.dist(p2, near) else ("2", "1")
    k.setpad(ref, a, na); k.setpad(ref, b_, nb)
    return k.padxy(ref, a), k.padxy(ref, b_)


def rounded(poly, r=0.8, n=5):
    """closed polygon with rounded corners (convex and concave)"""
    out = []
    m = len(poly)
    for i in range(m):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % m]
        a = pcbkit._unit(p0, p1); b_ = pcbkit._unit(p2, p1)
        s_, e_ = (p1[0] + a[0] * r, p1[1] + a[1] * r), (p1[0] + b_[0] * r, p1[1] + b_[1] * r)
        c = (s_[0] + b_[0] * r, s_[1] + b_[1] * r)
        a0 = math.atan2(s_[1] - c[1], s_[0] - c[0]); a1 = math.atan2(e_[1] - c[1], e_[0] - c[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        out += [(c[0] + r * math.cos(a0 + da * j / n), c[1] + r * math.sin(a0 + da * j / n)) for j in range(n + 1)]
    return out


def drive_misc(k, d):
    """Ground vias, power, sideband escapes and the per-drive logic block of drive d (everything but the pairs)."""
    xd = XD[d]; n = d + 1; jd = f"J{n}"
    Bp = lambda u, v: (xd + u, YC + v)
    N = lambda s_: f"D{d}_{s_}"
    PD = lambda pn: (k.padxy(jd, pn)[0] - xd, k.padxy(jd, pn)[1] - YC)
    # ---------------- ground
    for pn in ("S8", "S11", "S14", "S16", "S19", "S22", "S25", "S28", "E12", "E15", "E19", "E22"):
        v = PD(pn)[1]
        k.track("GND", "L1", [Bp(-1.7, v), Bp(-0.95, v)], 0.25); k.via("GND", *Bp(-0.95, v))
    k.track("GND", "L1", [Bp(-1.7, PD("E9")[1]), Bp(-0.95, 13.55)], 0.25); k.via("GND", *Bp(-0.95, 13.55))
    k.track("GND", "L1", [Bp(-1.75, PD("S15")[1]), Bp(-1.75, PD("S16")[1])], 0.25)      # HPT0 = GND
    for pn in ("S4", "S7", "P5", "P6", "P12"):
        v = PD(pn)[1]
        k.track("GND", "L1", [Bp(2.4, v), Bp(3.3, v)], 0.25); k.via("GND", *Bp(3.3, v))
    k.track("GND", "L1", [Bp(1.71, 16.0), Bp(2.0, 17.0)], 0.25); k.via("GND", *Bp(2.0, 17.0))
    k.via("GND", *Bp(0, -21.8)); k.via("GND", *Bp(0.9, 22.8))                          # retainer clips
    # ---------------- 12 V: eFuse (soft start, current limit, off while the bay is empty) -> L1 pour -> P13..P15
    dv = N("12V"); uf = f"U{n}4"
    EU, EV = 6.6, -20.0
    k.fp("u3adapter", fplib.RGE, uf, "TPS259824ONRGER", *Bp(EU, EV), 180, pads={
        **{str(p): "12V_IN" for p in (1, 2, 3, 16, 25)}, **{str(p): "GND" for p in (4, 5, 10, 11, 12, 14, 26)},
        **{str(p): dv for p in (17, 18, 19, 20, 21, 22, 23, 24)},
        "6": N("EN"), "7": N("ITMR"), "8": N("ILIM"), "9": N("IMON"), "15": N("DVDT")}, lcsc="C2155759")
    Q = lambda q: k.padxy(uf, str(q))
    k.rule_area(f"EFUSE_{d}", [Bp(EU - 2.6, EV - 2.6), Bp(EU + 2.6, EV - 2.6), Bp(EU + 2.6, EV + 2.6), Bp(EU - 2.6, EV + 2.6)])
    ein, egn = Q(25), Q(26)
    assert ein[1] > egn[1] and Q(19)[1] > ein[1] and Q(7)[1] < egn[1] and Q(1)[0] > ein[0], "eFuse orientation"
    for q in (1, 2, 3):
        k.track("12V_IN", "L1", [Q(q), (ein[0] + 1.2, Q(q)[1])], 0.24)
    k.track("12V_IN", "L1", [Q(16), (ein[0] - 1.2, Q(16)[1])], 0.24)
    for q in (4, 5):
        k.track("GND", "L1", [Q(q), (egn[0] + 1.2, egn[1])], 0.24)
    k.track("GND", "L1", [Q(14), (egn[0] - 1.2, egn[1])], 0.24)
    for q in (10, 11, 12):
        k.track("GND", "L1", [Q(q), (Q(q)[0], egn[1] - 0.3)], 0.24)
    for dx in (-0.85, 0.0, 0.85):
        k.via("12V_IN", ein[0] + dx, ein[1], 0.6, 0.3)
        k.via("GND", egn[0] + dx, egn[1])
    for q in (17, 18):
        k.track(dv, "L1", [Q(q), (Q(q)[0] - 0.55, Q(q)[1]), (Q(q)[0] - 0.55, Q(19)[1]), Q(19)], 0.24)
    # ILIM 390R (about 3.9 A), ITIMER 2.2 nF, IMON load: a row above the control pins; dV/dt 10 nF on the left
    gy = YC + EV - 5.45
    for q, ref, val, lc, du in ((7, f"C{n}24", "2.2nF", "", 0.5), (8, f"R{n}8", "390R 1%", "", 0.0),
                                (9, f"R{n}9", "10k", LC["10k"], -0.5)):
        px = Q(q)[0] + du
        sig, gnd = two(k, ref, C0402 if ref[0] == "C" else R0402, val, px, YC + EV - 4.0, 90, k.padnet(uf, str(q)),
                       "GND", (px, YC + EV), lc)
        k.track(k.padnet(uf, str(q)), "L1", [Q(q), (Q(q)[0], Q(q)[1] - 0.45), (px, Q(q)[1] - 0.45 - abs(du)), sig], LSW)
        k.track("GND", "L1", [gnd, (gnd[0], gy)], 0.25)
    k.track("GND", "L1", [(Q(7)[0] + 0.5, gy), (Q(9)[0] - 0.5, gy)], 0.25)
    k.via("GND", Q(9)[0] - 0.5, gy); k.via("GND", Q(7)[0] + 0.5, gy)
    p15 = Q(15)
    sig, gnd = two(k, f"C{n}25", C0402, "10nF", xd + 3.6, p15[1] - 0.48, 90, N("DVDT"), "GND", (xd + 3.6, p15[1]), "")
    k.track(N("DVDT"), "L1", [p15, sig], LSW)
    k.track("GND", "L1", [gnd, (gnd[0], gnd[1] - 1.1)], 0.25); k.via("GND", gnd[0], gnd[1] - 1.1)
    ven = (xd + 9.05, Q(6)[1] - 1.15)
    k.track(N("EN"), "L1", [Q(6), (xd + 9.05, Q(6)[1]), ven], LSW); k.via(N("EN"), *ven); ROOT[N("EN")] = ven
    cv, cg = two(k, f"C{n}20", C1206, "22uF 25V X5R", *Bp(6.9, -12.9), 0, dv, "GND", Bp(4.0, -12.9), LC["22uF"])
    k.track("GND", "L1", [cg, (cg[0], YC - 11.4)], 0.5); k.via("GND", cg[0], YC - 11.4, 0.6, 0.3)
    rt, rs = two(k, f"R{n}1", R0402, "24k 1%", *Bp(4.05, -12.55), 90, dv, N("SNS"), Bp(4.05, -14), LC["24k"])
    zp = [Bp(*p) for p in ((0.7, -16.4), (3.6, -16.4), (3.6, -17.6), (5.0, -17.6), (5.0, -18.45), (8.2, -18.45),
                           (8.2, -17.6), (9.3, -17.6), (9.3, -14.4), (6.1, -14.4),
                           (6.1, -11.9), (4.7, -11.9), (4.7, -12.7), (0.7, -12.7))]
    k.zone(dv, "L1", zp, prio=3, clearance=0.2, minw=0.2, thermal=False)
    KEEP.append(("L1", [Bp(*p) for p in ((0.4, -16.9), (3.2, -16.9), (3.2, -26.0), (9.5, -26.0), (9.5, -14.1),
                                         (6.4, -14.1), (6.4, -11.6), (4.4, -11.6), (4.4, -12.4), (0.4, -12.4))]))
    # ---------------- right row sidebands: via next to the pad, L3 trunk under the pad row toward the bottom
    for pn, sig in (("P10", "PRSNT_N"), ("P11", "ACT_N"), ("P4", "IFDET_N"), ("P3", "PWRDIS"), ("P1", "WAKE_N"),
                    ("E6", "IFDET2_N"), ("E5", "PRST_N"), ("E3", None)):
        u, v = PD(pn); net = k.padnet(jd, pn)
        k.track(net, "L1", [Bp(3.2 if pn[0] == "E" else 2.4, v), Bp(4.15, v)], 0.2); k.via(net, *Bp(4.15, v))
        ROOT[net] = Bp(4.15, v)
    for i, (pn, sig) in enumerate((("P10", "PRSNT_N"), ("P4", "IFDET_N"), ("P3", "PWRDIS"), ("P1", "WAKE_N"),
                                   ("E6", "IFDET2_N"))):
        ut = 0.9 + 0.35 * i; v = PD(pn)[1]
        # the trunks run at 0.35 mm pitch, where the router cannot tap them: fan the ends out to 0.75 mm pitch
        xe = -0.3 + 0.75 * i; vj = 11.0 + 0.3 * min(i, 2)
        pts = [Bp(4.15, v), Bp(ut + 0.3, v), Bp(ut, v + 0.3), Bp(ut, vj), Bp(xe, vj + abs(xe - ut)), Bp(xe, 14.0)]
        k.track(N(sig), "L3", pts, LSW); TRUNK[N(sig)] = pts
    # ---------------- left row: SMBus vias and trunks, port PERST# trunk
    for i, (pn, sig) in enumerate((("E23", "SCL"), ("E24", "SDA"))):
        u, v = PD(pn); ut = -2.65 + 0.35 * i
        k.track(N(sig), "L1", [Bp(-3.0, v), Bp(-3.9, v)], 0.2); k.via(N(sig), *Bp(-3.9, v))
        xe = -3.75 + 0.75 * i; vj = 13.0 + 0.3 * i
        pts = [Bp(-3.9, v), Bp(ut - 0.3, v), Bp(ut, v + 0.3), Bp(ut, vj), Bp(xe, vj + abs(xe - ut)), Bp(xe, 16.5)]
        k.track(N(sig), "L3", pts, LSW); TRUNK[N(sig)] = pts
    pts = [Bp(-1.95, -16.3), Bp(-1.95, 16.5)]      # top end above the SMBus jogs so the gate can reach it
    k.track(N("PRSTP"), "L3", pts, LSW); TRUNK[N("PRSTP")] = pts
    # ---------------- logic block left of the receptacle top end
    us, ua = f"U{n}1", f"U{n}2"
    k.fp(SOT, "SOT-23-6", us, "TPS3808G01DBVR", *Bp(-6.7, -10.6), 180, pads={
        "1": N("PG"), "2": "GND", "5": N("SNS"), "6": "3V3_AUX"}, lcsc="")
    k.fp(SOT, "SOT-23-5", ua, "SN74LVC1G08DBVR", *Bp(-6.7, -14.6), 0, pads={
        "1": N("PRSTP"), "2": N("PG"), "3": "GND", "4": N("PRST_N"), "5": "3V3_AUX"}, lcsc="")
    parts = []
    parts.append(two(k, f"C{n}21", C0402, "100nF", *Bp(-7.0, -8.25), 0, "3V3_AUX", "GND", Bp(-9, -8.25), LC["100nF"])
                 + ("3V3_AUX", "GND"))
    parts.append(two(k, f"R{n}3", R0402, "10k", *Bp(-7.0, -7.2), 0, "3V3_AUX", N("PG"), Bp(-9, -7.2), LC["10k"])
                 + ("3V3_AUX", N("PG")))
    parts.append(two(k, f"R{n}2", R0402, "1k 1%", *Bp(-7.0, -6.15), 0, "GND", N("SNS"), Bp(-9, -6.15), LC["1k"])
                 + ("GND", N("SNS")))
    parts.append(two(k, f"R{n}4", R0402, "10k", *Bp(-5.2, -17.3), 0, "3V3_AUX", N("DPEN_N"), Bp(-9, -17.3), LC["10k"])
                 + ("3V3_AUX", N("DPEN_N")))
    parts.append(two(k, f"R{n}5", R0402, "1k", *Bp(-6.5, -20.6), 0, "3V3_AUX", N("LEDA"), Bp(-9, -20.6), LC["1k"])
                 + ("3V3_AUX", N("LEDA")))
    k.fp("LED_SMD", "LED_0603_1608Metric", f"D{n}", "LED green 0603", *Bp(-6.5, -19.2), 0,
         pads={"1": N("ACT_N"), "2": N("LEDA")}, lcsc="C72043")
    un = f"U{n}3"                                   # drive detected (PRSNT# or IfDet# low) -> eFuse enable
    k.fp(SOT, "SOT-23-5", un, "SN74LVC1G00DBVR", *Bp(-6.7, -23.6), 0, pads={
        "1": N("PRSNT_N"), "2": N("IFDET_N"), "3": "GND", "4": N("EN"), "5": "3V3_AUX"}, lcsc="")
    parts.append(two(k, f"C{n}23", C0402, "100nF", *Bp(-6.7, -26.0), 0, "3V3_AUX", "GND", Bp(-9, -26.0), LC["100nF"])
                 + ("3V3_AUX", "GND"))
    parts.append(two(k, f"C{n}22", C0402, "22nF", *Bp(-7.4, -17.4), 0, "GND", N("CT"), Bp(-9, -17.4), "")
                 + ("GND", N("CT")))
    k.setpad(us, "4", N("CT"))
    # gated PERST# to the drive: AND output -> via -> L6 under the receptacle -> E5 via
    y4 = k.padxy(ua, "4")
    k.track(N("PRST_N"), "L1", [y4, Bp(-4.6, -12.1)], LSW); k.via(N("PRST_N"), *Bp(-4.6, -12.1))
    k.track(N("PRST_N"), "L6", [Bp(-4.6, -12.1), Bp(1.9, -12.1), Bp(2.2, -11.8), Bp(2.2, 3.575), Bp(2.5, 3.875),
                                Bp(4.15, 3.875)], LSW)
    # ---------------- air slot right of the receptacle
    if d < 3:
        sl = [(4.8, -10.5), (10.3, -10.5), (10.3, 16.0), (7.6, 16.0), (7.6, 7.6), (4.8, 7.6)]
    else:
        sl = [(4.8, -10.5), (8.3, -10.5), (8.3, 7.6), (4.8, 7.6)]
    SLOTS.append(rounded([Bp(*p) for p in sl]))
    return dict(us=us, ua=ua, un=un, parts=parts, rs=rs, led=f"D{n}", jd=jd)


KEEP = []
Y12 = 20.5                     # L4 is 12 V above this line


def port_sidebands(k, d):
    """SlimSAS sideband pins of drive d's port: vias, CPRSNT# diode, pull-downs."""
    xd = XD[d]; n = d + 1; c = d // 2; even = d % 2 == 0
    jc = SS(c); base = 19 if even else 1
    Bp = lambda u, v: (xd + u, YC + v)
    N = lambda s_: f"D{d}_{s_}"
    PX = lambda row, o: k.padxy(jc, f"{row}{base + o}")[0] - xd
    out = {}
    a_nets = {7: ("HOST_SCL" if d == 1 else None), 8: ("HOST_SDA" if d == 1 else None), 10: N("PRSTP"), 11: N("CPRSNT_N")}
    for o, net in a_nets.items():
        if not net:
            continue
        u = PX("A", o); vv = 30.15 if o in (7, 10) else 30.85
        k.setpad(jc, f"A{base + o}", net)
        k.track(net, "L6", [Bp(u, VA + 0.4), Bp(u, vv)], LSW); k.via(net, *Bp(u, vv))
        ROOT.setdefault(net, Bp(u, vv)); out[o] = Bp(u, vv)
    for o, net, vv in ((7, N("BPTYPE"), 24.6), (8, N("WAKE_N"), 25.3)):
        u = PX("B", o)
        k.setpad(jc, f"B{base + o}", net)
        k.track(net, "L6", [Bp(u, VB - 0.4), Bp(u, vv)], LSW); k.via(net, *Bp(u, vv))
        out["B%d" % o] = Bp(u, vv)
    uc = PX("A", 11)
    dref = f"D{n}0"
    k.fp(SOT, "SOT-23", dref, "BAT54A", *Bp(uc, 33.0), 90, pads={"1": N("PRSNT_N"), "2": N("IFDET_N"),
                                                                  "3": N("CPRSNT_N")}, lcsc="")
    k.track(N("CPRSNT_N"), "L1", [out[11], k.padxy(dref, "3")], LSW)
    sg = -1 if even else 1                            # resistors on the outer side: the middle stays free
    r6 = two(k, f"R{n}6", R0402, "100k", *Bp(uc + 2.4 * sg, 32.6), 90, N("PRSTP"), "GND", Bp(uc, 30), LC["100k"])
    r7 = two(k, f"R{n}7", R0402, "10k", *Bp(uc + (2.2 if even else 3.6), 32.6), 90, N("BPTYPE"), "GND", Bp(uc, 30), LC["10k"])
    return dict(dref=dref, r6=r6, r7=r7, vias=out)


def build():
    fplib.u3v(); fplib.ss8(); fplib.rge()
    k = Kit(OUT, NAME)
    # ---------------- receptacles
    for d, xd in enumerate(XD):
        pads = {}
        for pin, s in U3.items():
            pads[pin] = f"D{d}_{s}"
        for pin in U3_GND:
            pads[pin] = "GND"
        for pin, s in U3_SB.items():
            pads[pin] = "3V3_AUX" if s == "3V3_AUX" else f"D{d}_{s}"
        pads["MP"] = "GND"
        k.fp("u3adapter", fplib.U3V, f"J{d + 1}", "PSAS5F3130021TR", xd, YC, rot=90, pads=pads, lcsc="C5382954")
        k.rule_area(f"NECKDOWN_J{d + 1}L", [(xd - 4.3, YC - 9.3), (xd - 0.3, YC - 9.3), (xd - 0.3, YC + 16.3),
                                            (xd - 4.3, YC + 16.3)])
        k.rule_area(f"NECKDOWN_J{d + 1}R", [(xd + 0.5, YC + 8.8), (xd + 3.2, YC + 8.8), (xd + 3.2, YC + 15.4),
                                            (xd + 0.5, YC + 15.4)])
    # ---------------- SlimSAS 8i on the back
    for c, xc in enumerate(XC):
        pads = {"SH": "GND"}
        for n in SS_GND:
            pads[f"A{n}"] = pads[f"B{n}"] = "GND"
        k.fp("u3adapter", fplib.SS8, SS(c), "U10A474240T", xc, YJ, rot=180, bottom=True, pads=pads)
        k.rule_area(f"NECKDOWN_{SS(c)}", [(xc - 11.4, YA - 3.2), (xc + 11.4, YA - 3.2), (xc + 11.4, YA + 1.8),
                                           (xc - 11.4, YA + 1.8)])
        for n in SS_GND:                                  # one via between the rows per GND pin position
            a, b_ = k.padxy(SS(c), f"A{n}"), k.padxy(SS(c), f"B{n}")
            k.track("GND", "L6", [a, b_], 0.25); k.via("GND", a[0], (a[1] + b_[1]) / 2)
    info = {}
    for d in range(ND):
        drive_hs(k, d)
    for d in range(ND):
        info[d] = drive_misc(k, d)
        info[d].update(port_sidebands(k, d))
        # PERST#: fixed L3 link from the port's stub via through the gap in the GND via row up to the trunk end
        vx, vy = info[d]["vias"][10]
        tx, ty = TRUNK[f"D{d}_PRSTP"][-1]
        sx, yk = vx - 0.3, (YC + 26.7 if vx > tx else YC + 25.55)
        link = [(tx, ty), (tx, yk - abs(sx - tx)), (sx, yk), (sx, vy - 0.3), (vx, vy)]
        k.track(f"D{d}_PRSTP", "L3", link, LSW)
        TRUNK[f"D{d}_PRSTP"] = TRUNK[f"D{d}_PRSTP"] + link[1:]
    # ---------------- top edge, back side: fan chain in, 12 V in, 12 V out, fan, fan chain out (all right angle)
    MW = 18.0
    x = (W - (10.16 + 20.32 + 2 * MW + 3.1)) / 2
    for ref, kind, val in ((JFI, 4, "FAN CTRL IN (from mainboard / previous module)"),
                           (JPI, 0, "12V IN  PCIe 8-pin (Mini-Fit Jr 5569-08A2)"),
                           (JPO, 0, "12V OUT daisy chain (Mini-Fit Jr 5569-08A2)"),
                           (JF, 8, "FAN (pins 1-4) + FAN CTRL OUT (pins 5-8)")):
        if not kind:
            k.fp("Connector_Molex", "Molex_Mini-Fit_Jr_5569-08A2_2x04_P4.20mm_Horizontal", ref, val, x + 15.3, 13.9, 0,
                 bottom=True, pads={"1": "12V_IN", "2": "12V_IN", "3": "12V_IN", "5": "GND", "7": "GND", "8": "GND"},
                 lcsc="")
            x += MW + (1.0 if ref == JPI else 1.05)
        else:
            nets = ({"1": "GND", "3": "FAN_TACH", "4": "FAN_PWM"} if kind == 4 else
                    {"1": "GND", "2": "FAN_12V", "3": "FAN_TACH", "4": "FAN_PWM", "5": "GND", "8": "FAN_PWM"})
            k.fp("Connector_PinHeader_2.54mm", f"PinHeader_1x{kind:02d}_P2.54mm_Horizontal", ref, val,
                 x + 2.54 * kind - 1.27, 10.4, 90, bottom=True, pads=nets, lcsc="")
            x += 2.54 * kind + 1.05
    r12 = [k.padxy(ref, p) for ref in (JPI, JPO) for p in ("1", "2", "3", "4")]
    rg = [k.padxy(ref, p) for ref in (JPI, JPO) for p in ("5", "6", "7", "8")]
    y12, yg = r12[0][1], rg[0][1]
    x0, x1 = min(p[0] for p in r12) - 7.0, max(p[0] for p in r12) + 2.2
    for L in ("L1", "L6"):
        k.zone("12V_IN", L, [(x0, y12 - 2.4), (x1, y12 - 2.4), (x1, y12 + 2.45), (x0, y12 + 2.45)], prio=3,
               clearance=0.3, thermal=False)
        k.zone("GND", L, [(x0, yg - 2.45), (x1, yg - 2.45), (x1, yg + 2.2), (x0, yg + 2.2)], prio=3, clearance=0.3,
               thermal=False)
        KEEP.append((L, [(x0 - 0.4, 2.0), (x1 + 0.4, 2.0), (x1 + 0.4, yg + 2.5), (x0 - 0.4, yg + 2.5)]))
    # fan supply: 1206 PTC from the 12 V row to the fan header; input bulk on the drive side between the rows
    f2 = k.padxy(JF, "2")
    fa, fb = two(k, "F1", ("Fuse", "Fuse_1206_3216Metric"), "PTC 1206 1.1A 16V", x1 + 2.4, y12, 0, "12V_IN", "FAN_12V",
                 (x1, y12), "")
    k.track("12V_IN", "L1", [fa, (x1 - 0.5, y12)], 0.8)
    bulk = []
    for i, bx in enumerate((x0 + 1.4, x0 + 3.9)):
        bulk.append(two(k, f"C{5 + i}", C1206, "22uF 25V X5R", bx, (y12 + yg) / 2, 90, "12V_IN", "GND", (bx, y12),
                        LC["22uF"]))
    # ---------------- per connector pair: I/O expander + pull-ups under the SlimSAS tails, mux / LDO in the gap column
    arr = []

    def array(ref, val, x, y, rot, pairs):
        k.fp(*RN, ref, val, x, y, rot, lcsc=LC[val])
        for i, (na, nb) in enumerate(pairs):
            if na:
                k.setpad(ref, str(i + 1), na); k.setpad(ref, str(8 - i), nb)
            arr.append((ref, str(i + 1), na)); arr.append((ref, str(8 - i), nb))
    caps = []
    ics = []
    for c in range(NP):
        xo = 40.0 * c; de, do = 2 * c, 2 * c + 1
        ex = {"1": "3V3_AUX" if c & 1 else "GND", "2": "3V3_AUX" if c & 2 else "GND", "3": "GND", "8": "GND",
              "14": "HOST_SCL", "15": "HOST_SDA", "16": "3V3_AUX"}
        for j, sig in enumerate(("PRSNT_N", "IFDET_N", "IFDET2_N", "PWRDIS")):
            ex[str(4 + j)] = f"D{de}_{sig}"; ex[str(9 + j)] = f"D{do}_{sig}"
        ue = f"U{c + 5}"
        k.fp("Package_SO", "TSSOP-16_4.4x5mm_P0.65mm", ue, "TCA9554PWR", xo + 14.9, YC + 37.2, 90, pads=ex, lcsc="")
        ics.append(ue)
        caps.append(two(k, f"C{c + 10}", C0402, "100nF", xo + 18.6, YC + 36.7, 90, "3V3_AUX", "GND",
                        (xo + 18.6, YC + 38), LC["100nF"]))
        for dd, ax in ((de, xo + 8.0), (do, xo + 21.4)):
            prs = [(f"D{dd}_PRSNT_N", "3V3_AUX"), (f"D{dd}_IFDET_N", "3V3_AUX"), (f"D{dd}_IFDET2_N", "3V3_AUX"),
                   (f"D{dd}_PWRDIS", "GND")]
            array(f"RN{dd + 1}", "10k x4", ax, YC + 36.55, 90, prs)
            array(f"RN{dd + 11}", "4.7k x4", ax, YC + 39.85, 90,
                  [(f"D{dd}_SCL", "3V3_AUX"), (f"D{dd}_SDA", "3V3_AUX"), (None, None), (None, None)]
                  if dd != 1 else [("D1_SCL", "3V3_AUX"), ("D1_SDA", "3V3_AUX"), ("HOST_SCL", "3V3_AUX"),
                                   ("HOST_SDA", "3V3_AUX")])
    arr[:] = [a for a in arr if a[2]]
    # SMBus mux in the first gap column: upstream = connector J5 port A (drive 1's port), reset by that port's PERST#
    MX, MY = 34.0, YC + 28.6
    mx = {"1": "3V3_AUX", "2": "GND", "21": "GND", "3": "D1_PRSTP", "12": "GND", "22": "HOST_SCL", "23": "HOST_SDA",
          "24": "3V3_AUX"}
    for ch in range(ND):
        base = 4 + 2 * ch + (1 if ch >= 4 else 0)
        mx[str(base)] = f"D{ch}_SDA"; mx[str(base + 1)] = f"D{ch}_SCL"
    k.fp("Package_SO", "TSSOP-24_4.4x7.8mm_P0.65mm", "U1", "TCA9548APWR", MX, MY, 90, pads=mx, lcsc="")
    ics.append("U1")
    caps.append(two(k, "C3", C0402, "100nF", MX + 5.0, MY - 2.2, 90, "3V3_AUX", "GND", (MX + 5.0, MY), LC["100nF"]))
    # 3V3_AUX regulator on the drive side above the fan header pins, where the 12 V plane is
    LX, LY = (k.padxy(JF, "1")[0] + k.padxy(JF, "8")[0]) / 2, 4.8
    k.fp(SOT, "SOT-223-3_TabPin2", "U3", "MCP1703AT-3302E/DB", LX, LY, 0,
         pads={"1": "12V_IN", "2": "GND", "3": "3V3_AUX"}, lcsc="")
    ci = two(k, "C1", C0805, "10uF 25V X5R", LX - 5.6, LY, 90, "12V_IN", "GND", (LX - 7.4, LY), LC["10uF"])
    co = two(k, "C2", C0805, "10uF 25V X5R", LX + 5.6, LY, 90, "3V3_AUX", "GND", (LX + 7.4, LY), LC["10uF"])
    # ---------------- mounting holes, outline, air slots
    hp = [(3.2, 15.5), (W - 3.2, 15.5)] + [(36.0 + 40.0 * c, H - 4.2) for c in range(NP)]
    for i, (x, y) in enumerate(hp):
        k.fp("MountingHole", "MountingHole_3.2mm_M3", f"H{i + 1}", "M3", x, y, bom=False)
    k.outline([(0, 0), (W, 0), (W, H), (0, H)])
    for sl in SLOTS:
        k.outline(sl)
    info["glob"] = dict(ci=ci, co=co, caps=caps, arr=arr, ics=ics, bulk=bulk, fuse=(fa, fb))
    return k, info


def route(k, info):
    R = Router(k)
    R.keepouts += KEEP
    for net, pts in TRUNK.items():
        R.seed(net, [("L3", "seg", (p[0], p[1], q[0], q[1], LSW / 2)) for p, q in zip(pts, pts[1:])])
    T = lambda ref, p: ("L6" if k.fps[ref].IsFlipped() else "L1", *k.padxy(ref, p))
    L3 = dict(layer_cost={"L1": 1.5, "L6": 1.5}, via_cost=1.0)
    tasks = []
    add = lambda f, *a, **kw: tasks.append((f, a, kw))
    PW = ("GND", "3V3_AUX", "12V_IN")
    for d in range(ND):
        I = info[d]; N = lambda s_: f"D{d}_{s_}"
        us, ua, un = I["us"], I["ua"], I["un"]
        P_ = I["parts"]
        # local block
        add(R.route, N("PG"), T(us, "1"), T(ua, "2"), w=LSW)
        add(R.to_net, N("PG"), ("L1", *P_[1][1]), w=LSW)
        add(R.route, N("SNS"), T(us, "5"), ("L1", *P_[2][1]), w=LSW)
        add(R.route, N("CT"), T(us, "4"), ("L1", *P_[6][1]), w=LSW)
        add(R.route, N("DPEN_N"), ("L1", *P_[3][1]), T(I["jd"], "E25"), w=LSW)
        add(R.route, N("LEDA"), ("L1", *P_[4][1]), T(I["led"], "2"), w=LSW)
        for ref, pins in ((us, ("2", "6")), (ua, ("3", "5")), (un, ("3", "5"))):
            for p in pins:
                add(R.to_via, k.padnet(ref, p), T(ref, p))
        for pa, pb, na, nb in P_:
            for p, net in ((pa, na), (pb, nb)):
                if net in PW:
                    add(R.to_via, net, ("L1", *p))
        add(R.to_net, N("PRSTP"), T(ua, "1"), w=LSW, maxpad=16.0, **L3)
        add(R.route, N("SNS"), ("L1", *I["rs"]), T(us, "5"), w=LSW, maxpad=16.0, **L3)
        add(R.route, N("ACT_N"), ("all", *ROOT[N("ACT_N")]), T(I["led"], "1"), w=LSW, maxpad=16.0, **L3)
        add(R.route, N("EN"), ("all", *ROOT[N("EN")]), T(un, "4"), w=LSW, maxpad=24.0, **L3)
        add(R.to_net, N("PRSNT_N"), T(un, "1"), w=LSW, maxpad=32.0, **L3)
        add(R.to_net, N("IFDET_N"), T(un, "2"), w=LSW, maxpad=32.0, **L3)
    fails = R.run_tasks(tasks)
    print("stage 1 fails:", fails)
    # ---------------- bottom: everything that ends at the mux, the expanders and the port pins
    tasks = []
    G = info["glob"]
    for ref, p, net in G["arr"]:
        if net in PW:
            add(R.to_via, net, T(ref, p))
    for ref in G["ics"]:
        for p in k.fps[ref].Pads():
            if p.GetNetname() in PW:
                add(R.to_via, p.GetNetname(), T(ref, p.GetNumber()))
    for pa, pb in G["caps"]:
        add(R.to_via, "3V3_AUX", ("L1", *pa)); add(R.to_via, "GND", ("L1", *pb))
    for d in range(ND):
        I = info[d]; N = lambda s_: f"D{d}_{s_}"
        add(R.to_via, "GND", ("L1", *I["r6"][1])); add(R.to_via, "GND", ("L1", *I["r7"][1]))
        add(R.route, N("PRSTP"), ("all", *I["vias"][10]), ("L1", *I["r6"][0]), w=LSW)
        add(R.route, N("BPTYPE"), ("all", *I["vias"]["B7"]), ("L1", *I["r7"][0]), w=LSW, maxpad=16.0, **L3)
        add(R.to_net, N("WAKE_N"), ("all", *I["vias"]["B8"]), w=LSW, maxpad=24.0, **L3)
    for ref in G["ics"]:
        for p in k.fps[ref].Pads():
            net = p.GetNetname()
            if net and net not in PW:
                add(R.to_net, net, T(ref, p.GetNumber()), w=LSW, maxpad=48.0, **L3)
    for ref, p, net in G["arr"]:
        if net not in PW:
            add(R.to_net, net, T(ref, p), w=LSW, maxpad=24.0)
    for d in range(ND):
        I = info[d]
        for p in ("1", "2"):
            add(R.to_net, k.padnet(I["dref"], p), T(I["dref"], p), w=LSW, maxpad=48.0, **L3)
    # regulator
    add(R.route, "12V_IN", T("U3", "1"), ("L1", *G["ci"][0]), w=0.5)
    add(R.route, "3V3_AUX", T("U3", "3"), ("L1", *G["co"][0]), w=0.4)
    for a, net, w in ((("L1", *G["ci"][0]), "12V_IN", 0.5), (("L1", *G["co"][0]), "3V3_AUX", 0.4),
                      (("L1", *G["ci"][1]), "GND", 0.4), (("L1", *G["co"][1]), "GND", 0.4), (T("U3", "2"), "GND", 0.4),
                      (("L1", *k.padxy("U3", "2", 1)), "GND", 0.4)):
        add(R.to_via, net, a, w=w)
    # fan chain
    TH = lambda ref, p: ("all", *k.padxy(ref, p))          # through-hole pin: reachable on every layer
    add(R.route, "FAN_12V", ("L1", *G["fuse"][1]), TH(JF, "2"), w=0.5)
    add(R.route, "FAN_PWM", TH(JFI, "4"), TH(JF, "4"), w=0.2)
    add(R.route, "FAN_PWM", TH(JF, "4"), TH(JF, "8"), w=0.2)
    add(R.route, "FAN_TACH", TH(JFI, "3"), TH(JF, "3"), w=0.2)
    fails += R.run_tasks(tasks)
    return fails


def trim_stubs(k):
    """Cut back L3 track ends that end on nothing (trunk ends beyond the last tap).  Returns the number of cuts."""
    import math
    b = k.b
    n = 0
    for _ in range(8):
        byn = {}
        for t in b.GetTracks():
            byn.setdefault(t.GetNetname(), []).append(t)
        pads = {}
        for f in b.GetFootprints():
            for p in f.Pads():
                pads.setdefault(p.GetNetname(), []).append(p)
        changed, dead = 0, []
        for net, ts in byn.items():
            pts = []                                     # (x, y, owner) connection points of this net
            for t in ts:
                if t.GetClass() == "PCB_VIA":
                    pts.append((t.GetStart().x, t.GetStart().y, t))
                elif t.GetLayer() == pcbkit.LAYER["L3"]:
                    pts.append((t.GetStart().x, t.GetStart().y, t)); pts.append((t.GetEnd().x, t.GetEnd().y, t))
            for p in pads.get(net, []):
                if p.GetAttribute() == P.PAD_ATTRIB_PTH:
                    pts.append((p.GetPosition().x, p.GetPosition().y, p))
            tol = P.FromMM(0.09)
            for t in ts:
                if t.GetClass() == "PCB_VIA" or t.GetLayer() != pcbkit.LAYER["L3"]:
                    continue
                s, e = t.GetStart(), t.GetEnd()
                L = math.hypot(e.x - s.x, e.y - s.y)
                if L < 1:
                    continue
                ux, uy = (e.x - s.x) / L, (e.y - s.y) / L
                taps = []
                for x, y, o in pts:
                    if o is t:
                        continue
                    a = (x - s.x) * ux + (y - s.y) * uy
                    d = abs((x - s.x) * uy - (y - s.y) * ux)
                    if d <= tol and -tol <= a <= L + tol:
                        taps.append(min(max(a, 0), L))
                for o in ts:                               # an end that lands on the body of another L3 track
                    if o is t or o.GetClass() == "PCB_VIA" or o.GetLayer() != t.GetLayer():
                        continue
                    os_, oe = o.GetStart(), o.GetEnd()
                    oL = math.hypot(oe.x - os_.x, oe.y - os_.y) or 1
                    for q, a in ((s, 0), (e, L)):
                        pa = ((q.x - os_.x) * (oe.x - os_.x) + (q.y - os_.y) * (oe.y - os_.y)) / oL
                        pd = abs((q.x - os_.x) * (oe.y - os_.y) - (q.y - os_.y) * (oe.x - os_.x)) / oL
                        if pd <= tol and -tol <= pa <= oL + tol:
                            taps.append(a)
                if not taps:
                    continue
                lo, hi = min(taps), max(taps)
                if lo > tol or hi < L - tol:
                    if hi - lo < P.FromMM(0.05):             # joined at one point only: an unused trunk end
                        dead.append(t); changed += 1
                        continue
                    ns = P.VECTOR2I(int(s.x + ux * lo), int(s.y + uy * lo)); ne = P.VECTOR2I(int(s.x + ux * hi), int(s.y + uy * hi))
                    t.SetStart(ns); t.SetEnd(ne); changed += 1
        for t in dead:
            b.Delete(t)
        n += changed
        if not changed:
            break
    return n


def labels(k):
    """Silkscreen: board name and drive numbers on the drive side, connector names on the underside."""
    k.text(f"U.3 backplane {ND} x NVMe / SlimSAS 8i", 26.0, 3.0, P.F_SilkS, 1.2)
    k.text("12 V only", 9.5, 5.4, P.F_SilkS, 1.0)
    for d, xd in enumerate(XD):
        k.text(f"D{d}", xd, 22.4, P.F_SilkS, 1.2)
    for ref, s_ in ((JFI, "FAN CTRL IN"), (JPI, "12V IN"), (JPO, "12V OUT"), (JF, "FAN | CTRL OUT")):
        xs = [p.GetPosition().x for p in k.fps[ref].Pads() if p.GetNumber()]
        k.text(s_, (P.ToMM(min(xs)) + P.ToMM(max(xs))) / 2 - k.O[0], 23.2, P.B_SilkS, 1.0, mirror=True)
    for ref in (JFI, JF):
        x, y = k.padxy(ref, "1")
        k.text("1", x, y + 2.3, P.B_SilkS, 1.0, mirror=True)
    for c, xc in enumerate(XC):
        k.text(f"D{2 * c + 1}  <  SAS {c + 1}  >  D{2 * c}", xc, YJ - 9.6, P.B_SilkS, 1.0, mirror=True)


def finish(k):
    print("trimmed", trim_stubs(k), "open L3 track ends")
    labels(k)
    full = [(0, 0), (W, 0), (W, H), (0, H)]
    k.zone("GND", "L2", full, clearance=0.2, thermal=False)
    k.zone("GND", "L5", full, clearance=0.2, thermal=False)
    k.zone("3V3_AUX", "L3", full, clearance=0.2, thermal=False)
    # L4: 12 V above the drives and as a finger to every eFuse, 3.3 V everywhere else.  The low-speed routes cut the
    # 3.3 V pour on L3 into pieces; the L4 part joins them through every 3.3 V via.
    p12 = [(0, 0), (W, 0), (W, Y12)]
    for xd in reversed(XD):
        p12 += [(xd + 8.8, Y12), (xd + 8.8, Y12 + 11.5), (xd + 4.4, Y12 + 11.5), (xd + 4.4, Y12)]
    k.zone("12V_IN", "L4", p12 + [(0, Y12)], prio=2, clearance=0.25, thermal=False)
    k.zone("3V3_AUX", "L4", [(0, Y12 - 0.5), (W, Y12 - 0.5), (W, H), (0, H)], prio=1, clearance=0.25, thermal=False)
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
    return rpt


EXTRA_DRU = """
(rule "PWR_12V: eFuse pin fan-out (0.5 mm pitch QFN pins inside the EFUSE* areas; the pours carry the current)"
    (condition "A.NetClass == 'PWR_12V' && A.intersectsArea('EFUSE*')")
    (constraint track_width (min 0.2mm)))
(rule "silk may sit on masked copper and tented vias (only pads/holes need clearance)"
    (condition "A.Type != 'Pad' && B.Type != 'Pad'")
    (severity ignore)
    (constraint silk_clearance (min 0mm)))
"""

if __name__ == "__main__":
    k, info = build()
    if STAGE != "place":
        fails = route(k, info)
        for f_ in fails:
            print("FAIL", f_)
    finish(k)
