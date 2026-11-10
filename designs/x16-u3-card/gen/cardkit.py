"""Card-level circuitry shared by the x8 and x16 U.3 cards (rev C).

The region left of the fingers (x 0 .. 45, bracket side) is identical on every card, so the card-level parts sit
there: the 9DBL0442 REFCLK buffer (bottom side), the TCA9548A SMBus switch that hides the card-local bus from the
host, the TPS2116 3.3 V OR, CLKREQ# and WAKE#.  The management trunks (L3) and the REFCLK channel (L6) start here
and run along the window edge to every drive's block (geometry in sideband.py).
"""
import math
import pcbnew as P
from pcbkit import plen
import sideband as sb

RW, RG = 0.128, 0.254                         # REFCLK 100 ohm geometry (outer layers)
UX, UY = 21.0, -20.5                          # 9DBL0442, bottom side, rot 90 (outputs: DIF3 east, DIF2/DIF1 north,
                                              # DIF0 west; inputs on the south face)
DIF = {0: (13, 14), 1: (17, 18), 2: (22, 23), 3: (27, 28)}
OE = {0: 12, 1: 19, 2: 24, 3: 29}
R0402 = ("Resistor_SMD", "R_0402_1005Metric")
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C0603 = ("Capacitor_SMD", "C_0603_1608Metric")
LC = {"10k": "C25744", "4.7k": "C25900", "15k": "C25756", "0R": "C17168", "100nF": "C1525", "10uF": "C19702",
      "FB": "C19330"}


def two(k, ref, fp, val, x, y, rot, bottom, near, net_near, net_far, lcsc, dnp=False, place=True):
    if place:
        k.fp(*fp, ref, val, x, y, rot, bottom=bottom, lcsc=lcsc, dnp=dnp)
    p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
    if math.dist(p1, near) <= math.dist(p2, near):
        k.setpad(ref, "1", net_near); k.setpad(ref, "2", net_far); return p1, p2
    k.setpad(ref, "2", net_near); k.setpad(ref, "1", net_far); return p2, p1


def refclk(k, layer, center, starts, ends, h=0.22, L=0.4, extra=None):
    """Coupled REFCLK pair; skew trimmed with trapezoid bumps on the shorter line, spread over the longest centre
    segments (bump height grows up to 0.4 mm when the pair is short)."""
    res = k.pair(layer, center, starts, ends, RW, RG, dry=True)
    ln = {n: plen(v[0]) + (extra or {}).get(n, 0.0) for n, v in res.items()}
    (short, ls), (_, ll) = sorted(ln.items(), key=lambda kv: kv[1])
    segs = sorted(range(len(center) - 1), key=lambda i: -math.dist(center[i], center[i + 1]))
    for hh, gap in ((h, 0.5), (0.3, 0.5), (0.4, 0.4), (0.5, 0.3), (0.6, 0.3)):
        nb = round((ll - ls) / (2 * hh * (math.sqrt(2) - 1)))
        if nb <= 0:
            return k.pair(layer, center, starts, ends, RW, RG)
        pitch = L + 2 * hh + gap
        plan, left = [], nb
        for si in segs:
            seg = math.dist(center[si], center[si + 1])
            cap = max(0, int((seg - 1.0 + gap) / pitch))
            m = min(cap, left)
            if m:
                plan.append((si, [0.5 + (i - (m - 1) / 2) * pitch / seg for i in range(m)], hh, L))
                left -= m
            if not left:
                break
        if not left:
            plan.sort(key=lambda t: -t[0])            # insert from the far end so earlier indices stay valid
            for si, fr, hh_, L_ in plan:              # DRC: bumps widen the gap locally (rule area TUNE*)
                a_, b_ = center[si], center[si + 1]; seg = math.dist(a_, b_)
                t = ((b_[0] - a_[0]) / seg, (b_[1] - a_[1]) / seg); nrm = (-t[1], t[0]); w_ = RW + RG / 2 + hh_ + 0.2
                f0, f1 = min(fr) * seg - pitch / 2, max(fr) * seg + pitch / 2
                q = lambda f, s_: (a_[0] + t[0] * f + nrm[0] * s_, a_[1] + t[1] * f + nrm[1] * s_)
                k.rule_area(f"TUNE_{short}_{si}", [q(f0, -w_), q(f1, -w_), q(f1, w_), q(f0, w_)])
            return k.pair(layer, center, starts, ends, RW, RG, tune={short: plan})
    raise AssertionError(("no room to deskew", short, ll - ls))


def approach(JP, d, yp):
    """L6 end of a drive's REFCLK pair: arrive heading east under the receptacle's top-row pads; the north line turns
    into E7 (REFCLK+), the south line into E8.  Returns (centre end point, end entries)."""
    e7, e8 = JP("E7"), JP("E8")
    yn = yp + 3.25
    ys = yn + RW + RG
    ends = [(None, [e7, (e7[0], yn)]), (None, [e8, (e8[0], ys)])]
    return (e7[0] - 0.25, (yn + ys) / 2), ends


# DRC additions shared by every card (appended to the board's rules)
DRU = """(rule "REFCLK100: skew-tuning bumps (rule areas TUNE*) widen the gap locally"
    (condition "A.NetClass == 'REFCLK_100' && A.intersectsArea('TUNE*')")
    (constraint diff_pair_gap (min 0.245mm) (max 1.6mm)))
(rule "REFCLK100: uncoupled length incl. skew bumps and via/pin fan-outs <= 8 mm (100 MHz HCSL)"
    (condition "A.NetClass == 'REFCLK_100'")
    (constraint diff_pair_uncoupled (max 8.0mm)))
(rule "REFCLK100: slot clock input <= 16 mm uncoupled (P/N swap crossing at the buffer + its deskew bumps)"
    (condition "A.NetClass == 'REFCLK_100' && A.NetName == 'REFCLK_IN_*'")
    (constraint diff_pair_uncoupled (max 16.0mm)))
(rule "PWR_12V: eFuse pin fan-out (0.5 mm pitch QFN pins, inside the EFUSE* areas; the pours carry the current)"
    (condition "A.NetClass == 'PWR_12V' && A.intersectsArea('EFUSE*')")
    (constraint track_width (min 0.2mm)))"""


class Card:
    def __init__(self, k, R, xpin, fpad, drives, yp_first):
        """drives: [(d, xs, yp, JP)], in order along the card.  xpin(n): finger pin x.  fpad(name) -> pad xy."""
        self.k, self.R, self.xpin, self.fpad, self.drives = k, R, xpin, fpad, drives
        self.yA = yp_first

    # ------------------------------------------------------------------ REFCLK buffer
    def buffer(self, used):
        """used: {drive: DIF index}.  Places the buffer, routes REFCLK_IN and the support parts."""
        k = self.k
        pads = {"1": "GND", "8": "GND", "33": "GND", "4": "3V3_A", "21": "3V3_A", "11": "3V3", "15": "3V3",
                "25": "3V3", "9": "3V3", "10": "3V3", "31": "3V3", "5": "REFCLK_IN_P", "6": "REFCLK_IN_N"}
        for d, i in used.items():
            pads[str(DIF[i][0])], pads[str(DIF[i][1])] = f"REFCLK_{d}_P", f"REFCLK_{d}_N"
        for i, p in OE.items():
            pads[str(p)] = "GND" if i in used.values() else "3V3"        # OE# low = output on; unused outputs off
        k.fp("Package_DFN_QFN", "VQFN-32-1EP_5x5mm_P0.5mm_EP3.15x3.15mm", "U1", "9DBL0442BKILF", UX, UY, 90,
             bottom=True, pads=pads, lcsc="C1540554")
        U = lambda n: k.padxy("U1", str(n))
        self.U = U
        k.rule_area("NECKDOWN_U1", [(UX - 4.0, UY - 4.0), (UX + 4.0, UY - 4.0), (UX + 4.0, UY + 4.0), (UX - 4.0, UY + 4.0)])
        # exposed pad: 3x3 GND vias (filled via-in-pad), pins tied low run straight into the pad
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                k.via("GND", UX + 1.0 * i, UY + 1.0 * j)
        for p in [1, 8] + [OE[i] for i in used.values()]:
            x, y = U(p)
            if abs(y - UY) > 2:                          # north/south face: inward along y
                sy = -math.copysign(1, y - UY)
                pts = [(x, y), (x, y + sy * 0.55)]
                if abs(x - UX) > 1.35:                     # corner pin: dogleg in under the EP edge
                    pts.append((x - math.copysign(0.4, x - UX), y + sy * 0.95))
                else:
                    pts[-1] = (x, UY - sy * 1.2)
            else:
                sx = -math.copysign(1, x - UX)
                pts = [(x, y), (x + sx * 0.55, y)]
                if abs(y - UY) > 1.35:
                    pts.append((x + sx * 0.95, y - math.copysign(0.4, y - UY)))
                else:
                    pts[-1] = (UX - sx * 1.2, y)
            k.track("GND", "L6", pts, 0.2)
        # supplies: each pin -> short L6 stub -> via; decoupling on the top side right over the vias
        out = {}
        stubs = {4: (0, 1.0), 21: (0, -1.0), 11: (-1.0, 0), 15: (-1.0, 0), 25: (1.0, 0), 9: (-1.0, 0), 10: (-1.0, 0),
                 31: (1.0, 0)}
        for p, (dx, dy) in stubs.items():
            x, y = U(p); v = (x + dx, y + dy)
            if p in (9, 10):
                continue
            out[p] = v
        # OE# of the unused outputs (tied high): stub out + via, the router ties them to 3V3
        for i, p in OE.items():
            if i not in used.values():
                x, y = U(p)
                if abs(y - UY) > 2:
                    out[p] = (x, y + math.copysign(1.0, y - UY))
                else:
                    out[p] = (x + math.copysign(1.0, x - UX), y)
        # SMBus pins 9/10 and CKPWRGD 31 tie to 3V3 (bus unused, buffer always on)
        x9, x10 = U(9), U(10)
        k.track("3V3", "L6", [x9, (x9[0] - 0.7, x9[1]), (x10[0] - 0.7, x10[1]), x10], 0.2)
        k.track("3V3", "L6", [U(11), (U(11)[0] - 0.7, U(11)[1]), (x10[0] - 0.7, x10[1])], 0.2)
        out.pop(11)
        out[9] = (x9[0] - 1.3, x9[1] + 0.2)
        k.track("3V3", "L6", [(x9[0] - 0.7, x9[1]), out[9]], 0.2)
        # CKPWRGD (31): own via, then on L1 down to pin 25's supply via (an L6 tie would cut across the DIF3 pair)
        v31 = (U(31)[0] + 1.0, U(31)[1])
        k.track("3V3", "L6", [U(31), v31], 0.2); k.via("3V3", *v31)
        k.track("3V3", "L1", [v31, (U(25)[0] + 1.0, U(25)[1])], 0.2)
        out.pop(31)
        for p, v in out.items():
            net = k.padnet("U1", str(p))
            k.track(net, "L6", [U(p), v], 0.2); k.via(net, *v)
        self.supply_vias = out
        # decoupling (top): 100 nF at each supply via, 10 uF bulk; ferrite 3V3 -> 3V3_A for VDDA/VDDR
        caps = [(out[4], "3V3_A", "C1", "100nF", C0402), (out[21], "3V3_A", "C2", "100nF", C0402),
                (out[9], "3V3", "C3", "100nF", C0402), (out[15], "3V3", "C4", "100nF", C0402),
                (out[25], "3V3", "C5", "100nF", C0402)]
        for v, net, ref, val, fp in caps:
            cx = v[0] + (0.9 if v[0] >= UX else -0.9)
            vp, gp = two(k, ref, fp, val, cx, v[1], 0, False, v, net, "GND", LC[val])
            k.track(net, "L1", [v, vp], 0.25)
            gv = (gp[0] + (0.75 if gp[0] > vp[0] else -0.75), gp[1])
            if ref == "C5":                       # east of C5: the PERST# riser (L3) and the DIF3 pair; go north
                gv = (gp[0], gp[1] - 0.75)
            k.via("GND", *gv); k.track("GND", "L1", [gp, gv], 0.25)
        return out

    # ------------------------------------------------------------------ REFCLK input (fingers A13/A14 -> pins 5/6)
    def refclk_in(self, yrun=-14.2, ykneeA=-7.7, xt1=47.5, ycross=None):
        """A13/A14 -> buffer pins 5/6.  The fingers give P west of N heading north, the bottom-mounted buffer wants P
        east of N entering its south face, so the lines must cross once.  Both lines get exactly two vias: they
        leave the fingers on L6, both move to L1 at xt1 (side-by-side vias), and at the buffer N drops back to L6
        first, passes under P, then P drops; the pair finishes on L6 into the pins."""
        k, U = self.k, self.U
        x13, x14 = self.xpin(13), self.xpin(14)
        xin = (x13 + x14) / 2
        p5, p6 = U(5), U(6)
        xc = (p5[0] + p6[0]) / 2
        d = (RW + RG) / 2
        o = 0.6                                          # via offset from the pair centre (vias 1.2 mm apart)
        VIA_H = 1.5784
        yc = yrun if ycross is None else ycross             # the L1 run may step to another y before the crossing
        # A: L6, fingers -> north -> knee -> west to the first via pair
        cenA = [(xin, -5.76), (xin, ykneeA), (xin - (ykneeA - yrun), yrun), (xt1 + 1.0, yrun)]
        st = [("REFCLK_IN_P", [(x13, -5.62)]), ("REFCLK_IN_N", [(x14, -5.62)])]
        enA = [(None, [(xt1, yrun + o), (xt1 + o - d, yrun + d)]), (None, [(xt1, yrun - o), (xt1 + o - d, yrun - d)])]
        rA = k.pair("L6", cenA, st, enA, RW, RG, dry=True)
        assert abs(rA["REFCLK_IN_P"][0][-2][1] - (yrun + d)) < 1e-6, "REFCLK_IN: P should run south of N"
        k.pair("L6", cenA, st, enA, RW, RG)
        k.via("REFCLK_IN_P", xt1, yrun + o); k.via("REFCLK_IN_N", xt1, yrun - o)
        # crossing at X0 (on L1 heading west, P south / N north): N via at (X0, -o); P runs diagonally north over it
        # to its via at (X0 - 1.6, -o); N runs on L6 diagonally south under P to the south line
        X0 = xc + 6.0
        XP = X0 - 1.6
        Nx = [(X0 + o - d, yc - d), (X0, yc - o)]                               # L1 tail of N
        Px = [(X0 + 0.4, yc + d), (XP + 0.3, yc - o + 0.0), (XP, yc - o)]       # L1 tail of P
        # L6 after the crossing: P north line, N south line, west, then north into the pins (P east)
        yP1, yN1 = yc - d, yc + d
        P6 = [(XP, yc - o), (XP - (o - d), yP1), (p5[0], yP1), p5]
        N6 = [(X0, yc - o), (X0 - 1.2, yc + o), (X0 - 1.2 - (o - d), yN1), (p6[0], yN1), p6]
        assert p5[0] > p6[0]
        # B: L1 coupled run between the two via sites (deskew bumps go here)
        cenB = [(xt1 - 1.0, yrun)] + ([(xt1 - 1.0 - abs(yc - yrun), yc)] if yc != yrun else []) + [(X0 + 1.0, yc)]
        stB = [("REFCLK_IN_P", [(xt1, yrun + o), (xt1 - o + d, yrun + d)]),
               ("REFCLK_IN_N", [(xt1, yrun - o), (xt1 - o + d, yrun - d)])]
        enB = [(None, [Px[0]]), (None, [Nx[0]])]
        lA = {n: plen(v[0]) for n, v in rA.items()}
        tail = {"REFCLK_IN_P": lA["REFCLK_IN_P"] + plen(Px) + plen(P6) + 2 * VIA_H,
                "REFCLK_IN_N": lA["REFCLK_IN_N"] + plen(Nx) + plen(N6) + 2 * VIA_H}
        rB = refclk(k, "L1", cenB, stB, enB, extra=tail)
        # the P/N swap: the lines run apart (vias 1.6 mm) between XP and X0; same gap allowance as the deskew bumps
        k.rule_area("TUNE_REFCLK_IN_X", [(XP - 1.2, yc - 1.2), (X0 + 1.2, yc - 1.2), (X0 + 1.2, yc + 1.2), (XP - 1.2, yc + 1.2)])
        k.track("REFCLK_IN_P", "L1", Px, RW); k.via("REFCLK_IN_P", XP, yc - o)
        k.track("REFCLK_IN_N", "L1", Nx, RW); k.via("REFCLK_IN_N", X0, yc - o)
        k.track("REFCLK_IN_P", "L6", P6, RW)
        k.track("REFCLK_IN_N", "L6", N6, RW)
        lP = plen(rB["REFCLK_IN_P"][0]) + tail["REFCLK_IN_P"]
        lN = plen(rB["REFCLK_IN_N"][0]) + tail["REFCLK_IN_N"]
        self.refin_skew = lP - lN
        return lP - lN

    # ------------------------------------------------------------------ card-level parts
    def parts(self):
        """TCA9548A (slot SMBus -> card-local bus on ch0, address 0x77 with A0-A2 pulled up; close SJ1-SJ3 to move it
        to 0x70-0x76 if the host already uses 0x77, never onto 0x70-0x73 where the drives' TCA9543As sit on the
        local side), TPS2116 3.3 V OR (VIN1 = slot 3.3Vaux has priority, VIN2 = slot 3.3 V), buffer ferrite."""
        k = self.k
        # TCA9548A, rot 180: pins 1-12 on the east side (A0, A1, RESET#, SD0, SC0 bottom-up), 13-24 west (SCL/SDA/VCC)
        k.fp("Package_SO", "TSSOP-24_4.4x7.8mm_P0.65mm", "U2", "TCA9548APWR", 6.4, -21.5, 180, pads={
            "1": "MUXA0", "2": "MUXA1", "3": "MUX_RST_N", "4": "SMDAT", "5": "SMCLK", "12": "GND", "21": "MUXA2",
            "22": "SMCLK_SLOT", "23": "SMDAT_SLOT", "24": "3V3_AUX"}, lcsc="C130026")
        # TPS2116 (SOT-583): 1 GND, 2/7 VOUT, 3 VIN1, 4 PR1, 5 MODE (= VIN1), 6 VIN2, 8 ST (open)
        k.fp("Package_TO_SOT_SMD", "SOT-583-8", "U3", "TPS2116DRLR", 10.2, -14.2, 0, pads={
            "1": "GND", "2": "3V3_AUX", "3": "3V3_AUX_SLOT", "4": "PR1", "5": "3V3_AUX_SLOT", "6": "3V3",
            "7": "3V3_AUX"}, lcsc="C3235557")
        # 0.5 mm pitch: hand escapes.  VOUT 2-7 and VIN1 3-5 (MODE) tie under the body; stub ends are router terminals
        u = lambda q: k.padxy("U3", q)
        k.track("3V3_AUX", "L1", [u("2"), u("7")], 0.2)
        k.track("3V3_AUX_SLOT", "L1", [u("3"), (u("3")[0] + 0.5, u("3")[1]), (u("5")[0] - 0.5, u("5")[1]), u("5")], 0.15)
        g = (u("1")[0] - 0.75, u("1")[1] - 0.35)
        k.track("GND", "L1", [u("1"), (u("1")[0] - 0.4, u("1")[1]), g], 0.2); k.via("GND", *g)
        self.u3t = {"PR1": (u("4")[0] - 0.75, u("4")[1] + 0.35), "3V3_AUX_SLOT": (u("3")[0] - 0.8, u("3")[1]),
                    "3V3": (u("6")[0] + 0.8, u("6")[1]), "3V3_AUX": (u("7")[0] + 0.8, u("7")[1])}
        k.track("PR1", "L1", [u("4"), (u("4")[0] - 0.4, u("4")[1]), self.u3t["PR1"]], 0.15)
        for net, q in (("3V3_AUX_SLOT", "3"), ("3V3", "6"), ("3V3_AUX", "7")):
            k.track(net, "L1", [u(q), self.u3t[net]], 0.15)
        # 10k x4: A0, A1, A2, RESET# pull-ups
        k.fp("Resistor_SMD", "R_Array_Convex_4x0603", "RN10", "10k x4", 13.4, -18.9, 0, lcsc="C29718")
        ps = {q.GetNumber(): k.padxy("RN10", q.GetNumber()) for q in k.fps["RN10"].Pads()}
        near = sorted([q for q in ps if ps[q][0] < 13.4], key=lambda q: ps[q][1])
        for q, net in zip(near, ("MUXA2", "MUXA1", "MUX_RST_N", "MUXA0")):
            k.setpad("RN10", q, net)
        for q in ps:
            if q not in near:
                k.setpad("RN10", q, "3V3_AUX")
        self.two = []
        for i, (net, x) in enumerate((("MUXA0", 13.4), ("MUXA1", 16.0), ("MUXA2", 18.6))):
            ref = f"SJ{i + 1}"
            k.fp("Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", ref, f"A{i} (close = 0)", x, -27.4, 90,
                 bom=False)
            self.two.append((ref, two(k, ref, None, None, x, -27.4, 90, False, (x, -26.0), net, "GND", None, place=False)))
        L = [("R1", R0402, "4.7k", 12.0, -30.2, 90, (12.0, -31.2), "SMCLK", "3V3_AUX"),
             ("R2", R0402, "4.7k", 13.0, -30.2, 90, (13.0, -31.2), "SMDAT", "3V3_AUX"),
             ("C6", C0402, "100nF", 3.0, -16.4, 0, (3.5, -17.4), "3V3_AUX", "GND"),
             ("R3", R0402, "15k", 8.0, -14.2, 90, (8.0, -13.2), "PR1", "3V3_AUX_SLOT"),
             ("R4", R0402, "10k", 7.0, -14.2, 90, (7.0, -13.2), "PR1", "GND"),
             ("C7", C0402, "100nF", 12.5, -14.9, 90, (12.5, -14.0), "3V3_AUX_SLOT", "GND"),
             ("C8", C0402, "100nF", 13.5, -14.9, 90, (13.5, -14.0), "3V3", "GND"),
             ("C9", C0603, "10uF", 14.9, -15.2, 90, (14.9, -14.0), "3V3_AUX", "GND"),
             ("FB1", ("Inductor_SMD", "L_0603_1608Metric"), "600R@100MHz", 17.2, -16.4, 0, (16.0, -16.4), "3V3",
              "3V3_A")]
        for ref, fp, val, x, y, rot, near_, na, nb in L:
            lc = LC["FB"] if ref == "FB1" else LC.get(val, {"4.7k": "C25900", "15k": "C25756"}.get(val))
            self.two.append((ref, two(k, ref, fp, val, x, y, rot, False, near_, na, nb, lc)))

    def wire(self):
        """Connect the card-level parts with the router (after the risers): GND pads to stub vias, the rest to their net."""
        k, R = self.k, self.R
        T = lambda ref, q: ("L1", *k.padxy(ref, q))
        fails = []
        # PR1 divider: hand hop from U3's PR1 escape to R3's PR1 pad (right next to it)
        q3 = [q.GetNumber() for q in k.fps["R3"].Pads() if q.GetNetname() == "PR1"][0]
        k.track("PR1", "L1", [self.u3t["PR1"], k.padxy("R3", q3)], 0.15)

        def go(f, *a, **kw):
            try:
                f(*a, **kw)
            except RuntimeError as e:
                if "no target copper" not in str(e) or a[0] in R.conn:
                    fails.append((a, str(e)))
        for ref, q in (("U2", "12"),):
            go(R.to_via, "GND", T(ref, q))
        for ref, (pa, pb) in self.two:
            for p in (pa, pb):
                net = [q.GetNetname() for q in k.fps[ref].Pads() if math.dist(k.padxy(ref, q.GetNumber()), p) < 1e-6][0]
                if net == "GND":
                    go(R.to_via, "GND", ("L1", *p))
        for ref in ("U2", "RN10"):
            for q in k.fps[ref].Pads():
                net = q.GetNetname()
                if ref == "U2" and net in ("SMCLK", "SMDAT"):      # hand risers
                    continue
                if net and net != "GND":
                    go(R.to_net, net, T(ref, q.GetNumber()), maxpad=24.0, via_cost=1.0, layer_cost={"L6": 3.0})
        for ref, (pa, pb) in self.two:
            for p in (pa, pb):
                net = [q.GetNetname() for q in k.fps[ref].Pads() if math.dist(k.padxy(ref, q.GetNumber()), p) < 1e-6][0]
                if net != "GND":
                    go(R.to_net, net, ("L1", *p), maxpad=24.0, via_cost=1.0, layer_cost={"L6": 3.0})
        for a, e in fails:
            print("FAIL card wire", a, e)
        return fails

    def wake_clkreq(self):
        """B11 WAKE# -> via (L3 trunk); B12 CLKREQ# -> GND."""
        k, xpin, fpad = self.k, self.xpin, self.fpad
        x11, x12 = xpin(11), xpin(12)
        vw = (x11 + 0.55, -11.3)
        k.track("PCIE_WAKE_N", "L1", [(x11, -5.4), (x11, -9.4), (x11 + 0.55, -9.95), vw], 0.2)
        k.via("PCIE_WAKE_N", *vw)
        self.vwake = vw
        # CLKREQ# tied low (clock always requested, as on cards without clock power management): B12 joins
        # the B13 GND via of the finger GND row
        k.setpad("J1", "B11", "PCIE_WAKE_N"); k.setpad("J1", "B12", "GND")
        k.track("GND", "L1", [(x12, -5.4), (x12, -6.35), (x12 + 0.4, -6.75)], 0.2)

    # ------------------------------------------------------------------ REFCLK to the drives
    def clock_direct(self, d, dif):
        """Drive A: straight east from the buffer's east face (DIF3) to the receptacle on L6."""
        k, U = self.k, self.U
        _, xs, yp, JP = [t for t in self.drives if t[0] == d][0]
        pp, pn = DIF[dif]
        y0 = (U(pp)[1] + U(pn)[1]) / 2
        cend, ends = approach(JP, d, yp)
        x0 = U(pp)[0] + 0.7
        cen = [(x0, y0), (cend[0] - 1.5 - abs(cend[1] - y0), y0), (cend[0] - 1.5, cend[1]), cend]
        r = refclk(k, "L6", cen, [(f"REFCLK_{d}_P", [U(pp)]), (f"REFCLK_{d}_N", [U(pn)])], ends)
        self._check(d, r, JP)
        return r

    def clock_channel(self, d, dif, row, xdrop, col_dx=0.0, steps=()):
        """REFCLK pair from a north/west face output: up a column to its channel row (y), east under the drives,
        south at xdrop, east into the target receptacle.  steps: [(x0, x1, dy)] diagonal jogs of the row."""
        k, U = self.k, self.U
        _, xs, yp, JP = [t for t in self.drives if t[0] == d][0]
        pp, pn = DIF[dif]
        a, b = U(pp), U(pn)
        cend, ends = approach(JP, d, yp)
        if abs(a[1] - b[1]) < 1e-6:              # north face: straight up
            xc = (a[0] + b[0]) / 2 + col_dx
            cen = [(xc, a[1] - 0.7)]
        else:                                     # west face: out west, then up
            yc = (a[1] + b[1]) / 2
            xc = a[0] - 1.6 + col_dx
            cen = [(a[0] - 0.7, yc), (xc + 0.6, yc), (xc, yc - 0.6)]
        cen += [(xc, row + 0.6), (xc + 0.6, row)]
        y = row
        for x0, x1, dy in steps:
            cen += [(x0, y), (x1, y + dy)]
            y += dy
        cen += [(xdrop - 0.6, y), (xdrop, y + 0.6), (xdrop, cend[1] - 0.6), (xdrop + 0.6, cend[1]), cend]
        r = refclk(k, "L6", cen, [(f"REFCLK_{d}_P", [a]), (f"REFCLK_{d}_N", [b])], ends)
        self._check(d, r, JP)
        return r

    def _check(self, d, r, JP):
        p = r[f"REFCLK_{d}_P"][0][-1]
        assert math.dist(p, JP("E7")) < 1e-6, f"REFCLK_{d}: P does not end on E7"
        self.k.setpad(f"J{d}", "E7", f"REFCLK_{d}_P"); self.k.setpad(f"J{d}", "E8", f"REFCLK_{d}_N")
        lp, ln = plen(r[f"REFCLK_{d}_P"][0]), plen(r[f"REFCLK_{d}_N"][0])
        print(f"REFCLK_{d}: {lp:.2f} / {ln:.2f} mm, skew {lp - ln:+.3f}")

    # ------------------------------------------------------------------ management trunks (L3)
    def trunks(self, starts, steps=(), aux_taps=()):
        """starts: {net: x of the line start at the card's left end}.  Lines run at sideband.TRK_Y (relative to each
        drive's peg line).  At every block the line dips into a U on L3 under the gap between the I/O expander and
        the SMBus switch (nested: the edge-side line makes the smallest, shallowest U), with a tap via on the U's
        bottom below the band; the last block gets a hook down to its tap via.  The blocks' parts connect to the tap
        vias on L1.  steps: [(x0, x1)] where the channel moves between peg lines (x16 window step).
        aux_taps: x positions between blocks where 3V3_AUX gets an extra tap via (lines 2-4 dip in nested U's;
        the vias go to self.aux_taps).  Returns {net: start point} for the risers."""
        k, R = self.k, self.R
        P_ = 1.2
        E_MID = [1.5 - P_ * i for i in range(5)]
        S_MID = [3.5 + P_ * i for i in range(5)]
        self.tr_lines, self.taps, self.aux_taps = {}, {}, []
        first = {}
        for i, net in enumerate(sb.TRUNKS):
            ty, yu = sb.TRK_Y[i], sb.TAP_Y[i]
            x0 = starts[net]
            pts = [(x0, self.drives[0][2] + ty)]
            first[net] = pts[0]
            taps = []
            ypr = self.drives[0][2]
            for j, (d, xs, yp, JP) in enumerate(self.drives):
                if yp != ypr:
                    sg = 1 if yp < ypr else -1         # stepping north: the edge-side line turns first
                    for (sx0, sx1) in steps:
                        if pts[-1][0] < sx0 < xs:
                            pts += [(sx0 + sg * 0.4 * i, ypr + ty), (sx1 + sg * 0.4 * i, yp + ty)]
                ypr = yp
                for xd in sorted(aux_taps):
                    if i >= 2 and pts[-1][0] < xd < xs:
                        hw = 0.6 + 0.45 * (i - 2)                 # 3V3_AUX innermost; PERST#, WAKE# around it
                        yd = yp + sb.TRK_Y[2] + 1.25 + 0.6 * (i - 2)
                        pts += [(xd - hw, yp + ty), (xd - hw, yd), (xd + hw, yd), (xd + hw, yp + ty)]
                        if i == 2:
                            self.aux_taps.append((xd, yd)); k.via(net, xd, yd)
                xe, xr = xs + E_MID[i], xs + S_MID[i]
                if j == len(self.drives) - 1:
                    pts += [(xe, yp + ty), (xe, yp + yu)]
                    tv = (xe, yp + yu)
                else:
                    pts += [(xe, yp + ty), (xe, yp + yu), (xr, yp + yu), (xr, yp + ty)]
                    tv = ((xe + xr) / 2 if i == 0 else xe + P_ / 2, yp + yu)
                k.via(net, *tv)
                taps.append(tv)
            k.track(net, "L3", pts, sb.TRK_W)
            self.tr_lines[net], self.taps[net] = pts, taps
        return first

    def seed_trunks(self):
        """Root the trunks (call after the risers from the sources are routed)."""
        for net, pts in self.tr_lines.items():
            self.R.seed(net, [("L3", "seg", (p[0], p[1], q[0], q[1], sb.TRK_W / 2)) for p, q in zip(pts, pts[1:])] +
                        [("all", "circle", (x, y, 0.25)) for x, y in self.taps[net] +
                         (self.aux_taps if net == "3V3_AUX" else [])])

    def after_block(self, j):
        pass

