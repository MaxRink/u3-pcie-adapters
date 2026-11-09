# Minisforum MS-01 / MS-A2 U.3 adapters

Goal: run U.3-only drives (HPE P50230-B21, PM1735a, 2.5" U.3, SFF-TA-1001 wiring) in the Minisforum MS-01 and MS-A2. The stock M.2-to-U.2 adapter boards are wired for U.2, so these drives don't initialize on them.

Decision (Max, 2026-11-09): pursue both routes.

## Route A: PCIe slot (`pcie-x4-card/`)
- Use a U.3-wired PCIe x4 card with the drive mounted on it, in the low-profile slot.
- On the MS-01, a 15mm U.2 drive on a thin x4 card fits with the lid closed (Intel P4610, L1T thread 212765). No U.3 card has been tested there yet.
- Candidates: Max's Cablecc card (amazon.de/dp/B0C3CLGZDK, known working with these drives) and StarTech PEX4SFF8639U3.
- Open: does the Cablecc card have a low-profile bracket? Does the drive and card fit the MS-A2 slot?
- A custom card is designed only if no off-the-shelf card fits.

## Route B: M.2-slot replacement board (`m2-board/`)
- Replaces the stock adapter. The board is M.2 M-key at 0.8 mm, carries PCIe 4.0 x4 to an SFF-8639 receptacle with U.3 lane mapping, and the run is about 30-40 mm.
- MS-01: primary M.2 slot, PCIe 4.0 x4. A motherboard switch puts the slot in a "higher-power" U.2 mode, and the rails it puts on the M.2 pins are not published. Under the fan there is room for a 7mm drive only (STH review).
- MS-A2: slot 1, PCIe 4.0 x4. The new adapter has a small power cable to the motherboard and there is no switch. The pinout, the cable, and the maximum drive thickness are not published.
- Blocker: a 15mm PM1735a won't fit the internal 7mm bay. So this board serves 7mm U.3 drives, a case mod, or a cabled-out drive.
- Inputs needed:
  - Max: photos of both sides of each stock board with a ruler, board size, mounting hole position, photos of the MS-A2 power cable connector, and voltages on P13-P15 (12V) and E3 (3.3Vaux) with no drive attached.
  - Minisforum support: emailed 2026-11-09 (from Max's Gmail to support@minisforum.com) for the pinout, power, drawings, and max drive thickness.
- Rules: ../../design-rules/, template jlc04081h-3313_0.8mm (JLC04081H-3313, 0.8 mm, 4 layers).
  - PCIe runs on L1 only, with no vias; 85 ohm diff = 0.157/0.152 mm.
  - Void L2 under the fingers and keep GND on L3.
  - No AC caps on the board: the host TX caps are on the motherboard and the drive has its own.
  - Fingers: JLC offers ENIG only. PCBWay offers hard gold and ±0.08 mm thickness (README §7 of the rules).
- Pin map: share it with the x16 card thread (SFF-TA-1001).

## Sources
- https://www.servethehome.com/minisforum-ms-01-review-the-10gbe-with-pcie-slot-mini-pc-intel/2/
- https://www.servethehome.com/minisforum-ms-a2-review-an-almost-perfect-amd-ryzen-intel-10gbe-homelab-system/2/
- https://forum.level1techs.com/t/minisforum-ms-01-15mm-enterprise-u-2-u-3-solution/212765
- https://forum.level1techs.com/t/minisforum-ms-a2-m-2-slots/236614

Status: no KiCad files yet. The design waits on the stock-board measurements.
