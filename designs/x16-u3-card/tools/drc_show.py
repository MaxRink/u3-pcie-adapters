import re, sys
s = open(sys.argv[1]).read()
skip = sys.argv[2].split(",") if len(sys.argv) > 2 else ["silk", "lib_footprint"]
for bl in re.split(r'\n(?=\[)', s):
    if bl.startswith('[') and not any(bl.startswith('[' + k) for k in skip):
        lines = bl.strip().split("\n")
        print(lines[0][:160]); [print("   ", l.strip()[:120]) for l in lines[2:4]]
