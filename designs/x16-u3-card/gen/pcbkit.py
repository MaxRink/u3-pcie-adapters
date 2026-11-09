"""Small scripted-layout toolkit on top of KiCad 7 pcbnew (used by every board generator).

Coordinates are in mm in a board-local frame (x right, y down); ORIGIN shifts them into the sheet.
"""
import math, os, shutil, re
import pcbnew as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OURLIB = os.path.join(ROOT, "lib", "u3adapter.pretty")
KILIB = "/usr/share/kicad/footprints"
RULES = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "design-rules"))
TEMPLATE6 = os.path.join(RULES, "templates", "jlc06161h-3313_1.6mm", "jlc06161h-3313_1.6mm")

MM = P.FromMM
LAYER = {"L1": P.F_Cu, "L2": P.In1_Cu, "L3": P.In2_Cu, "L4": P.In3_Cu, "L5": P.In4_Cu, "L6": P.B_Cu}

# PCIe 85 ohm and REFCLK 100 ohm geometry on JLC06161H-3313 outer layers (design-rules README sec. 3)
PCIE_W, PCIE_G = 0.157, 0.152
CLK_W, CLK_G = 0.128, 0.254


def offset_polyline(pts, d):
    """Offset a polyline by d to the +normal side, normal = direction rotated +90 deg (x,y)->(-y,x)."""
    out = []
    n = len(pts)
    for i in range(n):
        if i == 0:
            t = _unit(pts[1], pts[0]); nn = (-t[1], t[0])
            out.append((pts[0][0] + d * nn[0], pts[0][1] + d * nn[1]))
        elif i == n - 1:
            t = _unit(pts[-1], pts[-2]); nn = (-t[1], t[0])
            out.append((pts[-1][0] + d * nn[0], pts[-1][1] + d * nn[1]))
        else:
            t1 = _unit(pts[i], pts[i - 1]); t2 = _unit(pts[i + 1], pts[i])
            n1 = (-t1[1], t1[0]); n2 = (-t2[1], t2[0])
            s = (n1[0] + n2[0], n1[1] + n2[1]); k = 1 + n1[0] * n2[0] + n1[1] * n2[1]
            out.append((pts[i][0] + d * s[0] / k, pts[i][1] + d * s[1] / k))
    return out


def _unit(a, b):
    dx, dy = a[0] - b[0], a[1] - b[1]; L = math.hypot(dx, dy)
    return (dx / L, dy / L)


def bump(line, si, fracs, h, L):
    """Insert trapezoid length-tuning bumps (45 deg flanks, height |h|, flat L) into segment si of line.
    h>0 bulges toward +normal of that segment.  Each bump adds 2|h|(sqrt2-1)."""
    a, c = line[si], line[si + 1]
    t = _unit(c, a); n = (-t[1], t[0]); seglen = math.dist(a, c)
    ins = []
    for f in sorted(fracs):
        s0 = f * seglen - (L / 2 + abs(h))
        for s_, o in ((s0, 0), (s0 + abs(h), h), (s0 + abs(h) + L, h), (s0 + 2 * abs(h) + L, 0)):
            ins.append((a[0] + t[0] * s_ + n[0] * o, a[1] + t[1] * s_ + n[1] * o))
    return line[:si + 1] + ins + line[si + 1:]


def plen(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


class Kit:
    def __init__(self, outdir, name, origin=(100.0, 100.0), template=TEMPLATE6):
        os.makedirs(outdir, exist_ok=True)
        self.dir, self.name = outdir, name
        self.pcb = os.path.join(outdir, name + ".kicad_pcb")
        for ext in (".kicad_pcb", ".kicad_pro", ".kicad_dru"):
            shutil.copy(template + ext, os.path.join(outdir, name + ext))
        with open(os.path.join(outdir, "fp-lib-table"), "w") as t:
            rel = os.path.relpath(OURLIB, outdir)
            t.write('(fp_lib_table\n  (lib (name "u3adapter")(type "KiCad")(uri "${KIPRJMOD}/%s")(options "")(descr "U.3 adapter project"))\n)\n' % rel)
        with open(os.path.join(outdir, "sym-lib-table"), "w") as t:
            rel = os.path.relpath(os.path.join(ROOT, "lib", "u3adapter.kicad_sym"), outdir)
            t.write('(sym_lib_table\n  (lib (name "u3adapter")(type "KiCad")(uri "${KIPRJMOD}/%s")(options "")(descr ""))\n)\n' % rel)
        # KiCad 7 netclass patterns are plain wildcards ([..] classes do not match), so pin the
        # PCIe pattern explicitly for our net names (PETn_P/N, PERn_P/N)
        import json
        pro = os.path.join(outdir, name + ".kicad_pro")
        pj = json.load(open(pro))
        pats = pj["net_settings"].setdefault("netclass_patterns", [])
        for pat in ("PET?_?", "PER?_?", "*_PET?_?", "*_PER?_?"):
            pats.insert(0, {"netclass": "PCIe_85", "pattern": pat})
        json.dump(pj, open(pro, "w"), indent=2)
        txt = open(self.pcb).read()                   # drop the template's placeholder outline
        txt = re.sub(r'\n\s*\(gr_(rect|line|text)[^\n]*\(layer "(Edge.Cuts|Dwgs.User|Cmts.User)"\)[^\n]*', '', txt)
        open(self.pcb, "w").write(txt)
        self.b = P.LoadBoard(self.pcb)
        self.O = origin
        self.nets = {}
        self.fps = {}
        self.bom = []          # (ref, value, footprint, lcsc, side, x, y, rot, dnp)
        self.lines = {}        # net -> list of (layer, pts, w) for length bookkeeping
        self.vias_by_net = {}

    # ---------------------------------------------------------------- basics
    def V(self, x, y):
        return P.VECTOR2I(MM(x + self.O[0]), MM(y + self.O[1]))

    def net(self, name):
        if name not in self.nets:
            ni = P.NETINFO_ITEM(self.b, name)
            self.b.Add(ni)
            self.nets[name] = ni
        return self.nets[name]

    def fp(self, lib, fpname, ref, value, x, y, rot=0, bottom=False, pads=None, lcsc="", dnp=False, bom=True):
        path = OURLIB if lib == "u3adapter" else os.path.join(KILIB, lib + ".pretty")
        f = P.FootprintLoad(path, fpname)
        assert f is not None, (lib, fpname)
        f.SetReference(ref); f.SetValue(value)
        f.SetFPID(P.LIB_ID(lib, fpname))
        self.b.Add(f)
        f.SetPosition(self.V(x, y))
        f.SetOrientationDegrees(rot)
        if bottom:
            f.Flip(f.GetPosition(), True)
        for p in f.Pads():
            n = (pads or {}).get(p.GetNumber())
            if n:
                p.SetNet(self.net(n))
        if dnp:
            f.SetAttributes(f.GetAttributes() | P.FP_EXCLUDE_FROM_BOM)
        self.fps[ref] = f
        if bom:
            self.bom.append(dict(ref=ref, value=value, fp=f"{lib}:{fpname}", lcsc=lcsc,
                                 side="bottom" if bottom else "top", x=x, y=y, rot=rot, dnp=dnp))
        return f

    def padxy(self, ref, num, which=0):
        ps = [p for p in self.fps[ref].Pads() if p.GetNumber() == num]
        c = ps[which].GetPosition()
        return (P.ToMM(c.x) - self.O[0], P.ToMM(c.y) - self.O[1])

    def setpad(self, ref, num, net):
        for p in self.fps[ref].Pads():
            if p.GetNumber() == num:
                p.SetNet(self.net(net))

    def padnet(self, ref, num):
        for p in self.fps[ref].Pads():
            if p.GetNumber() == num:
                return p.GetNetname()

    # ---------------------------------------------------------------- copper
    def track(self, net, layer, pts, w):
        for a, c in zip(pts, pts[1:]):
            if math.dist(a, c) < 1e-4:
                continue
            t = P.PCB_TRACK(self.b)
            t.SetStart(self.V(*a)); t.SetEnd(self.V(*c)); t.SetWidth(MM(w))
            t.SetLayer(LAYER[layer]); t.SetNet(self.net(net))
            self.b.Add(t)
        self.lines.setdefault(net, []).append((layer, list(pts), w))

    def via(self, net, x, y, d=None, drill=None):
        """Rev D (dual-fab JLC+PCBWay): annular >= 0.15 mm.  HS vias 0.25/0.55, generic 0.2/0.5."""
        hs = net.startswith(("PET", "PER", "REFCLK")) and "PERST" not in net
        d = d or (0.55 if hs else 0.5); drill = drill or (0.25 if hs else 0.2)
        v = P.PCB_VIA(self.b)
        v.SetPosition(self.V(x, y)); v.SetDrill(MM(drill)); v.SetWidth(MM(d))
        v.SetLayerPair(P.F_Cu, P.B_Cu); v.SetViaType(P.VIATYPE_THROUGH)
        v.SetNet(self.net(net))
        self.b.Add(v)
        self.vias_by_net.setdefault(net, []).append((x, y))
        return v

    def pair(self, layer, center, starts, ends, w=PCIE_W, g=PCIE_G, tune=None):
        """Route a coupled pair.
        center: centerline polyline (coupled part).
        starts/ends: two entries each, (net or None, [points from the terminal toward the coupled part]).
          Terminal = pad centre or via.  Entries whose net is None take the net of the line they get
          matched to (used to assign the far connector's pad nets = polarity follows geometry).
        Returns {net: full polyline}."""
        d = (w + g) / 2
        lp = offset_polyline(center, +d); ln = offset_polyline(center, -d)
        t0 = _unit(center[1], center[0]); n0 = (-t0[1], t0[0])
        t1 = _unit(center[-1], center[-2]); n1 = (-t1[1], t1[0])

        def side(pt, base, n):
            return (pt[0] - base[0]) * n[0] + (pt[1] - base[1]) * n[1]

        s = sorted(starts, key=lambda e: -side(e[1][-1], center[0], n0))   # [+side, -side]
        e = sorted(ends, key=lambda e: -side(e[1][-1], center[-1], n1))
        out = {}
        for (sn, sp), (en, ep), line, sg in ((s[0], e[0], lp, 1), (s[1], e[1], ln, -1)):
            net = sn or en
            assert net, "pair needs at least one named end"
            for (si, fracs, h, L) in (tune or {}).get(net, []):
                line = bump(line, si, fracs, sg * h, L)
            full = list(sp) + line + list(reversed(ep))
            self.track(net, layer, full, w)
            out[net] = (full, sn, en)
        return out

    def zone(self, net, layer, poly, prio=0, clearance=0.2, minw=0.15, thermal=True, name=None,
             layers=None):
        z = P.ZONE(self.b)
        if layers:
            ls = P.LSET()
            for L in layers:
                ls.AddLayer(LAYER[L])
            z.SetLayerSet(ls)
        else:
            z.SetLayer(LAYER[layer])
        if net:
            z.SetNet(self.net(net))
        o = z.Outline(); o.NewOutline()
        for x, y in poly:
            o.Append(MM(x + self.O[0]), MM(y + self.O[1]))
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(MM(clearance))
        z.SetMinThickness(MM(minw))
        z.SetPadConnection(P.ZONE_CONNECTION_THERMAL if thermal else P.ZONE_CONNECTION_FULL)
        z.SetThermalReliefGap(MM(0.25)); z.SetThermalReliefSpokeWidth(MM(0.35))
        z.SetIslandRemovalMode(P.ISLAND_REMOVAL_MODE_ALWAYS)
        if name:
            z.SetZoneName(name)
        self.b.Add(z)
        return z

    def rule_area(self, name, poly):
        z = P.ZONE(self.b)
        ls = P.LSET()
        for L in LAYER.values():
            ls.AddLayer(L)
        z.SetLayerSet(ls)
        o = z.Outline(); o.NewOutline()
        for x, y in poly:
            o.Append(MM(x + self.O[0]), MM(y + self.O[1]))
        z.SetIsRuleArea(True); z.SetZoneName(name)
        z.SetDoNotAllowCopperPour(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        self.b.Add(z)

    def outline(self, poly, layer=P.Edge_Cuts, w=0.1):
        for a, c in zip(poly, poly[1:] + poly[:1]):
            s = P.PCB_SHAPE(self.b); s.SetShape(P.SHAPE_T_SEGMENT)
            s.SetStart(self.V(*a)); s.SetEnd(self.V(*c)); s.SetLayer(layer); s.SetWidth(MM(w))
            self.b.Add(s)

    def text(self, s, x, y, layer=P.F_SilkS, size=1.0, mirror=False):
        t = P.PCB_TEXT(self.b); t.SetText(s); t.SetPosition(self.V(x, y)); t.SetLayer(layer)
        t.SetTextSize(P.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(0.15))
        if mirror:
            t.SetMirrored(True)
        self.b.Add(t)

    # ---------------------------------------------------------------- finish
    def save(self):
        self.b.Save(self.pcb)

    def fill_and_check(self, extra_dru=""):
        if extra_dru:
            with open(os.path.join(self.dir, self.name + ".kicad_dru"), "a") as f:
                f.write("\n" + extra_dru + "\n")
        self.save()
        b = P.LoadBoard(self.pcb)
        P.ZONE_FILLER(b).Fill(b.Zones())
        b.Save(self.pcb)
        b = P.LoadBoard(self.pcb)
        rpt = os.path.join(self.dir, self.name + "-drc.rpt")
        P.WriteDRCReport(b, rpt, P.EDA_UNITS_MILLIMETRES, True)
        return b, rpt


def drc_summary(rpt):
    s = open(rpt).read()
    items = re.findall(r"\n\[(\w+)\]: ([^\n]*)", s)
    from collections import Counter
    c = Counter(k for k, _ in items)
    return c, items
