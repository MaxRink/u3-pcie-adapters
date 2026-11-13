"""Tiny grid maze router for low-speed nets (used by the sideband blocks).

Obstacles are rasterised from what is already on the board (tracks, vias, pads, holes, board edge), inflated by
clearance + half the new track width, so every route it returns is DRC clean by construction (up to grid
rounding, covered by a small extra margin).  A* over (layer, x, y) on a 0.05 mm grid with 45-degree moves; layer
changes place a through via (checked against all routing layers).  Zones are ignored (they refill around tracks).
"""
import os
import heapq, math
import numpy as np
from PIL import Image, ImageDraw
import pcbnew as P
MM = P.FromMM

LAYER = {"L1": P.F_Cu, "L3": P.In2_Cu, "L6": P.B_Cu, "L2": P.In1_Cu, "L4": P.In3_Cu, "L5": P.In4_Cu}


class Router:
    def __init__(self, k, g=0.05, clearance=0.2, margin=0.03):
        self.k, self.g, self.c, self.m = k, g, clearance, margin
        self.O = k.O
        self.routed = []
        self.keepouts = []          # (layer, poly) no router copper (e.g. over a power pour)
        self.conn = {}              # net -> [(layer, kind, geo)] copper known to be connected to the net's root
        # rip-up and reroute bookkeeping (run_tasks): copper made by a task is "soft" and may be ripped up
        self.tasks, self.items, self.order, self.conn_add, self.rips = [], {}, {}, {}, {}
        self.soft, self._soft_shapes, self._tick = {}, [], 0
        self._soft_mode, self._last_conn = False, None

    def seed(self, net, items):
        self.conn.setdefault(net, []).extend(items)

    # ------------------------------------------------------------------ obstacles
    def _shapes(self, bbox, net_=None):
        """List of (layers, net, kind, geom) inside bbox (board-local mm).  In soft mode, other nets' copper made
        by run_tasks goes to self._soft_shapes (with its owning task) instead."""
        x0, y0, x1, y1 = bbox
        O = self.O
        out = []
        self._soft_shapes = soft = []
        chk = self._soft_mode and bool(self.soft)

        def inb(x, y, r):
            return x0 - r < x < x1 + r and y0 - r < y < y1 + r

        for t in self.k.b.GetTracks():
            net = t.GetNetname()
            dst = out
            if chk and net != net_:
                o = self.soft.get(t.m_Uuid.AsString())
                if o is not None:
                    dst = _Tag(soft, o)
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition(); x, y = P.ToMM(p.x) - O[0], P.ToMM(p.y) - O[1]
                if inb(x, y, 2):
                    dst.append(("all", net, "circle", (x, y, P.ToMM(t.GetWidth()) / 2)))
            else:
                a, b = t.GetStart(), t.GetEnd()
                ax, ay, bx, by = P.ToMM(a.x) - O[0], P.ToMM(a.y) - O[1], P.ToMM(b.x) - O[0], P.ToMM(b.y) - O[1]
                if max(ax, bx) < x0 - 2 or min(ax, bx) > x1 + 2 or max(ay, by) < y0 - 2 or min(ay, by) > y1 + 2:
                    continue
                L = [n for n, l in LAYER.items() if l == t.GetLayer()]
                dst.append((L[0] if L else "x", net, "seg", (ax, ay, bx, by, P.ToMM(t.GetWidth()) / 2)))
        for f in self.k.b.GetFootprints():
            for p in f.Pads():
                c = p.GetPosition(); x, y = P.ToMM(c.x) - O[0], P.ToMM(c.y) - O[1]
                if not inb(x, y, 6):
                    continue
                net = p.GetNetname()
                if p.GetAttribute() == P.PAD_ATTRIB_NPTH:
                    ds = p.GetDrillSize()
                    r = max(P.ToMM(ds.x), P.ToMM(ds.y)) / 2
                    if abs(P.ToMM(ds.x) - P.ToMM(ds.y)) < 1e-3:
                        out.append(("all", "<npth>", "circle", (x, y, r + 0.1)))
                    else:                                   # slot: approximate by its pad polygon + hole margin
                        sp = p.GetEffectivePolygon()
                        out.append(("all", "<npth>", "poly", (self._poly(sp), 0.1)))
                    continue
                sp = p.GetEffectivePolygon()
                poly = self._poly(sp)
                if p.GetAttribute() == P.PAD_ATTRIB_PTH:
                    out.append(("all", net, "poly", (poly, 0.0)))
                else:
                    for n, l in LAYER.items():
                        if p.IsOnLayer(l) and n in ("L1", "L6"):
                            out.append((n, net, "poly", (poly, 0.0)))
        edges = [d for d in self.k.b.GetDrawings() if d.GetLayer() == P.Edge_Cuts]
        for f in self.k.b.GetFootprints():                 # footprint outlines (CEM finger notches)
            edges += [d for d in f.GraphicalItems() if d.GetLayer() == P.Edge_Cuts]
        for d in edges:
            pts = [d.GetStart(), d.GetEnd()]
            if d.GetShape() == P.SHAPE_T_ARC:
                c = d.GetCenter(); r = P.ToMM(d.GetRadius())
                a0 = math.atan2(pts[0].y - c.y, pts[0].x - c.x)
                am = math.atan2(d.GetArcMid().y - c.y, d.GetArcMid().x - c.x)
                a1 = math.atan2(pts[1].y - c.y, pts[1].x - c.x)
                d1 = (am - a0 + math.pi) % (2 * math.pi) - math.pi
                d2 = (a1 - am + math.pi) % (2 * math.pi) - math.pi
                cx, cy = P.ToMM(c.x) - O[0], P.ToMM(c.y) - O[1]
                xy = [(cx + r * math.cos(a0 + (d1 + d2) * i / 12), cy + r * math.sin(a0 + (d1 + d2) * i / 12))
                      for i in range(13)]
            else:
                xy = [(P.ToMM(q.x) - O[0], P.ToMM(q.y) - O[1]) for q in pts]
            for (ax, ay), (bx, by) in zip(xy, xy[1:]):
                if inb((ax + bx) / 2, (ay + by) / 2, abs(bx - ax) / 2 + abs(by - ay) / 2 + 1):
                    out.append(("all", "<edge>", "seg", (ax, ay, bx, by, 0.05)))
        return out

    def _poly(self, sp):
        pts = []
        for i in range(sp.OutlineCount()):
            o = sp.Outline(i)
            pts.append([(P.ToMM(o.CPoint(j).x) - self.O[0], P.ToMM(o.CPoint(j).y) - self.O[1])
                        for j in range(o.PointCount())])
        return pts

    def _mask(self, shapes, layer, net, infl, bbox, extra_free=()):
        x0, y0, x1, y1 = bbox
        g = self.g
        W, H = int(round((x1 - x0) / g)) + 1, int(round((y1 - y0) / g)) + 1
        im = Image.new("1", (W, H), 0)
        dr = ImageDraw.Draw(im)
        T = lambda x, y: ((x - x0) / g, (y - y0) / g)
        for L, n, kind, geo in shapes:
            if n == net or (L != "all" and L != layer):
                continue
            _draw(dr, T, g, kind, geo, infl + _extra(n, self.c), 1)   # edge 0.3, PCIe 0.4, REFCLK 0.5 vs 0.2 copper
        for L, poly in self.keepouts:
            if L == layer and net is not None:
                dr.polygon([T(*q) for q in poly], fill=1)
        m = np.array(im, dtype=bool)
        return m

    def _target(self, items, layer, bbox, exclude=None):
        x0, y0, x1, y1 = bbox
        g = self.g
        W, H = int(round((x1 - x0) / g)) + 1, int(round((y1 - y0) / g)) + 1
        im = Image.new("1", (W, H), 0)
        dr = ImageDraw.Draw(im)
        T = lambda x, y: ((x - x0) / g, (y - y0) / g)
        for L, kind, geo in items:
            if L != "all" and L != layer:
                continue
            if kind == "circle":
                x, y, r = geo
                if exclude and math.dist((x, y), exclude) < r + 0.05:
                    continue
                cx, cy = T(x, y); R = max(r - 0.05, 0.03) / g
                dr.ellipse([cx - R, cy - R, cx + R, cy + R], fill=1)
            elif kind == "seg":
                ax, ay, bx, by, hw = geo
                A, B = T(ax, ay), T(bx, by)
                dr.line([A, B], fill=1, width=1)
            else:
                polys, _ = geo
                for pts in polys:
                    if exclude and _inside(exclude, pts):
                        break
                else:
                    for pts in polys:
                        if len(pts) > 2:
                            dr.polygon([T(*q) for q in pts], fill=1)
        return np.array(im, dtype=bool)

    # ------------------------------------------------------------------ search
    def route(self, net, a, b, w=0.15, **kw):
        return self._search(net, a, ("pt", b), w, **kw)

    def to_net(self, net, a, w=0.15, **kw):
        """Route from terminal a to the nearest copper of net (seeded root copper if the net was seeded)."""
        return self._search(net, a, ("net",), w, **kw)

    def to_via(self, net, a, w=0.2, **kw):
        """Short stub from terminal a to a new via (plane nets)."""
        return self._search(net, a, ("via",), w, **kw)

    # ------------------------------------------------------------------ rip-up and reroute
    def _goal(self, f, a):
        nm = f.__name__
        if nm == "route":
            return ("pt", a[2]), 0.15
        return (("net",), 0.15) if nm == "to_net" else (("via",), 0.2)

    def _run(self, tid, f, a, kw):
        self.k.made, self._last_conn = [], None
        kw = dict(kw); strict = kw.pop("_strict", False)
        try:
            f(*a, **kw)
            ok = True
        except RuntimeError as e:
            # nothing of an unseeded net left to reach within maxpad: already connected.  A seeded net always has its
            # root somewhere, so for it this is a failure (the window was too small)
            ok = "no target copper" in str(e) and a[0] not in self.conn and not strict
        made, self.k.made = self.k.made, None
        if not ok:
            for it in made:
                self.k.b.Delete(it)
            return False
        self.items[tid] = [(it.m_Uuid.AsString(), it) for it in made]
        for u, _ in self.items[tid]:
            self.soft[u] = tid
        self._tick += 1
        self.order[tid] = self._tick
        if self._last_conn:
            self.conn_add[tid] = self._last_conn
        return True

    def _rip(self, tid):
        for u, it in self.items.pop(tid, []):
            self.soft.pop(u, None)
            self.k.b.Delete(it)
        self.order.pop(tid, None)
        if tid in self.conn_add:
            net, lst = self.conn_add.pop(tid)
            for it in lst:
                try:
                    self.conn[net].remove(it)
                except ValueError:
                    pass

    def _cascade(self, o):
        """o plus the later to_net tasks of the same net (they may end on o's copper)."""
        net = self.tasks[o][1][0]
        out = {o}
        for t, tk in self.order.items():
            f, a, _ = self.tasks[t]
            if t != o and a[0] == net and f.__name__ == "to_net" and tk > self.order[o]:
                out.add(t)
        return out

    def run_tasks(self, tasks, max_tries=int(os.environ.get('U3_TRIES', '12')), log=print):
        """Route (f, args, kw) tasks in order; a task that cannot route is searched again with the copper of
        earlier tasks as costly-but-passable, the tasks it crosses are ripped up, it is routed, and they are
        queued again.  Returns the failure messages."""
        base = len(self.tasks)
        self.failed = []
        self.tasks.extend(tasks)
        queue = list(range(base, base + len(tasks)))
        tries, fails = {}, []
        for _ in range(3):
            fails += self._rr(queue, tries, max_tries, log)
            queue = self._isolated(range(base, len(self.tasks)))
            if not queue:
                break
            for t in queue:                 # keep its copper (other routes may end on it), add a link to the net
                f, a, kw = self.tasks[t]
                kw = dict(kw); kw["maxpad"] = 16.0; kw["_strict"] = True
                self.tasks[t] = (f, a, kw)
            log(f"  verify: {len(queue)} start pads not joined to their net, routing again")
        self.failed = [t - base for t in dict.fromkeys(self.failed) if t not in self.order]
        return fails

    def rip_since(self, base):
        """Rip every routed task with id >= base (to route a block again in another order)."""
        for t in [t for t in list(self.order) if t >= base]:
            self._rip(t)

    def _isolated(self, tids):
        """to_net tasks whose start pad pcbnew sees joined to no other pad of a multi-pad net (zone nets skipped)."""
        b = self.k.b
        zn = {z.GetNetname() for z in b.Zones()}
        b.BuildConnectivity()
        c = b.GetConnectivity()
        pads = {}
        for p in b.GetPads():
            pads.setdefault(p.GetNetname(), []).append(p)
        ox, oy = self.k.O
        out = []
        for t in tids:
            f, a, _ = self.tasks[t]
            net = a[0]
            if f.__name__ != "to_net" or net in zn or len(pads.get(net, [])) < 2:
                continue
            x, y = MM(a[1][1] + ox), MM(a[1][2] + oy)
            hit = [p for p in pads[net] if p.HitTest(P.VECTOR2I(int(x), int(y)))]
            if hit and self._cluster_pads(c, hit[0]) == 0:
                out.append(t)
        return out

    @staticmethod
    def _cluster_pads(c, pad):
        """Other pads reachable from pad over tracks and vias (GetConnectedPads only gives direct neighbours)."""
        seen, st, n = {pad.m_Uuid.AsString()}, [pad], 0
        while st:
            it = st.pop()
            for q in list(c.GetConnectedTracks(it)) + list(c.GetConnectedPads(it)):
                u = q.m_Uuid.AsString()
                if u in seen:
                    continue
                seen.add(u); st.append(q)
                n += q.Type() == P.PCB_PAD_T
        return n

    def _rr(self, queue, tries, max_tries, log):
        fails = []
        while queue:
            tid = queue.pop(0)
            f, a, kw = self.tasks[tid]
            first = tries.get(tid, 0) == 0
            if self._run(tid, f, a, kw):
                continue
            tries[tid] = tries.get(tid, 0) + 1
            goal, w0 = self._goal(f, a)
            kws = {k_: v for k_, v in kw.items() if k_ not in ("pad", "maxpad", "_strict")}
            kws.setdefault("w", w0)
            w_ = kws.pop("w")
            try:
                own = self._search(a[0], a[1], goal, w_, pad=4.0, maxpad=16.0, soft=True, **kws)
            except RuntimeError:
                own = None
            if (own is None or tries[tid] > max_tries) and f.__name__ == "to_via":
                # no room for a plane via: join the net's existing copper (another via of the plane) instead
                if self._run(tid, self.to_net, (a[0], a[1]), {"w": w0, "maxpad": 8.0, "via_cost": 1.0, "_strict": True}):
                    continue
            if own is None or tries[tid] > max_tries:
                fails.append(f"router: no path for {a[0]} {a[1]} -> {goal[0]}" + (" (gave up)" if own else ""))
                self.failed.append(tid)
                continue
            rip = set()
            for o in own:
                if o in self.order:
                    rip |= self._cascade(o)
            for o in rip:
                self._rip(o)
                self.rips[o] = self.rips.get(o, 0) + 1
                tries[o] = max(tries.get(o, 0), 1)
            self.rips[tid] = self.rips.get(tid, 0)
            kw2 = dict(kw); kw2["maxpad"] = 16.0
            if not self._run(tid, f, a, kw2):
                queue.append(tid)
            queue.extend(sorted(rip))
            log(f"  ripup {a[0]} @({a[1][1]:.2f},{a[1][2]:.2f}): ripped {len(rip)} -> queue {len(queue)}")
        return fails

    def _search(self, net, a, goal, w=0.15, layers=("L1", "L3", "L6"), via_cost=4.0, pad=3.0, viad=0.5,
                layer_cost=None, bbox=None, allow_via=True, maxpad=12.0, soft=False):
        g = self.g
        b = goal[1] if goal[0] == "pt" else None
        import time, os
        while True:
            t0 = time.time()
            try:
                self._soft_mode = soft
                return self._search1(net, a, goal, w, layers, via_cost, pad, viad, layer_cost, bbox, allow_via, soft)
            except RuntimeError:
                if bbox is not None or pad >= maxpad:
                    raise
                pad *= 2
            finally:
                self._soft_mode = False
                if os.environ.get("RTIME") and time.time() - t0 > 2.0:
                    print(f"  slow {time.time() - t0:5.1f}s {net} {goal[0]} pad {pad} from {a}", flush=True)

    def _search1(self, net, a, goal, w, layers, via_cost, pad, viad, layer_cost, bbox, allow_via, soft=False):
        self._pad = pad
        g = self.g
        b = goal[1] if goal[0] == "pt" else None
        if bbox is None:
            if b is not None:
                bbox = (min(a[1], b[1]) - pad, min(a[2], b[2]) - pad, max(a[1], b[1]) + pad, max(a[2], b[2]) + pad)
            else:
                bbox = (a[1] - pad, a[2] - pad, a[1] + pad, a[2] + pad)
        x0, y0, x1, y1 = bbox
        x0, y0 = math.floor(x0 / g) * g, math.floor(y0 / g) * g
        bbox = (x0, y0, x1, y1)
        shapes = self._shapes(bbox, net)
        infl = self.c + w / 2 + self.m
        M = {L: self._mask(shapes, L, net, infl, bbox) for L in layers}
        vinfl = self.c + viad / 2 + self.m
        OW = VOW = None
        if soft:                                          # owner rasters of rip-able copper (task id + 1)
            Wd, Hd = M[layers[0]].shape[1], M[layers[0]].shape[0]
            Tt = lambda x, y: ((x - x0) / g, (y - y0) / g)

            def oras(Ls, inf):
                im = Image.new("I", (Wd, Hd), 0); dr = ImageDraw.Draw(im)
                for L_, n_, kind, geo, o in self._soft_shapes:
                    if L_ == "all" or L_ in Ls:
                        _draw(dr, Tt, g, kind, geo, inf + _extra(n_, self.c), o + 1)
                return np.array(im, dtype=np.int64)
            OW = {L: oras((L,), infl) for L in layers}
            VOW = oras(("L1", "L3", "L6"), vinfl)
            SC = 25.0
            pen = lambda o: SC * (1 + self.rips.get(o - 1, 0))
        VM = None
        if (allow_via and len(layers) > 1) or goal[0] == "via":
            VM = np.zeros_like(M[layers[0]])
            for L in ("L1", "L3", "L6"):
                VM |= self._mask(shapes, L, net, vinfl, bbox)
                # a via must also clear same-net SMD pads it does not sit on: keep it off every pad
            # drilled holes: keep 0.25 mm hole-to-hole from every existing via (any net, same net included)
            x0_, y0_ = bbox[0], bbox[1]
            for L, n_, kind, geo in shapes:
                if kind == "circle" and L == "all" and n_ != "<npth>":
                    x, y, r = geo
                    cx, cy = (x - x0_) / g, (y - y0_) / g; Rr = (0.2 + 0.25 + 0.05) / g
                    yy, xx = np.ogrid[:VM.shape[0], :VM.shape[1]]
                    VM |= (xx - cx) ** 2 + (yy - cy) ** 2 <= Rr * Rr
        H, W = M[layers[0]].shape
        lc = layer_cost or {}

        def cell(x, y):
            return int(round((x - x0) / g)), int(round((y - y0) / g))

        def terms(e):
            Ls = layers if e[0] == "all" else [e[0]]
            i, j = cell(e[1], e[2])
            return [(L, i, j) for L in Ls if L in layers]

        S = terms(a)
        for (L, i, j) in S + (terms(b) if b else []):
            for di in range(-2, 3):
                for dj in range(-2, 3):
                    if 0 <= j + dj < H and 0 <= i + di < W:
                        M[L][j + dj, i + di] = False
        if goal[0] == "pt":
            tset = set(terms(b)); ti, tj = terms(b)[0][1], terms(b)[0][2]
            is_goal = lambda s: s in tset
            h = lambda i, j: math.hypot(i - ti, j - tj)
        elif goal[0] == "net":
            items = self.conn.get(net)
            if items is None:
                items = [(L, kind, geo) for L, n_, kind, geo in shapes if n_ == net]
                items = _drop_connected(items, (a[1], a[2]), a[0])
            TM = {L: self._target(items, L, bbox, exclude=(a[1], a[2])) for L in layers}
            if not any(t.any() for t in TM.values()):
                raise RuntimeError(f"router: no target copper for {net}")
            is_goal = lambda s: TM[s[0]][s[2], s[1]]
            h = lambda i, j: 0.0
        else:
            si, sj = S[0][1], S[0][2]
            mind = 0.45 / g
            is_goal = lambda s: (not VM[s[2], s[1]]) and math.hypot(s[1] - si, s[2] - sj) >= mind
            h = lambda i, j: 0.0
        dist, prev, pq = {}, {}, []
        for s in S:
            dist[s] = 0.0
            heapq.heappush(pq, (h(s[1], s[2]), 0.0, s, None))
        moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                 (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        found = None
        vstep = via_cost / g
        while pq:
            f, d, s, dirn = heapq.heappop(pq)
            if d > dist.get(s, 1e18) + 1e-9:
                continue
            if is_goal(s):
                found = s
                break
            L, i, j = s
            for di, dj, cst in moves:
                ni, nj = i + di, j + dj
                if not (0 <= ni < W and 0 <= nj < H) or M[L][nj, ni]:
                    continue
                if di and dj and (M[L][j, ni] or M[L][nj, i]):
                    continue
                turn = 0.0 if dirn in (None, (di, dj)) else 0.6
                nd = d + cst * (1 + lc.get(L, 0.0)) + turn
                if OW is not None and OW[L][nj, ni]:
                    nd += pen(OW[L][nj, ni])
                ns = (L, ni, nj)
                if nd < dist.get(ns, 1e18):
                    dist[ns] = nd; prev[ns] = s
                    heapq.heappush(pq, (nd + h(ni, nj), nd, ns, (di, dj)))
            if allow_via and VM is not None and len(layers) > 1 and not VM[j, i]:
                for L2 in layers:
                    if L2 == L or M[L2][j, i]:
                        continue
                    ns = (L2, i, j)
                    nd = d + vstep
                    if VOW is not None and VOW[j, i]:
                        nd += pen(VOW[j, i])
                    if nd < dist.get(ns, 1e18):
                        dist[ns] = nd; prev[ns] = s
                        heapq.heappush(pq, (nd + h(i, j), nd, ns, None))
        if found is None:
            import os
            if os.environ.get("DUMP_FAIL") == net and not getattr(self, "_dumped", False) and \
                    abs(a[1] - float(os.environ.get("DUMP_X", a[1]))) < 0.01 and self._pad >= float(os.environ.get("DUMP_PAD", 0)):
                self._dumped = True
                rows = []
                for L in layers:
                    img = np.zeros(M[L].shape + (3,), np.uint8) + 255
                    img[M[L]] = (180, 180, 180)
                    if goal[0] == "net":
                        img[TM[L]] = (0, 170, 0)
                    seen = np.zeros_like(M[L])
                    for (L_, i_, j_) in dist:
                        if L_ == L:
                            seen[j_, i_] = True
                    img[seen] = (120, 200, 255)
                    if VM is not None:
                        vv = ~VM & ~M[L]
                        img[vv & ~seen] = (255, 240, 200)
                    rows += [img, np.zeros((4, img.shape[1], 3), np.uint8)]
                Image.fromarray(np.vstack(rows)).resize((W * 3, (H + 4) * len(layers) * 3), Image.NEAREST).save(
                    os.environ.get("DUMP_PNG", "/tmp/dump.png"))
                print("dumped", net, a, bbox)
            raise RuntimeError(f"router: no path for {net} {a} -> {goal[0]}")
        path = [found]
        while path[-1] in prev:
            path.append(prev[path[-1]])
        path.reverse()
        if soft:
            own = set()
            for p_, s_ in zip([None] + path[:-1], path):
                o = OW[s_[0]][s_[2], s_[1]]
                if o:
                    own.add(int(o) - 1)
                if p_ is not None and p_[0] != s_[0] and VOW[s_[2], s_[1]]:
                    own.add(int(VOW[s_[2], s_[1]]) - 1)
            if goal[0] == "via" and VOW[found[2], found[1]]:
                own.add(int(VOW[found[2], found[1]]) - 1)
            return own
        segs, vias = [], []
        cur_L, pts = path[0][0], [path[0]]
        for s in path[1:]:
            if s[0] != cur_L:
                segs.append((cur_L, pts)); vias.append(s)
                cur_L, pts = s[0], [s]
            else:
                pts.append(s)
        segs.append((cur_L, pts))
        out = []
        new = []
        if not hasattr(self.k, "router_ids"):
            self.k.router_ids = set()
        self.k.tag_router = True
        for idx, (L, pts) in enumerate(segs):
            xy = [(x0 + i * g, y0 + j * g) for _, i, j in pts]
            if idx == 0:
                xy[0] = (a[1], a[2])
            if idx == len(segs) - 1 and b is not None:
                xy[-1] = (b[1], b[2])
            if idx == len(segs) - 1 and goal[0] == "net":     # finish inside a via/pad-centre target
                ex, ey = xy[-1]
                for L_, kind, geo in items:
                    if kind == "circle" and L_ in ("all", L) and math.dist((ex, ey), geo[:2]) <= geo[2] + 0.05:
                        xy.append(geo[:2]); break
            xy = simplify(xy)
            if len(xy) > 1:
                self.k.track(net, L, xy, w)
                for p, q in zip(xy, xy[1:]):
                    new.append((L, "seg", (p[0], p[1], q[0], q[1], w / 2)))
            out.append((L, xy))
        for _, i, j in vias:
            self.k.via(net, x0 + i * g, y0 + j * g, viad, 0.2 if viad <= 0.5 else 0.3)
            new.append(("all", "circle", (x0 + i * g, y0 + j * g, viad / 2)))
        if goal[0] == "via":
            vx, vy = x0 + found[1] * g, y0 + found[2] * g
            self.k.via(net, vx, vy, viad, 0.2 if viad <= 0.5 else 0.3)
        self.k.tag_router = False
        if net in self.conn and goal[0] == "net":          # only a route that reached the root copper is rooted
            add = list(new) + [("all" if a[0] == "all" else a[0], "circle", (a[1], a[2], 0.1))]
            if b is not None:
                add.append(("all" if b[0] == "all" else b[0], "circle", (b[1], b[2], 0.1)))
            self.conn[net].extend(add)
            self._last_conn = (net, add)
        return out


class _Tag:
    """list proxy that appends (shape..., owner) to the soft list"""
    def __init__(self, lst, o):
        self.lst, self.o = lst, o

    def append(self, sh):
        self.lst.append(sh + (self.o,))


def _draw(dr, T, g, kind, geo, ex, fill):
    if kind == "circle":
        x, y, r = geo; cx, cy = T(x, y); R = (r + ex) / g
        dr.ellipse([cx - R, cy - R, cx + R, cy + R], fill=fill)
    elif kind == "seg":
        ax, ay, bx, by, hw = geo
        R = (hw + ex) / g
        A, B = T(ax, ay), T(bx, by)
        L_ = math.hypot(B[0] - A[0], B[1] - A[1])
        if L_ > 1e-9:                                   # exact rectangle (PIL thins diagonal wide lines)
            nx, ny = -(B[1] - A[1]) / L_ * R, (B[0] - A[0]) / L_ * R
            dr.polygon([(A[0] + nx, A[1] + ny), (B[0] + nx, B[1] + ny), (B[0] - nx, B[1] - ny),
                        (A[0] - nx, A[1] - ny)], fill=fill)
        for cx, cy in (A, B):
            dr.ellipse([cx - R, cy - R, cx + R, cy + R], fill=fill)
    else:
        polys, add = geo
        R = (ex + add) / g
        for pts in polys:
            tp = [T(*q) for q in pts]
            if len(tp) > 2:
                dr.polygon(tp, fill=fill)
            for q0, q1 in zip(tp, tp[1:] + tp[:1]):
                dr.line([q0, q1], fill=fill, width=max(1, int(math.ceil(2 * R))))
                dr.ellipse([q0[0] - R, q0[1] - R, q0[0] + R, q0[1] + R], fill=fill)


def _extra(n, c=0.2):
    """clearance beyond the router's base clearance c (absolute targets: edge 0.3, PCIe 0.4, REFCLK 0.5, 12 V 0.2;
    +0.02 on the HS classes for grid rounding)"""
    if n == "<edge>":                                    # 0.3 copper-to-edge: c + extra + 0.05 (outline half width)
        return 0.24 - c
    if n.startswith("REFCLK") or n.startswith("U1_REFCLK"):
        return 0.52 - c
    if n.startswith(("PET", "PER", "C_PER", "C_PET")):
        return 0.42 - c
    if n.startswith("12V"):
        return max(0.0, 0.2 - c)
    return 0.0


def simplify(xy):
    if len(xy) < 3:
        return xy
    out = [xy[0]]
    for p, q in zip(xy[1:-1], xy[2:]):
        a = out[-1]
        d1 = (p[0] - a[0], p[1] - a[1]); d2 = (q[0] - p[0], q[1] - p[1])
        if abs(d1[0] * d2[1] - d1[1] * d2[0]) < 1e-9 and d1[0] * d2[0] + d1[1] * d2[1] > 0:
            continue
        out.append(p)
    out.append(xy[-1])
    return out


def _inside(p, poly):
    x, y = p; c = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            c = not c
    return c


def _touch(it, pts_r):
    """does shape it touch any (point, radius, layer) in pts_r (same layer, or either one a through item)?"""
    L, kind, geo = it
    for (px, py), pr, Lq in pts_r:
        if not (L == "all" or Lq == "all" or L == Lq):
            continue
        if kind == "circle":
            x, y, r = geo
            if math.hypot(px - x, py - y) <= r + pr + 0.02:
                return True
        elif kind == "seg":
            ax, ay, bx, by, hw = geo
            vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy
            t = 0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
            if math.hypot(px - ax - t * vx, py - ay - t * vy) <= hw + pr + 0.02:
                return True
        else:
            for poly in geo[0]:
                if _inside((px, py), poly) or any(math.hypot(px - qx, py - qy) <= pr + 0.02 for qx, qy in poly):
                    return True
    return False


def _keypts(it):
    L, kind, geo = it
    if kind == "circle":
        return [((geo[0], geo[1]), geo[2], L)]
    if kind == "seg":
        ax, ay, bx, by, hw = geo
        n = max(1, int(math.hypot(bx - ax, by - ay) / 0.1))
        return [((ax + (bx - ax) * i / n, ay + (by - ay) * i / n), hw, L) for i in range(n + 1)]
    out = []
    for poly in geo[0]:
        cx = sum(q[0] for q in poly) / len(poly); cy = sum(q[1] for q in poly) / len(poly)
        out.append(((cx, cy), 0.0, L))
        out += [((qx, qy), 0.0, L) for qx, qy in poly]
    return out


def _drop_connected(items, start, layer="all"):
    """Remove the copper already connected to start (flood over touching same-net shapes on a shared layer)."""
    seen = [((start), 0.05, layer)]
    rest = list(items)
    changed = True
    while changed:
        changed = False
        keep = []
        for it in rest:
            if _touch(it, seen):
                seen += _keypts(it); changed = True
            else:
                keep.append(it)
        rest = keep
    return rest
