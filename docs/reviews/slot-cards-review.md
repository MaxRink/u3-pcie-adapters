# Design review: x8, x16 (4-drive) and x16 (3-drive) U.3 slot cards, rev B

- **Boards:** `designs/x16-u3-card/boards/{x8,x16p,x16p3}`, PR #8 at commit 9bd130b (branch `x8-card`).
- **Review date:** 2026-11-09.
- **Scope:** full spec compliance (PCIe CEM 4.0, SFF-TA-1001 Rev 1.1, datasheets, design-rules Rev E, JLC/PCBWay), plus Max's requirement that **SMBus and all sidebands are wired** and best practices followed.
- **How it was checked:**
  - KiCad 7.0.11 DRC with zones filled: **0 errors on all three boards** (library warnings only).
  - Pad-by-pad net dump of every footprint, compared against the U.3 and CEM pinouts.
  - Three independent reviews: electrical/sidebands/power, SI/fab (measured on filled zones), and mechanical/BOM.
- **No ERC:** the boards are generated straight to layout, so there is no schematic to run ERC on.

## Summary

| # | Sev | Finding | Boards |
|---|---|---|---|
| C1 | **Critical** | Slot 12 V budget exceeded with the documented "slot" default | all |
| C2 | **Critical** | Far drives exceed the Gen4 loss budget by 2.8–6.1 dB, so they are not PCIe 4.0 compliant passively | x16p C/D, x16p3 C |
| C3 | **Critical** | Window edge likely inside the seated drive's envelope (housing face ≠ 11.75 mm guide-tip line), so drives may not seat | all (+ cage) |
| C4 | **Critical** | No structure carries drive weight: SMT receptacle peel, and 312 mm card sag | all, worst x16p |
| M1 | Major | 9DBL411B REFCLK buffer is Gen1–3 only | all |
| M2 | Major | Card dead without slot 3.3Vaux, which is optional in CEM; R9 0R back-feeds the host | all |
| M3 | Major | 3.3Vaux 20 mA limit (non-wake card) vs LEDs and pull-ups | all |
| M4 | Major | PERST# not gated on drive 12 V power-good; PCIE_RST_N has no pull-down | all |
| M5 | Major | 12 V jumper: no shunts in BOM, SMD footprint vs THT part, no SLOT/AUX silk, shunt current rating | all |
| M6 | Major | SMBus: 2 devices per drive on the host bus; 0x70–0x73 collides with motherboard muxes and with a second card | all |
| M7 | Major | No per-drive 12 V protection (eFuse) | all |
| M8 | Major | TX lanes cross REFCLK via voids; PET8_P 0.102 mm from a REFCLK via | all |
| M9 | Major | REFCLK_C/D run on the window edge (0.046 mm plane margin, 0.35 mm to edge) and have no return vias | x16 |
| M10 | Major | Glass weave: 86–149 mm on-axis runs on the longest lanes | x16 |
| M11 | Major | Bracket screw holes have L4 12 V within 0.20 mm of the hole wall | all |
| M12 | Major | 12V_AUX L4 band necks to 1.45 mm (~90 °C rise with A+B on aux) | x16 |
| M13 | Major | Each card takes the slot *above* (secondary side); drives 25–31 mm over CEM height | all |
| M14 | Major | J5 plugs in from beyond the 312 mm end, so the card measures ~340–360 mm with cable in the N5 | x16p |
| M15 | Major | Receptacle retention-clip slots have no paste | all |
| M16 | Major | WAKE# not wired to slot B11 (Max: all sidebands wired) | all |

## Critical

### C1: Slot 12 V budget
- **Limits (CEM 4.0 §4.2 via ADI DN346):**
  - x4/x8 card: 25 W, 12 V 2.1 A.
  - x16 card: 75 W, 12 V 5.5 A, and only after Set_Slot_Power_Limit. At power-up it gets 25 W.
  - The finger has 5 × 12 V pins (B1–B3, A2–A3) at ~1.1 A each.
- **Load:** a 25 W PM1735a draws 2.26 A at 11.04 V (12 V −8 %).
- **Default draw:**

| Board | Default draw | Limit |
|---|---|---|
| x8 | 4.5 A | 2.1 A (one drive alone already exceeds it) |
| x16p3 | 6.8 A | 5.5 A |
| x16p | 9.1 A | 5.5 A |

- Both x16 cards also exceed the finger-pin rating.
- A PCIe 6-pin is rated 75 W, so x16p with all four drives on aux (100 W) is over that too.
- **Fix:**
  - Default every drive to aux.
  - Use a PCIe 8-pin (150 W) on x16p/x16p3; x8 is fine on the 6-pin (50 W).
  - Correct the README power text.
  - Max asked for slot-default, so this is pending his decision.

### C2: Gen4 loss budget on the far drives
- **Model (Rev E):** 0.05 dB/mm + 0.1 dB/via + 0.3 dB fingers + 1.0 dB receptacle + 0.15 dB per AC cap, against ≤ 4.0 dB for our hardware at 8 GHz.

| Board / drive | Copper | IL @ 8 GHz | Margin |
|---|---|---|---|
| x8 A / B | 30–47 mm | 2.80–3.97 dB | +0.03 dB min (PER4) |
| x16 B | 45–53 mm | 3.67–4.04 dB | −0.04 dB |
| x16 C | 107–111 mm | 6.77–7.22 dB | **−2.8 to −3.2 dB** |
| x16p D | 164–168 mm | 9.62–10.07 dB | **−5.6 to −6.1 dB** |

- The DRU `length max 300mm` exception only silences DRC.
- **Fix:** put a retimer on lanes 8–15 (and preferably 4–7), e.g. TI DS160PT801 with its EEPROM/SMBus config path, straps and a REFCLK per retimer. Alternatively, force Gen3 on ports C/D as the compliant fallback.
- Even with the optimistic old Rev D numbers (1.1 dB/in, 6 dB), C and D still fail.

### C3: Drive seating vs window edge
- `gen/fplib.py:67` uses 11.75 mm from the peg line as the mating face. Per the Amphenol drawing that is the **tip of the chamfered guide posts** (sheet 1: 1.70 mm tips, 2 × 30°; sheet 2's (9.40) ends at the keep-out apex).
- The housing face is ~9.9–10.05 mm from the peg line. The drive plug stands 0.3 mm proud of the drive end (SFF-8223), and the drive base is 0.65 mm below the PCB top (2.85 mm centreline vs SFF-8223 A7 3.50).
- With the window edge at YP − 10.75, the drive overlaps the board by ~0.4–0.7 mm and cannot fully seat. Premate is only 0.55 mm.
- `tools/render/procedural.py` offsets the drive by 0.4 mm, so the renders hide this.
- **Fix:**
  - Window edge ≤ YP − 9.4; move the L3 trunks ~1.35 mm.
  - Add a separate housing-face constant (~10.05).
  - Fit-check one receptacle and drive before ordering.
  - The cage board needs the same fix.

### C4: Mechanical support
- Each ~150 g drive hangs on an SMT right-angle receptacle: ~0.09 N·m static peel moment on 0.6 mm pads ~3 mm from the pivot, and 5–10 × that under shock. The pegs are NPTH and only locate.
- x16p (0.6 kg of drives, 312 mm, only 34–40 mm strips under the windows) sags an estimated 5–8 mm at the far end and puts ~0.3 N·m on the slot.
- **Fix:**
  - Add a stiffener (aluminium angle or printed spine) tied into the bracket column and into each drive's SFF-8201 bottom M3 holes.
  - Add a far-end support.
  - Add a per-drive cradle so the receptacle carries no moment.

## Major

### Electrical
- **M1:** the 9DBL411B is "4-Output 3.3 V PCIe Gen1-2-3" (Renesas), and LCSC has 10 in stock. Use a 9DBL0442 (100 Ω, Gen1–6, internal terminations, drop the 33 Ω) or 9DBL0441 (85 Ω). Community input reports host freezes caused by a Gen3 buffer on a commercial card.
- **M2:** slot 3.3Vaux is optional in CEM.
  - Without it, the TCA9543A, TCA9554 and 74LVC1G08 are unpowered, drive PERST# floats, and unpowered devices sit on the host SMBus.
  - R9 (DNP 0 Ω 3V3 → 3V3_AUX) back-feeds the host's 3.3 V from aux in S3/S5 if fitted.
  - **Fix:** ideal-diode ORing (LM66200 / TPS2116) of slot 3V3 and 3V3Aux onto a local rail.
- **M3:** a card that is not wake-enabled may draw only 20 mA from 3.3Vaux.
  - The activity LEDs (1 kΩ, ~1.3 mA each), locate LEDs and IfDet#/IfDet2# pull-ups (grounded by the drive, 0.33 mA each) add up quickly. The drive's own E3 draw is unverified.
  - **Fix:** move the LEDs to 3V3 main and confirm the PM1735a 3.3Vaux current.
- **M4:** each drive's PERST# = slot PERST# AND RST_EN only.
  - Nothing ensures 12V_DRV has been in tolerance ≥ 100 ms (T_PVPERL) before deassert, which matters when a drive is on a late or absent aux cable.
  - **Fix:** 74LVC1G11 with a per-drive 12 V power-good (eFuse PG or TPS3808), plus a 100 kΩ pull-down on PCIE_RST_N.
- **M5:** the 12 V jumper.
  - No shunts are in the BOM, so no drive is powered as delivered.
  - The footprint is SMD (`PinHeader_1x03_..._SMD_Pin1Left`) but C2937625 is a through-hole part.
  - There is no SLOT/AUX silk or pin-1 mark.
  - Typical 2.54 mm shunts are rated 2–3 A, against ~2.3 A continuous plus inrush.
  - The `sideband.py:15` docstring has the pins reversed (the wiring, BOM and README agree with each other).
  - **Fix:** a ≥ 3 A shunt in the BOM or 0 Ω links, matching footprint and part, and silk labels.
- **M6:** the host SMBus.
  - Each drive puts a TCA9543A (0x70 + n) and a TCA9554 (0x20 + n) on the host bus: 8 devices and ~140 pF on x16p, against the CEM per-card guideline.
  - 0x70–0x73 is the default range of common motherboard PCA954x muxes, and two cards in one system always collide.
  - **Fix:** one TCA9548A per card with A0–A2 on jumpers, with the expanders behind it.
- **M7:** there is no eFuse or fuse on 12V_DRV or on 12V_AUX, so a shorted drive faults the slot or the PSU rail. **Fix:** a per-drive eFuse (TPS25982 / TPS1663, ~3 A ILIM), which also supplies the PG for M4.
- **M16 (requirement):** WAKE# is only read by the expander. Wire it to slot B11 through a 74LVC1G07 per drive (wired-OR). This needs 3.3Vaux and puts the card in the 375 mA wake class. Also add a 0 Ω-to-GND footprint on B12 CLKREQ#.

### SI / fab
- **M8:** PCIe TX lanes cross REFCLK via antipad voids on L2.
  - Crossings: PET0_P and PET4_P 0.83 mm (all boards); PET8_P 1.25 mm at (179.875, −25.7…−27.0); PET12_P 0.98 mm.
  - PET8_P's edge is 0.102 mm from the REFCLK_C_N via pad. It passes DRC only because of the NECKDOWN rule.
  - **Fix:** move the REFCLK vias ≥ 1 mm away from the lane-0 riser.
- **M9:** REFCLK_C_P (L1) and REFCLK_D_P (L6) run along the window edge for ~150 / 210 mm.
  - Plane margin beyond the trace edge is 0.046 mm, and the trace is 0.35 mm from the board edge. README §5 requires ≥ 3w and ≥ 1 mm from the edge.
  - REFCLK vias have no GND return via; the nearest is 1.3–9.1 mm away. REFCLK_D has an extra L6↔L1 hop.
  - **Fix:** move both pairs ≥ 1 mm inboard, add 2 GND vias per transition, and remove the hop.
- **M10:** 86–149 mm straight on-axis runs on lanes 9–15 and REFCLK_D, against README §5's 5–10° rule. These are exactly the lanes with no margin.
- **M11:** bracket NPTH H1 (7.5, −94.75) and H2 (7.5, −9.35) have L4 12V_AUX / 12V and the GND planes within 0.20 mm of the hole wall. **Fix:** ≥ 1 mm inner keepout, and no outer copper under a Ø 6.5 mm screw head.
- **M12:** the 12V_AUX band on L4 (0.5 oz) is 3–7 mm wide, with a 1.45 mm neck at x = 84.6 and 3.1 mm at x ≈ 158 / 232. A+B on aux gives a ~90 °C rise. **Fix:** a wide L1/L6 pour, or document "aux only for C/D".

### Mechanical
- **M13:** the receptacles and drives sit on the secondary side, which faces the CPU / the slot above.
  - They intrude ~11.7 mm into slot N−1, against the CEM secondary-side limit of 2.67 mm. Slot N−1 must stay empty.
  - Drive tops are 136–142 mm above the finger edge, vs 111.15 mm CEM full height. That is still under the N5's 160 mm cooler clearance, but leaves no room for a side-panel fan.
  - **Fix:** document "occupies slot N and N−1".
- **M14:** J5 mates along +x beyond the far end. On x16p the plug and its bend make the assembly ~340–360 mm long, against the N5's 325 mm (front AIO) / 350 mm limit. **Fix:** rotate J5 so the plug enters from the top edge.
- **M15:** the receptacle MP retention-clip slots (0.8 × 1.9) have no paste. **Fix:** paste-in-hole, or order hand soldering.

## Minor
| # | Finding | Fix |
|---|---|---|
| m1 | x8 PER0/PER4 have only +0.03…0.23 dB of loss margin | Shorten lane 4, or move its caps to the bottom (saves 2 vias) |
| m2 | Lane length isn't checked across `PERn` + `C_PERn`, so the 50.8 mm cap can be bypassed | Check whole-lane length in the generator |
| m3 | Mating-side via row: PET0/4/8/12 and C_PER0/4/8/12 share one GND via at 1.031 mm (rule: 2 vias, ≤ 1.0 mm) | Add a second GND via |
| m4 | Antipads are actually Ø 1.35 / 1.55 (README/DRU say 0.95); HS vias keep their non-functional pads | Encode one size; enable remove-unconnected on HS vias |
| m5 | KiCad 7 skew is measured against the average, so `max 0.127` allows 0.254 P–N (REFCLK B/C at 0.186 / 0.214) | Generate 0.0635 |
| m6 | Bottom AC caps see L4 12 V under their L5 void | Add a GND island on L4 under each cap pair |
| m7 | Lanes 8–15 at 0.9 mm pitch over 110–145 mm (FEXT) | Use a 1.2 mm pitch |
| m8 | x8 PER7_N runs 0.47 mm from the raised edge | Move it ≥ 1 mm in |
| m9 | 22 / 46 / 31 open vias in pads | Order filled and capped vias, or move them |
| m10 | No fab notes or IPC-D-356 netlist | Add: stackup JLC06161H-3313, impedance, fingers plus 30° bevel, ±0.13 mm thickness, via fill |
| m11 | x16p is exactly 312.00 mm long, with no routing tolerance | Make it ~311.6 mm |
| m12 | x16p3 silk/README say "x8x4x4", which strands drive B | Change to x4x4x4x4 or x4x4x8 |
| m13 | x16p3: OE1# is on GND, so DIF1 is enabled with no load | Tie it to 3V3 |
| m14 | TCA9554 output register powers up at 0xFF | Document writing 0x01 before 0x03, or PWRDIS glitches high |
| m15 | No reset path for a hung mux (RESET# shares the INT pull-up) | Add an expander- or jumper-driven reset |
| m16 | DualPortEn# can be changed in software, but REFCLK1 is open | Pin it high or document it |
| m17 | 12V_DRV has only ~3–4 µF effective; no bulk at the fingers | Add 47–100 µF per drive and some at the fingers |
| m18 | 12 V jumper feed is 0.6 mm with 2 vias for 2.3 A | Widen it and add vias |
| m19 | Lateral drive clearance is 1.07 mm (A to bracket column, x16p3 C); an SFF-8223 connector offset could eat it | Make it ≥ 2.5 mm, or measure a drive |
| m20 | Locate LEDs face the CPU side and can't be seen | Move them to the primary side |
| m21 | C13585 is labelled 25 V; the part is 50 V | Fix the label |
| m22 | The HPE P50230-B21 ships in a carrier, which must be removed | Add to the docs |
| m23 | DRU exceptions (length, REFCLK uncoupled) are missing from the README §5 table | Add them |

## Verified OK
- **U.3 pinout (all 9 receptacles):**
  - S-lane map correct; HPT0 (S15) = GND; HPT1 open.
  - 220 nF (C16772, Basic) on PER0/PER1 per SFF-TA-1001 Table 4-11.
  - PER P/N inverted at the U.3 pins (legal); REFCLK not inverted.
  - SMBus via TCA9543A with 4.7 kΩ downstream pull-ups.
  - PERST0#/PERST1#, PWRDIS (10 kΩ pull-down), DualPortEn# (pull-up), PRSNT#, IfDet#, IfDet2#, WAKE#, ACTIVITY# → LED, E3 3.3Vaux, and 12 V on P13–P15 are all wired.
- **Edge fingers:**
  - Signal mapping per CEM: B14 = host TX → U.3 S2; A16 = card TX ← U.3 S5/S6.
  - PRSNT1# A1 ↔ B48 (x8) / B81 (x16).
  - 0.70 × 4.3 mm pads at 1.0 mm pitch; key at 56.2–58.1 mm.
  - L2/L4/L5 voided under the fingers; no vias in the fingers.
- **REFCLK buffer:**
  - 9DBL411B pin map and strapping are correct.
  - 33 Ω = Zo − 17 for 100 Ω.
  - REFCLK reaches every drive.
- **SMBus addresses:** TCA9543A at 0x70–0x73 and TCA9554 at 0x20–0x23 are unique on a card; downstream 0x6A/0x53 are isolated per channel.
- **Power-up defaults:** drive powered, single port, reset follows the slot.
- **SI and layout:**
  - PCIe only on L1/L6, through vias only (no stubs).
  - 0.157 / 0.152 mm and 0.128 / 0.254 mm everywhere.
  - PCIe P/N skew 0.000.
  - No antipad merging across pairs.
  - All L6 pairs reference L5, so the L4 split is never a reference.
  - AC-cap voids are correct.
- **12 V separation:** slot 12 V and 12V_AUX never meet. J5 pins 1–3 = 12 V.
- **Outline:** 111.15 mm height; 312 / 239 / 190 mm lengths; thickness 1.578 mm.
- **Gerbers and drill files** are complete. Minimum drill 0.20 mm, HS vias 0.25 / 0.55.

## Not verified
- CEM 4.0 §4.2 power table text (taken from ADI DN346 and memory).
- CEM bracket and retention-latch geometry.
- PM1735a 3.3Vaux and inrush current.
- SFF-8223 Fig. 3-1 lateral connector offset.
- 9DBL411B additive jitter.
- JLC stock for C22454449: 16 at LCSC and not in the JLC library (global sourcing). The 4-drive card needs 4.

## Sources
- SNIA SFF-TA-1001 Rev 1.1: https://members.snia.org/document/dl/26900
- SFF-8223 rev 2.7: https://members.snia.org/document/dl/25855
- Amphenol PSAS4F213002XXX rev 3: `designs/x16-u3-card/docs/ref/psas4f213002xxx.pdf`
- PCIe CEM 4.0 v1.0 (partial): https://billxiang.github.io/BillXiang-BookMarks/./书签工具栏/设备与驱动/PCI/PCIe/PCIe_CEM_SPEC_R4_V1_0_08072019_NCB.pdf
- ADI DN346 (CEM rails): https://www.analog.com/en/design-notes/pci-express-power-and-mini-card-solutions.html
- Renesas 9DBL411: https://www.renesas.com/en/products/9dbl411; 9DBL0442: https://www.renesas.com/en/products/9dbl0442
- TI TCA9543A: https://www.ti.com/lit/ds/symlink/tca9543a.pdf; TCA9554: https://www.ti.com/lit/ds/symlink/tca9554.pdf
- Jonsbo N5 review: https://nascompares.com/?p=74926
- LCSC/JLC part pages for every BOM C-number (checked 2026-11-09)
