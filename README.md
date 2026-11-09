# U.3 PCIe adapters

Passive, PCIe 4.0 adapters for U.3 (SFF-TA-1001) NVMe drives, built around HPE P50230-B21 /
Samsung PM1735a drives that refuse U.2-wired hosts. KiCad projects, fabbed at JLCPCB or PCBWay.

## Layout

| Path | Contents |
| --- | --- |
| [`design-rules/`](design-rules/) | Shared PCIe 4.0 + JLCPCB/PCBWay rules: stackups, impedance, `.kicad_dru` DRC rules, KiCad starter templates, SI scripts |
| [`designs/x16-u3-card/`](designs/x16-u3-card/) | x16 slot (bifurcated x4x4x4x4) card for 2–4 U.3 drives |
| [`designs/minisforum-u3/`](designs/minisforum-u3/) | U.3 adapters for Minisforum MS-01 / MS-A2 (PCIe x4 card, M.2-slot board) |
| [`docs/`](docs/) | Research notes and links |

## Conventions

- One folder per design under `designs/`; one KiCad project per board inside it.
- Every board uses a template from `design-rules/templates/` and the custom rules in
  `design-rules/pcie4_jlc_pcbway.kicad_dru`. Change the rules there, not per board.
- Don't commit KiCad backups, `*.kicad_prl`, or fab output zips (see `.gitignore`);
  attach fab outputs to GitHub releases instead.
