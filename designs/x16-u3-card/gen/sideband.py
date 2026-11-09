"""Per-drive sideband block, identical on every U.3 slot card (x8, x16 3-drive, x16 4-drive).

Placed right of each receptacle (receptacle on the bottom side, mirrored, centre xs, peg line yp) in the gap to the
next drive, plus the drive's 12 V source jumper on top over the receptacle's 12 V end.  Relative frame:
X = x - xs, Y = y - yp (Y negative = toward the mating face).  Uses ~X 12.5 .. 38, Y -0.4 .. -8.1.

  * TCA9543A (top)  : SMBus switch, address 0x70 + idx; channel 0 -> drive SMBus (E23/E24), channel 1 unused
                      (pulled up).  Drives all answer at 0x6A (NVMe-MI) / 0x53 (FRU), so each needs its own channel.
  * TCA9554 (bottom): I/O expander, address 0x20 + idx.
        P0 PWRDIS (out, 10k pull-down = drive powered by default)    P4 PRSNT#  (in, 10k pull-up)
        P1 DualPortEn# (out, 10k pull-up = single port by default)   P5 IfDet#  (in, 10k pull-up)
        P2 RST_EN (out, 10k pull-up = follows slot PERST#)           P6 IfDet2# (in, 10k pull-up)
        P3 locate LED (out, low = on)                                P7 WAKE#   (in, 10k pull-up)
  * 74LVC1G08 (bottom): PERST0#/PERST1# = slot PERST# AND RST_EN, a buffered per-drive reset.
  * 1x3 SMD header + shunt: 1-2 = slot 12 V (default), 2-3 = aux 12 V from the PCIe 6-pin.  12V_DRV_x feeds
    P13-P15 and the drive's bulk caps.  One shunt can never tie slot and aux 12 V together.
Everything runs from 3V3_AUX (slot B10; a DNP 0R at the fingers can bridge 3V3 for slots without aux power).
"""
import math

R0402 = ("Resistor_SMD", "R_0402_1005Metric")
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C1206 = ("Capacitor_SMD", "C_1206_3216Metric")
LCSC = {"10k": "C25744", "4.7k": "C25900", "1k": "C11702", "100nF": "C1525", "10uF": "C13585"}


def place2(k, ref, fp, val, x, y, rot, bottom, nets, lcsc):
    """Two-pad part; nets = (net of pad nearer to -X/-Y after rotation, other)."""
    k.fp(*fp, ref, val, x, y, rot, bottom=bottom, lcsc=lcsc)
    p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
    first = "1" if (p1[0] + p1[1] * 0.001) < (p2[0] + p2[1] * 0.001) or (rot % 180 == 90 and p1[1] < p2[1]) else "2"
    other = "2" if first == "1" else "1"
    k.setpad(ref, first, nets[0]); k.setpad(ref, other, nets[1])
    return k.padxy(ref, first), k.padxy(ref, other)


def block(k, R, d, idx, xs, yp, JP, refbase, rbase, cbase):
    """Place and route drive d's block.  JP(n) -> receptacle pad xy.  Returns dict of useful points."""
    X = lambda v: xs + v
    Y = lambda v: yp + v
    a0, a1, a2 = idx & 1, (idx >> 1) & 1, (idx >> 2) & 1
    S = lambda b: "3V3_AUX" if b else "GND"
    n = lambda s: f"{s}_{d}"
    # ---------------------------------------------------------------- drive pin nets
    for pin, net in (("E4", n("DRST")), ("E5", n("DRST")), ("E6", n("IFDET2")), ("P1", n("WAKE")),
                     ("P3", n("PWRDIS")), ("P4", n("IFDET")), ("P10", n("PRSNT")), ("E23", n("SMBCLK")),
                     ("E24", n("SMBDAT")), ("E25", n("DPEN")), ("P13", n("12V_DRV")), ("P14", n("12V_DRV")),
                     ("P15", n("12V_DRV"))):
        k.setpad(f"J{d}", pin, net)
    # ---------------------------------------------------------------- parts
    um, ue, ug, jh, dl = f"U{refbase}", f"U{refbase + 1}", f"U{refbase + 2}", f"JP{idx + 1}", f"D{10 + idx}"
    k.fp("Package_SO", "TSSOP-14_4.4x5mm_P0.65mm", um, "TCA9543APWR", X(35.2), Y(-4.25), 0, pads={
        "1": S(a0), "2": S(a1), "3": n("MUXCTL"), "4": n("MUXCTL"), "5": n("SMBDAT"), "6": n("SMBCLK"),
        "7": "GND", "8": n("MUXCTL"), "9": n("SD1"), "10": n("SC1"), "12": "SMCLK", "13": "SMDAT",
        "14": "3V3_AUX"}, lcsc="C2653307")
    k.fp("Package_SO", "TSSOP-16_4.4x5mm_P0.65mm", ue, "TCA9554PWR", X(35.2), Y(-4.25), 0, bottom=True, pads={
        "1": S(a0), "2": S(a1), "3": S(a2), "4": n("PWRDIS"), "5": n("DPEN"), "6": n("RSTEN"), "7": n("LOC"),
        "8": "GND", "9": n("PRSNT"), "10": n("IFDET"), "11": n("IFDET2"), "12": n("WAKE"),
        "14": "SMCLK", "15": "SMDAT", "16": "3V3_AUX"}, lcsc="C477924")
    k.fp("Package_TO_SOT_SMD", "SOT-353_SC-70-5", ug, "SN74LVC1G08DCKR", X(26.1), Y(-6.2), 0, bottom=True, pads={
        "1": "PCIE_RST_N", "2": n("RSTEN"), "3": "GND", "4": n("DRST"), "5": "3V3_AUX"}, lcsc="C7832")
    k.fp("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical_SMD_Pin1Left", jh,
         "12V src: 2-3 slot (default), 1-2 aux", X(26.0), Y(-4.54), 0,
         pads={"3": "12V", "2": n("12V_DRV"), "1": "12V_AUX"}, lcsc="C2937625")
    k.fp("LED_SMD", "LED_0603_1608Metric", dl, "yellow (locate)", X(40.8), Y(-1.0), 180, bottom=True,
         pads={"1": n("LOC"), "2": n("LOCA")}, lcsc="C72038")

    def array(ref, val, lc, x, y, bottom, sigs, toward):
        """4x0603 array; the pad column nearer x=toward carries sigs (listed top = more negative y first)."""
        k.fp("Resistor_SMD", "R_Array_Convex_4x0603", ref, val, X(x), Y(y), 0, bottom=bottom, lcsc=lc)
        ps = {p.GetNumber(): k.padxy(ref, p.GetNumber()) for p in k.fps[ref].Pads()}
        near = sorted([q for q in ps if abs(ps[q][0] - X(toward)) < abs((2 * X(x) - ps[q][0]) - X(toward))],
                      key=lambda q: ps[q][1])
        far = [q for q in ps if q not in near]
        for q, net in zip(near, sigs):
            k.setpad(ref, q, net)
        for q in far:
            k.setpad(ref, q, "3V3_AUX")
        return [(ref, (ps[q], ps[str(9 - int(q))]), (net, "3V3_AUX"), bottom) for q, net in zip(near, sigs)]

    parts = []
    parts += array(f"RN{2 * idx + 1}", "4.7k x4", "C1980", 41.3, -2.65, False,
                   (n("SC1"), n("SD1"), n("SMBDAT"), n("SMBCLK")), 35.2)
    parts += array(f"RN{2 * idx + 2}", "10k x4", "C29718", 29.5, -3.0, True,
                   (n("WAKE"), n("IFDET2"), n("IFDET"), n("PRSNT")), 35.2)
    rr = [("3V3_AUX", n("MUXCTL"), "10k", 35.2, -0.95, 0, False),
          ("GND", n("PWRDIS"), "10k", 41.0, -6.0, 0, True),
          ("3V3_AUX", n("RSTEN"), "10k", 41.0, -4.5, 0, True),
          ("3V3_AUX", n("LOCA"), "1k", 43.4, -1.0, 0, True)]
    cc = [("3V3_AUX", "GND", "100nF", 40.3, -6.35, 0, False),         # mux decoupling (top, by pin 14)
          ("3V3_AUX", "GND", "100nF", 30.2, -7.4, 0, True),          # expander decoupling (bottom, by pin 16)
          ("3V3_AUX", "GND", "100nF", 26.1, -8.2, 0, True)]          # gate decoupling
    for i, (na, nb, val, x, y, rot, bot) in enumerate(rr):
        ref = f"R{rbase + i}"
        parts.append((ref, place2(k, ref, R0402, val, X(x), Y(y), rot, bot, (na, nb), LCSC[val]), (na, nb), bot))
    for i, (na, nb, val, x, y, rot, bot) in enumerate(cc):
        ref = f"C{cbase + i}"
        parts.append((ref, place2(k, ref, C0402, val, X(x), Y(y), rot, bot, (na, nb), LCSC[val]), (na, nb), bot))
    # bulk 12V_DRV caps on top over the receptacle's 12 V end
    bulk = []
    for i, (x, y) in enumerate(((17.0, -4.6), (19.4, -4.9))):
        ref = f"C{cbase + 3 + i}"
        k.fp(*C1206, ref, "10uF 25V X5R", X(x), Y(y), 90, lcsc=LCSC["10uF"])
        p1, p2 = k.padxy(ref, "1"), k.padxy(ref, "2")
        hi, lo = (p1, p2) if p1[1] > p2[1] else (p2, p1)              # hi = nearer the fingers
        k.setpad(ref, "1" if hi is p1 else "2", n("12V_DRV")); k.setpad(ref, "2" if hi is p1 else "1", "GND")
        gv = (lo[0], lo[1] - 1.25); k.via("GND", *gv); k.track("GND", "L1", [lo, gv], 0.5)
        bulk.append(ref)
    # ---------------------------------------------------------------- 12 V jumper: plane vias + 12V_DRV pour
    p3, p2, p1 = k.padxy(jh, "1"), k.padxy(jh, "2"), k.padxy(jh, "3")      # p1 = slot side (pin 3)
    for v in ((X(23.4), Y(-0.6)), (X(25.6), Y(-0.6))):
        k.via("12V", *v, 0.6, 0.3); k.track("12V", "L1", [p1, v], 0.6)
    for v in ((X(22.4), Y(-7.08)), (X(22.4), Y(-6.0))):
        k.via("12V_AUX", *v, 0.6, 0.3); k.track("12V_AUX", "L1", [p3, v], 0.6)
    k.zone(n("12V_DRV"), "L1", [(X(12.75), Y(-1.95)), (X(21.15), Y(-1.95)), (X(21.15), Y(-3.85)),
                               (X(29.1), Y(-3.85)), (X(29.1), Y(-5.25)), (X(12.75), Y(-5.25))],
           prio=3, clearance=0.25, minw=0.3, thermal=False)
    for sx in (-1, 1):                       # keep L3 routes off the receptacle hold-down pads (thermal spokes)
        mx, my = X(22.0 * sx), Y(-2.35)
        R.keepouts.append(("L3", [(mx - 1.6, my - 2.2), (mx + 1.6, my - 2.2), (mx + 1.6, my + 2.2), (mx - 1.6, my + 2.2)]))
    R.keepouts.append(("L1", [(X(12.6), Y(-1.8)), (X(29.2), Y(-1.8)), (X(29.2), Y(-5.4)), (X(12.6), Y(-5.4))]))
    return dict(parts=parts, um=um, ue=ue, ug=ug, jh=jh, dl=dl, bulk=bulk)


def route_block(k, R, d, info, JP, yvm, yvt):
    """Wire the block with the maze router (after the trunks SMCLK/SMDAT/3V3_AUX/PCIE_RST_N exist)."""
    n = lambda s: f"{s}_{d}"
    um, ue, ug, dl = info["um"], info["ue"], info["ug"], info["dl"]
    pad = lambda ref, p: k.padxy(ref, p)
    side = lambda ref: "L6" if k.fps[ref].IsFlipped() else "L1"
    T = lambda ref, p: (side(ref), *pad(ref, p))
    via = lambda pin: ("all", JP(pin)[0], yvt if pin.startswith("E2") else yvm)
    fails = []

    retry = []

    def tryit(f, *a, **kw):
        try:
            f(*a, **kw)
        except RuntimeError as e:
            retry.append((f, a, kw))
    L3 = dict(layer_cost={"L1": 2.0, "L6": 2.0}, via_cost=1.0)
    def nearest(net, p):
        best = 1e9
        for ref in (um, ue, ug, dl):
            for q in k.fps[ref].Pads():
                if q.GetNetname() == net:
                    best = min(best, math.dist(p, k.padxy(ref, q.GetNumber())))
        return best
    # expander pins with no local part: escape to a via before the block fills up
    tryit(R.to_via, n("DPEN"), T(ue, "5"))
    tryit(R.route, n("LOC"), T(dl, "1"), T(ue, "7"), via_cost=1.0)
    local = []
    for ref, (pa, pb), (na, nb), bot in info["parts"]:
        L = "L6" if bot else "L1"
        for p, net in ((pa, na), (pb, nb)):
            if net not in ("GND", "3V3_AUX"):
                local.append((nearest(net, p), net, (L, *p)))
    for _, net, a in sorted(local):
        if _ < 3.5:
            tryit(R.to_net, net, a, via_cost=1.0)
    # 1. short local nets first: resistor signal pads -> IC pins, MUXCTL, RSTEN, LOC, straps
    # 3. ground stubs, then 3V3_AUX / bus / reset to the trunks
    for ref, (pa, pb), (na, nb), bot in info["parts"]:
        L = "L6" if bot else "L1"
        for p, net in ((pa, na), (pb, nb)):
            if net == "GND":
                tryit(R.to_via, net, (L, *p))
    for ref, pins in ((um, ("1", "2", "7")), (ue, ("1", "2", "3", "8")), (ug, ("3",))):
        for p in pins:
            if k.padnet(ref, p) == "GND":
                tryit(R.to_via, "GND", T(ref, p))
    for ref, pins in ((um, ("14", "12", "13", "1", "2")), (ue, ("16", "14", "15", "1", "2", "3")), (ug, ("5", "1"))):
        for p in pins:
            net = k.padnet(ref, p)
            if net != "GND":
                tryit(R.to_net, net, T(ref, p), maxpad=16.0, **L3)
    for ref, (pa, pb), (na, nb), bot in info["parts"]:
        L = "L6" if bot else "L1"
        for p, net in ((pa, na), (pb, nb)):
            if net == "3V3_AUX":
                tryit(R.to_net, net, (L, *p), maxpad=16.0, via_cost=1.0)
    xs_ = [k.padxy(r, q.GetNumber())[0] for r in (um, ue) for q in k.fps[r].Pads()]
    tryit(R.to_net, "3V3_AUX", via("E3"), bbox=(via("E3")[1] - 2.0, yvm - 6.0, max(xs_) + 3.0, yvt + 1.2), **L3)
    for _, net, a in sorted(local):
        if _ >= 3.5:
            tryit(R.to_net, net, a, via_cost=1.0)
    for net, a in ((n("MUXCTL"), T(um, "3")), (n("MUXCTL"), T(um, "8")), (n("RSTEN"), T(ug, "2")),
                   ):
        tryit(R.to_net, net, a, via_cost=1.0)
    # 2. drive pins -> block (mostly on L3 under the receptacle and the block)
    tryit(R.route, n("DRST"), T(ug, "4"), via("E5"), **L3)
    tryit(R.route, n("DRST"), via("E4"), via("E5"), **L3)
    for net, pin in ((n("SMBCLK"), "E23"), (n("SMBDAT"), "E24"), (n("DPEN"), "E25"), (n("PWRDIS"), "P3"),
                     (n("IFDET"), "P4"), (n("PRSNT"), "P10"), (n("IFDET2"), "E6"), (n("WAKE"), "P1")):
        v = via(pin)
        xs_ = [k.padxy(r, q.GetNumber())[0] for r in (um, ue) for q in k.fps[r].Pads()]
        bb = (min(v[1], min(xs_)) - 2.0, yvm - 6.0, max(xs_) + 3.0, yvt + 1.2)
        tryit(R.to_net, net, v, bbox=bb, **L3)
    for f, a, kw in retry:                       # second pass: wider search window, cheaper vias
        kw = dict(kw); kw.update(maxpad=20.0, via_cost=0.5)
        try:
            f(*a, **kw)
        except RuntimeError as e:
            fails.append(str(e)); print("FAIL", e)
    return fails
