"""Generate and run an OpenFOAM (ESI v1912+) CFD case for N upright 2.5" drives in a ducted shroud.

Solver: buoyantSimpleFoam (steady, compressible air, energy equation), k-omega SST turbulence
(--laminar to switch it off), gravity off (forced convection dominates). Each drive is a solid
block removed from the mesh; its wetted surface gets a uniform heat flux P / A_wet
(externalWallHeatFluxTemperature, mode flux). The shroud and the card side are adiabatic walls.
The fan is a uniform-velocity inlet over the shroud cross-section at the given airflow; pick the
airflow from the analytic fan operating point (analytic.py).

The drive cases are aluminium, so the area-mean wall temperature of each drive is the
representative case temperature; the max wall temperature (hot spot of the uniform-flux model)
is an upper bound.

Usage: python3 foamcase.py <case_dir> --drives 2 --gap 5 --cfm 21 [--power 25] [--laminar] [--run]
Note: no function objects are used: the Debian/Ubuntu OpenFOAM v1912 package aborts in
functionObjectList::read (sha1 digest bug), so results are parsed from the written fields.
"""
import argparse
import json
import os
import re
import shutil
import subprocess

import numpy as np

CFM = 4.71947e-4
L, H, TH = 69.85, 100.0, 15.0
UP, DOWN, TOP = 30.0, 50.0, 5.0
AIR = dict(mu=1.9e-5, Pr=0.71, cp=1007.0, M=28.96, p0=1e5)
ITERS = 2000
FOAM_ENV = os.environ.get("FOAM_BASHRC", "/usr/share/openfoam/etc/bashrc")

HDR = "FoamFile {{ version 2.0; format ascii; class {cls}; object {obj}; }}\n"


def w(case, rel, obj, body, cls="dictionary"):
    p = os.path.join(case, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(HDR.format(cls=cls, obj=obj) + body)


def drive_boxes(n, gap):
    return [(UP, gap + i * (TH + gap), 0.0, UP + L, gap + i * (TH + gap) + TH, H) for i in range(n)]


def field(case, name, dims, internal, bcs, cls="volScalarField"):
    body = f"dimensions {dims};\ninternalField uniform {internal};\nboundaryField {{\n"
    for patch, bc in bcs.items():
        body += f"  {patch} {{ {bc} }}\n"
    w(case, f"0.orig/{name}", name, body + "}\n", cls)


def build(case, n, gap, cfm, power, laminar=False, dy=0.625, dx=1.0, dz=2.0, T_in=35.0, iters=None):
    W = n * TH + (n + 1) * gap
    X, Z = UP + L + DOWN, H + TOP
    nx = [round(UP / max(1.5, dx)), round(L / dx), round(DOWN / max(2.0, dx))]
    ny = round(W / dy)
    nz = [round(H / dz), max(4, round(TOP / 0.625))]
    sx, sz = sum(nx), sum(nz)
    w(case, "system/blockMeshDict", "blockMeshDict", f"""scale 0.001;
vertices ( (0 0 0) ({X} 0 0) ({X} {W} 0) (0 {W} 0) (0 0 {Z}) ({X} 0 {Z}) ({X} {W} {Z}) (0 {W} {Z}) );
blocks ( hex (0 1 2 3 4 5 6 7) ({sx} {ny} {sz})
  simpleGrading ( ( ({UP/X} {nx[0]/sx} 1) ({L/X} {nx[1]/sx} 1) ({DOWN/X} {nx[2]/sx} 1) )
                  1
                  ( ({H/Z} {nz[0]/sz} 1) ({TOP/Z} {nz[1]/sz} 1) ) ) );
edges ();
boundary (
  inlet  {{ type patch; faces ((0 4 7 3)); }}
  outlet {{ type patch; faces ((1 2 6 5)); }}
  shroud {{ type wall; faces ((0 1 5 4) (3 7 6 2) (4 5 6 7)); }}
  card   {{ type wall; faces ((0 3 2 1)); }}
  drives {{ type wall; faces (); }}
);
""")
    boxes = "\n".join(
        f"  {{ name drives; type cellSet; action {'new' if i == 0 else 'add'}; source boxToCell; "
        f"box ({b[0]/1000} {b[1]/1000} -0.001) ({b[3]/1000} {b[4]/1000} {b[5]/1000}); }}"
        for i, b in enumerate(drive_boxes(n, gap)))
    w(case, "system/topoSetDict", "topoSetDict", f"""actions (
{boxes}
  {{ name fluid; type cellSet; action new; source cellToCell; set drives; }}
  {{ name fluid; type cellSet; action invert; }}
);
""")
    A_wet = 2 * L * H + 2 * TH * H + L * TH          # mm^2: faces, leading/trailing ends, top
    q = power / (A_wet * 1e-6)
    A_in = W * Z * 1e-6
    U_in = cfm * CFM / A_in
    Tk = T_in + 273.15

    w(case, "constant/thermophysicalProperties", "thermophysicalProperties", f"""thermoType {{ type heRhoThermo; mixture pureMixture;
  transport const; thermo hConst; equationOfState perfectGas; specie specie; energy sensibleEnthalpy; }}
mixture {{ specie {{ molWeight {AIR['M']}; }} thermodynamics {{ Cp {AIR['cp']}; Hf 0; }}
  transport {{ mu {AIR['mu']}; Pr {AIR['Pr']}; }} }}
""")
    w(case, "constant/g", "g", "dimensions [0 1 -2 0 0 0 0];\nvalue (0 0 0);\n", "uniformDimensionedVectorField")
    w(case, "constant/hRef", "hRef", "dimensions [0 2 -2 0 0 0 0];\nvalue 0;\n", "uniformDimensionedScalarField")
    w(case, "constant/turbulenceProperties", "turbulenceProperties",
      "simulationType laminar;\n" if laminar else
      "simulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }\n")

    walls = '"(shroud|card|drives)"'
    field(case, "U", "[0 1 -1 0 0 0 0]", f"({U_in} 0 0)", {
        "inlet": f"type fixedValue; value uniform ({U_in} 0 0);",
        "outlet": "type inletOutlet; inletValue uniform (0 0 0); value uniform (0 0 0);",
        walls: "type noSlip;"}, "volVectorField")
    field(case, "p", "[1 -1 -2 0 0 0 0]", AIR["p0"], {
        "inlet": f"type calculated; value uniform {AIR['p0']};",
        "outlet": f"type calculated; value uniform {AIR['p0']};",
        walls: f"type calculated; value uniform {AIR['p0']};"})
    field(case, "p_rgh", "[1 -1 -2 0 0 0 0]", AIR["p0"], {
        "inlet": f"type fixedFluxPressure; value uniform {AIR['p0']};",
        "outlet": f"type fixedValue; value uniform {AIR['p0']};",
        walls: f"type fixedFluxPressure; value uniform {AIR['p0']};"})
    field(case, "T", "[0 0 0 1 0 0 0]", Tk, {
        "inlet": f"type fixedValue; value uniform {Tk};",
        "outlet": f"type inletOutlet; inletValue uniform {Tk}; value uniform {Tk};",
        '"(shroud|card)"': "type zeroGradient;",
        "drives": f"type externalWallHeatFluxTemperature; mode flux; q uniform {q}; kappaMethod fluidThermo; value uniform {Tk};"})
    I, lt = 0.05, 0.004
    k0 = 1.5 * (U_in * I) ** 2
    om0 = k0 ** 0.5 / (0.09 ** 0.25 * lt)
    field(case, "k", "[0 2 -2 0 0 0 0]", k0, {
        "inlet": f"type fixedValue; value uniform {k0};", "outlet": f"type inletOutlet; inletValue uniform {k0}; value uniform {k0};",
        walls: f"type kqRWallFunction; value uniform {k0};"})
    field(case, "omega", "[0 0 -1 0 0 0 0]", om0, {
        "inlet": f"type fixedValue; value uniform {om0};", "outlet": f"type inletOutlet; inletValue uniform {om0}; value uniform {om0};",
        walls: f"type omegaWallFunction; value uniform {om0};"})
    field(case, "nut", "[0 2 -1 0 0 0 0]", 0, {
        "inlet": "type calculated; value uniform 0;", "outlet": "type calculated; value uniform 0;",
        walls: "type nutLowReWallFunction; value uniform 0;"})
    field(case, "alphat", "[1 -1 -1 0 0 0 0]", 0, {
        "inlet": "type calculated; value uniform 0;", "outlet": "type calculated; value uniform 0;",
        walls: "type compressible::alphatWallFunction; Prt 0.85; value uniform 0;"})

    w(case, "system/controlDict", "controlDict", f"""application buoyantSimpleFoam;
startFrom latestTime; startTime 0; stopAt endTime; endTime {iters or ITERS}; deltaT 1;
writeControl timeStep; writeInterval {iters or ITERS}; purgeWrite 0; writeFormat ascii; writePrecision 8;
runTimeModifiable false;
""")
    w(case, "system/fvSchemes", "fvSchemes", """ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes { default none;
  div(phi,U) bounded Gauss linearUpwind grad(U);
  div(phi,h) bounded Gauss linearUpwind grad(h);
  div(phi,K) bounded Gauss linear;
  div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind;
  div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
""")
    w(case, "system/fvSolution", "fvSolution", """solvers {
  p_rgh { solver GAMG; smoother DIC; tolerance 1e-8; relTol 0.01; }
  "(U|h|k|omega)" { solver PBiCGStab; preconditioner DILU; tolerance 1e-9; relTol 0.05; }
}
SIMPLE { momentumPredictor yes; nNonOrthogonalCorrectors 0;
  residualControl { p_rgh 1e-5; U 1e-6; h 1e-7; "(k|omega)" 1e-5; } }
relaxationFactors { fields { rho 1.0; p_rgh 0.7; } equations { U 0.3; h 0.5; "(k|omega)" 0.5; } }
""")
    w(case, "system/decomposeParDict", "decomposeParDict", "numberOfSubdomains 4;\nmethod hierarchical;\ncoeffs { n (4 1 1); }\n")
    meta = dict(drives=n, gap_mm=gap, cfm=cfm, power_W=power, U_in=U_in, A_in=A_in, q_Wm2=q, A_wet_mm2=A_wet,
                laminar=laminar, T_in=T_in, boxes=drive_boxes(n, gap), cells=sx * ny * sz, dims_mm=[X, W, Z],
                cells_xyz=[nx, ny, nz], iters=iters or ITERS)
    json.dump(meta, open(os.path.join(case, "meta.json"), "w"), indent=1)
    return meta


def sh(case, cmd, log):
    with open(os.path.join(case, log), "w") as fh:
        subprocess.run(["bash", "-c", f"source {FOAM_ENV} >/dev/null 2>&1; {cmd}"], cwd=case, check=True,
                       stdout=fh, stderr=subprocess.STDOUT)


def latest_time(case):
    ts = [d for d in os.listdir(case) if re.fullmatch(r"[\d.]+", d) and d != "0"]
    return sorted(ts, key=float)[-1]


def run(case, nproc=4):
    sh(case, "blockMesh", "log.blockMesh")
    sh(case, "topoSet", "log.topoSet")
    sh(case, "subsetMesh fluid -patch drives -overwrite", "log.subsetMesh")
    sh(case, "checkMesh", "log.checkMesh")
    shutil.rmtree(os.path.join(case, "0"), ignore_errors=True)
    shutil.copytree(os.path.join(case, "0.orig"), os.path.join(case, "0"))
    if nproc > 1:
        sh(case, "decomposePar -force", "log.decomposePar")
        sh(case, f"mpirun --allow-run-as-root --oversubscribe -np {nproc} buoyantSimpleFoam -parallel", "log.solver")
        sh(case, "reconstructPar -latestTime", "log.reconstructPar")
        for d in os.listdir(case):
            if d.startswith("processor"):
                shutil.rmtree(os.path.join(case, d))
    else:
        sh(case, "buoyantSimpleFoam", "log.solver")


def _read_patch(path, patch):
    s = open(path).read()
    i = s.index("boundaryField")
    seg = s[re.search(r"\n\s*" + patch + r"\s*\n\s*\{", s[i:]).start() + i:]
    seg = seg[:seg.index("}")]
    m = re.search(r"value\s+nonuniform\s+List<(\w+)>\s*(\d+)\s*\(", seg)
    if not m:
        u = re.search(r"value\s+uniform\s+([-\deE.+]+)", seg)
        return float(u.group(1)) if u else None
    n = int(m.group(2))
    return np.array(seg[m.end():].split(None, n)[:n], float)


def _foam_list(path, kind):
    s = open(path).read()
    m = re.search(r"\n(\d+)\s*\n\(", s)
    n, body = int(m.group(1)), s[m.end():]
    if kind == "points":
        return np.array(re.findall(r"\(([-\deE.+]+) ([-\deE.+]+) ([-\deE.+]+)\)", body)[:n], float)
    return [list(map(int, f.split())) for f in re.findall(r"\d+\(([\d ]+)\)", body)[:n]]


def patch_geometry(case, patch):
    """Face centres (mm) and areas (m^2) of one boundary patch, from constant/polyMesh."""
    pm = os.path.join(case, "constant", "polyMesh")
    b = open(os.path.join(pm, "boundary")).read()
    m = re.search(r"\b" + patch + r"\s*\{[^}]*?nFaces\s+(\d+);[^}]*?startFace\s+(\d+);", b, re.S)
    nf, sf = int(m.group(1)), int(m.group(2))
    pts = _foam_list(os.path.join(pm, "points"), "points")
    faces = _foam_list(os.path.join(pm, "faces"), "faces")[sf:sf + nf]
    C = np.array([pts[f].mean(0) for f in faces])
    A = np.array([0.5 * np.linalg.norm(np.cross(pts[f[2]] - pts[f[0]], pts[f[3]] - pts[f[1]])) for f in faces])
    return C * 1000, A


def results(case):
    meta = json.load(open(os.path.join(case, "meta.json")))
    t = latest_time(case)
    T = _read_patch(os.path.join(case, t, "T"), "drives") - 273.15
    C, A = patch_geometry(case, "drives")
    out = []
    for i, b in enumerate(meta["boxes"]):
        sel = (C[:, 1] > b[1] - 0.5) & (C[:, 1] < b[4] + 0.5) & (C[:, 0] > b[0] - 1.5) & (C[:, 0] < b[3] + 1.5)
        out.append(dict(drive=i + 1, T_mean=float((T[sel] * A[sel]).sum() / A[sel].sum()), T_max=float(T[sel].max()), T_p95=float(np.percentile(T[sel], 95)),
                        area_m2=float(A[sel].sum())))
    p = _read_patch(os.path.join(case, t, "p_rgh"), "inlet")
    _, Ai = patch_geometry(case, "inlet")
    dp = float((np.asarray(p) * Ai).sum() / Ai.sum()) - AIR["p0"] if np.ndim(p) else float(p) - AIR["p0"]
    Tout = _read_patch(os.path.join(case, t, "T"), "outlet")
    log = open(os.path.join(case, "log.solver")).read()
    iters = re.findall(r"^Time = (\d+)", log, re.M)
    res = {k: float(v) for k, v in re.findall(r"Solving for (\w+), Initial residual = ([-\deE.+]+)", log[-20000:])}
    meta.update(drives_T=out, dp_Pa=dp, iterations=int(iters[-1]) if iters else None, time=t,
                T_out_mean=float(np.mean(Tout) - 273.15) if Tout is not None else None, final_residuals=res)
    json.dump(meta, open(os.path.join(case, "results.json"), "w"), indent=1)
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--drives", type=int, default=2)
    ap.add_argument("--gap", type=float, default=5.0)
    ap.add_argument("--cfm", type=float, default=21.0)
    ap.add_argument("--power", type=float, default=25.0)
    ap.add_argument("--laminar", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--np", type=int, default=4)
    a = ap.parse_args()
    print(build(a.case, a.drives, a.gap, a.cfm, a.power, a.laminar))
    if a.run:
        run(a.case, a.np)
        print(json.dumps(results(a.case), indent=1))
