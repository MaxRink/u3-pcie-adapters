"""Generate KiCad 7 template boards (stackup + design settings) and .kicad_pro (net classes)."""
import json, os, sys, copy
OUT=sys.argv[1]
MASK=("0.02","3.8","0.025")
STACKS={
 "jlc06161h-3313_1.6mm": dict(title="JLC06161H-3313 6L 1.6mm", cu=6, layers=[
   ("F.Cu",0.035),("prepreg","3313",0.0994,4.1),("In1.Cu",0.0152),("core","Core",0.55,4.6),("In2.Cu",0.0152),
   ("prepreg","2116",0.1088,4.16),("In3.Cu",0.0152),("core","Core",0.55,4.6),("In4.Cu",0.0152),("prepreg","3313",0.0994,4.1),("B.Cu",0.035)],
   names={"F.Cu":"L1_SIG_HS","In1.Cu":"L2_GND","In2.Cu":"L3_LS_3V3","In3.Cu":"L4_12V","In4.Cu":"L5_GND","B.Cu":"L6_SIG_HS"}),
 "jlc04161h-3313_1.6mm": dict(title="JLC04161H-3313 4L 1.6mm", cu=4, layers=[
   ("F.Cu",0.035),("prepreg","3313",0.0994,4.1),("In1.Cu",0.0152),("core","Core",1.265,4.6),("In2.Cu",0.0152),("prepreg","3313",0.0994,4.1),("B.Cu",0.035)],
   names={"F.Cu":"L1_SIG_HS","In1.Cu":"L2_GND","In2.Cu":"L3_PWR_GND","B.Cu":"L4_SIG_LS"}),
 "jlc04081h-3313_0.8mm": dict(title="JLC04081H-3313 4L 0.8mm (M.2)", cu=4, layers=[
   ("F.Cu",0.035),("prepreg","3313",0.0994,4.1),("In1.Cu",0.0152),("core","Core",0.5,4.6),("In2.Cu",0.0152),("prepreg","3313",0.0994,4.1),("B.Cu",0.035)],
   names={"F.Cu":"L1_SIG_HS","In1.Cu":"L2_GND","In2.Cu":"L3_GND_PWR","B.Cu":"L4_SIG_LS"}),
}
LAYER_IDS={"F.Cu":0,"In1.Cu":1,"In2.Cu":2,"In3.Cu":3,"In4.Cu":4,"B.Cu":31}
def pcb(st):
    cu=[l for l in st["layers"] if len(l)==2]
    ly="  (layers\n"
    for l in cu:
        ly+=f'    ({LAYER_IDS[l[0]]} "{l[0]}" signal "{st["names"][l[0]]}")\n'
    for i,n,t in [(32,"B.Adhes","user \"B.Adhesive\""),(33,"F.Adhes","user \"F.Adhesive\""),(34,"B.Paste","user"),(35,"F.Paste","user"),
                  (36,"B.SilkS","user \"B.Silkscreen\""),(37,"F.SilkS","user \"F.Silkscreen\""),(38,"B.Mask","user"),(39,"F.Mask","user"),
                  (40,"Dwgs.User","user \"User.Drawings\""),(41,"Cmts.User","user \"User.Comments\""),(44,"Edge.Cuts","user"),(45,"Margin","user"),
                  (46,"B.CrtYd","user \"B.Courtyard\""),(47,"F.CrtYd","user \"F.Courtyard\""),(48,"B.Fab","user"),(49,"F.Fab","user")]:
        ly+=f'    ({i} "{n}" {t})\n'
    ly+="  )\n"
    s='    (stackup\n'
    s+='      (layer "F.SilkS" (type "Top Silk Screen"))\n      (layer "F.Paste" (type "Top Solder Paste"))\n'
    s+=f'      (layer "F.Mask" (type "Top Solder Mask") (thickness {MASK[0]}) (material "LPI") (epsilon_r {MASK[1]}) (loss_tangent {MASK[2]}))\n'
    d=1
    for l in st["layers"]:
        if len(l)==2: s+=f'      (layer "{l[0]}" (type "copper") (thickness {l[1]}))\n'
        else:
            kind,mat,th,er=l
            s+=f'      (layer "dielectric {d}" (type "{kind}") (thickness {th}) (material "NP-155F {mat}") (epsilon_r {er}) (loss_tangent 0.02))\n'; d+=1
    s+=f'      (layer "B.Mask" (type "Bottom Solder Mask") (thickness {MASK[0]}) (material "LPI") (epsilon_r {MASK[1]}) (loss_tangent {MASK[2]}))\n'
    s+='      (layer "B.Paste" (type "Bottom Solder Paste"))\n      (layer "B.SilkS" (type "Bottom Silk Screen"))\n'
    s+='      (copper_finish "ENIG")\n      (dielectric_constraints yes)\n      (edge_connector bevelled)\n      (edge_plating no)\n    )\n'
    setup=f"""  (setup
{s}    (pad_to_mask_clearance 0)
    (solder_mask_min_width 0.1)
    (allow_soldermask_bridges_in_footprints no)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros false) (usegerberextensions true) (usegerberattributes true) (usegerberadvancedattributes true) (creategerberjobfile true)
      (dashed_line_dash_ratio 12.000000) (dashed_line_gap_ratio 3.000000) (svgprecision 4) (plotframeref false) (viasonmask false) (mode 1)
      (useauxorigin false) (hpglpennumber 1) (hpglpenspeed 20) (hpglpendiameter 15.000000) (dxfpolygonmode true) (dxfimperialunits true)
      (dxfusepcbnewfont true) (psnegative false) (psa4output false) (plotreference true) (plotvalue true) (plotinvisibletext false)
      (sketchpadsonfab false) (subtractmaskfromsilk true) (outputformat 1) (mirror false) (drillshape 0) (scaleselection 1) (outputdirectory "gerbers/")
    )
  )
"""
    return f"""(kicad_pcb (version 20221018) (generator pcbnew)
  (general (thickness {sum(l[1] if len(l)==2 else l[2] for l in st['layers'])+2*float(MASK[0]):.4f}))
  (paper "A4")
  (title_block (title "{st['title']} - PCIe4 rule template") (comment 1 "Rule set: /mnt/project-files/design-rules/"))
{ly}{setup}  (net 0 "")
  (gr_rect (start 100 100) (end 150 130) (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts"))
)
"""
def pro(name, cu):
    nc_default={"name":"Default","clearance":0.15,"track_width":0.2,"via_diameter":0.6,"via_drill":0.3,"microvia_diameter":0.3,"microvia_drill":0.1,"diff_pair_width":0.2,"diff_pair_gap":0.25,"diff_pair_via_gap":0.25,"wire_width":6,"bus_width":12,"line_style":0,"pcb_color":"rgba(0, 0, 0, 0.000)","schematic_color":"rgba(0, 0, 0, 0.000)"}
    def nc(n,**k):
        d=copy.deepcopy(nc_default); d.update(name=n,**k); return d
    classes=[nc_default,
      nc("PCIe_85",clearance=0.40,track_width=0.157,diff_pair_width=0.157,diff_pair_gap=0.152,diff_pair_via_gap=0.50,via_diameter=0.55,via_drill=0.25),
      nc("REFCLK_100",clearance=0.50,track_width=0.128,diff_pair_width=0.128,diff_pair_gap=0.254,diff_pair_via_gap=0.50,via_diameter=0.55,via_drill=0.25),
      nc("PWR_12V",clearance=0.20,track_width=1.0,via_diameter=0.6,via_drill=0.3),
      nc("PWR_3V3",clearance=0.15,track_width=0.4,via_diameter=0.6,via_drill=0.3),
      nc("GND",clearance=0.15,track_width=0.3,via_diameter=0.55,via_drill=0.25),
      nc("LowSpeed",clearance=0.15,track_width=0.15,via_diameter=0.55,via_drill=0.25)]
    patterns=[{"netclass":"PCIe_85","pattern":p} for p in ("*PET?_?","*PER?_?","*PET1?_?","*PER1?_?","*TX?_?","*RX?_?","*TX1?_?","*RX1?_?")]
    patterns+=[{"netclass":"REFCLK_100","pattern":"*REFCLK*"},{"netclass":"PWR_12V","pattern":"*12V*"},{"netclass":"PWR_3V3","pattern":"*3V3*"},
              {"netclass":"GND","pattern":"GND"}]
    rules={"min_clearance":0.1,"min_track_width":0.1,"min_via_diameter":0.5,"min_via_annular_width":0.15,"min_through_hole_diameter":0.2,
           "min_hole_to_hole":0.25,"min_hole_clearance":0.2,"min_copper_edge_clearance":0.3,"min_silk_clearance":0.15,"min_text_height":1.0,
           "min_text_thickness":0.15,"min_microvia_diameter":0.2,"min_microvia_drill":0.1,"solder_mask_to_copper_clearance":0.0,"use_height_for_length_calcs":True,
           "allow_blind_buried_vias":False,"allow_microvias":False,"max_error":0.005,"min_resolved_spokes":2,"solder_mask_clearance":0.0,"solder_mask_min_width":0.1}
    p={"board":{"design_settings":{"defaults":{"board_outline_line_width":0.1,"copper_line_width":0.2,"copper_text_size_h":1.5,"copper_text_size_v":1.5,"copper_text_thickness":0.3,"silk_line_width":0.15,"silk_text_size_h":1.0,"silk_text_size_v":1.0,"silk_text_thickness":0.15},
        "diff_pair_dimensions":[{"gap":0.0,"via_gap":0.0,"width":0.0},{"gap":0.152,"via_gap":0.5,"width":0.157},{"gap":0.254,"via_gap":0.5,"width":0.128},{"gap":0.10,"via_gap":0.5,"width":0.10}],
        "rules":rules,"track_widths":[0.0,0.1,0.128,0.157,0.2,0.4,1.0,2.0],
        "via_dimensions":[{"diameter":0.0,"drill":0.0},{"diameter":0.55,"drill":0.25},{"diameter":0.6,"drill":0.3},{"diameter":0.5,"drill":0.2}]}},
       "meta":{"filename":name+".kicad_pro","version":1},
       "net_settings":{"classes":classes,"meta":{"version":3},"net_colors":None,"netclass_assignments":None,"netclass_patterns":patterns},
       "pcbnew":{"last_paths":{}},"sheets":[],"text_variables":{}}
    return json.dumps(p,indent=2)
os.makedirs(OUT,exist_ok=True)
for name,st in STACKS.items():
    d=os.path.join(OUT,name); os.makedirs(d,exist_ok=True)
    open(os.path.join(d,name+".kicad_pcb"),"w").write(pcb(st))
    open(os.path.join(d,name+".kicad_pro"),"w").write(pro(name,st["cu"]))
    print("wrote",d)

# ---- self-test: resolve sample net names through pcbnew (KiCad patterns are plain * ? wildcards) ----
EXPECT={"/PET0_P":"PCIe_85","PER3_N":"PCIe_85","/J1/PET12_N":"PCIe_85","/PCIE_RST_N":"Default","/PERST_N":"Default",
        "/REFCLK0_P":"REFCLK_100","+12V":"PWR_12V","/SMB_CLK":"Default","/U3_TX0_P":"PCIe_85","/PER15_P":"PCIe_85","/PERST1_N":"Default"}
try:
    import pcbnew, shutil, tempfile
    d0=os.path.join(OUT,"jlc06161h-3313_1.6mm"); t=tempfile.mkdtemp()
    for e in ("kicad_pcb","kicad_pro"): shutil.copy(os.path.join(d0,"jlc06161h-3313_1.6mm."+e),os.path.join(t,"t."+e))
    b=pcbnew.LoadBoard(os.path.join(t,"t.kicad_pcb"))
    for n in EXPECT: b.Add(pcbnew.NETINFO_ITEM(b,n))
    b.SynchronizeNetsAndNetClasses(True)
    got={n.GetNetname():n.GetNetClassName() for n in b.GetNetsByName().values() if n.GetNetname()}
    bad={k:(v,got.get(k)) for k,v in EXPECT.items() if got.get(k)!=v}
    print("netclass self-test:", "PASS" if not bad else "FAIL %r"%bad)
    if bad: sys.exit(1)
except ImportError:
    print("pcbnew not available: netclass self-test skipped")
