"""Fabrication outputs for JLCPCB and PCBWay from a generated board: Gerbers + Excellon drill (zip),
BOM and CPL (JLC column names, PCBWay accepts the same), plus a PDF-free PNG preview is done elsewhere.
usage: python3 fab.py <board.kicad_pcb> <bom_raw.json> <outdir>"""
import sys, os, csv, json, zipfile, glob
from collections import OrderedDict
import pcbnew as P

pcb, bomjson, out = [os.path.abspath(a) for a in sys.argv[1:4]]
name = os.path.splitext(os.path.basename(pcb))[0]
os.makedirs(out, exist_ok=True)
gdir = os.path.join(out, "gerber"); os.makedirs(gdir, exist_ok=True)
for f in glob.glob(os.path.join(gdir, "*")):
    os.remove(f)
b = P.LoadBoard(pcb)

pc = P.PLOT_CONTROLLER(b); po = pc.GetPlotOptions()
po.SetOutputDirectory(gdir); po.SetPlotFrameRef(False); po.SetUseGerberProtelExtensions(True)
po.SetUseGerberX2format(False); po.SetIncludeGerberNetlistInfo(False); po.SetCreateGerberJobFile(False)
po.SetSubtractMaskFromSilk(True); po.SetUseAuxOrigin(False); po.SetGerberPrecision(6)
po.SetPlotValue(False); po.SetPlotReference(True); po.SetDrillMarksType(P.DRILL_MARKS_NO_DRILL_SHAPE)
layers = [(P.F_Cu, "F_Cu"), (P.In1_Cu, "In1_Cu"), (P.In2_Cu, "In2_Cu"), (P.In3_Cu, "In3_Cu"), (P.In4_Cu, "In4_Cu"),
          (P.B_Cu, "B_Cu"), (P.F_Mask, "F_Mask"), (P.B_Mask, "B_Mask"), (P.F_Paste, "F_Paste"),
          (P.B_Paste, "B_Paste"), (P.F_SilkS, "F_Silkscreen"), (P.B_SilkS, "B_Silkscreen"), (P.Edge_Cuts, "Edge_Cuts")]
for L, suf in layers:
    pc.SetLayer(L); pc.OpenPlotfile(suf, P.PLOT_FORMAT_GERBER, suf); pc.PlotLayer()
pc.ClosePlot()
dw = P.EXCELLON_WRITER(b)
dw.SetOptions(False, True, P.VECTOR2I(0, 0), False)       # no mirror, minimal header, abs origin, separate NPTH
dw.SetFormat(True, P.GENDRILL_WRITER_BASE.DECIMAL_FORMAT, 3, 3)
dw.CreateDrillandMapFilesSet(gdir, True, False)
zpath = os.path.join(out, f"{name}-gerbers.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(os.path.join(gdir, "*"))):
        z.write(f, os.path.basename(f))

# ---- BOM + CPL (positions taken from the saved board, so they match the Gerbers)
raw = {r["ref"]: r for r in json.load(open(bomjson))}
fps = {f.GetReference(): f for f in b.GetFootprints()}
groups = OrderedDict()
cpl = []
for ref, r in raw.items():
    if r.get("dnp"):
        continue
    f = fps[ref]
    key = (r["value"], r["fp"].split(":")[1], r["lcsc"])
    groups.setdefault(key, []).append(ref)
    pos = f.GetPosition()
    cpl.append([ref, f"{P.ToMM(pos.x):.3f}mm", f"{-P.ToMM(pos.y):.3f}mm",
                "Bottom" if f.IsFlipped() else "Top", f"{f.GetOrientationDegrees() % 360:.1f}"])
with open(os.path.join(out, f"{name}-BOM.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Quantity"])
    for (val, fp, lcsc), refs in groups.items():
        w.writerow([val, ",".join(sorted(refs, key=lambda s: (s[0], int(''.join(c for c in s if c.isdigit()) or 0)))),
                    fp, lcsc, len(refs)])
with open(os.path.join(out, f"{name}-CPL.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    w.writerows(sorted(cpl))
# ---- BOM variants for parts with thin stock: same footprints, only the part number changes
#      (value in the generated board, replacement value, replacement LCSC number)
VARIANTS = {
    "clock-9DBL0442C": [("PI6CB33401ZHIEX", "9DBL0442CKILF", "")],
    "efuse-TPS259827": [("TPS259824ONRGER", "TPS259827ONRGER", "C2155761")],
    "clock-9DBL0442C_efuse-TPS259827": [("PI6CB33401ZHIEX", "9DBL0442CKILF", ""),
                                        ("TPS259824ONRGER", "TPS259827ONRGER", "C2155761")],
}
have = {val for (val, fp, lcsc) in groups}
for vname, subs in VARIANTS.items():
    if not all(old in have for old, _, _ in subs):      # e.g. a CDCDB400 card has no drop-in clock alternative
        continue
    with open(os.path.join(out, f"{name}-BOM-{vname}.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Quantity"])
        for (val, fp, lcsc), refs in groups.items():
            for old, newv, newl in subs:
                if val == old:
                    val, lcsc = newv, newl
            w.writerow([val, ",".join(sorted(refs, key=lambda s: (s[0], int(''.join(c for c in s if c.isdigit()) or 0)))),
                        fp, lcsc, len(refs)])
# loose parts (not placed by the assembler): one 2.54 mm shunt per drive 12 V jumper, fitted on 2-3 (SLOT)
jps = sorted(r for r in fps if r.startswith("JP") and r[2:].isdigit())
if jps:
    with open(os.path.join(out, f"{name}-loose-parts.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Comment", "For", "LCSC Part #", "Quantity"])
        w.writerow(["Jumper shunt 2.54 mm 1x2 (HCTL HC-JP254-1-65-CL-B-G0), fit on pins 2-3 = SLOT 12V", ",".join(jps),
                    "C5380290", len(jps)])
print("wrote", zpath, len(groups), "BOM lines,", len(cpl), "placements")
