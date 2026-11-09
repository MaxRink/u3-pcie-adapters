# U.3 adapter boards: x16 card, x8 card, OCuLink cage board

Passive PCIe 4.0 boards that carry true SFF-TA-1001 (U.3) wiring to 2.5" U.3 drives such as the
HPE P50230-B21 / Samsung PM1735a, which refuse U.2-wired hosts. Designed for a Jonsbo N5 build
with a 3D-printed cooling shroud.

![cage board with a drive plugged in](../../docs/img/x16-u3-card/cage_drive_iso_top.png)

## Boards

| Board | What it is | Status |
| --- | --- | --- |
| **x8 card** (`boards/x8/`) | x8 slot (x4x4 bifurcation), 2 drives standing upright on their connectors, connectors facing the motherboard, passive, 9DBL411 REFCLK buffer, full sidebands, per-drive 12 V jumper, 190 mm | rev B routed, DRC clean (Rev E, all lanes ≤50 mm) |
| **x16 card, passive, 4 drives** (`boards/x16p/`) | x16 slot (x4x4x4x4), 4 upright drives in a row on a 312 mm card; drives B–D sit 5.7 mm higher so lanes 8–15 pass under drive B | rev B routed, DRC clean; drive A in budget, B 45–54 mm, C ~110 mm, D ~170 mm (populate as needed) |
| **x16 card, passive, 3 drives** (`boards/x16p3/`) | same card with drives A–C only, 239 mm; host bifurcation x4x4x4 or x8x4x4, lanes 12–15 unused | rev B routed, DRC clean |
| **x16 card with retimer** | as above, with a retimer on lanes 8–15 so all 4 drives stay compliant | planned (part search) |
| **OCuLink cage board** (`boards/cage/`) | OCuLink 4i (SFF-8611) to U.3 breakout for a drive in a printed cage; 12 V in on a PCIe 6-pin | routed, DRC clean (design-rules Rev D); rev B only if cabled drives come back |

Renders are regenerated from the KiCad files whenever a board changes (see
[`tools/render`](../../tools/render/)); boards still in layout get their renders when they are DRC clean.

## OCuLink cage board

56.5 x 40 mm, 6 layers (JLC06161H-3313), PCIe lanes on L1/L6 only. The OCuLink receptacle sits on
the bottom in the edge notch, the U.3 receptacle on top mates the drive at the upper edge, and a
PCIe 6-pin (Molex Mini-Fit Jr) brings 12 V through a PTC fuse; an AMS1117 makes 3.3 V aux.
Four M3 slots (3.2 x 6.2 mm, along the insertion axis) hold it in the printed cage.

| Top | Bottom (seen from below) |
| --- | --- |
| ![top](../../docs/img/x16-u3-card/cage_top.png) | ![bottom](../../docs/img/x16-u3-card/cage_bottom.png) |
| ![iso top](../../docs/img/x16-u3-card/cage_iso_top.png) | ![iso bottom](../../docs/img/x16-u3-card/cage_iso_bottom.png) |

With a 15 mm U.3 drive plugged in:

| Front | Back |
| --- | --- |
| ![drive front](../../docs/img/x16-u3-card/cage_drive_iso_top.png) | ![drive back](../../docs/img/x16-u3-card/cage_drive_iso_top_back.png) |

Copper, mask and silkscreen in the renders come from the real layer geometry. The U.3 and
OCuLink receptacles, the Mini-Fit header and the drive are simplified appearance models.

Fab files: [`fab/cage/`](fab/cage/) (Gerbers, BOM, CPL for JLCPCB / PCBWay).

## x8 card

CEM x8 edge (bifurcate the slot x4x4). Both U.3 receptacles sit on the bottom, mirrored, so the drives stand
upright with their connectors facing the motherboard and lane order needs no crossings. The card is cut away
behind the drives for airflow. A 9DBL411 buffer fans REFCLK out to both drives (33 Ω series per the datasheet).
AC caps (220 nF) sit on the drive-to-host lanes per SFF-TA-1001. 190 mm long. Sidebands and 12 V work as described
under [Sidebands and power](#sidebands-and-power). Fab files: [`fab/x8/`](fab/x8/).

## x16 card (passive)

Same construction as the x8, four drives in a row (A–D, 73 mm pitch, 312 mm = CEM full length). The 3-drive card
(`U3_DRIVES=3 python3 gen/x16.py`) is the same design cut after drive C (239 mm). Drive B's
lane pads sit right above fingers 8–15, and right of the fingers the card edge rises to 12.75 mm, so lanes 8–15
run in a 0.9 mm-pitch stack under drive B and drives B–D sit 5.7 mm higher than A to make room. Lane lengths
finger→receptacle: A 30–46 mm, B 45–54 mm, C 107–115 mm, D 164–172 mm (the DRU documents the over-budget nets).
One 9DBL411 feeds all four REFCLKs (B/C/D runs are about 100/205/265 mm), in channels between the sideband blocks
and the window edges. Fab files: [`fab/x16p/`](fab/x16p/), [`fab/x16p3/`](fab/x16p3/).

## Sidebands and power

Every drive has its own sideband block next to its receptacle (`gen/sideband.py`), all on 3.3 V aux:

| Part | Address | Does |
| --- | --- | --- |
| TCA9543A SMBus switch | 0x70 + drive index | slot SMBus (B5/B6) to the drive's SMBus on channel 0, so drives with the same address don't collide |
| TCA9554 IO expander | 0x20 + drive index | P0 PWRDIS (10k pull-down: drive on by default), P1 DualPortEn#, P2 reset enable (pull-up), P3 locate LED, P4 PRSNT#, P5 IfDet#, P6 IfDet2#, P7 WAKE# (inputs pulled up) |
| 74LVC1G08 | | PERST0#/PERST1# = slot PERST# AND reset enable, so software can hold one drive in reset |

HPT0 (S15) is tied to GND for U.3 x4. REFCLK1 and port B stay open (single-port x4). Slot WAKE# and CLKREQ# are not
used; each drive's WAKE# can be read on its expander. R9 (DNP 0R) feeds 3.3 V aux from 3.3 V for slots without aux.
SMBus, 3.3 V aux and PERST# run as trunks on L3.

**12 V:** each drive has a 3-pin jumper (JP1–JP4). Shunt on pins 2–3 (default) = slot 12 V, pins 1–2 = the PCIe
6-pin (J5). One shunt can never join the two supplies. L4 is split into a slot-12 V plane next to the fingers and an
aux-12 V plane fed only by J5. A slot gives at most 66 W at 12 V, so with more than two 25 W drives move some jumpers
to aux and plug in the 6-pin. Jumper shunts (2.54 mm) are not in the BOM.

## Cooling

Two or four 25 W drives standing on the card need a ducted fan. Summary from
[`docs/thermal`](../../docs/thermal/): 2 drives need ~25 CFM through 5 mm gaps (35 °C air in,
70 °C case), 4 drives ~43 CFM; 3 mm gaps cut that to 15 and 26 CFM but need a high-pressure fan.
A quiet 92 mm fan is not enough; a 92x38 mm server-class fan holds the drives around 60–66 °C.

## Generator

All boards are generated by Python scripts on KiCad 7 `pcbnew`. To change a board, edit its script and rerun it; don't hand-edit the board.

- `lib/`: custom footprints (Amphenol PSAS4F213002 U.3 receptacle, Amphenol G14A421211112HR OCuLink 4i) and symbols
- `gen/pcbkit.py`: layout toolkit (pair router with skew bumps, zones, rule areas, DRC)
- `gen/x8.py`: x8 card (2 upright drives on the bottom, REFCLK fan-out buffer, drive window for airflow)
- `gen/x16.py`: x16 passive card (4 drives; `U3_DRIVES=3` for the 3-drive card)
- `gen/sideband.py`: per-drive sideband block (SMBus switch, IO expander, PERST# gate, 12 V jumper)
- `gen/router.py`: small grid maze router for the low-speed sideband nets
- `gen/cage.py`: Design 3, the OCuLink 4i to U.3 cage board (status: routed, DRC clean on design-rules Rev D)
- `gen/fab.py`: Gerbers, drill, BOM and CPL (JLCPCB/PCBWay)
- `boards/<board>/`: generated KiCad project, DRC report, per-net lengths
- `fab/<board>/`: Gerber zip, BOM and CPL for ordering
- `docs/ref/`: vendor drawings and third-party licences

Rules come from `../../design-rules/` (copied into each board at generation time).

Run: `python3 gen/fplib.py && python3 gen/symlib.py && python3 gen/cage.py && python3 gen/fab.py boards/cage/u3_cage.kicad_pcb boards/cage/bom_raw.json fab/cage`

Render: `xvfb-run -a python3 ../../tools/render/render.py boards/cage/u3_cage.kicad_pcb ../../docs/img/x16-u3-card --prefix cage --drives`
