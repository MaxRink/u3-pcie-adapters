# Reference data typed in from the source drawings and specs (2026-11-13)

Read from the rendered PDFs (the tables and drawings are images or drawings, so they are transcribed here).
Check against the original before changing a footprint or pin map.

## SFF-9402 Rev 1.1, Tables 6-2 / 6-3: SFF-8654 8i (74-circuit), "Other Protocol" (PCIe) x8

Source: https://members.snia.org/document/dl/27380 pages 19-20. Cables are full crossover: pin An at one
end is pin Bn at the other end (same number). Names below are host-centric (PET = root transmits).

| Pin | Root / host-card connector | Backplane connector |
| --- | --- | --- |
| A1 A4 A7 A13 A16 A19 A22 A25 A31 A34 A37 | GND | GND |
| B1 B4 B7 B13 B16 B19 B22 B25 B31 B34 B37 | GND | GND |
| A10, A28, B10, B28 | GND (sideband ground) | GND |
| A2 / A3 | PERp0 / PERn0 | PETp0 / PETn0 |
| A5 / A6 | PERp1 / PERn1 | PETp1 / PETn1 |
| A8 | BP_TYPEA | 2W-CLKA (SMBus clock, set A) |
| A9 | CWAKEA# / OBFFA | 2W-DATAA (SMBus data, set A) |
| A11 / A12 | REFCLKA+ / REFCLKA- (root drives) | PERSTA# / CPRSNTA# |
| A14 / A15 | PERp2 / PERn2 | PETp2 / PETn2 |
| A17 / A18 | PERp3 / PERn3 | PETp3 / PETn3 |
| A20 / A21 | PERp4 / PERn4 | PETp4 / PETn4 |
| A23 / A24 | PERp5 / PERn5 | PETp5 / PETn5 |
| A26 | BP_TYPEB | 2W-CLKB |
| A27 | CWAKEB# / OBFFB | 2W-DATAB |
| A29 / A30 | REFCLKB+ / REFCLKB- | PERSTB# / CPRSNTB# |
| A32 / A33 | PERp6 / PERn6 | PETp6 / PETn6 |
| A35 / A36 | PERp7 / PERn7 | PETp7 / PETn7 |
| B2 / B3 | PETp0 / PETn0 | PERp0 / PERn0 |
| B5 / B6 | PETp1 / PETn1 | PERp1 / PERn1 |
| B8 | 2W-CLKA | BP_TYPEA |
| B9 | 2W-DATAA | CWAKEA# |
| B11 / B12 | PERSTA# / CPRSNTA# | REFCLKA+ / REFCLKA- |
| B14 / B15 | PETp2 / PETn2 | PERp2 / PERn2 |
| B17 / B18 | PETp3 / PETn3 | PERp3 / PERn3 |
| B20 / B21 | PETp4 / PETn4 | PERp4 / PERn4 |
| B23 / B24 | PETp5 / PETn5 | PERp5 / PERn5 |
| B26 | 2W-CLKB | BP_TYPEB |
| B27 | 2W-DATAB | CWAKEB# |
| B29 / B30 | PERSTB# / CPRSNTB# | REFCLKB+ / REFCLKB- |
| B32 / B33 | PETp6 / PETn6 | PERp6 / PERn6 |
| B35 / B36 | PETp7 / PETn7 | PERp7 / PERn7 |

Lanes 0-3 with sideband set A are the first x4 port, lanes 4-7 with set B the second.
The spec's own device column maps backplane B11/B12 to U.2 E7/E8 (REFCLK+/-) and B9 to P1 (WAKE#).

## Amphenol PSAS5F313002xxx (vertical SMT SFF-8639 receptacle), drawing rev 3 sheet 2

Source: https://cdn.amphenol-cs.com/media/wysiwyg/files/drawing/psas5f313002xxx.pdf
Recommended PCB layout, top view, origin = connector centreline (x) and peg line (y), y up, tolerance 0.05.

- Row 1 (y above the peg line): 40 pads 0.50 x 1.60, pitch 0.80, pad centre y = +2.32.
  Left to right: E7..E16, S8..S28, E17..E25. E7 at x = -15.48, E25 at x = +15.72.
- Row 2 (below the peg line):
  - S1..S7: 0.60 x 1.70, pitch 1.27, S1 at x = -15.87, S7 at x = -8.25, pad centre y = -1.71
  - E1..E6: 0.50 x 2.20, pitch 0.80, E1 at x = -7.075, E6 at x = -3.075, pad centre y = -2.29
  - P1..P15: 0.60 x 1.70, pitch 1.27, P1 at x = -1.905, P15 at x = +15.875, pad centre y = -1.71
- Outer pad edges are 5.68 apart (row 1 outer edge y = +3.12, S/P outer edge y = -2.56).
- Pegs (NPTH) on the peg line: dia 0.90 at x = -18.58, dia 1.30 at x = +18.58.
- Retainer clip pads 2.60 x 2.40 at x = +/-21.80 on the peg line.
- Body 45.45 x 5.50, 8.15 high. Pegs protrude below the board.

## Amphenol U10A474xxxT (SlimSAS 8i right angle), drawing u10a474xxxt_2.pdf

Source: https://cdn.amphenol-cs.com/media/wysiwyg/files/drawing/u10a474xxxt_2.pdf
Top view, origin = midpoint of the two dia 1.30 NPTH pegs, +y toward the plug (mating face).

- Row A (A1..A37): 37 pads 0.35 x 1.30, pitch 0.60, pad centre y = +2.70. A1 at x = +10.80, A37 at x = -10.80.
- Row B (B1..B37): same, pad centre y = +5.05. B1 at x = +10.80.
- NPTH dia 1.30 at (+/-10.95, 0).
- Latch pins, PTH dia 0.66: (+/-11.63, -5.15) and (+/-11.63, -8.15). Option 4 = 2.20 mm pin length.
- Component keep-out 24.25 x 16.20, y from -10.30 to +5.90. Body 23.5 wide, 15.8 deep, 6.7 high.
- Plug needs 26.0 mm width in front of the mating face.

## TI DS160PR810 (SNLS658, Dec 2020), NJX 64-pin WQFN 5.5 x 10 mm, 0.4 mm pitch

- Left side pins 1-23: RX0P 1, RX0N 2, VREG1 3, RX1P 4, RX1N 5, VCC 6, RX2P 7, RX2N 8, GND 9, RX3P 10, RX3N 11,
  GND 12, RX4P 13, RX4N 14, VREG2 15, RX5P 16, RX5N 17, VCC 18, RX6P 19, RX6N 20, GND 21, RX7P 22, RX7N 23.
- Bottom pins 24-32: GND 24, PD0 25, PD1 26, EQ0_1 27, GAIN1 28, EQ1_1 29, RSVD1 30, ALL_DONE_N 31, GND 32.
- Right side pins 33-55 (bottom to top): TX7N 33, TX7P 34, VREG2 35, TX6N 36, TX6P 37, VCC 38, TX5N 39, TX5P 40,
  GND 41, TX4N 42, TX4P 43, GND 44, TX3N 45, TX3P 46, VREG1 47, TX2N 48, TX2P 49, VCC 50, TX1N 51, TX1P 52,
  GND 53, TX0N 54, TX0P 55.
- Top pins 56-64: GND 56, READ_EN_N 57, RSVD0 58, EQ0_0/ADDR0 59, EQ1_0/ADDR1 60, MODE 61, RX_DET/SCL 62,
  GAIN0/SDA 63, GND 64. EP = GND.
- 4-level straps: L0 = 1 k to GND, L1 = 13 k, L2 = 59 k, L3 = float. MODE L0 = pin mode.
  RX_DET float = PCIe receiver detect. GAIN float = default. PD0/PD1 low = run (internal 1 M pull-down).
  RSVD0/RSVD1 float. READ_EN_N, ALL_DONE_N float in pin mode.
- EQ index (EQ1, EQ0) -> boost at 8 GHz: (L0,L0) -0.2, (L0,L1) 4.5, (L0,L2) 5.5, (L0,L3) 6.5, (L1,L0) 7.0,
  (L1,L1) 8.0, (L1,L2) 9.0, (L1,L3) 10.0, (L2,L0) 11.0, (L2,L1) 12.0, (L2,L2) 13.0, (L2,L3) 13.5, (L3,L0) 15.0,
  (L3,L1) 16.5, (L3,L2) 17.0, (L3,L3) 18.0 dB.
- 3.3 V single supply, 107 mW per channel. VREG1 (pins 3, 47) and VREG2 (15, 35): 0.1 uF each, do not join.
  VCC 6, 18, 38, 50: 0.1 uF each plus 1 uF.
- Datasheet figure 8-2 shows 220 nF AC coupling on both the input and the output of every channel.
- Land pattern: side pads 0.6 x 0.2 at x = +/-2.65, top/bottom pads at y = +/-4.9, pitch 0.4, EP 4.1 x 8.6.

## TI DS160PT801 retimer

The public datasheet (SNLS592A) is a 9-page brief: features, package outline ACB0332A (332-ball FCCSP,
8.5 x 13.4 mm, staggered 0.5 mm rows = 0.7071 mm diagonal pitch, land dia 0.3) and no ball map or pin functions.
The full datasheet is released by TI on request. EVM user guide SNLU254 is public.
