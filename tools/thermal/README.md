# tools/thermal: airflow and temperature of the drive stack

| File | What it does |
| --- | --- |
| `analytic.py` | 1-D network model: parallel-plate channels between upright 2.5" drives, developing-flow laminar / Gnielinski turbulent heat transfer, effectiveness-NTU drive temperature, Shah friction, 92 mm fan curve operating points. Writes the plots and tables in `docs/thermal/`. Runs in seconds. |
| `foamcase.py` | Builds and runs an OpenFOAM case (`buoyantSimpleFoam`, k-ω SST) of N drives in the shroud with a uniform heat flux on each drive; parses drive temperatures and pressure drop into `results.json`. |
| `sweep.py` | The CFD cases behind `docs/thermal/` (2 and 4 drives, several gaps and airflows). |
| `plot_cfd.py` | Mid-height temperature/speed slices, CFD-vs-analytic chart and the results table. |
| `render_cfd.py` | 3D picture of a case: drive surface temperature and streamlines coloured by air temperature. |

Results and assumptions: [`docs/thermal/README.md`](../../docs/thermal/README.md).

Requirements (Ubuntu 24.04): `apt install openfoam xvfb`, `pip install numpy matplotlib pyvista`.
