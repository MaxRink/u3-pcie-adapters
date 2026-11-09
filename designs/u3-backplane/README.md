# 4-drive U.3 backplane (plan)

A passive backplane for four 2.5" 15 mm U.3 drives (HPE P50230-B21 / PM1735a, ~25 W each), fed by
two 8i cables (each 8i = two x4 ports = two drives). Modules are identical and sit side by side
in a 3D-printed cage, so the drive count scales in steps of four.

**Status: planned, low priority.** The x8 and x16 slot cards come first (Max, 2026-11-09). Nothing
here is laid out yet. This file records the decisions and open items so layout can start without
redoing the research.

## Topology

```
host x16 slot ── host card (retimer, 2x SlimSAS 8i) ══ 2x 8i cable ══ backplane ── 4x U.3 drive
                 x4x4x4x4 bifurcation                 0.5 m, 85 Ω      passive
```

- Each module takes one x16 slot's worth of lanes (4 x4 ports). A second module needs a second
  host card or a card with 4 8i ports.
- The cabled path cannot meet the loss budget passively (design-rules Rev E §9). **The host card
  needs a retimer for full PCIe 4.0 compliance.** A passive host card (no retimer) will very likely
  still train at 16 GT/s with ≤0.5 m cables, but that is a working build, not a compliant one.

## Decisions

### 8i connector: SlimSAS 8i (SFF-8654), not MCIO 8i

| | SlimSAS 8i (SFF-8654, 74 pin) | MCIO 8i (SFF-TA-1016, 74 pin) |
| --- | --- | --- |
| Sidebands for 2x x4 | SFF-9402 x8 defines two sideband sets, A and B ("Both sets of sidebands (A and B)" are needed for a pair of x4), so each drive gets its own REFCLK and PERST# from the host | OCP M-XIO §7.1.2 x8 has **one** REFCLK, one PERST#, one CBL_PRES for the whole 8i; the second x4 would need a clock buffer and shared reset on the backplane |
| PCIe 4.0 cables (8i to 8i, 85 Ω, with sidebands) | common: e.g. 10Gtek "24G SlimSAS SFF-8654 8i, PCIe 4.0, 85 Ω, with sidebands" 0.5–1 m | fewer, pricier (Icy Dock MCIO 8i 0.5 m) |
| Host cards (x16 to 2x 8i) | many on amazon.de / ebay.de, incl. retimer and redriver cards (e.g. C-Payne, sold by ram-koenig.de) | mostly Gen5 cards, pricier |

Pick SlimSAS 8i. Gen4 needs nothing MCIO offers.

**Cable rule:** buy only cables sold as **PCIe 4.0, 85 Ω, with sidebands**. 10Gtek sells the same
SFF-8654 cable "without sidebands" (SAS) and in 100 Ω; those drop REFCLK/PERST# and will not work.
Ring out every cable before first power-up (same check as the OCuLink cable, review M7).

**Pinout:** SFF-9402 Rev 1.1 Tables 6-2/6-3 (x8) and 6-6 (sideband use) give the pin-level map. Our
text extraction of the SNIA PDF lost the table images, so the pin map must be typed in from the
rendered PDF before layout (open item 1). Vendors differ on SlimSAS PCIe sideband wiring
(Broadcom tri-mode vs SFF-9402), so the host card must be SFF-9402 "PCIe" pinout.

### Drive receptacle: Amphenol PSAS5F3130021TR (vertical SMT)

- Vertical (mates perpendicular to the PCB), SMT with stamped retainer clips, 8.15 mm above board,
  85 Ω, listed by Amphenol for **cU.2 and U.3** at 32 GT/s, 500 cycles.
- JLC/LCSC **C5382954** (Extended part; stock and price not visible on the page we read, check
  before ordering).
- This is the classic server-backplane geometry: the drive slides in and plugs straight into the board.
- Unlike the right-angle PSAS4F213002 on the cage board (review M3: listed as U.2 only), this part is
  vendor-qualified for U.3.
- Footprint: build it from the Amphenol drawing (the EasyEDA footprint linked from the JLC page is a
  cross-check, not a source). Commit the drawing to `docs/ref/`.

### Mechanics: a 4-drive module that tiles

- Drives stand on edge (15 mm side horizontal), **20 mm pitch** = 5 mm air gap, the gap the thermal
  model used (`docs/thermal/`). 3 mm gaps (18 mm pitch) cut the airflow needed from 43 to 26 CFM for
  4 drives but need a high-pressure fan.
- Module pitch = 4 × drive pitch = 80 mm, so a gap between modules is the same as a gap inside one.
  Board is about 80 mm wide (≤79.6 mm, so neighbours never touch) and ~75 mm tall (drive width
  69.85 mm plus a bottom band for the 8i and power connectors).
- **Airflow:** air runs along the drives and through the backplane. Mill slots in each 20 mm column
  between receptacles and above the receptacle band, the way server backplanes do. Milled internal
  slots ≥1 mm are part of normal routing at JLC and PCBWay, so they should not add cost (confirm on
  the quote). Keep PCIe ≥1 mm from any slot edge and never route over a slot (rules §5).
- **Mounting:** M3 slots (lib `MountingSlot_M3_3.2x6.2`), elongated along the board's vertical axis
  to absorb the drive-height tolerance that is still open (review M8). Two per side edge, at the same
  positions on every module, so the printed cage uses one rail design for all modules.
- The cage, not the backplane, locates the drives: rails on the drive's side holes (SFF-8201), with
  ±0.5 mm float, and the backplane floats on its slots until the drives are seated.
- Connectors on the back face: two right-angle SlimSAS 8i and the power header in the bottom band,
  cables leaving sideways along the bottom so they don't block the air path behind the drives.

### Electrical (lessons from the cage board review)

| Item | Plan |
| --- | --- |
| HPT0 (S15) | GND on every receptacle (review C1) |
| Lanes 0/1 drive TX (PER0/PER1, S5/S6 and S12/S13) | 220 nF X7R 0402 on the backplane, populated, L2 void under the pads (review C2). The host card must **not** also cap its RX on these lanes. PER2/PER3 and all PET: no caps |
| Wiring | true SFF-TA-1001 lane map (S pins), reuse `U3_PINS` from `gen/symlib.py` |
| REFCLK | per drive from the cable (SFF-9402 sideband A/B per x4). Optional DNP 100 MHz HCSL generator + 4-output buffer, only for SRIS-capable hosts |
| PERST# | per drive: 100 k pull-down, Ioff buffer (74LVC1G17/74AUP class) powered from 3V3_AUX, so a missing cable holds the drive in reset and an unpowered backplane isn't back-fed (review M2) |
| CPRSNT# / cable present | per x4, drive it low when the drive is present (gate from drive IfDet#) |
| SMBus | per-drive DNP 0 Ω links. All drives answer at 0x6A, so connect at most one per bus, or add a PCA9546 mux later |
| DualPortEn# / PWRDIS | 10 k pull-up / 10 k pull-down per drive |
| 12 V | 4 × 25 W = 100 W ≈ 8.8 A at 11.4 V. **PCIe 8-pin** (Mini-Fit Jr 2x4, 150 W) rather than the cage board's 6-pin (75 W). Per-drive 3 A PTC (TECHFUSE mSMD300-16V, C6851473), so one shorted drive doesn't take the others down. 12 V on L4 plane |
| 3V3_AUX | one HT7533-1 (C14289, 30 V in) for all four drives |
| Activity LED | per drive, KT-0603YG (C2289) + 470 Ω (review M5) |
| Stackup / rules | JLC06161H-3313, design-rules Rev E, PCIe on L1/L6 only, one via per net |

### Loss budget on the backplane

- Drive-side segment after a host-card retimer: ~17 dB for host traces + cable + backplane
  (rules §9), so the backplane is not the constraint. Keep each lane ≤ 60 mm anyway (≈3 dB),
  which also keeps the passive build's margin.
- The SlimSAS connectors sit in the middle of the bottom band, so the outer drives' lanes are the
  longest. Estimate: 35–60 mm. Measure after layout and record in `lengths.json`.

## Host card

The x16 retimer card being designed now feeds onboard drives, not cables. Two ways to feed this
backplane:

1. Buy a PCIe 4.0 x16 to 2x SlimSAS 8i card with a **retimer** (not a redriver), SFF-9402 pinout,
   no RX AC caps. Check the chip before buying.
2. Later, a project-made host card: x16 fingers, 2x DS160PT801 (or similar), 2x SlimSAS 8i.

Either way, the host card must provide x4x4x4x4 with a separate REFCLK and PERST# per x4 on the
A/B sideband sets.

## Open items before layout

1. Type in the SFF-9402 x8 and sideband tables from the rendered PDF (pin map for the 8i).
2. Pick the SlimSAS 8i receptacle (right-angle SMT, e.g. Amphenol U10 series or ACES 230-10089) and
   confirm LCSC stock and drawing.
3. Get the PSAS5F3130021TR drawing and LCSC stock; build and test-print the footprint.
4. Drive height relative to the receptacle (review M8) applies here too: measure on a real part.
5. Choose the host card (retimer, pinout) and buy two cables to ring out.
6. Cage model: rails, fan wall (92x38 class fan per 4 drives), cable exits.

## Sources

- SFF-9402 Rev 1.1, https://members.snia.org/document/dl/27380 (sideband sets A/B for 2x x4)
- OCP M-XIO Base Spec v1.0 RC4 §7.1.2, https://www.opencompute.org/documents/m-xio-r1-v1p0-rc4-pdf/ (MCIO 8i: single sideband set)
- Amphenol SAS/PCIe 5.0 (U.2 & U.3) connectors, https://www.mouser.com/pdfDocs/ssio_sas_pcie5_u2_u3.pdf
- JLC part C5382954, https://jlcpcb.com/partdetail/6257216-PSAS5F3130021TR/C5382954
- 10Gtek SlimSAS 8i cables, https://store.10gtek.com/de/24g-internal-slimsas-sff-8654-to-sff-8654-8i-cable-sas-4-0-85-ohm-0-5-1-meter/p-7863 and https://store.10gtek.com/24g-internal-slimsas-sff-8654-to-sff-8654-8i-cable-standard-profile-straight-to-low-profile-straight-pcie-4-0-100-ohm-30awg-without-sidebands/p-23020
- C-Payne SlimSAS adapters (DE shop), https://en.ram-koenig.de/c-payne-slimsas-8i-to-pcie-4.0-x8-x16-adapter-2x-sff-8654-lp-6-pin-cables-10226
- Cage board review, [`docs/reviews/cage-board-review.md`](../../docs/reviews/cage-board-review.md)
