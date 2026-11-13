"""Fill the zones in memory and write the DRC report of a board next to it.  Exit code 1 if anything but the
library-link warnings is left.
usage: python3 tools/drc.py board.kicad_pcb"""
import sys, re, os
from collections import Counter
import pcbnew as P

pcb = os.path.abspath(sys.argv[1])
b = P.LoadBoard(pcb)
P.ZONE_FILLER(b).Fill(b.Zones())
rpt = pcb[:-len(".kicad_pcb")] + "-drc.rpt"
P.WriteDRCReport(b, rpt, P.EDA_UNITS_MILLIMETRES, True)
s = open(rpt).read()
c = Counter(re.findall(r"\n\[(\w+)\]", s))
un = int(re.search(r"Found (\d+) unconnected", s).group(1))
print(os.path.basename(pcb), dict(c), "unconnected:", un)
sys.exit(1 if un or set(c) - {"lib_footprint_issues", "lib_footprint_mismatch"} else 0)
