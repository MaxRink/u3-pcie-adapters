# Design review: OCuLink 4i → U.3 cage board (rev A)

- **Board:** `designs/x16-u3-card/boards/cage/` (generator `gen/cage.py`), as committed in 4e8dfb5 (initial import)
- **Review date:** 2026-11-09
- **Scope:** full spec compliance. Every pin, net, power rail, sideband signal, footprint and fab rule was checked against primary sources where we could get them.
- **Method:** KiCad 7.0.11 DRC was run with `pcbnew.WriteDRCReport` on the board's own `.kicad_dru`, with zones filled. Nets on J1 and J2 were dumped pad by pad and compared with the pin maps. Four independent reviews covered spec/datasheet compliance (U.3 + drive power, OCuLink, parts/BOM, fab/SI), plus a mechanical check.
- **No ERC:** the boards are generated straight to layout with no schematic, so ERC is not possible. Connectivity is only as correct as `gen/cage.py` and the pin maps in `gen/symlib.py`, which is why the pin-by-pin audit below matters.

Fix status refers to the design thread's branch `u3-boards` (cards PR) and the rules thread's PR #3 (design-rules Rev E).

## Summary

| # | Sev | Finding | Status |
|---|---|---|---|
| C1 | **Critical** | U.3 S15 (HPT0) left floating, so the drive selects the U.2 (Quad PCIe) lane map and cannot link | Fixed on `u3-boards` |
| C2 | **Critical** | No AC caps on PER0/PER1. A compliant U.3 drive must not cap lanes 0/1 TX, so the host has to | Being fixed (220 nF 0402 on PER0/PER1) |
| M1 | Major | L2/L5 GND planes slotted ~11 mm along the PET via row; PET transitions have no continuous return | Sent to design thread |
| M2 | Major | REFCLK and PERST# come over the cable with no fallback or isolation; unpowered cage back-powered via PERST#/REFCLK/SMBus | Sent to design thread |
| M3 | Major | J1 (Amphenol PSAS4F213002) land pattern cites a drawing that isn't in the repo; Amphenol lists the part as "U.2" | Sent to design thread |
| M4 | Major | F1 polyfuse has no part, and Ihold 2.6 A derates below the drive's ~2.2 A at cage temperature | Sent to design thread |
| M5 | Major | D2 LED C72043 is out of stock and has Vf 3.3 V, so it would stay dark on 3V3 through 1 k | Sent to design thread |
| M6 | Major | Cabled path can't meet the conservative loss budget passively; a retimer on the host card is needed for full compliance | Rules Rev E §9 |
| M7 | Major | OCuLink cable choice: SAS-pinout or sideband-less cables drop REFCLK/PERST# | Bring-up/BOM note |
| M8 | Major | Drive height, orientation and X offset vs the receptacle depend on the Amphenol drawing; the holder must locate the drive | Sent to design thread |
| m1–m19 | Minor | See below | Mixed |

## Critical

### C1: HPT0 (S15) must be grounded by the host
- `u3net()` returned `None` for HPT0, so J1 S15 had no net.
- SFF-TA-1001 Rev 1.1 §4.2: "An SFF-TA-1001 compliant slot shall assert this pin low."
- Table 4-4: HPT0 open (with HPT1 and DualPortEn# open) selects **Quad PCIe single x4**, which is the U.2 map with lane 0 on E10–E14 and lane 3 on E17–E21. HPT0 = GND selects **SFF-TA-1001 single x4**.
- As built, the drive would look for lanes 0 and 3 on unconnected E pins, so no link.
- This is very likely also why Max's cheap U.2 adapters failed to initialise these drives.
- **Fix:** map HPT0 to GND. HPT1 (E16) may stay open. Done on `u3-boards`, where S15 joins the S16 GND via on L1.

### C2: Lanes 0 and 1, drive → host, are DC-coupled
- SFF-TA-1001 §4.5: "in-line AC coupling capacitors shall not be added for those locations identified as 'not required'."
- Table 4-11 (device, SFF-TA-1001 mode) marks the device TX on S5/S6 and S12/S13 as **not required**, so a compliant drive has no caps there.
- Table 4-10 puts 220 nF ±10 % on **all 16 host S-pins** instead.
- A PCIe root port has no RX caps, and the board had none either.
- **Fix:**
  - Fit 220 nF X7R 0402, ≥16 V, on PER0_P/N and PER1_P/N, populated by default, with an L2 void under the pads.
  - PER2/PER3: the drive fits 220 nF. Direct is inside the PCIe range; Appendix A intends 110 nF in series.
  - PET0–3: nothing to add. The host TX caps plus the drive's 2.2 µF RX caps cover them.
- Apply the same fix to the x8/x16 cards and the Minisforum boards.
- `design-rules/README.md` and `designs/minisforum-u3/README.md` ("drives carry their own TX caps") were wrong for lanes 0/1.

## Major

### M1: GND reference slot under the PET via transitions
- The PET L1→L6 vias at y = 26.65 sit at 0.7–0.8 mm pitch, with the A9–A13 low-speed vias interleaved.
- Their antipads merge with each other and with the J2 Ø1.0 NPTH voids. With zones filled, L2 and L5 are cut for x = −2.05 … 9.1 mm.
- The y = 27.4 return vias are on the far side of that slot. The nearest trace-side stitching is ~3 mm away.
- **Fix:**
  - Use a pair-to-pair via pitch of ≳1.25 mm, or stagger the vias in y.
  - Move the low-speed vias off the row.
  - Add a trace-side GND via per pair.

### M2: Cable sideband dependency and back-powering
- REFCLK (B12/B13) and PERST# (A12) are taken from the cable, with no local clock option.
- PERST# has no pull resistor and no isolation. If the host card or cable lacks it, E5 floats.
- An unpowered cage is back-powered through PERST#, REFCLK and SMBus.
- **Fix:**
  - Add a 100 k pull-down on PCIE_RST_N.
  - Add an Ioff-rated buffer gated by 3V3_AUX (74LVC1G08/74AUP class). Antmicro uses a 74AUP2G132.
  - Optionally add a DNP 100 MHz HCSL clock generator footprint.
  - Bring-up rule: cage 12 V on before host PERST# deasserts.
- SMBus A9/A10 → E23/E24 has no pull-ups and no isolation. Add DNP 0 Ω links (minor), so four drives at the NVMe-MI address 0x6A can be separated.

### M3: J1 land pattern can't be traced to a drawing
- `gen/fplib.py` cites `docs/ref/psas4f213002xxx.pdf` rev 3, but that file is not in the repo.
- Amphenol's PCIe 4.0 family datasheet (LCSC copy for C22454449) lists PSAS4F213002 as "U.2, R/A SMT, 2.85 mm, Standard". Only vertical parts in that family are listed for "U.2 & U.3". All 68 positions are present, so U.3 works mechanically, but the part is not vendor-qualified for PCIe on S1–S14.
- The top row has 0.6 mm pads at 0.8 mm pitch, which leaves a 0.2 mm gap (bridging risk).
- JLC stock is 16 pcs.
- **Fix:**
  - Commit the drawing to `docs/ref/`.
  - Re-check the pads, the ±19 mm Ø1.78 pegs, the ±22 mm retainer slots and handedness.
  - Test-fit a 1:1 print against a real part.
  - Candidate U.3-qualified alternative: PSAS5F2130021TR (LCSC availability unconfirmed).

### M4: F1 polyfuse
- The LCSC field is empty, so JLC won't place the part.
- The PM1735 draws 25 W max, about 2.2 A at 11.4 V. A 2.6 A hold rating derates to ~2.0 A at 50–60 °C.
- **Fix:** use a 3 A hold part:
  - TECHFUSE mSMD300-16V (C6851473, 3 A / 5 A trip, 16 V, 12 mΩ)
  - RUILON SMD1812P300TF/16V (C55996, JLC Extended)

### M5: Activity LED
- C72043 (Everlight emerald, Vf ~3.3 V) is out of stock, and on 3.3 V it won't light.
- **Fix:** use KT-0603YG (C2289, Vf ~2.1 V) and optionally drop R5 to 470 Ω.
- Note: some NVMe firmware never drives P11.

### M6: Cabled path loss budget and retimers
- The rules thread re-derived the budget (Rev E). The CEM 28 dB at 16 GT/s splits as root package 5 + system board 13.5 + connector 1.5 + AIC 8. The AIC 8 dB has to include the endpoint package, which leaves ≤4.0 dB for our hardware.
- On the OCuLink path, the connectors alone take ~2.3 dB of that 4.0 dB. Cage PET0 is estimated at 1.3–1.7 dB (30.4 mm).
- A passive cabled link therefore cannot be shown compliant at any useful cable length.
- **For full PCIe 4.0 compliance, the x16 OCuLink host card needs retimers**, e.g. TI DS160PT801 (x8, two per x16). LCSC availability is not yet checked.
- A passive 0.25–0.5 m link will very likely still train at 16 GT/s, but that is margin-dependent, not compliant. Validate it with AER error counters and keep the retimer option.
- Open: the PCI-SIG SFF-8639 Module spec's host allocation (members only) might relax this.

### M7: OCuLink cables
- Market "SAS" OCuLink cables and many eGPU cables don't state whether REFCLK (12/13) and sideband pins 9/10/12/13 are wired. SAS cables are often 100 Ω.
- **Fix:**
  - Buy a cable explicitly sold as a PCIe 4.0 OCuLink 4i cable (SFF-8611↔SFF-8611, 85 Ω).
  - Ring it out: high-speed pins A→B on the same number, and host A12/A13 ↔ device B12/B13.
  - Delock 85211 is rated Gen3 only and is discontinued.

### M8: Drive height, orientation and lateral offset not pinned down (mechanical)
- J1's mating face sits exactly on the board edge (y = 0), so the drive hangs entirely off the board. It can't hit any component, but its SFF-8201 mounting holes can't line up with H1–H4. The printed holder has to locate the drive on its own.
- On the drive side the numbers are solid: the connector datum is 3.50 ± 0.38 mm above the drive bottom (SFF-8223 A7), and the side holes are 3.00 mm up (SFF-8201 A23) at 14.00 / 90.60 mm from the connector end.
- On the receptacle side they are not. Amphenol only says "2.85 mm height, Standard", and the drawing is needed to know what that is measured to. The two readings put the drive bottom at either 0.65 mm below or 2.85 mm above the PCB top, a 3.5 mm difference.
- With reading (a), any drive travel past the board edge hits the PCB.
- The connector's X offset relative to the drive side rails (SFF-8223 A2/A3/A5) is also not verified.
- **Fix:**
  - Read the PCB-to-datum height, drive orientation (label up), PCB edge line and recommended board thickness from the Amphenol drawing, or measure a sample with calipers.
  - Locate the drive in the holder by its side holes, with ±0.5 mm lateral float. Tighten the screws only after mating.
  - Consider pulling the board edge back 0.5–1.0 mm under the receptacle front if the drawing allows.
  - Test-fit a blank board before PCBA.

## Minor

| # | Finding | Fix |
|---|---|---|
| m1 | REFCLK via pair (4.68, 21.08)/(4.12, 20.52) has no GND via within 3.7 mm | Add 2 symmetric GND vias |
| m2 | The REFCLK antipad pinches the PET1_P L2 reference to 0.12 mm beyond the trace edge (PER1_P on L5: 0.32 mm) | Move the via pair ~0.4 mm |
| m3 | PET0 is 30.36 mm including the via, over the 30 mm per-board cap, so host lane 0 must be ≤19.6 mm | Shorten the PET0 route, or budget it on the host card |
| m4 | J2 NPTH to unused A1/A21 copper is 0.107/0.133 mm, below JLC's 0.2 NPTH-to-copper. The DRC exception doesn't cover fab DFM | Remove the A1/A21 copper from the footprint |
| m5 | 0.12 mm tracks and one 0.120 mm clearance (GND via ↔ J1 E10) fall outside PCBWay's "normal" tier | Use 0.127 mm minimum |
| m6 | C3 (C1525, 16 V) is on 12 V | C307331 (100 nF 50 V X7R 0402, Basic) |
| m7 | AMS1117: 15 V abs max, wants 22 µF tantalum, 10 mA minimum load, and the 3V3_AUX load is lower | HT7533-1 (C14289, 30 V in), or 22 µF plus a ~390 Ω preload; optional TVS (SMBJ15A) on 12V_IN |
| m8 | Q1 2N7002: Vth up to 2.5 V with only 3.3 V gate drive | BSS138 or 2N7002K |
| m9 | CPRSNT# is asserted whenever 12 V is present, even with no drive | Optional: gate it from drive IfDet# (P4) |
| m10 | Pin-map docs: device B9 is BP_TYPE (not NC); host A9 is BP_TYPE (not CBLPRSNT#). The crossover is defined in SFF-9402, not SFF-8611 | Fix the comments in `symlib.py` |
| m11 | `gen/pcbkit.py:12` hardcodes `/mnt/project-files/design-rules` (a stale copy) | Make the path repo-relative |
| m12 | Redundant GND vias 0.52 mm apart near C3/C5 (`cage.py` C3/C5 GND vias) | Drop one |
| m13 | Board setup still carries `edge_connector bevelled` from the template | Remove it; don't order fingers or bevel |
| m14 | Double-sided PCBA (J2/U1/Q1/C*/R3/F1 on the bottom). J3 is THT and J1's retainers need pin-in-paste or hand solder | Expect double setup and stencil cost; order spare J1/J2 (low stock) |
| m15 | Library silk and refdes are stripped, so placement relies entirely on the CPL | Check J2/U1/Q1/F1 rotation in JLC's preview |
| m16 | The J1 retainer at (−22, 9.4) is 0.4 mm from C2's courtyard, and its fillet sits next to C2 | Nudge C2 |
| m17 | J3 (Molex 45558) is not reflow-rated (PS-45558-001 §4.6); Molex recommends a 1.78 mm PCB; the footprint is the 5569-06A2 pattern | Hand or selective solder; check the peg Ø against SD-45558-001 |
| m18 | H2 courtyard runs past the board edge; a 7 mm washer on H4 leaves ~0.6 mm to the 6-pin plug | Move H2/H4 to y ≈ 36.5; use plain M3 heads |
| m19 | Bottom side holds J2 (~4 mm), J3 tails, F1, U1 and C1/C2 (~2 mm), and the OCuLink plug hangs below the board | Holder standoffs ≥5 mm, or a pocket |

## Verified OK

### U.3 side (SFF-TA-1001 Rev 1.1, Tables 4-1 … 4-3)
- Every `U3_PINS` entry matches the spec:
  - S-row lanes 0–3 with host-centric PET/PER naming (S2/S3 = host TX → drive RX)
  - E7/E8 REFCLK, E5 PERST#, E3 3.3Vaux, E23/E24 SMBus, E25 DualPortEn#, P3 PWRDIS, P11 ACTIVITY#, P13–P15 12 V
  - U.2-only E-pin lanes left unused
- Detect pins P4/P10/E6 are drive outputs (Table 4-8), so leaving them unconnected is correct.
- DualPortEn# pulled up selects single port. PWRDIS is active high, so the 10 k pull-down keeps the drive on.
- P13 12V_PRE tied to 12 V is fine without hot-plug. Power pins are 1.5 A each (SFF-TA-8639 §8.1), giving 4.5 A against 2.2 A needed.
- 5 V is not used by the device.
- AMS1117 dissipation is fine at ≤25 mA aux: ~0.3 W.

### OCuLink side (SFF-9402 Rev 1.1, Table 6-1, notes 16/16b/18)
- `OCU_DEV_PINS` is correct for the endpoint end. The cable crosses the A and B rows, sidebands included; 5 V and Vact are not crossed.
- Pin map matches Antmicro's oculink-pcie-adapter, traced to its x16 slot.
- CPRSNT# is endpoint-driven open drain, so the Q1 pull-down is correct.

### Footprint J2
- Identical to Antmicro's land pattern (42 × 0.31 × 0.91 mm at 0.5 mm pitch, shields, asymmetric Ø1.0 NPTH keys).
- Bottom-side mirroring is correct.

### Polarity
- PET0 and all four PER pairs are P/N inverted. This is legal: receivers must support polarity inversion (PCIe Base §4.2.4.4), and it holds at 16 GT/s.
- REFCLK polarity is preserved (asserted in code).

### Power
- J3 (C7545781 = Molex 45558-0003, verified): pads 1–3 (12 V) are on the non-latch row and 4–6 GND on the latch row, matching PCIe 6-pin cables (latch side = grounds). The sense pin tied to GND is fine.
- The 12 V path J3 → F1 → L4 plane → J1 has 3–4× via and copper margin at 2.5 A.

### BOM
- C25744, C11702, C8545, C6186, C15850 (25 V), C12891 (25 V), C5156927 and C22454449 all match their value and package.

### Fab and SI
- The stackup in the file matches JLC06161H-3313 exactly.
- PCIe and REFCLK copper is only on L1/L6, with exactly one through via per net.
- All pairs are 0.157/0.152 (REFCLK 0.128/0.254). Skew ≤0.023 mm.
- L2/L5 are continuous elsewhere: ≥0.32–0.6 mm of plane beyond every trace edge, apart from M1 and m2.
- Rule set vs JLC/PCBWay: no surcharge triggers. Gaps were closed in Rev E: neck-down 0.10, PTH hole-to-hole 0.45, PTH hole-to-copper 0.30.
- Gerbers: 13 layers with FileFunction attributes, closed outline (56.5 × 40 mm with a notch), metric drill files with separate PTH and NPTH, smallest drill 0.2 mm, all vias tented. CPL matches `kicad-cli pcb export pos`.

### DRC
- KiCad 7.0.11 DRC: 0 errors. The 20 warnings are all library-table or library-mismatch warnings, because the generator strips library silk on purpose.

## Not verified (no primary source available)
- PCI-SIG *PCIe SFF-8639 Module* spec (members only): 3.3Vaux current limit, ACTIVITY# sink/VOL, PWRDIS levels, host loss allocation.
- PCI-SIG OCuLink spec text. PCIe Base 4.0 §4.2.4.4 was quoted from knowledge, not checked against the document.
- PM1735a datasheet: inrush and 12 V peak current. 25 W is from Dell's PM1735 sheet; one HPE page says 15 W.
- Amphenol drawings for PSAS4F213002 and G14A421211112HR (vendor sites blocked; the J2 footprint was checked against Antmicro instead).
- Molex 45558-0003 peg diameter vs the KiCad Ø3.0 hole.
- amazon.de listings (blocked for automated fetching).

## Bring-up checklist
1. With a meter: cable yellow wires → J3 pads 1–3, and pads 1–3 not shorted to GND.
2. Ring out the OCuLink cable (see M7).
3. Power the cage 12 V before the host. Check 3V3_AUX and that CPRSNT# is low.
4. Insert the drive and check `lspci -vv` for LnkSta 16GT/s x4. Watch AER correctable errors under load (`fio`) for an hour.

## Sources
- SNIA SFF-TA-1001 Rev 1.1 — https://members.snia.org/document/dl/26900
- SNIA SFF-9639 Rev 2.2 — https://members.snia.org/document/dl/26887
- SNIA SFF-TA-8639 Rev 2.2 — https://members.snia.org/document/dl/26489
- SNIA SFF-9402 Rev 1.1 — https://members.snia.org/document/dl/27380 (PDF copy: github.com/williamyang98/oculink_m2_adapter)
- SNIA SFF-8611 — https://members.snia.org/document/dl/26704
- Antmicro oculink-pcie-adapter — https://github.com/antmicro/oculink-pcie-adapter
- Amphenol PCIe 4.0 SFF-8639 family datasheet (LCSC copy) — https://datasheet.lcsc.com/datasheet/pdf/529fb16cf5a85091ddea6cda6d075d7e.pdf
- Molex 45558-0003 — https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/455/45558/455580003_sd.pdf
- AMS1117 datasheet — https://files.waveshare.com/upload/b/b8/AMS1117-datasheet.pdf
- JLCPCB capabilities — https://jlcpcb.com/capabilities/pcb-capabilities ; impedance/stackups — https://jlcpcb.com/impedance
- PCBWay capabilities — https://www.pcbway.com/capabilities.html
- PCIe channel budget breakdown (Astera Labs) — https://www.asteralabs.com/resources/blog/pci-express-5-0-architecture-channel-insertion-loss-budget/
- Dell PM1735 spec — https://manualmachine.com/dell/expressflashpm1735/10693912-technical-specifications-and-information
- LCSC parts: C22454449, C5156927, C7545781, C6851473, C55996, C2289, C307331, C14289
