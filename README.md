# U.3 PCIe adapters

Passive, PCIe 4.0 adapters for U.3 (SFF-TA-1001) NVMe drives, built around HPE P50230-B21 /
Samsung PM1735a drives that refuse U.2-wired hosts. KiCad projects, fabbed at JLCPCB or PCBWay.

![OCuLink-to-U.3 cage board with a drive](docs/img/x16-u3-card/cage_drive_iso_top.png)

## Designs

| Design | Boards | Status |
| --- | --- | --- |
| [**x16 / x8 U.3 cards**](designs/x16-u3-card/) | x8 card (2 drives), x16 card (4 drives, passive or with retimer), OCuLink cage board | cage board routed and DRC clean; cards in layout |
| [**Minisforum MS-01 / MS-A2**](designs/minisforum-u3/) | U.3-wired x4 card for the PCIe slot, U.3-wired replacement for the M.2 adapter | waiting on measurements of the stock adapters |
| [**Cooling shroud**](docs/thermal/) | 3D-printed high-temp shroud for the Jonsbo N5 | sized from the thermal analysis; model in progress |

<table>
<tr>
<td><img src="docs/img/x16-u3-card/cage_iso_top.png" width="400"><br>Cage board, top</td>
<td><img src="docs/img/x16-u3-card/cage_iso_bottom.png" width="400"><br>Cage board, bottom (OCuLink)</td>
</tr>
<tr>
<td><img src="docs/img/x16-u3-card/x8_drive_iso_top.png" width="400"><br>x8 card with 2 drives</td>
<td><img src="docs/img/x16-u3-card/x16p_drive_iso_top.png" width="400"><br>x16 card with 4 drives</td>
</tr>
<tr>
<td><img src="docs/thermal/cfd_3d_inline_n4_g5_q30_coarse.png" width="400"><br>CFD: 4 drives x 25 W in line, 30 CFM</td>
<td><img src="docs/thermal/analytic_temp_vs_airflow_inline.png" width="400"><br>Hottest drive vs airflow (x8 / x16)</td>
</tr>
</table>

## Cooling in one paragraph

Each drive can draw ~25 W, and on the cards the drives sit in a row, so the air passes them one
after another. With 35 °C air coming in and a 70 °C case limit, the x8 card (2 drives) needs about
20 CFM and the x16 card (4 drives) about 30 CFM at ~150 Pa. That takes a 92x38 mm server-class
fan: it holds 2 drives at ~66 °C and 4 drives at ~71 °C (marginal; 3 mm shroud gaps or a 20 W
drive power state give margin). A 92x25 mm fan is not enough for either. Details, OpenFOAM
results and the calibrated model: [`docs/thermal/`](docs/thermal/).

## Layout

| Path | Contents |
| --- | --- |
| [`design-rules/`](design-rules/) | Shared PCIe 4.0 + JLCPCB/PCBWay rules: stackups, impedance, `.kicad_dru` DRC rules, KiCad starter templates, SI scripts |
| [`designs/x16-u3-card/`](designs/x16-u3-card/) | x16 / x8 slot cards for 2–4 U.3 drives, OCuLink cage board |
| [`designs/minisforum-u3/`](designs/minisforum-u3/) | U.3 adapters for Minisforum MS-01 / MS-A2 (PCIe x4 card, M.2-slot board) |
| [`tools/render/`](tools/render/) | Headless 3D renders of any `.kicad_pcb` (real copper/mask/silk, STEP parts, drives plugged in) |
| [`tools/thermal/`](tools/thermal/) | Analytical airflow/thermal model and OpenFOAM CFD case generator for the drive stack |
| [`docs/`](docs/) | Research notes, renders (`docs/img/`), thermal results (`docs/thermal/`) |

## Conventions

- One folder per design under `designs/`; one KiCad project per board inside it.
- Every board uses a template from `design-rules/templates/` and the custom rules in
  `design-rules/pcie4_jlc_pcbway.kicad_dru`. Change the rules there, not per board.
- Don't commit KiCad backups, `*.kicad_prl`, or fab output zips (see `.gitignore`);
  attach fab outputs to GitHub releases instead.
- Re-render a board after changing it (`tools/render/render.py`) so the README pictures match.
