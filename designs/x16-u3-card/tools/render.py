import sys, os, pcbnew as P, cairosvg
pcb, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
b = P.LoadBoard(pcb)
pc = P.PLOT_CONTROLLER(b); po = pc.GetPlotOptions()
po.SetOutputDirectory(out); po.SetPlotFrameRef(False); po.SetMirror(False)
po.SetDrillMarksType(P.DRILL_MARKS_FULL_DRILL_SHAPE)
sets = {"top": [P.F_Cu, P.F_SilkS, P.Edge_Cuts, P.F_CrtYd], "bot": [P.B_Cu, P.B_SilkS, P.Edge_Cuts, P.B_CrtYd],
        "l3": [P.In2_Cu, P.Edge_Cuts]}
for name, layers in sets.items():
    for i, L in enumerate(layers):
        pc.SetLayer(L); pc.OpenPlotfile(f"{name}_{i}", P.PLOT_FORMAT_SVG, name); pc.PlotLayer()
    pc.ClosePlot()
print("ok")
