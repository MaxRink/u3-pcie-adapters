import re, sys
s = open(sys.argv[1]).read()
nets = dict(re.findall(r'\(net (\d+) "([^"]*)"\)', s))
fp = re.search(r'\(footprint "antmicro-footprints:Amphenol_G14A421211112HR"(.*?)\n\t\)\n', s, re.S).group(1)
at = re.search(r'\(at ([-\d. ]+)\)', fp).group(1).split()
ax, ay = float(at[0]), float(at[1]); print("J1 at", at)
for m in re.finditer(r'\(via\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([\d.]+)\)\s*\(drill ([\d.]+)\)\s*\(layers ([^)]*)\)\s*\(net (\d+)\)', s):
    x, y, sz, d, ly, n = m.groups(); dx, dy = -(float(x) - ax), -(float(y) - ay)  # undo 180 rot
    if abs(dx) < 9 and abs(dy) < 9:
        print("via rel %.3f %.3f size %s drill %s %s %s" % (dx, dy, sz, d, ly, nets.get(n, n)))
for m in re.finditer(r'\(segment\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)\s*\(width ([\d.]+)\)\s*\(layer "([^"]+)"\)\s*\(net (\d+)\)', s):
    x1, y1, x2, y2, w, l, n = m.groups(); nn = nets.get(n, n)
    if abs(float(x1) - ax) < 8 and abs(float(y1) - ay) < 8 and re.search('TX0|RX0|REF0', nn):
        print('seg', l, w, nn, round(ax - float(x1), 3), round(ay - float(y1), 3), round(ax - float(x2), 3), round(ay - float(y2), 3))
