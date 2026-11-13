# Review of all U.3 designs, 2026-11-13

Scope: cage board, x8 card, x16 cards (4 and 3 drives), 4-drive backplane plan, Minisforum notes.
The x8/x16 cards were reviewed at PR #11 commit 9700ca7 and not edited here (their layout thread owns them and
applies these findings as rev E). The cage board was changed here (rev B).

New constraint from Max (2026-11-13): parts may be hand-soldered with hot air and bought from Mouser or Digi-Key,
so one-sided, hot-air-friendly parts are preferred.

How it was checked: pad-by-pad net dumps of the generated boards with `pcbnew` 7.0.11, the DRC reports, the
generator code, and the vendor datasheets for the clock buffer (Renesas 9DBL02x2/04x2 family datasheet rev 1,
Nov 2022), the eFuse (TI TPS25982, SLVSEI3D), the power mux (TI TPS2116, SLVSFG1A) and TI TPS2421 (SLUS907K).
Items marked *unverified* could not be checked against a primary source from this environment.

## 1. Key findings

| # | Sev | Board | Finding | Status |
|---|---|---|---|---|
| K1 | Critical | x8, x16 | 9DBL0442 pin 1 is the tri-level mode pin, not GND. Tied to GND it runs every buffer as a low-bandwidth PLL instead of a fan-out buffer | accepted for rev E |
| K2 | Critical | cage | Rev A still had no AC caps on PER0/PER1 and the board edge under the seated drive | fixed in cage rev B (this PR) |
| K3 | Major | x16 | REFCLK chain is three buffers deep to drive D: 10.2 ns typ / 13.5 ns max against the 12 ns common-clock limit | accepted for rev E |
| K4 | Major | x8, x16 | Card 3.3 V rail takes slot 3.3Vaux first, so the whole rail loads 3.3Vaux in normal operation | accepted for rev E |
| K5 | Major | x8, x16 | eFuse is a circuit breaker with no blanking time: any peak above 3.2 A latches the drive off | accepted for rev E |
| K6 | Major | backplane | Plan leaves SMBus as DNP links and has no power-good gating on PERST#, against Max's "all sidebands wired" rule | sent to the backplane thread |
| K7 | Major | all | Most consumer motherboards do not wire SMBus to the PCIe slots, so the mux/expander features may be unreachable. A 4-pin header on the card bus fixes that for a few cents | proposed (section 7) |
| K8 | Minor | x8, x16 | Hand assembly: two QFNs and the 0.5 mm SOT-583 are the hard parts; the bottom side carries a QFN and 0402s | section 6 |

## 2. Cage board (changed here, rev B)

Rev A on `main` had the HPT0 fix but none of the other findings of `cage-board-review.md`. Rev B (`gen/cage.py`):

| Review item | Rev B |
|---|---|
| C2: no AC caps on drive TX lanes 0/1 | 220 nF 0402 (C11–C14) on PER0/PER1, bottom side, L5 voided under the pads. Nets after the caps are `C_PER0/1_P/N` |
| M8 / C3: board edge at the guide-post tip line, under the seated drive | Edge at 9.4 mm from the peg line (y = 2.35), 0.65 mm short of the housing face. Board is now 56.5 x 37.65 mm |
| M1: 11 mm slot in L2/L5 along the PET via row | Low-speed vias moved to two rows in front of the PET row; extra GND via between PET3 and PET2. Two short slots with a 2.7 mm bridge remain (0.7 mm via pitch inside a 0.5 mm-pitch connector cannot be opened further without staggering the PET vias) |
| M2: PERST# floats without a cable | 100 k pull-down (R6). Isolation of PERST#/REFCLK/SMBus for an unpowered cage is still open |
| M4: F1 without a part | mSMD300-16V, 3 A hold (C6851473) |
| M5: LED that cannot light | KT-0603YG (C2289) |
| m5: 0.12 mm tracks | 0.127 mm |
| m6: 16 V cap on 12 V | 50 V (C307331) |
| m7: AMS1117 at its 15 V limit, not ceramic-stable | SOT-89 LDO: HT7533-1 (C14289, SOT-89-3 confirmed on LCSC) or MCP1703AT-3302E/MB from Mouser/Digi-Key. *Unverified:* the SOT-89 pinout (1 GND, 2 VIN + tab, 3 VOUT) is from memory for both parts; check the datasheets before ordering |

DRC: 0 errors, 0 unconnected pads (library warnings only). One rule was added: the via-to-cap fan on PER0/PER1 may
be up to 1.3 mm apart for up to 6 mm, because 0402 pads sit wider than the pair.

Not done: return vias beside the REFCLK transition (m1; no position keeps 0.5 mm to the clock and 0.4 mm to the
lanes), PET0 length 30.4 mm (m3), unused A1/A21 pads near the NPTHs (m4, footprint), mounting-hole positions (m18),
renders (still rev A). The cabled path still needs a retimer on the host card for full compliance.

Hand assembly: two-sided by construction (OCuLink on the bottom gives crossing-free lanes). The bottom parts are
the OCuLink receptacle (0.5 mm pitch), SOT-89, SOT-23, 0805/1206 and seven 0402s. Solder the bottom first.

## 3. x8 and x16 cards (PR #11, not edited)

### Must fix

1. **9DBL0442 pin 1** (`cardkit.py:103`, `x16.py:466`). Table 1 of the datasheet: pin 1 `HIBW_BYPM_LOBW#`, tri-level,
   biased to VDD/2 internally. Open = bypass (fan-out buffer), low = low-bandwidth PLL, high = high-bandwidth PLL.
   The boards tie it to GND. Leave it open on U1, U40, U41. GND is only pin 8 and the exposed pad. Pins 2/3 are
   `FB_DNC` (connect nothing), 7/16/20/26/30 NC, 32 `SADR_tri` (internal pull-down). The rest of the pin map
   (VDDR 4, VDDA 21, VDDDIG 11, VDDO 15/25, CLK_IN 5/6, DIF 13/14, 17/18, 22/23, 27/28, OE# 12/19/24/29,
   CKPWRGD_PD# 31) matches.
2. **Clock chain depth (x16).** Bypass-mode delay is 2.5 / 3.4 / 4.5 ns per buffer (Table 7). Drive D sits behind
   U1, U40 and U41 and about 340 mm of clock trace, against 170 mm of data trace. That is about 11 ns typical
   and over 14 ns worst case of clock-to-data mismatch; the common-clock limit is 12 ns. Feed U41 from a third
   output of U1 (two stages maximum), or feed all four drives from U1's four outputs. Running the chain in PLL mode
   instead removes the delay but stacks PLL jitter (0.26 typ / 0.48 max ps RMS per stage against 0.5 ps at Gen4).
3. **3.3 V source priority.** TPS2116 pinout is right (1 GND, 2/7 VOUT, 3 VIN1, 4 PR1, 5 MODE, 6 VIN2, 8 ST), but
   VIN1 (priority) is slot 3.3Vaux. In S0 the whole card rail then loads 3.3Vaux: two repeaters at about 40 mA
   each (they are on 3V3_AUX), expanders, switches, LEDs and each drive's E3. The slot limit is 375 mA for a
   wake-enabled card and 20 mA otherwise. Swap the inputs: VIN1, MODE and the PR1 divider on slot 3.3 V, VIN2 on
   3.3Vaux. In standby the mux falls back to 3.3Vaux on its own.
4. **eFuse trip behaviour.** TPS259824O is the circuit-breaker variant. ITIMER (pin 7) is open, which is the
   fastest response, so a short peak above 3.22 A (470 Ω: 1460/R + 0.11) latches the drive off (RETRY_DLY is
   grounded). Add a capacitor footprint on pin 7 (4.7 nF gives about 2 ms from the table values) and use 390 Ω
   (3.85 A). The drive's peak current is not published, so keep the footprint adjustable.

The TPS25982 pin map and both exposed pads (pad 1 IN, pad 2 GND) match Table 5-1. The custom footprint's pad
positions are still not checked against TI's land pattern (the generator says so itself).

### Should fix

5. IMON (pin 9) has 10 kΩ to GND: 2.46 V/A, which clamps at normal load. Use 1 kΩ (0.25 V/A) and a test point.
   The gain is only specified from 3 A up, so it is a rough reading at 2 A.
6. The buffers' SDATA/SCLK are tied straight to 3.3 V. Put them on the card bus instead (addresses 0x6B/0x6C/0x6D
   by the SADR strap). That gives software control of each output and its amplitude for no extra parts.
7. No test points anywhere, and the only headers are the 12 V jumpers. See section 7.
8. Per-drive TCA9543A switches have RESET# on a shared pull-up, so a hung drive SMBus cannot be reset without a
   power cycle. Drive RESET# from a spare expander pin, or see the simplification below.
9. BOM has LCSC numbers only. Add a manufacturer part number column so the same BOM orders at Mouser/Digi-Key.

### Optional simplification

The card has a TCA9548A (8 channels) and one TCA9543A per drive. Putting each drive's SMBus on its own TCA9548A
channel and the expanders on another removes four TSSOP-14, four resistor arrays and eight passives on the 4-drive
card, at the cost of two more trunk lines per drive. Only worth it if the trunk channel has room.

### Still open from the earlier review (known, decided or accepted)

Slot 12 V budget with the slot-default jumpers (Max chose slot default; three or more drives should ship with
jumpers on AUX and the 6-pin fitted), drives C/D at Gen3 on the passive card, drive support (printed holder),
card occupies two slots.

## 4. Backplane plan (PR #7, owned by its own thread)

Sent to the backplane thread: SMBus must be muxed and all sidebands wired (K6), PERST# gated by per-drive
power-good, S15 to GND and caps on PER0/PER1 only, the datasheet facts of section 3, MCP1703 as the
Mouser/Digi-Key equivalent of the HT7533, and a preference for a PTC plus a SOT-23 supervisor over a QFN eFuse.

## 5. Minisforum boards (notes only, no layout yet)

The README is consistent with the review rules (S15 to GND, caps on PER0/PER1, L1-only routing). To add before layout:

- **12 V.** An M.2 slot supplies 3.3 V only. A U.3 drive needs 12 V on P13–P15, up to 25 W for the PM1735a. The
  board needs a 12 V input (the MS-A2 cable, or the MS-01's undocumented "U.2 mode" pins) and should carry the same
  protection as the cards. This is the first thing to measure on the stock adapters.
- **SMBus level.** *Unverified, from memory of the M.2 spec:* M.2 SMBus (pins 40/42) and ALERT# are 1.8 V
  signals, U.3 SMBus is 3.3 V. Wiring them needs a level shifter (PCA9306 class).
- **Sidebands.** PERST# straight through with a pull-down, CLKREQ# tied low, PWRDIS pulled down, DualPortEn#
  pulled up, 3.3Vaux (E3) from the slot's 3.3 V, activity LED.

## 6. Hand assembly and sourcing

| Part | Package | Hot air | Note |
|---|---|---|---|
| TPS259824ONRGER eFuse | VQFN-24, 0.5 mm, split pad | hard | Paste and preheat needed; pads are hidden. Leaded alternative: TPS2421-1 (HSOP-8 PowerPAD, 3–20 V, PG and FLT outputs, current limit by one resistor). Its PG is active low, so the reset gate would change |
| 9DBL0442BKILF buffer | VFQFPN-32, 0.5 mm | hard | One on the bottom of every card. No leaded Gen4 buffer was found; keep it, but move it to the top if routing allows so the bottom has no fine-pitch part |
| TPS2116DRLR | SOT-583, 0.5 mm | medium | Fine with paste |
| TCA95xx TSSOP, SC-70 gates, arrays | 0.65 mm | easy | |
| 0402 passives | | medium | 50 on the x8, 94 on the 4-drive x16. Too many to place by hand comfortably |
| U.3 receptacle, Mini-Fit, 1206 bulk | | easy | |

Recommendation: let the fab assemble the top side (all the small parts; every one except the receptacle, eFuse,
buffer and locate LED had LCSC stock on 2026-11-13) and hand-solder the bottom: receptacles, bulk caps, the four or
eight 0402 AC caps and the buffer. That needs one stencil and one assembly side. Parts JLC cannot source
(receptacle, and the eFuse and buffer while LCSC is out) come from Mouser or Digi-Key by manufacturer part number.

## 7. Features that cost almost nothing

Ranked by value for the price. Costs are parts per card at small quantity, rough.

| # | Feature | Cost | Value |
|---|---|---|---|
| 1 | 4-pin header on the card-local I2C bus (3V3_AUX, SCL, SDA, GND) | 0.05–0.30 USD | High. Consumer boards rarely wire slot SMBus, so without it PWRDIS, locate LEDs, presence and the clock buffer are unreachable. With it a USB-I2C dongle or an ESP32 can run them |
| 2 | Test points: 12V_DRV, 3V3_AUX, PERST#, PG and IMON per drive, GND loops | 0 | High for bring-up; IMON gives a rough per-drive current reading with a multimeter |
| 3 | Fault LED per drive on the eFuse power-good (lit when a drive is powered, dark when tripped) | 0.05 per drive | High. Shows at a glance which drive tripped or has no 12 V |
| 4 | 4-pin PWM fan header fed from the card's 12 V, PWM pulled high, tach to a test point | 0.30 | High. The thermal study needs a 92x38 fan on the shroud; this powers it at the card |
| 5 | Extra M3 holes for the printed shroud, drive cradle and a far-end card support | 0 | High. The drives hang on SMT receptacles and the 312 mm card sags |
| 6 | Supply LEDs: slot 12 V, aux 12 V, 3.3 V | 0.10 | Medium |
| 7 | Clock buffer on the card bus (item 6 of section 3) | 0 | Medium. Unused outputs off, amplitude tuning |
| 8 | TVS on the aux 12 V input (SMBJ15A) | 0.10 | Medium. Protects against a hot-plugged PSU cable |
| 9 | Silkscreen: I2C address table, jumper legend, pin 1 marks, repo link | 0 | Medium |
| 10 | ID EEPROM at 0x50 on the card bus (24C02) | 0.10 | Low to medium. Board revision and serial readable in software |
| 11 | Temperature sensor per drive bay (TMP1075 or LM75B class) | 0.50 per drive | Low to medium. NVMe SMART already reports drive temperature; this adds air temperature for fan control |
| 12 | Fan controller on the card bus (EMC2101 class) instead of the plain header | 1.50–2.00 | Medium, only if nothing else controls the fan |
| 13 | Accurate per-drive power monitor (INA3221: 3 channels, VQFN-16, 0–26 V, plus shunts) | 2–3 | Low. The eFuse IMON pin already gives a rough value, and the part is another QFN |

Items 1–10 together add under 1 USD per card and no hard-to-solder part.

## Sources

- Renesas 9DBL02x2/04x2/06x1/08x1 family datasheet, rev 1: https://www.renesas.com/en/document/dst/9dbl02x2-04x2-06x1-08x1-family-datasheet
- TI TPS25982: https://www.ti.com/lit/ds/symlink/tps25982.pdf
- TI TPS2116: https://www.ti.com/lit/ds/symlink/tps2116.pdf
- TI TPS2421: https://www.ti.com/lit/ds/symlink/tps2421-1.pdf
- TI INA3221: https://www.ti.com/lit/ds/symlink/ina3221.pdf
- LCSC C14289 (HT7533-1, SOT-89-3): https://www.lcsc.com/product-detail/C14289.html
- Earlier reviews: `cage-board-review.md`, `slot-cards-review.md` (PR #6)
