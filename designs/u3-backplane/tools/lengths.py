"""Routed length and via count of every high-speed net of a board, written as JSON.
usage: python3 tools/lengths.py board.kicad_pcb out.json"""
import sys, re, json
import pcbnew as P

b = P.LoadBoard(sys.argv[1])
L, V = {}, {}
for t in b.GetTracks():
    n = t.GetNetname()
    if not re.search(r"(PE[TR]\d+|REFCLK\w*)_[PN]$", n):
        continue
    if t.GetClass() == "PCB_VIA":
        V[n] = V.get(n, 0) + 1
    else:
        L[n] = L.get(n, 0.0) + P.ToMM(t.GetLength())
out = {n: {"mm": round(L[n], 3), "vias": V.get(n, 0)} for n in sorted(L)}
pairs = {}
for n in out:
    pairs.setdefault(n[:-2], []).append(out[n]["mm"])
skew = {p: round(abs(v[0] - v[1]), 3) for p, v in pairs.items() if len(v) == 2}
lane = {}                                        # both sides of an AC cap (DnC_... + Dn_...) are one lane
for n, v in out.items():
    if "REFCLK" not in n:
        key = re.sub(r"^D(\d+)C_", r"D\1_", n)
        e = lane.setdefault(key, {"mm": 0.0, "vias": 0})
        e["mm"] = round(e["mm"] + v["mm"], 3); e["vias"] += v["vias"]
hs = [v["mm"] for v in lane.values()]
summary = {"lane_min_mm": min(hs), "lane_max_mm": max(hs), "max_skew_mm": max(skew.values()),
           "max_vias_per_lane": max(v["vias"] for v in lane.values())}
json.dump({"summary": summary, "lanes": lane, "skew_mm": skew, "nets": out}, open(sys.argv[2], "w"), indent=1)
print(summary)
