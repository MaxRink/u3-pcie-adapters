"""Rev F additions shared by the x8 and x16 cards: bring-up and service features, all on the top side in leaded or
0603-and-larger parts.  Everything here is placed and wired AFTER the sideband blocks are routed, in areas the block
router never uses, so the block routing of rev E is unchanged.

  * J6    1x4 2.54 mm header on the card-local bus (3V3_AUX, SCL, SDA, GND), bracket-side column
  * U4    24C02 EEPROM at 0x50 on the card-local bus (FRU / notes), WP tied low
  * TPx   1 mm test pads: 3V3_AUX, 3V3, 12 V slot, 12 V aux, PERST#, and per drive 12V_DRV, PG, IMON; two GND loops
  * LEDs  slot 12 V, aux 12 V, 3.3 V, and one per drive on 12V_DRV (lit while the drive's eFuse output is up; it
          hangs on the eFuse output, not on the open-drain PG line, so PG keeps its full swing at the reset gate)
  * J7    4-pin PWM fan header (1 GND, 2 +12 V, 3 tach, 4 PWM).  +12 V through one of two solder jumpers:
          SJ4 = slot 12 V (bridged by default), SJ5 = aux 12 V (open).  Never close both.  Tach and PWM go to test
          pads only (a 4-wire fan runs at full speed with PWM open).
  * D50   SMBJ15A across the aux 12 V input
  * H7..  extra M3 holes in the two columns (shroud / cradle / card support)
"""
import math

R0603 = ("Resistor_SMD", "R_0603_1608Metric")
C0603 = ("Capacitor_SMD", "C_0603_1608Metric")
LED0603 = ("LED_SMD", "LED_0603_1608Metric")
TP = ("TestPoint", "TestPoint_Pad_D1.0mm")
LOOP = ("TestPoint", "TestPoint_Loop_D2.50mm_Drill1.0mm")
LC = {"2.2k": "C4190", "1k": "C21190", "100nF": "C1591", "LED": "C2289"}
SILK = 1.0


class Extras:
    def __init__(self, k, R, P):
        self.k, self.R, self.P = k, R, P
        self.fails = []
        self.ntp = 0; self.fan_aux_w = None

    # ------------------------------------------------------------------ helpers
    def net(self, kind, net, xy, w=0.2, layer="L1", **kw):
        """kind 'net': route to the nearest copper of the net; 'via': stub to a new via (plane nets)."""
        kw.setdefault("maxpad", 24.0)
        kw.setdefault("via_cost", 1.0)
        quiet = kw.pop("quiet", False)
        f = self.R.to_net if kind == "net" else self.R.to_via
        ws = w if isinstance(w, (list, tuple)) else [w]
        for i, wi in enumerate(ws):                       # widest width that routes
            try:
                f(net, (layer, *xy), w=wi, **kw)
                if i:
                    print("extras", net, [round(v, 2) for v in xy], "routed at", wi)
                return wi
            except RuntimeError as e:
                err = str(e)
        if quiet:
            return None
        self.fails.append((net, xy, err))
        print("FAIL extras", net, [round(v, 2) for v in xy], err[:80])

    def tp(self, net, x, y, label=None, lx=0.0, ly=-1.2):
        self.ntp += 1
        ref = f"TP{self.ntp}"
        self.k.fp(*TP, ref, net, x, y, 0, pads={"1": net}, bom=False)
        if label:
            self.k.text(label, x + lx, y + ly, self.P.F_SilkS, SILK)
        return (x, y)

    def two(self, ref, fp, val, x, y, rot, n1, n2, lcsc):
        """Two-pad part; n1 on the pad toward -x (rot 0/180) or -y (rot 90/270).  Returns (xy1, xy2)."""
        k = self.k
        k.fp(*fp, ref, val, x, y, rot, lcsc=lcsc)
        a, b = sorted("12", key=lambda q: (k.padxy(ref, q)[0], k.padxy(ref, q)[1]))
        k.setpad(ref, a, n1); k.setpad(ref, b, n2)
        return k.padxy(ref, a), k.padxy(ref, b)

    def led(self, rref, dref, x, y, src, mid, rval="2.2k", dirn=(1, 0)):
        """src -> R -> LED -> GND; R at (x, y), LED 3.1 mm further along dirn.  Returns the R pad on src."""
        k = self.k
        rot = 0 if dirn[0] else 90
        pa_, pb_ = self.two(rref, R0603, rval, x, y, rot, mid, mid, LC[rval])
        lx, ly = x + 3.1 * dirn[0], y + 3.1 * dirn[1]
        r_led, r_src = sorted((pa_, pb_), key=lambda p: math.dist(p, (lx, ly)))
        for q in "12":
            k.setpad(rref, q, mid if math.dist(k.padxy(rref, q), r_led) < 1e-6 else src)
        k.fp(*LED0603, dref, "KT-0603YG", lx, ly, rot, lcsc=LC["LED"])
        if math.dist(k.padxy(dref, "2"), r_led) > math.dist(k.padxy(dref, "1"), r_led):   # anode faces the resistor
            k.fps[dref].SetOrientationDegrees(rot + 180)
        pa, pk = k.padxy(dref, "2"), k.padxy(dref, "1")
        k.setpad(dref, "2", mid); k.setpad(dref, "1", "GND")
        k.track(mid, "L1", [r_led, pa], 0.25)
        self.net("via", "GND", pk, w=0.25)
        return r_src

    def hole(self, ref, x, y):
        k = self.k
        k.keepout(f"{ref}_L4_VOID", [(x + 2.7 * math.cos(math.radians(a)), y + 2.7 * math.sin(math.radians(a)))
                                     for a in range(0, 360, 30)], ["L4"])
        k.fp("MountingHole", "MountingHole_3.2mm_M3", ref, "M3", x, y, bom=False)

    # ------------------------------------------------------------------ bracket-side column: bus header, EEPROM
    def column(self):
        k, P = self.k, self.P
        # J6: pin 1 (square) at the top
        x, y = 8.8, -45.6
        k.fp("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical", "J6", "I2C local bus", x, y, 0,
             pads={"1": "3V3_AUX", "2": "SMCLK", "3": "SMDAT", "4": "GND"}, lcsc="C124378")
        for q, lab in zip("1234", ("3V3", "SCL", "SDA", "GND")):
            px, py = k.padxy("J6", q)
            k.text(lab, px - 3.2, py, P.F_SilkS, SILK)
        for q, net in (("2", "SMCLK"), ("3", "SMDAT"), ("1", "3V3_AUX")):
            self.net("net", net, k.padxy("J6", q), w=0.25 if net == "3V3_AUX" else 0.2, layer="all", maxpad=48.0)
        # EEPROM (0x50: A0-A2 low), WP low = writable
        ex, ey = 5.6, -51.2
        k.fp("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", "U4", "AT24C02C-SSHM-T", ex, ey, 0, pads={
            "1": "GND", "2": "GND", "3": "GND", "4": "GND", "5": "SMDAT", "6": "SMCLK", "7": "GND", "8": "3V3_AUX"},
            lcsc="C6203")
        u = lambda q: k.padxy("U4", q)
        k.track("GND", "L1", [u("1"), u("4")], 0.3)
        self.net("via", "GND", (u("4")[0] - 0.6, u("4")[1]), w=0.3)
        k.track("GND", "L1", [u("4"), (u("4")[0] - 0.6, u("4")[1])], 0.3)
        c1, c2 = self.two("C90", C0603, "100nF", ex, ey - 3.9, 0, "GND", "3V3_AUX", LC["100nF"])
        k.track("3V3_AUX", "L1", [c2, (u("8")[0] + 0.3, c2[1]), (u("8")[0] + 0.3, u("8")[1]), u("8")], 0.25)
        self.net("via", "GND", c1, w=0.25)
        self.net("via", "GND", u("7"), w=0.2)
        for q, net in (("8", "3V3_AUX"), ("6", "SMCLK"), ("5", "SMDAT")):
            self.net("net", net, u(q), w=0.2, maxpad=24.0)
        # test points and GND loop
        t = self.tp("3V3_AUX", 2.0, -36.2, "3V3A", lx=3.4, ly=0.0)
        self.net("net", "3V3_AUX", t, w=0.25, maxpad=48.0)
        k.fp(*LOOP, "TP90", "GND", 2.6, -40.6, 0, pads={"1": "GND"}, lcsc="")
        k.text("GND", 2.6, -42.8, P.F_SilkS, SILK)
        # aux 12 V: test pad + LED (L4 is the aux plane under the whole column)
        y = -66.6
        t = self.tp("12V_AUX", 2.0, y, "AUX 12V", lx=3.6, ly=-1.6)
        r = self.led("R90", "D40", 4.7, y, "12V_AUX", "LEDA_AUX")
        k.track("12V_AUX", "L1", [t, r], 0.5)
        self.net("via", "12V_AUX", t, w=0.5)
        # silk legend
        for i, s in enumerate(("I2C ADDR", "77 HOST MUX", "70+N DRV SW", "20+N DRV IO", "50 EEPROM", "JP 12V SRC",
                               "2-3 SLOT", "1-2 AUX", "SJ1-3 A0-2", "CLOSED = 0", "V P I = 12V", "PG IMON")):
            k.text(s, 6.0, -92.0 + 1.6 * i, P.F_SilkS, SILK)

    # ------------------------------------------------------------------ foot left of the fingers: slot rails
    def foot(self):
        """Board foot between the bracket tab and the CEM notch (x 33.35 .. 41.35)."""
        k, P = self.k, self.P
        xt = 37.3
        t = self.tp("12V", xt, -11.6)
        r = self.led("R91", "D41", 35.0, -10.9, "12V", "LEDA_SLOT", dirn=(0, 1))
        k.track("12V", "L1", [t, r], 0.5)
        self.net("via", "12V", t, w=0.5)
        t = self.tp("3V3", xt, -9.4)
        r = self.led("R92", "D42", 39.6, -10.9, "3V3", "LEDA_3V3", rval="1k", dirn=(0, 1))
        k.track("3V3", "L1", [t, (r[0] - 1.2, r[1] + 1.0), (r[0] - 1.2, r[1]), r], 0.25)
        self.net("net", "3V3", t, w=0.25, maxpad=48.0)
        t = self.tp("PCIE_RST_N", xt, -7.0)
        self.net("net", "PCIE_RST_N", t, w=0.2)
        k.text("12V", 35.0, -5.6, P.F_SilkS, SILK); k.text("3V3", 39.5, -5.6, P.F_SilkS, SILK)
        k.text("R", xt, -5.6, P.F_SilkS, SILK)

    # ------------------------------------------------------------------ per drive: 12V_DRV / PG / IMON pads, LED
    def drive(self, d, idx, xs, yp, last, dy=0.0):
        k = self.k
        XY = lambda a, b: (xs + a, yp + b)
        drv, pg, im = f"12V_DRV_{d}", f"PG_{d}", f"IMON_{d}"
        if last:            # the aux plug sits below the last drive: a column right of the eFuse instead
            x = 42.7
            t = self.tp(drv, *XY(x, -2.0 + dy), "V", lx=1.35, ly=0.0)
            r = self.led(f"R{93 + idx}", f"D{43 + idx}", *XY(x, -4.6 + dy), drv, f"LEDA_DRV_{d}", dirn=(0, -1))
            tpg = self.tp(pg, *XY(x, 0.1 + dy), "P", lx=1.35, ly=0.0)
            tim = self.tp(im, *XY(x, 2.2 + dy), "I", lx=-1.35, ly=0.0)
        else:               # a row below the eFuse parts, above the lanes
            y = 3.95
            t = self.tp(drv, *XY(23.6, y), f"12V{d}", lx=0.0, ly=1.4)
            r = self.led(f"R{93 + idx}", f"D{43 + idx}", *XY(26.3, y), drv, f"LEDA_DRV_{d}")
            tim = self.tp(im, *XY(35.6, y), "IMON", lx=-0.6, ly=1.4)
            tpg = self.tp(pg, *XY(38.2, y), "PG", lx=0.4, ly=1.4)
        k.track(drv, "L1", [t, r], 0.5)
        self.net("net", drv, t, w=0.5)
        self.net("net", pg, tpg, w=0.15)
        self.net("net", im, tim, w=0.15)

    # ------------------------------------------------------------------ fan header, supply select, aux TVS
    def fan(self, xf, yf, aux_kind, slot_kind, tvs_xy, tvs_rot=90, default="slot", flip=False, jx=0.0):
        """Fan header centred on (xf, yf), pins along x, key toward the fingers.  aux_kind / slot_kind: 'via' where
        that rail is the L4 plane under the jumpers, else 'net' (track to the nearest copper of the rail)."""
        k, P = self.k, self.P
        k.fp("Connector", "FanPinHeader_1x04_P2.54mm_Vertical", "J7", "fan 4-pin PWM", xf + (-3.81 if flip else 3.81), yf,
             0 if flip else 180, pads={"1": "GND", "2": "12V_FAN", "3": "FAN_TACH", "4": "FAN_PWM"}, lcsc="C240840")
        p = {q: k.padxy("J7", q) for q in "1234"}
        assert (p["1"][0] < p["4"][0]) == flip
        yj = yf - 5.1
        # TVS on the aux 12 V input (cathode = pad 1 on 12V_AUX)
        k.fp("Diode_SMD", "D_SMB", "D50", "SMBJ15A", *tvs_xy, tvs_rot, pads={"1": "12V_AUX", "2": "GND"}, lcsc="C113988")
        sj = ("Jumper", "SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm")
        so = ("Jumper", "SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm")
        # one of the two is bridged from the fab: slot 12 V on the x8, aux 12 V on the x16 cards (a 92x38 fan draws up
        # to 3 A, which the slot's 5.5 A cannot spare next to three or four drives)
        k.fp(*(sj if default == "slot" else so), "SJ4", "fan = slot 12V" + (" (default)" if default == "slot" else ""),
             xf + jx + 0.8, yj, 0, pads={"1": "12V", "2": "12V_FAN"}, bom=False)
        k.fp(*(so if default == "slot" else sj), "SJ5", "fan = aux 12V" + ("" if default == "slot" else " (default)"),
             xf + jx + 4.1, yj, 0, pads={"1": "12V_FAN", "2": "12V_AUX"}, bom=False)
        k.text("FAN", xf + 7.3, yf, P.F_SilkS, SILK)
        k.text("SLOT", xf + jx + 0.2, yj + 1.95, P.F_SilkS, SILK); k.text("AUX", xf + jx + 4.4, yj + 1.95, P.F_SilkS, SILK)
        a, b = k.padxy("SJ4", "2"), k.padxy("SJ5", "1")
        k.track("12V_FAN", "L1", [a, b], 1.0)                # 3 A fan path: 1.0 mm, two feeds per rail
        if flip:                                             # jumpers west of the header: up, east under pin 1, 45 deg in
            k.track("12V_FAN", "L1", [b, (b[0], yj + 1.9), (p["2"][0] - 1.3, yj + 1.9), (p["2"][0], yj + 3.2), p["2"]], 1.0)
        else:
            k.track("12V_FAN", "L1", [a, (p["2"][0], yj + 0.9), p["2"]], 1.0)
        # slot feed: one stub + via into the 12 V plane (about 1 A).  Aux feed: 1.0 mm on L1 all the way to the J5/TVS
        # copper where that routes (3 A), else the same stub + via
        self.net(slot_kind, "12V", k.padxy("SJ4", "1"), w=[1.0, 0.5], maxpad=48.0)
        self.fan_aux_w = self.net("net", "12V_AUX", k.padxy("SJ5", "2"), w=1.0, maxpad=48.0, quiet=True)
        if not self.fan_aux_w:
            self.net(aux_kind, "12V_AUX", k.padxy("SJ5", "2"), w=[1.0, 0.5], maxpad=48.0)
        print("fan aux feed on L1 at", self.fan_aux_w, "mm")
        t = self.tp("FAN_TACH", xf + 0.6 if flip else xf - 2.0, yj)
        if flip:                                             # the header's locating peg sits under pin 3: pass west of it
            k.track("FAN_TACH", "L1", [t, (xf, yj + 0.6), (xf, yf - 1.27), p["3"]], 0.2)
        else:
            k.track("FAN_TACH", "L1", [t, (p["3"][0], yj + 1.3), p["3"]], 0.2)
        t = self.tp("FAN_PWM", xf + 3.3 if flip else xf - 4.4, yj)
        k.track("FAN_PWM", "L1", [t, (p["4"][0], yj + 1.3), p["4"]], 0.2)
        self.net("net", "12V_AUX", k.padxy("D50", "1"), w=0.5, maxpad=48.0)
        self.net("via", "GND", k.padxy("D50", "2"), w=0.5)

    # ------------------------------------------------------------------ clamp holes in the strip between drives
    def gap_holes(self, xs, n0, ywin=(-21.0, -14.0), span=6.0):
        """One M3 NPTH near each x in xs (midway between receptacles) for the cradle/shroud clamp.  The spot is searched
        on the finished copper: >= 3.0 mm from L1 copper and top parts (screw head), >= 2.05 mm from copper on the
        other layers, >= 4.5 mm from bottom parts (printed boss).  Call last, after all routing."""
        k, P = self.k, self.P
        ox, oy = 100.0, 100.0
        f1 = k.b.GetLayerID("F.Cu") if hasattr(k.b, "GetLayerID") else P.F_Cu
        cu = []
        for t in k.b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition(); cu.append((p.x / 1e6 - ox, p.y / 1e6 - oy, p.x / 1e6 - ox, p.y / 1e6 - oy, t.GetWidth() / 2e6, None))
            else:
                a, b = t.GetStart(), t.GetEnd()
                cu.append((a.x / 1e6 - ox, a.y / 1e6 - oy, b.x / 1e6 - ox, b.y / 1e6 - oy, t.GetWidth() / 2e6, t.GetLayer() == P.F_Cu))
        boxes = []
        for f in k.b.GetFootprints():
            bb = f.GetBoundingBox(False, False)
            boxes.append((bb.GetLeft() / 1e6 - ox, bb.GetRight() / 1e6 - ox, bb.GetTop() / 1e6 - oy, bb.GetBottom() / 1e6 - oy, f.IsFlipped()))

        def dseg(px, py, ax, ay, bx, by):
            dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
            t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
            return math.hypot(px - ax - t * dx, py - ay - t * dy)

        def margin(x, y):
            m = 9.0
            for ax, ay, bx, by, r, top in cu:
                if min(ax, bx) - x > 6 or x - max(ax, bx) > 6:
                    continue
                m = min(m, dseg(x, y, ax, ay, bx, by) - r - (2.05 if top is False else 3.0 if top else 2.05))
                if m < 0:
                    return m
            for x0, x1, y0, y1, back in boxes:
                d = math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))
                m = min(m, d - (4.6 if back else 3.5))
            return m

        out = []
        for i, xt in enumerate(xs):
            best = None
            for j in range(int(span / 0.5) * 2 + 1):
                dx = ((j + 1) // 2) * 0.5 * (1 if j % 2 else -1)
                c = max(((margin(xt + dx, y / 2), y / 2) for y in range(int(ywin[0] * 2), int(ywin[1] * 2) + 1)), key=lambda v: v[0])
                if c[0] >= 0:
                    best = (xt + dx, c[1], c[0]); break
            if best:
                self.hole(f"H{n0 + i}", best[0], best[1])
                print(f"gap hole H{n0 + i} at ({best[0]:.1f}, {best[1]:.1f}), margin {best[2]:.2f}")
            else:
                print(f"gap hole near x={xt}: no free spot")
            out.append(best)
        return out

    # ------------------------------------------------------------------ holes, second GND loop
    def holes(self, XR, ys_right, y_gnd):
        k, P = self.k, self.P
        n = 7
        for x, y in [(6.0, -71.6), (6.0, -104.0)] + [(XR - 4.0, y) for y in ys_right]:
            self.hole(f"H{n}", x, y); n += 1
        k.fp(*LOOP, "TP91", "GND", XR - 4.0, y_gnd, 0, pads={"1": "GND"}, lcsc="")
        k.text("GND", XR - 4.0, y_gnd - 2.4, P.F_SilkS, SILK)
