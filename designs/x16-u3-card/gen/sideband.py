"""Per-drive sideband + power block, identical on every U.3 slot card (x8, x16 3-drive, x16 4-drive).  Rev C.

Relative frame: X = x - xs, Y = y - yp (receptacle centre xs, peg line yp; Y negative = toward the mating face).
The receptacle sits on the bottom side; its housing face is at Y -10.05, the window edge at Y -9.4.

  * Sideband logic on the TOP side over the receptacle body (X -19.5 .. 10.5, Y -3.3 .. -8.9):
      TCA9543A  SMBus switch, address 0x70 + idx on the card-local bus; ch0 -> drive SMBus (E23/E24), ch1 unused.
      TCA9554   I/O expander, address 0x20 + idx on the card-local bus.
          P0 PWRDIS (out, 10k pull-down = powered)       P4 PRSNT#  (in, 10k pull-up)
          P1 DualPortEn# (out, 10k pull-up = single port) P5 IfDet#  (in, 10k pull-up)
          P2 RST_EN (out, 10k pull-up = follows PERST#)   P6 IfDet2# (in, 10k pull-up)
          P3 locate LED (out, low = on)                    P7 WAKE#   (in, 10k pull-up)
          Program the output register (0x01) before the configuration register (0x03), so the pins never glitch.
      74LVC1G11 PERST0#/PERST1# = slot PERST# AND RST_EN AND PG (the drive's eFuse power-good): a drive is held in
                reset until its own 12 V is up, and software can hold one drive in reset.
      74LVC1G07 drive WAKE# -> slot WAKE# (B11), open drain, wired-OR across drives.
    The card-local bus (SMCLK/SMDAT) sits behind the card's TCA9548A (channel 0), so none of these addresses
    reach the host's SMBus segment.
  * Power in the gap to the next receptacle (X 23 .. 47): a 1x3 2.54 mm SMD header + shunt selects the drive's
    12 V source (2-3 = slot 12 V, default; 1-2 = aux 12 V from the card's 6-pin; one shunt can never join the two),
    then a TPS25982 eFuse (~3.2 A circuit breaker, latch-off, soft start) feeds 12V_DRV_x on an L6 pour to the
    drive's P13-P15 and the bulk caps.  Its PG gates the drive's PERST#.
Everything logic runs from 3V3_AUX, the card's local 3.3 V (slot 3.3Vaux, or slot 3.3 V through the ideal-diode OR).
"""
import math

R0402 = ("Resistor_SMD", "R_0402_1005Metric")
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C1206 = ("Capacitor_SMD", "C_1206_3216Metric")
LCSC = {"10k": "C25744", "4.7k": "C25900", "1k": "C11702", "100nF": "C1525", "10uF": "C13585", "22uF": "C12891",
        "470R": "C25117", "100k": "C25741", "15k": "C25756", "1nF": "C1523"}

# ---------------------------------------------------------------- channel geometry (relative to the peg line)
YEDGE = -9.4                                   # window edge: housing face at -10.05, 0.65 mm margin
TRUNKS = ["SMCLK", "SMDAT", "3V3_AUX", "PCIE_RST_N", "PCIE_WAKE_N"]   # L3, edge side first
TRK_Y = [-8.95, -8.5, -8.05, -7.6, -7.15]
TRK_W = 0.2
TAP_Y = [-6.55, -5.95, -5.35, -4.75, -4.15]     # trunk tap vias (bottom of each line's U at a block), edge side first
CLK_Y = [-8.145, -7.135, -6.125]               # L6 REFCLK pair centres, edge side first (>= 1 mm from the edge)
YSPLIT = -2.2                                  # L4: slot 12 V toward the fingers, 12V_AUX toward the window


def place2(k, ref, fp, val, x, y, rot, bottom, nets, lcsc):
    """Two-pad part; nets = (net of pad nearer to -X/-Y after rotation, other)."""
    k.fp(*fp, ref, val, x, y, rot, bottom=bottom, lcsc=lcsc)
    p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
    first = "1" if (p1[0] + p1[1] * 0.001) < (p2[0] + p2[1] * 0.001) or (rot % 180 == 90 and p1[1] < p2[1]) else "2"
    other = "2" if first == "1" else "1"
    k.setpad(ref, first, nets[0]); k.setpad(ref, other, nets[1])
    return k.padxy(ref, first), k.padxy(ref, other)


def block(k, R, d, idx, xs, yp, JP, refbase, rbase, cbase):
    """Place drive d's block and lay its fixed power copper.  JP(n) -> receptacle pad xy.  Returns an info dict."""
    X = lambda v: xs + v
    Y = lambda v: yp + v
    XY = lambda a, b: (X(a), Y(b))
    a0, a1, a2 = idx & 1, (idx >> 1) & 1, (idx >> 2) & 1
    S = lambda b: "3V3_AUX" if b else "GND"
    n = lambda s: f"{s}_{d}"
    # ---------------------------------------------------------------- drive pin nets
    for pin, net in (("E4", n("DRST")), ("E5", n("DRST")), ("E6", n("IFDET2")), ("P1", n("WAKE")),
                     ("P3", n("PWRDIS")), ("P4", n("IFDET")), ("P10", n("PRSNT")), ("E23", n("SMBCLK")),
                     ("E24", n("SMBDAT")), ("E25", n("DPEN")), ("P13", n("12V_DRV")), ("P14", n("12V_DRV")),
                     ("P15", n("12V_DRV"))):
        k.setpad(f"J{d}", pin, net)
    um, ue, ug, uw, uf = (f"U{refbase}", f"U{refbase + 1}", f"U{refbase + 2}", f"U{refbase + 3}", f"U{30 + idx}")
    jh, dl = f"JP{idx + 1}", f"D{10 + idx}"
    # ---------------------------------------------------------------- logic (top, over the receptacle body)
    k.fp("Package_TO_SOT_SMD", "SOT-353_SC-70-5", uw, "SN74LVC1G07DCKR", *XY(-17.6, -4.55), 0, pads={
        "2": n("WAKE"), "3": "GND", "4": "PCIE_WAKE_N", "5": "3V3_AUX"}, lcsc="C7830")
    k.fp("Package_TO_SOT_SMD", "SOT-363_SC-70-6", ug, "SN74LVC1G11DCKR", *XY(-17.6, -7.75), 0, pads={
        "1": "PCIE_RST_N", "2": "GND", "3": n("RSTEN"), "4": n("DRST"), "5": "3V3_AUX", "6": n("PG")}, lcsc="C529281")
    k.fp("Package_SO", "TSSOP-16_4.4x5mm_P0.65mm", ue, "TCA9554PWR", *XY(-10.2, -6.15), 0, pads={
        "1": S(a0), "2": S(a1), "3": S(a2), "4": n("PWRDIS"), "5": n("DPEN"), "6": n("RSTEN"), "7": n("LOC"),
        "8": "GND", "9": n("PRSNT"), "10": n("IFDET"), "11": n("IFDET2"), "12": n("WAKE"),
        "14": "SMCLK", "15": "SMDAT", "16": "3V3_AUX"}, lcsc="C477924")
    k.fp("Package_SO", "TSSOP-14_4.4x5mm_P0.65mm", um, "TCA9543APWR", *XY(15.0, -6.15), 180, pads={
        "1": S(a0), "2": S(a1), "3": n("MUXCTL"), "4": n("MUXCTL"), "5": n("SMBDAT"), "6": n("SMBCLK"),
        "7": "GND", "8": n("MUXCTL"), "9": n("SD1"), "10": n("SC1"), "12": "SMCLK", "13": "SMDAT",
        "14": "3V3_AUX"}, lcsc="C2653307")
    k.fp("LED_SMD", "LED_0603_1608Metric", dl, "yellow (locate)", *XY(9.6, -8.4), 180,
         pads={"1": n("LOC"), "2": n("LOCA")}, lcsc="C72038")

    def array(ref, val, lc, x, y, sigs, toward):
        """4x0603 array (top); the pad column nearer x=toward carries sigs (top = more negative y first)."""
        k.fp("Resistor_SMD", "R_Array_Convex_4x0603", ref, val, X(x), Y(y), 0, lcsc=lc)
        ps = {p.GetNumber(): k.padxy(ref, p.GetNumber()) for p in k.fps[ref].Pads()}
        near = sorted([q for q in ps if abs(ps[q][0] - X(toward)) < abs((2 * X(x) - ps[q][0]) - X(toward))],
                      key=lambda q: ps[q][1])
        far = [q for q in ps if q not in near]
        for q, net in zip(near, sigs):
            k.setpad(ref, q, net)
        for q in far:
            k.setpad(ref, q, "3V3_AUX")
        return [(ref, (ps[q], ps[str(9 - int(q))]), (net, "3V3_AUX"), False) for q, net in zip(near, sigs)]

    parts = []
    parts += array(f"RN{2 * idx + 2}", "10k x4", "C29718", -3.8, -4.95,
                   (n("WAKE"), n("IFDET2"), n("IFDET"), n("PRSNT")), -10.2)
    parts += array(f"RN{2 * idx + 1}", "4.7k x4", "C1980", 20.4, -5.6,
                   (n("SC1"), n("SD1"), n("SMBDAT"), n("SMBCLK")), 15.0)
    rr = [("GND", n("PWRDIS"), "10k", -5.0, -7.55, 0),
          ("3V3_AUX", n("RSTEN"), "10k", -5.0, -8.55, 0),
          ("3V3_AUX", n("PG"), "10k", -15.0, -8.75, 0),
          ("3V3_AUX", n("MUXCTL"), "10k", 10.0, -5.6, 0),
          ("3V3_AUX", n("LOCA"), "1k", 10.0, -7.15, 0)]
    cc = [("3V3_AUX", "GND", "100nF", -15.0, -4.1, 90),           # G07
          ("3V3_AUX", "GND", "100nF", -15.0, -6.6, 90),           # G11
          ("3V3_AUX", "GND", "100nF", -5.88, -3.75, 90),          # expander (pin 16 top right)
          ("3V3_AUX", "GND", "100nF", 19.8, -8.45, 0)]           # switch (pin 14 top right)
    for i, (na, nb, val, x, y, rot) in enumerate(rr):
        ref = f"R{rbase + i}"
        parts.append((ref, place2(k, ref, R0402, val, X(x), Y(y), rot, False, (na, nb), LCSC[val]), (na, nb), False))
    # PWRDIS pull-down sits over the L3 trunks (no via room) and gets boxed in by the expander fan-out: its GND
    # via is laid now, just south of the trunk strip (WAKE# trunk edge y -31.05, via top -30.75)
    gp = parts[-len(rr)][1][0]
    early_gnd = [gp]
    k.via("GND", gp[0], gp[1] + 1.05); k.track("GND", "L1", [gp, (gp[0], gp[1] + 1.05)], 0.2)
    for i, (na, nb, val, x, y, rot) in enumerate(cc):
        ref = f"C{cbase + i}"
        parts.append((ref, place2(k, ref, C0402, val, X(x), Y(y), rot, False, (na, nb), LCSC[val]), (na, nb), False))

    # ---------------------------------------------------------------- power (gap to the next receptacle)
    sel, drv = n("12V_SEL"), n("12V_DRV")
    JX, JY = 28.2, -2.2
    k.fp("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical_SMD_Pin1Left", jh,
         "12V src: 2-3 SLOT (default), 1-2 AUX", *XY(JX, JY), 0,
         pads={"3": "12V", "2": sel, "1": "12V_AUX"}, lcsc="C6886650")
    pj = {q: k.padxy(jh, q) for q in "123"}
    assert pj["1"][1] < pj["3"][1] and pj["2"][0] > pj["1"][0], "jumper orientation"
    # slot 12 V via toward the fingers (L4 slot band), aux 12 V via toward the window (L4 aux area)
    vs, va = XY(JX - 3.6, JY + 3.4), XY(JX - 3.6, JY - 1.75)   # va: L4 aux side, clear of the PG run (L6)
    k.via("12V", *vs, 0.8, 0.4); k.track("12V", "L1", [pj["3"], (vs[0] + 0.6, pj["3"][1]), vs], 0.8)
    k.via("12V_AUX", *va, 0.8, 0.4); k.track("12V_AUX", "L1", [pj["1"], (va[0] + 0.6, pj["1"][1]), va], 0.8)
    for dx in (-1.1,):
        k.via("12V", vs[0] + dx, vs[1], 0.8, 0.4); k.track("12V", "L1", [vs, (vs[0] + dx, vs[1])], 0.8)
        k.via("12V_AUX", va[0] + dx, va[1], 0.8, 0.4); k.track("12V_AUX", "L1", [va, (va[0] + dx, va[1])], 0.8)
    # eFuse, unrotated: IN pins 1-3 face the jumper, OUT pins 19-24 face the window, control pins toward the fingers
    EX, EY = 36.4, -2.0
    k.fp("u3adapter", "TI_RGE0024M_VQFN-24_4x4mm_P0.5mm_SplitEP", uf, "TPS259824ONRGER", *XY(EX, EY), 0, pads={
        **{str(p): sel for p in (1, 2, 3, 16, 25)}, **{str(p): "GND" for p in (4, 5, 10, 11, 12, 14, 26)},
        **{str(p): drv for p in (17, 18, 19, 20, 21, 22, 23, 24)},
        "6": n("EN"), "8": n("ILIM"), "9": n("IMON"), "13": n("PG"), "15": n("DVDT")}, lcsc="C2155759")
    P_ = lambda q: k.padxy(uf, str(q))
    k.rule_area(f"EFUSE_{d}", [XY(EX - 2.6, EY - 2.6), XY(EX + 2.6, EY - 2.6), XY(EX + 2.6, EY + 2.6), XY(EX - 2.6, EY + 2.6)])
    ein = (X(EX), Y(EY - 0.625)); egn = (X(EX), Y(EY + 0.925))
    for q in (1, 2, 3):
        k.track(sel, "L1", [P_(q), (ein[0] - 1.2, P_(q)[1])], 0.24)
    k.track(sel, "L1", [P_(16), (ein[0] + 1.2, P_(16)[1])], 0.24)
    for q in (4, 5):
        k.track("GND", "L1", [P_(q), (egn[0] - 1.2, egn[1])], 0.24)
    k.track("GND", "L1", [P_(14), (egn[0] + 1.2, egn[1])], 0.24)
    for q in (10, 11, 12):
        k.track("GND", "L1", [P_(q), (P_(q)[0], egn[1] + 0.3)], 0.24)
    for dx in (-0.8, 0.0, 0.8):                     # GND exposed pad: filled vias to the GND planes
        k.via("GND", egn[0] + dx, egn[1])
    for q in (17, 18):
        k.track(drv, "L1", [P_(q), (P_(q)[0] + 0.55, P_(q)[1]), (P_(q)[0] + 0.55, P_(19)[1]), P_(19)], 0.24)
    # 12V_SEL: L1 pour from jumper pin 2 to the IN pins (plus the input cap)
    k.zone(sel, "L1", [XY(JX + 0.7, JY - 1.9), XY(EX - 1.55, JY - 1.9), XY(EX - 1.55, EY - 0.2), XY(JX + 0.7, EY - 0.2)],
           prio=3, clearance=0.25, minw=0.25, thermal=False)
    # 12V_DRV: OUT pins -> top pour -> via row -> L6 pour (bottom, gap + under the receptacle's 12 V end) -> P13-P15
    k.zone(drv, "L1", [XY(EX - 1.5, EY - 1.7), XY(EX + 1.6, EY - 1.7), XY(EX + 1.6, EY - 4.3),
                       XY(EX - 1.5, EY - 4.3)], prio=3, clearance=0.25, minw=0.25, thermal=False)
    for dx in (-1.0, 0.0, 1.0):
        k.via(drv, *XY(EX + dx, EY - 2.5), 0.6, 0.3)
    # (down to -2.0 past the receptacle peg hole so the pour stays one piece; down over the P13-P15 vias)
    k.zone(drv, "L6", [XY(12.3, 0.6), XY(EX + 2.4, 0.6), XY(EX + 2.4, EY - 2.9), XY(33.0, EY - 2.9), XY(33.0, -2.6),
                       XY(16.6, -2.6), XY(16.6, -3.0), XY(12.6, -3.0), XY(12.6, -1.6), XY(12.3, -1.6)],
           prio=3, clearance=0.25, minw=0.25, thermal=False)
    # bulk on 12V_DRV (bottom, in the gap, inside the L6 pour) and the eFuse input cap (top)
    bulk = []
    for i, (x, y, val) in enumerate(((31.0, -0.7, "22uF"), (26.0, -0.7, "22uF"), (36.0, -0.7, "10uF"))):
        ref = f"C{cbase + 4 + i}"
        k.fp(*C1206, ref, f"{val} {'25V' if val == '22uF' else '50V'} X5R", *XY(x, y), 0, bottom=True, lcsc=LCSC[val])
        bulk.append(ref)
    for ref in bulk:
        ps = sorted("12", key=lambda q: k.padxy(ref, q)[0])         # left pad 12V_DRV, right pad GND
        k.setpad(ref, ps[0], drv); k.setpad(ref, ps[1], "GND")
        gp = k.padxy(ref, ps[1])
        # GND via just outside the pad: east of the first cap, toward the fingers under the eFuse parts (top side)
        gv = (gp[0] + 0.9, gp[1]) if gp[0] < X(29.0) else (gp[0], gp[1] + 1.3)
        k.track("GND", "L6", [gp, gv], 0.5); k.via("GND", *gv)
    # eFuse support parts (top), hand-wired at the pins (0.5 mm pitch): EN divider (UVLO ~9.2 V), ILIM (470R ~ 3.2 A
    # breaker), IMON load, dVdT (1 nF).  The router never touches these.
    def r2(ref, val, x, y, rot, nets, lc, fp=R0402):
        k.fp(*fp, ref, val, *XY(x, y), rot, lcsc=lc)
        ps = sorted("12", key=lambda q: (k.padxy(ref, q)[1], k.padxy(ref, q)[0]) if rot % 180 else k.padxy(ref, q))
        k.setpad(ref, ps[0], nets[0]); k.setpad(ref, ps[1], nets[1])
        return k.padxy(ref, ps[0]), k.padxy(ref, ps[1])
    W = 0.15
    en, ilim, imon, dvdt, pg = n("EN"), n("ILIM"), n("IMON"), n("DVDT"), n("PG")
    # EN divider stacked in the 1.35 mm between the jumper's and the eFuse's courtyards
    hi_, lo_ = r2(f"R{rbase + 5}", "100k", 33.3, EY + 0.25, 90, (sel, en), LCSC["100k"])         # top in the SEL pour
    e_, g_ = r2(f"R{rbase + 6}", "15k", 33.3, EY + 2.25, 90, (en, "GND"), LCSC["15k"])
    k.track(en, "L1", [lo_, e_], W); k.track(en, "L1", [(lo_[0], P_(6)[1]), P_(6)], W)
    k.track(sel, "L1", [hi_, (hi_[0], hi_[1] - 0.4)], 0.5)
    k.via("GND", g_[0], g_[1] + 0.8); k.track("GND", "L1", [g_, (g_[0], g_[1] + 0.8)], 0.25)
    il, ilg = r2(f"R{rbase + 7}", "470R", 35.35, 1.35, 90, (ilim, "GND"), LCSC["470R"])
    k.track(ilim, "L1", [P_(8), (P_(8)[0], Y(0.15)), (il[0], Y(0.45)), il], W)
    k.via("GND", ilg[0], ilg[1] + 0.85); k.track("GND", "L1", [ilg, (ilg[0], ilg[1] + 0.85)], 0.25)
    im, img = r2(f"R{rbase + 8}", "10k", 36.35, 1.35, 90, (imon, "GND"), LCSC["10k"])
    k.track(imon, "L1", [P_(9), (P_(9)[0], Y(0.75)), im], W)
    k.via("GND", img[0], img[1] + 0.85); k.track("GND", "L1", [img, (img[0], img[1] + 0.85)], 0.25)
    dv, dvg = r2(f"C{cbase + 7}", "1nF", 39.75, EY + 0.25, 0, (dvdt, "GND"), LCSC["1nF"], fp=C0402)
    k.track(dvdt, "L1", [P_(15), dv], W)
    k.via("GND", dvg[0] + 0.7, dvg[1]); k.track("GND", "L1", [dvg, (dvg[0] + 0.7, dvg[1])], 0.25)
    vpg = XY(EX + 3.2, EY + 1.65)
    k.track(pg, "L1", [P_(13), (P_(13)[0] + 0.8, P_(13)[1]), vpg], W); k.via(pg, *vpg)
    # PG back to the reset gate: L6 under the receptacle housing (between the 12V_DRV pour and the REFCLK rows),
    # then up beside the 74LVC1G07 to the 74LVC1G11 (pin 6)
    YPG = -5.25
    vpg2 = XY(-15.9, -5.35)
    # (dips to -3.6 under the trunk tap vias, which sit on a diagonal across -5.25 between x -3.3 and 2.5)
    k.track(pg, "L6", [vpg, (vpg[0], Y(YPG)), XY(4.0, YPG), XY(2.35, -3.6), XY(-4.5, -3.6), XY(-6.15, YPG),
                       (vpg2[0] + 0.1, Y(YPG)), vpg2], 0.2); k.via(pg, *vpg2)
    p6 = k.padxy(ug, "6")
    k.track(pg, "L1", [vpg2, (vpg2[0], Y(-8.1)), p6], 0.15)
    ref = f"C{cbase + 8}"
    k.fp(*C1206, ref, "10uF 50V X5R", *XY(33.95, -6.0), 0, lcsc=LCSC["10uF"])          # above the eFuse
    ps = sorted("12", key=lambda q: k.padxy(ref, q)[0])
    k.setpad(ref, ps[0], sel); k.setpad(ref, ps[1], "GND")
    k.track(sel, "L1", [k.padxy(ref, ps[0]), (k.padxy(ref, ps[0])[0], Y(JY - 1.6))], 0.6)
    gpad = k.padxy(ref, ps[1])
    k.track("GND", "L1", [gpad, (gpad[0] + 1.2, gpad[1])], 0.5); k.via("GND", gpad[0] + 1.2, gpad[1])
    # silk: jumper legend next to the pins (pin 1 = AUX, pin 3 = SLOT), drive letter
    k.text("AUX", X(JX - 4.6), Y(JY - 4.0), size=1.0)
    k.text("SLOT", X(JX - 4.9), Y(JY + 4.2), size=1.0)
    k.text(f"12V {d}", X(JX + 3.0), Y(JY + 4.5), size=1.0)
    # keep the router off the power pours and the jumper/eFuse field
    R.keepouts.append(("L1", [XY(JX - 2.4, JY - 3.8), XY(EX + 2.3, JY - 3.8), XY(EX + 2.3, JY + 2.0), XY(JX - 2.4, JY + 2.0)]))
    R.keepouts.append(("L6", [XY(12.2, 1.2), XY(EX + 2.5, 1.2), XY(EX + 2.5, EY - 3.0), XY(32.9, EY - 3.0), XY(32.9, -2.7),
                             XY(16.7, -2.7), XY(16.7, -3.1), XY(12.5, -3.1), XY(12.5, -1.7), XY(12.2, -1.7)]))
    return dict(parts=parts, early_gnd=early_gnd, um=um, ue=ue, ug=ug, uw=uw, uf=uf, jh=jh, dl=dl, bulk=bulk, xs=xs, yp=yp, vpg=vpg)


FANOUTS = ((), ("U6", "U5"), ("U12", "U13", "E14", "E15", "U6", "U5"))


BLOCK_CLEARANCE = 0.15          # Default netclass clearance; the card-level routes keep the router's 0.2


def route_block(k, R, d, info, JP, yvm, yvt):
    """Wire the block with the maze router (after the trunks and clocks exist).  Tries a few fan-out strategies; a
    failed attempt is ripped up (its tracks and vias removed, router state restored)."""
    fails = _route_block_once(k, R, d, info, JP, yvm, yvt, ())
    for e in fails:
        print("FAIL", e)
    return fails


def _route_block_once(k, R, d, info, JP, yvm, yvt, fan):
    n = lambda s: f"{s}_{d}"
    um, ue, ug, uw, uf, dl = info["um"], info["ue"], info["ug"], info["uw"], info["uf"], info["dl"]
    pad = lambda ref, p: k.padxy(ref, p)
    side = lambda ref: "L6" if k.fps[ref].IsFlipped() else "L1"
    T = lambda ref, p: (side(ref), *pad(ref, p))
    via = lambda pin: ("all", JP(pin)[0], yvt if pin.startswith("E2") else yvm)
    xs, yp = info["xs"], info["yp"]
    fails, retry = [], []
    L3 = dict(layer_cost={"L1": 2.0, "L6": 2.0}, via_cost=1.0)

    tasks = []

    def tryit(f, *a, **kw):
        if a[0] not in ("GND", "3V3_AUX"):          # 0.127 / 0.15 signals in the block (fab min 0.1 / 0.1)
            kw.setdefault("w", 0.127)
        tasks.append((f, a, kw))
    ics = (um, ue, ug, uw, dl)
    taps_left = dict(info.get("taps", {}))

    def nearest(net, p):
        best = 1e9
        for ref in ics:
            for q in k.fps[ref].Pads():
                if q.GetNetname() == net:
                    best = min(best, math.dist(p, k.padxy(ref, q.GetNumber())))
        return best
    # the locate LED line crosses the whole block: lay it first
    tryit(R.route, n("LOC"), T(dl, "1"), T(ue, "7"), via_cost=1.0)
    # card-bus / supply / slot pins first, while the corners around the ICs are still open
    # (lowest pin first, so the upper pins wrap around it), then the strap pins (GND vias / 3V3_AUX)
    for ref, pins in ((ue, ("14", "15", "16")), (um, ("12", "13", "14")), (ug, ("5", "1")), (uw, ("5", "4")),
                      (ue, ("3", "2", "1", "8")), (um, ("2", "1", "7")), (ug, ("2",)), (uw, ("3",))):
        for p in pins:
            net = k.padnet(ref, p)
            if net == "GND":
                tryit(R.to_via, net, T(ref, p))
            elif net in taps_left:                    # first pin of a bus net lands on this block's tap via
                tryit(R.route, net, T(ref, p), ("all", *taps_left.pop(net)), maxpad=12.0, **L3)
            else:
                tryit(R.to_net, net, T(ref, p), maxpad=12.0, **L3)
    # drive pins: short L1 hops from the receptacle via rows straight down into the block
    for net, pin, ref, p in ((n("DRST"), "E5", ug, "4"), (n("IFDET2"), "E6", ue, "11"), (n("WAKE"), "P1", ue, "12"),
                             (n("PWRDIS"), "P3", ue, "4"), (n("IFDET"), "P4", ue, "10"), (n("PRSNT"), "P10", ue, "9"),
                             (n("DPEN"), "E25", ue, "5"), (n("SMBCLK"), "E23", um, "6"), (n("SMBDAT"), "E24", um, "5")):
        tryit(R.route, net, via(pin), T(ref, p), via_cost=1.0, pad=4.0, maxpad=16.0)
    tryit(R.route, n("DRST"), via("E4"), via("E5"), **L3)
    for net, a in ((n("MUXCTL"), T(um, "3")), (n("MUXCTL"), T(um, "4")), (n("MUXCTL"), T(um, "8")),
                   (n("RSTEN"), T(ue, "6")), (n("RSTEN"), T(ug, "3")), (n("WAKE"), T(uw, "2"))):
        tryit(R.to_net, net, a, via_cost=1.0, maxpad=24.0)
    for f_ in fan:
        ref, pin = (um if f_[0] == "U" else ue), f_[1:]
        tryit(R.to_via, k.padnet(ref, pin), T(ref, pin))
    local = []
    for ref, (pa, pb), (na, nb), bot in info["parts"]:
        L = "L6" if bot else "L1"
        for p, net in ((pa, na), (pb, nb)):
            if net not in ("GND", "3V3_AUX") and not net.startswith("12V"):
                local.append((nearest(net, p), net, (L, *p)))
    for _, net, a in sorted(local):
        if _ < 3.5:
            tryit(R.to_net, net, a, via_cost=1.0)
    for ref, (pa, pb), (na, nb), bot in info["parts"]:
        L = "L6" if bot else "L1"
        for p, net in ((pa, na), (pb, nb)):
            if net == "GND" and p not in info.get("early_gnd", ()):
                tryit(R.to_via, net, (L, *p))
    for ref, pins in ((um, ("1", "2", "7")), (ue, ("1", "2", "3", "8")), (ug, ("2",)), (uw, ("3",))):
        for p in pins:
            if k.padnet(ref, p) == "GND":
                tryit(R.to_via, "GND", T(ref, p))
    for ref, pins in ((um, ("14", "12", "13", "1", "2")), (ue, ("16", "14", "15", "1", "2", "3")),
                      (ug, ("5", "1")), (uw, ("5", "4"))):
        for p in pins:
            net = k.padnet(ref, p)
            if net != "GND":
                tryit(R.to_net, net, T(ref, p), maxpad=24.0, **L3)
    for ref, (pa, pb), (na, nb), bot in info["parts"]:
        L = "L6" if bot else "L1"
        for p, net in ((pa, na), (pb, nb)):
            if net == "3V3_AUX":
                tryit(R.to_net, net, (L, *p), maxpad=16.0, via_cost=1.0)
    tryit(R.to_net, "3V3_AUX", via("E3"), maxpad=16.0, **L3)
    for _, net, a in sorted(local):
        if _ >= 3.5:
            tryit(R.to_net, net, a, via_cost=1.0, maxpad=24.0)
    c0, R.c = R.c, BLOCK_CLEARANCE
    try:
        # a block that leaves pins unrouted is routed again with those pins first (the order decides who gets the
        # few via sites over the trunk strip)
        for attempt in range(3):
            base = len(R.tasks)
            fails = R.run_tasks(tasks)
            if not fails or attempt == 2:
                return fails
            bad = R.failed
            print(f"  block {d}: {len(fails)} unrouted, routing the block again with them first")
            R.rip_since(base)
            tasks = [tasks[i] for i in bad] + [t for i, t in enumerate(tasks) if i not in bad]
    finally:
        R.c = c0
