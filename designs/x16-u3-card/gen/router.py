"""Tiny grid maze router for low-speed nets (used by the sideband blocks).

Obstacles are rasterised from what is already on the board (tracks, vias, pads, holes, board edge), inflated by
clearance + half the new track width, so every route it returns is DRC clean by construction (up to grid
rounding, covered by a small extra margin).  A* over (layer, x, y) on a 0.05 mm grid with 45-degree moves; layer
changes place a through via (checked against all routing layers).  Zones are ignored (they refill around tracks).
"""
import heapq, math
import numpy as np
from PIL import Image, ImageDraw
import pcbnew as P

LAYER = {"L1": P.F_Cu, "L3": P.In2_Cu, "L6": P.B_Cu, "L2": P.In1_Cu, "L4": P.In3_Cu, "L5": P.In4_Cu}


class Router:
    def __init__(self, k, g=0.05, clearance=0.2, margin=0.03):
        self.k, self.g, self.c, self.m = k, g, clearance, margin
        self.O = k.O
        self.routed = []
        self.keepouts = []          # (layer, poly) no router copper (e.g. over a power pour)
        self.conn = {}              # net -> [(layer, kind, geo)] copper known to be connected to the net's root

    def seed(self, net, items):
        self.conn.setdefault(net, []).extend(items)

    # ------------------------------------------------------------------ obstacles
    def _shapes(self, bbox):
        """List of (layers, net, kind, geom) inside bbox (board-local mm)."""
        x0, y0, x1, y1 = bbox
        O = self.O
        out = []

        def inb(x, y, r):
            return x0 - r < x < x1 + r and y0 - r < y < y1 + r

        for t in self.k.b.GetTracks():
            net = t.GetNetname()
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition(); x, y = P.ToMM(p.x) - O[0], P.ToMM(p.y) - O[1]
                if inb(x, y, 2):
                    out.append(("all", net, "circle", (x, y, P.ToMM(t.GetWidth()) / 2)))
            else:
                a, b = t.GetStart(), t.GetEnd()
                ax, ay, bx, by = P.ToMM(a.x) - O[0], P.ToMM(a.y) - O[1], P.ToMM(b.x) - O[0], P.ToMM(b.y) - O[1]
                if max(ax, bx) < x0 - 2 or min(ax, bx) > x1 + 2 or max(ay, by) < y0 - 2 or min(ay, by) > y1 + 2:
                    continue
                L = [n for n, l in LAYER.items() if l == t.GetLayer()]
                out.append((L[0] if L else "x", net, "seg", (ax, ay, bx, by, P.ToMM(t.GetWidth()) / 2)))
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
        for d in self.k.b.GetDrawings():
            if d.GetLayer() == P.Edge_Cuts:
                a, b = d.GetStart(), d.GetEnd()
                out.append(("all", "<edge>", "seg", (P.ToMM(a.x) - O[0], P.ToMM(a.y) - O[1],
                                                     P.ToMM(b.x) - O[0], P.ToMM(b.y) - O[1], 0.05)))
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
            ex = infl + _extra(n)                            # edge 0.3, PCIe 0.4, REFCLK 0.5 vs 0.2 copper
            if kind == "circle":
                x, y, r = geo; cx, cy = T(x, y); R = (r + ex) / g
                dr.ellipse([cx - R, cy - R, cx + R, cy + R], fill=1)
            elif kind == "seg":
                ax, ay, bx, by, hw = geo
                R = (hw + ex) / g
                A, B = T(ax, ay), T(bx, by)
                L_ = math.hypot(B[0] - A[0], B[1] - A[1])
                if L_ > 1e-9:                                   # exact rectangle (PIL thins diagonal wide lines)
                    nx, ny = -(B[1] - A[1]) / L_ * R, (B[0] - A[0]) / L_ * R
                    dr.polygon([(A[0] + nx, A[1] + ny), (B[0] + nx, B[1] + ny), (B[0] - nx, B[1] - ny),
                                (A[0] - nx, A[1] - ny)], fill=1)
                for cx, cy in (A, B):
                    dr.ellipse([cx - R, cy - R, cx + R, cy + R], fill=1)
            else:
                polys, add = geo
                R = (ex + add) / g
                for pts in polys:
                    tp = [T(*q) for q in pts]
                    if len(tp) > 2:
                        dr.polygon(tp, fill=1)
                    for q0, q1 in zip(tp, tp[1:] + tp[:1]):
                        dr.line([q0, q1], fill=1, width=max(1, int(math.ceil(2 * R))))
                        dr.ellipse([q0[0] - R, q0[1] - R, q0[0] + R, q0[1] + R], fill=1)
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

    def _search(self, net, a, goal, w=0.15, layers=("L1", "L3", "L6"), via_cost=4.0, pad=3.0, viad=0.5,
                layer_cost=None, bbox=None, allow_via=True, maxpad=12.0):
        g = self.g
        b = goal[1] if goal[0] == "pt" else None
        import time, os
        while True:
            t0 = time.time()
            try:
                return self._search1(net, a, goal, w, layers, via_cost, pad, viad, layer_cost, bbox, allow_via)
            except RuntimeError:
                if bbox is not None or pad >= maxpad:
                    raise
                pad *= 2
            finally:
                if os.environ.get("RTIME") and time.time() - t0 > 2.0:
                    print(f"  slow {time.time() - t0:5.1f}s {net} {goal[0]} pad {pad} from {a}", flush=True)

    def _search1(self, net, a, goal, w, layers, via_cost, pad, viad, layer_cost, bbox, allow_via):
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
        shapes = self._shapes(bbox)
        infl = self.c + w / 2 + self.m
        M = {L: self._mask(shapes, L, net, infl, bbox) for L in layers}
        vinfl = self.c + viad / 2 + self.m
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
                items = _drop_connected(items, (a[1], a[2]))
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
        if net in self.conn and goal[0] == "net":          # only a route that reached the root copper is rooted
            self.conn[net].extend(new)
            self.conn[net].append(("all" if a[0] == "all" else a[0], "circle", (a[1], a[2], 0.1)))
            if b is not None:
                self.conn[net].append(("all" if b[0] == "all" else b[0], "circle", (b[1], b[2], 0.1)))
        return out


def _extra(n):
    if n == "<edge>":                                    # 0.3 copper-to-edge: c + 0.04 + 0.05 (outline half width)
        return 0.04
    if n.startswith("REFCLK") or n.startswith("U1_REFCLK"):
        return 0.3
    if n.startswith(("PET", "PER", "C_PER", "C_PET")):
        return 0.2
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
    """does shape it touch any (point, radius) in pts_r?"""
    L, kind, geo = it
    for (px, py), pr in pts_r:
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
        return [((geo[0], geo[1]), geo[2])]
    if kind == "seg":
        ax, ay, bx, by, hw = geo
        n = max(1, int(math.hypot(bx - ax, by - ay) / 0.1))
        return [((ax + (bx - ax) * i / n, ay + (by - ay) * i / n), hw) for i in range(n + 1)]
    out = []
    for poly in geo[0]:
        cx = sum(q[0] for q in poly) / len(poly); cy = sum(q[1] for q in poly) / len(poly)
        out.append(((cx, cy), 0.0))
        out += [((qx, qy), 0.0) for qx, qy in poly]
    return out


def _drop_connected(items, start):
    """Remove the copper already connected to start (flood over touching same-net shapes)."""
    seen = [((start), 0.05)]
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
