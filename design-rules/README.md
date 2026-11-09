# PCIe 4.0 + JLCPCB / PCBWay design rules (Rev E, 2026-11-09)

Shared rule set for every board in the U.3 adapter project:

- the x16 card (4 drives) and x8 card (2 drives)
- the OCuLink-to-U.3 device board for the cage
- the MS-01 / MS-A2 M.2-slot board

All numbers that the fab tunes to come from JLCPCB's own impedance calculator, read on 2026-11-09. A 2D field solver cross-checks them (see `si/`).

## 1. Files

| File | What it is |
|---|---|
| `pcie4_jlc_pcbway.kicad_dru` | Custom DRC rules: fab limits, PCIe 85 Ω, REFCLK 100 Ω, finger zone, neck-downs. Tested on KiCad 7.0.11; also loads on 8/9. |
| `pair_skew_kicad8.kicad_dru` | One-rule intra-pair skew check (KiCad 8/9 only, because it uses `within_diff_pairs`). |
| `gen_pair_skew_rules.py` | KiCad 7: generates one skew rule per diff pair from a board. Append its output to the `.kicad_dru`. |
| `templates/<stackup>/` | Empty boards with the exact JLC stackup in Board Setup, plus net classes, patterns and rules in the `.kicad_pro`. Import them with **Board Setup → Import Settings**, or copy all 3 files and rename. |
| `stackups.csv`, `impedance.csv` | Stackup layer tables and trace geometry, with the source of each number. |
| `si/` | 2D finite-difference impedance solver and the scans behind the numbers. |
| `make_templates.py` | Regenerates the templates. |

Required net classes (the template `.kicad_pro` assigns them by pattern):

- `PCIe_85`: `*PET?_?`, `*PER?_?`, `*PET1?_?`, `*PER1?_?`, `*TX?_?`, `*RX?_?`, `*TX1?_?`, `*RX1?_?`. Name pairs like `PET0_P` / `PER12_N`. KiCad 7 patterns are plain `*`/`?` wildcards with no `[...]` classes, and they are not anchored, so `*PER??_?` would catch `PERST_N`. Rev C patterns pass a pcbnew self-test in `make_templates.py`: PET0/PER15/U3_TX0 resolve to PCIe_85, and PERST_N/PERST1_N/PCIE_RST_N to Default.
- `REFCLK_100`: `*REFCLK*`
- `PWR_12V`, `PWR_3V3`, `GND`, `LowSpeed`

Required rule areas (draw as a Rule Area with no keepouts set, and name it exactly):

- `FINGERS` over the gold-finger zone including the bevel
- `NECKDOWN_xx` over each connector pin field where pairs have to narrow (OCuLink, U.3 receptacle, finger pads)

## 2. Stackups (all use JLC 3313 outer prepreg)

| Board | JLC stackup | Finished | Layer use |
|---|---|---|---|
| x16 / x8 cards, OCuLink device board | **JLC06161H-3313**, 6L 1.6 mm | 1.54 mm Cu+dielectric, ~1.58 mm with mask | L1 PCIe/REFCLK · L2 GND · L3 low-speed + 3V3 (GND pour under fingers) · L4 12V · L5 GND · L6 PCIe/REFCLK |
| simple device board (if 4L) | JLC04161H-3313, 4L 1.6 mm | 1.56 mm | L1 PCIe · L2 GND · L3 PWR/GND · L4 low-speed |
| MS-01/MS-A2 M.2 board | **JLC04081H-3313**, 4L 0.8 mm | 0.80 mm (+mask) | L1 PCIe (all M.2 PCIe pins are top-side) · L2 GND · L3 GND/PWR · L4 low-speed |

The 6L-3313 layer layout is L1 / 3313 0.0994 / L2 / core 0.55 / L3 / 2116 0.1088 / L4 / core 0.55 / L5 / 3313 0.0994 / L6. Dk: 3313 = 4.1, 2116 = 4.16, core = 4.6. Laminate is Nan Ya NP-155F (Tg 150). Outer copper is 1 oz and inner is 0.5 oz.

**Do not use JLC06161H-2116 for PCIe.** Its outer dielectric is 0.223 mm, which makes 85 Ω pairs 0.30 mm wide, and those do not neck into 0.5 mm-pitch OCuLink pads cleanly.

**Why L4 = 12V and L5 = GND:** L6 high-speed must reference GND, so L5 is GND. L3 sits 0.109 mm from L4 but 0.55 mm from L2, so a stripline on L3 would reference L4 (power). L3 is therefore not used for PCIe or REFCLK.

## 3. Trace geometry (JLC calculator, outer layer over adjacent GND, 3313)

| Net class | Width | Gap | Notes |
|---|---|---|---|
| PCIe_85 (85 Ω diff) | **0.157 mm (6.19 mil)** | **0.152 mm (6 mil)** | JLC's calculator value, which is what the fab tunes to under impedance control. Our 2D solver (si/) gives 89–91 Ω for this geometry; the difference is the soldermask and etch model. Keep JLC's numbers, because the fab adjusts the width to hit 85 Ω on its coupon. PCBWay also tunes width to its own model, so give them the target impedance, not just the width. |
| REFCLK_100 (100 Ω diff) | **0.128 mm (5.03 mil)** | **0.254 mm (10 mil)** | JLC calculator; our solver gives ~107 Ω, still within the HCSL tolerance. 100 Ω matches CEM/HCSL. 85 Ω is also acceptable if the clock buffer has 85 Ω internal terminations. |
| 50 Ω single-ended | 0.151 mm | – | for reference only |
| Neck-down inside `NECKDOWN_*` areas | ≥ 0.10 mm | ≥ 0.10 mm (Rev E: PCBWay minimum) | keep each neck-down ≤ 2.5 mm long |

Order with **Impedance control = Yes** and the stackup set explicitly. JLC tolerance is ±10%. The PCIe CEM limit for 16 GT/s is 85 Ω ±15%, so JLC's tolerance fits inside it.

## 4. Fab limits encoded in the DRU (pass at JLC multilayer AND PCBWay standard)

| Item | Rule | JLC limit | PCBWay limit |
|---|---|---|---|
| Track / space | ≥ 0.10 / 0.10 mm everywhere | 0.09 / 0.09 | 0.10 / 0.10 |
| PCIe signal via | 0.25 drill / 0.55 pad (Rev D; rule allows 0.25–0.30 / 0.55–0.60) | 0.15/0.25 abs, 0.20 recommended on impedance boards | 0.15 min drill, 0.15 annular |
| Generic via | ≥ 0.20 drill, ≥ 0.15 annular (0.2/0.5) | ok | ok (0.15 annular) |
| PTH annular | ≥ 0.15 mm | 0.15 abs / 0.20 rec | 0.15 |
| Hole to hole | vias ≥ 0.25 mm; PTH pad holes ≥ 0.45 mm (Rev E) | via 0.20, PTH pad 0.45 | – |
| Copper to hole | vias and NPTH ≥ 0.20 mm; PTH pads ≥ 0.30 mm (Rev E) | via–track 0.20, PTH–track 0.28 (0.35 rec), inner PTH 0.30, NPTH 0.20 | – |
| Copper to edge | ≥ 0.30 mm (0 inside FINGERS) | 0.20 | 0.20 |
| Soldermask web | ≥ 0.10 mm, expansion 0 (JLC LDI is 1:1) | 0.10 green | – |
| Silk | ≥ 1.0 mm text height, ≥ 0.15 mm line | 1.0 / 0.15 | – |

## 5. PCIe 4.0 electrical rules

**Loss budget at 8 GHz (Nyquist of 16 GT/s), Rev E (conservative).** The total channel budget is 28 dB bump to bump. CEM 4.0 splits it as root package 5.0, system board 13.5, CEM connector 1.5 and add-in card 8.0 dB (Astera Labs' summary of the CEM table). There is no separate endpoint-package line, so the 8.0 dB AIC figure must **include the endpoint package**. Our passive hardware sits in front of the drive, and the drive's package plus internal routing must also fit in that 8.0 dB. PM1735 internals are unpublished, so we assume ~4 dB for them. That leaves **≤ 4.0 dB for our hardware**. Rev D said 6 dB, which assumed the package was excluded. FR4 loss is budgeted at **1.25 dB/in (0.05 dB/mm)** at 8 GHz, the middle of 1.1–1.4 dB/in for NP-155F (Df ≈ 0.02) with standard copper roughness.

| Topology | Allocation | Rule |
|---|---|---|
| Direct-attach (x16/x8 card with onboard U.3) | fingers + breakout 0.3, 2 vias 0.2, U.3 receptacle 1.0 = 1.5 → **copper ≤ 2.5 dB ≈ 50 mm** | **Hard max 50 mm finger edge to U.3 pin, per lane (DRU length cap 50.8 mm).** Lanes that cannot meet this, e.g. a stacked deck with an extra connector, need a retimer for compliance. |
| Cabled, passive (x16 card → OCuLink → device board → U.3) | 2 mated OCuLink 1.0, U.3 1.0, vias 0.3 = 2.3 → only **1.7 dB for both boards' copper plus the cable** (e.g. 20 mm copper total plus ~15 cm cable) | **Not practical as a compliant design: a retimer is required** (§9). A passive link will very likely still train at Gen4, but cannot be claimed compliant. |

To gain margin, have PCBWay build the cabled boards in mid-loss laminate (e.g. IT-170GRA or FR408HR, ~0.5 dB/in). That roughly doubles the allowed trace length.

**Impedance and routing**

- PCIe data routes only on L1/L6 (DRU enforces this). Each net gets at most 2 vias, one L1↔L6 transition (DRU enforces this). An L1↔L6 through via has no stub, so **no backdrill is needed**. JLC does offer backdrill: 4–32 layers, ≥ 0.8 mm thick, back-drill +0.2 mm, ≥ 0.15 mm dielectric left. We don't need it.
- Every signal via gets a GND return via with **centre-to-centre distance ≤ 1.0 mm** (edge-to-edge ≥ 0.25 mm for drilling), 2 per pair, placed symmetrically, to carry the return from L2 to L5. Plane antipad is Ø 0.95 mm on all layers (DRU: 0.20 zone clearance around the 0.55 pad, plus 0.325 hole clearance). A shared oval antipad per pair is fine. Via-pair pitch is 0.8–1.0 mm.
- Pair-to-pair and pair-to-other-net spacing is ≥ 0.40 mm (≈ 4h, in the DRU). TX and RX groups should sit ≥ 0.6 mm apart or have a GND pour with stitching between them. Keep PCIe ≥ 1 mm from the board edge, except at fingers and connectors.
- Never cross a plane split, antipad field or slot. Keep the reference plane ≥ 3w beyond each trace edge.
- Uncoupled length is ≤ 2.5 mm (DRU), for pin escapes only.
- Corners are 45° or arcs, never 90°. Glass weave: 3313/2116 are fairly open weaves, so run any straight segment longer than 25 mm at 5–10° off the board axis or with a gentle zig-zag.
- P/N polarity inversion within a pair is allowed (link training corrects it), so use it to avoid crossovers. Do not rely on lane reversal on bifurcated x4 ports.

**Skew**

- Intra-pair skew ≤ 0.127 mm (5 mil) per pair, including PCB via length. Board Setup has "use stackup height" on. Correct it within 3 mm of where the mismatch arises, with small bumps (height ≤ 2× gap, length ≥ 3× width), not with serpentines at the far end.
- Lane-to-lane skew needs no matching, because PCIe deskews. Keep lanes of one port within 25 mm of each other as a sanity limit.
- REFCLK intra-pair ≤ 0.127 mm.

**AC coupling.** These boards take **no AC caps**. The host TX caps are on the motherboard, and SFF-8639/U.3 drives carry their own TX caps. A second series cap only adds a discontinuity. If a redriver, retimer or switch is ever added, put 220 nF 0201/0402 caps (allowed range 176–265 nF) on its TX side, with a GND void under the pads on L2.

**REFCLK.** The CEM slot gives one 100 MHz REFCLK. With x4x4x4x4 bifurcation each drive needs its own, so use a PCIe Gen4-rated LP-HCSL fan-out buffer with internal terminations matched to the trace impedance (e.g. a 9DBL4xx-class part), placed close to the fingers. Common-clock mode is assumed; do not rely on SRIS. OCuLink cables carry REFCLK, so route it on the host card into the OCuLink connector the same way as the data pairs.

**Power: aux 12V is an optional fit (per Max, 2026-11-09).** Lay out the aux 12V connector (PCIe 6-pin or SATA) as a DNP option. Slot 12V and aux 12V must never be tied directly together. OR them through an ideal-diode/eFuse, or select with a solder jumper (default: slot), so an unpopulated or unplugged aux input is safe. Slot limits are 66 W on 12V (5.5 A) and 10 W on 3V3. Without aux, the 4-drive config only fits if total drive draw stays ≤ 5.5 A at 12V, e.g. with the drives' power-state limit set via `nvme set-feature -f 2`. The 2-drive config fits on slot power.

**Documented exceptions (per-net DRU overrides are allowed when listed here)**

| Board | Net | Exception | Justification |
|---|---|---|---|
| OCuLink→U.3 cage board | PET0 pair | length ~30 mm (vs 25 mm guideline); `diff_pair_uncoupled` ≤ 7 mm | U.3 lane 0 sits on the front pin row. The extra 5 mm is ≈ 0.2 dB and fits the per-link rule. Uncoupled length comes from bump flanks (5 × 0.24 mm bumps, gap 0.39 mm, inside NECKDOWN_J1) that correct 1.04 mm of corner skew down to 0.023 mm, which is electrically better than leaving the skew in. |
| OCuLink→U.3 cage board | J2 locating NPTHs | NPTH to no-net corner pads A1/A21 at 0.11–0.13 mm | manufacturer land pattern; the pads carry no signal |

Write each override as its own rule at the end of the board's `.kicad_dru`, with a condition naming the exact nets or pads, never a whole net class.

## 6. Connectors and edge fingers

- **CEM x16/x8 edge.** Use KiCad's `Connector_PCBEdge:BUS_PCIexpress_x16` / `_x8` pad pattern (0.70 mm pads on 1.0 mm pitch).
  - Void **L2 under the finger pads**, and keep a solid **GND pour on L3** under the whole finger zone. The solver gives ~94 Ω diff with the void and 39 Ω without it; adjacent GND fingers pull it toward 85–90 Ω.
  - No vias and no other copper inside `FINGERS`. Bevel both faces.
  - Board thickness spec is 1.57 ± 0.13 mm. JLC's 6L-3313 nominal is ~1.58 mm, but JLC's stated tolerance is ±10% (±0.16 mm), which is wider than CEM.
- **M.2 edge (MS-01/MS-A2 board).** 0.8 ± 0.08 mm thick, on JLC04081H-3313 (nominal 0.80 mm; JLC tolerance is ±0.1 mm). Void L2 under the PCIe finger pads, with GND on L3 (solver: ~105 Ω with the void, 63 Ω without, lower with GND neighbours). Bevel, hard gold, and no copper within 0.5 mm of the bevel line except the fingers.
- **U.3 receptacle (SFF-8639 / SFF-TA-1001 wiring), OCuLink (0.5 mm pitch) and MCIO/SlimSAS.**
  - Put a `NECKDOWN_*` area over the pin field and enter each pad straight, with matched P/N geometry.
  - Place GND vias next to each GND pin of the receptacle.
  - For SMT pads wider than 0.40 mm, consider a partial L2 void under the pad. Only do this if L3 is GND there, and check it with `si/zcalc.py`.

## 7. Fabrication choice and compliance gaps

| Requirement | JLCPCB | PCBWay |
|---|---|---|
| Hard-gold fingers (CEM/M.2 expect electroplated hard gold over Ni) | **No.** Gold fingers only come with ENIG (soft immersion gold, ~1–3 µin) | **Yes.** Electroplated Ni/Au, 3–50 µin |
| Finger bevel | 30° or 45°; board ≥ 50 × 50 mm; no bevel on V-cut panels | 20°/30°/45°/60° |
| Impedance control | ±10%, fixed stackups listed above | yes, custom stackup |
| Low-loss laminate | No (NP-155F FR4 only) | IT-170GRA, FR408HR, S1000-2M, Megtron-class, Rogers |
| Backdrill | yes | yes (+0.1 mm, depth ±0.1 mm) |
| Assembly with LCSC parts | yes (native) | yes, but parts are sourced separately |

**Decision (Max, 2026-11-09): design for both fabs and pick on price at the end.** Every rule in this set passes both fabs: Rev D raised via annular to 0.15 mm for PCBWay. One set of Gerbers serves both. Only the order options differ:

| Order option | JLCPCB | PCBWay |
|---|---|---|
| Stackup / impedance | JLC06161H-3313 (or JLC04081H-3313 for M.2), impedance control on | same stackup in the notes, ±10%, 85 Ω / 100 Ω coupons |
| Finish | ENIG | ENIG + hard-gold fingers 30 µin |
| Gold fingers | yes, 30° bevel | yes, 20° or 30° bevel |
| Thickness | 1.6 mm (6L) / 0.8 mm (M.2) | same, ask for ±0.13 / ±0.08 mm |
| Vias | tented / epoxy-filled as offered | tented |

Compliance difference: only the PCBWay finger finish meets the CEM/M.2 hard-gold expectation. JLC's ENIG fingers work but wear faster. Max (2026-11-09): the cards are inserted once and not replugged, so ENIG wear is accepted and JLC fingers are acceptable. Boards without fingers are compliant at either fab.

## 8. Verification before ordering

1. DRC is clean with this `.kicad_dru` plus the generated skew rules.
2. Measure every PCIe net length and add up the loss budget per topology (section 5).
3. Check that the stackup in Board Setup matches the chosen JLC stackup name, and enter that name in the order notes.
4. After assembly: `lspci -vv` shows `LnkSta: Speed 16GT/s, Width x4` for each drive, and the AER correctable-error counters stay at zero during a 30-minute `fio` run. This is the practical stand-in for a PCI-SIG compliance test.

Sources:
- JLCPCB impedance stackups, https://jlcpcb.com/impedance
- JLCPCB impedance calculator, https://jlcpcb.com/pcb-impedance-calculator
- JLCPCB capabilities, https://jlcpcb.com/capabilities/PCB-capabilities
- JLCPCB back-drill, https://jlcpcb.com/help/article/back-drill-process
- JLCPCB gold fingers, https://jlcpcb.com/help/article/jlcpcb-gold-fingers
- PCBWay capabilities and gold fingers, https://www.pcbway.com/capabilities.html and https://www.pcbway.com/pcb_prototype/PCB_Gold_fingers.html
- PCIe CEM 4.0 loss split, https://www.asteralabs.com/resources/blog/pci-express-5-0-architecture-channel-insertion-loss-budget/

To check against the PCI-SIG documents themselves: the CEM bevel angle and finger plating thickness, and the exact AIC budget reference points. This rule set treats the 8.0 dB AIC figure as finger to device pins, excluding the package.

## 9. Cabled path: when is a retimer required? (Rev E, 2026-11-09)

Under the conservative budget in §5 (≤ 4.0 dB for our hardware), the cabled topology's fixed parts already use 2.3 dB: two mated OCuLink connectors, the U.3 receptacle and vias. That leaves 1.7 dB for both boards' copper plus the cable, which is less than any useful cage cable.

Cable loss figures are typical twinax values, not measured on a specific cable. Consumer OCuLink cables are often 32–34 AWG.

| Cable | ~IL at 8 GHz | Passive link total (incl. 40 mm copper, 2.0 dB) | vs 4.0 dB |
|---|---|---|---|
| 0.25 m, 30 AWG | ~1.1 dB | 5.4 dB | −1.4 |
| 0.5 m, 30 AWG | ~2.3 dB | 6.6 dB | −2.6 |
| 0.5 m, 34 AWG | ~3.8 dB | 8.1 dB | −4.1 |

**Conclusion: for a fully compliant cabled design, a retimer is mandatory at any realistic cable length.** Put it on the x16 host card next to the fingers.

- A retimer is the only spec-defined fix. It splits the link into two channels, and each gets its own full 28 dB budget. The drive-side segment then has ~17 dB for traces, cable and connectors (28 dB minus ~3 dB retimer package minus ~8 dB drive), which allows 1 m+ cables.
- Redrivers are not defined by the PCIe spec, so a redriver design cannot be claimed compliant even when it works.
- Candidate: TI DS160PT801 (Gen4 x8, two per x16; LCSC availability not checked). It needs its own REFCLK, SMBus/EEPROM config, 0.9/1.8 V rails and BGA fan-out (the part's layout guide decides whether 6 layers are enough).
- Without a retimer, a 0.25–0.5 m passive link will very likely still train at Gen4. Host boards rarely use their full 13.5 dB, and Gen4 receivers (CTLE + DFE) have margin. It is a working build, not a compliant one.
- Direct-attach cards need no retimer when every lane is ≤ 50 mm (§5).

**How far "full validation" can go**

1. Budget analysis (this doc), with the conservative interpretation of the CEM AIC allocation.
2. Channel simulation with S-parameter models: Amphenol OCuLink and U.3 receptacle models (usually on request), the cable model, and our traces extracted from the stackup. Run them through a PCIe Gen4 statistical eye tool (PCI-SIG Seasim, which needs membership, or open-source PyBERT).
3. Post-build: **PCIe 4.0 Lane Margining at the Receiver** (mandatory on Gen4 ports) gives real per-lane eye margin. Combine it with `LnkSta 16GT/s x4` and zero AER errors under `fio`.
4. The formal PCI-SIG compliance test (CBB/CLB fixtures and a scope) is lab-only.
5. Not settled: the PCIe SFF-8639 Module spec's own host-side allocation at the drive connector. If it grants the host more than the CEM AIC split implies, §5 can be relaxed. It needs the PCI-SIG document.
