# Design decisions: every choice, its reason and the alternatives

Date: 2026-11-13. Covers the OCuLink cage board, the x8 card, the x16 cards (3 and 4 drives), the
4-drive backplane plan and the Minisforum boards.

Each record says what was chosen, why, which alternatives were looked at, and a verdict:

- **Keep**: the choice holds.
- **Change**: the review recommends a different choice (who does it is named).
- **Open**: needs a fact or a decision from Max before it can be closed.

Availability and prices are from the cost thread's `docs/fab-cost-options.md` (PR #13) and the fab
quotes in `docs/fab-quotes.md` (PR #11), both read on 2026-11-13. Pin and electrical facts marked
"datasheet" were read from the vendor datasheet during the 2026-11-13 review
([`reviews/full-review-2026-11-13.md`](reviews/full-review-2026-11-13.md)). Anything marked
"from memory" was not checked against a datasheet and must be checked before it is relied on.
Section 12 collects those.

Board state this was written against: cage rev B (PR #12), x8 rev D and x16 rev C (PR #11), with
the rev E changes that the layout thread has accepted but not yet pushed.

## Summary: choices the review changes or leaves open

| # | Choice today | Verdict | What to do |
| --- | --- | --- | --- |
| D2 | REFCLK buffer 9DBL0442**B**KILF | **Change**, part is obsolete | Order the C revision if it can be had, otherwise buy the 100 remaining B parts; check PI6CB33401 pin by pin before trusting it as a drop-in |
| D3 | Buffer pin 1 tied to GND (PLL mode) | **Change** (accepted for rev E) | Pin 1 open = fan-out mode on the first two stages |
| E1 | eFuse TPS259824ONRGER | **Open**, out of stock at Mouser and Digi-Key until Feb 2027 | Buy from LCSC "other suppliers" now, or take TPS259827ONRGER (no overvoltage cut-off, same footprint) |
| E2 | eFuse RILIM 470R, no ITIMER cap | **Change** (accepted for rev E) | 390R and 4.7 nF |
| E3 | TPS2116 priority on slot 3.3Vaux | **Change** (accepted for rev E) | Priority on slot 3.3 V main, 3.3Vaux as fallback |
| C1 | U.3 receptacle PSAS4F2130021TR | **Open**, 16 pieces at LCSC, none at Mouser or Digi-Key | Buy the LCSC stock now for the first build, or re-footprint for PSAS4F2130201TR |
| I3 | Cage LDO AMS1117 | **Changed** in cage rev B to HT7533-1 / MCP1703A in SOT-89 | Check the SOT-89 pinout before ordering (section 12) |
| F7 | Yellow locate LED C72038 | **Change**, 0 stock | XL-1608UYC-06 (C965802) |
| B4 | 0.2 mm generic vias | **Open** | 0.3 mm saves about $19 to $25 per order if the layout allows it |
| G5 | 0402 passives on both sides | **Open** | 0603 and one-sided where there is room, if Max solders by hand |

---

## 1. Architecture

### A1. Passive boards with true U.3 wiring

- **Choice:** boards that wire the PCIe slot straight to SFF-TA-1001 (U.3) receptacles, with no
  controller in the data path.
- **Why:** the HPE P50230-B21 (PM1735a) has no U.2 fallback. U.2-wired adapters do not initialize it,
  and no passive multi-drive U.3-wired card is sold. A passive board adds no driver, firmware or heat,
  and the drive appears as a plain NVMe device.

| Alternative | For | Against | Availability |
| --- | --- | --- | --- |
| Tri-mode HBA (Broadcom 95xx/96xx) | native multi-drive U.3, hot-plug, works today | not passive, the drives sit behind the HBA's firmware and driver, 15 to 25 W more heat, expensive | sold, used market |
| Single-drive U.3 cards (Cablecc, StarTech PEX4SFF8639U3, Ableconn PEXU3-132) | known to work with these drives, no design risk | one slot per drive | sold |
| U.2 multi-drive cards and cables | cheap, many | do not work with these drives | sold |
| PCIe switch card (Switchtec, PEX) | no bifurcation needed, any slot | BGA, firmware, $100+ per chip, heat | chips hard to buy in small numbers |

- **Verdict: Keep.** The single-drive Cablecc card stays the known-good reference for buzzing out the pin map.

### A2. Drives directly on the card, standing upright

- **Choice:** on the x8 and x16 cards the receptacles sit on the bottom side, so the drives stand
  upright with their connectors toward the motherboard.
- **Why:** it is the only arrangement that keeps the lanes short. Direct attach gives 2.5 dB of copper
  (about 50 mm per lane), and a cable would use the whole budget on its own (design rules, section 9).
  Mirrored receptacles on the bottom also keep the lane order free of crossings, so each lane needs
  one layer change at most.

| Alternative | For | Against |
| --- | --- | --- |
| Drives lying flat along the card | lower build | 100 mm of drive along the card per drive, lanes far over 50 mm, blocks the next slots just as much |
| Cabled drives (OCuLink or SlimSAS to a cage) | drives sit anywhere, easy cooling | not compliant without a retimer, cable quality varies, cables cost $15 to $40 each |
| Receptacles on the top side | parts and drives on one side for assembly | lane order reverses, every lane crosses another, more vias |

- **Verdict: Keep** for 2 drives. For 3 and 4 drives see A3.

### A3. Three card variants, and Gen3 on the far drives

- **Choice:** x8 card with 2 drives (190 mm), x16 card with 3 drives (239 mm), x16 card with 4 drives
  (312 mm). On the x16 cards drive C (about 110 mm of lane) and drive D (about 170 mm) are past the
  Gen4 budget and are labelled "PCIe Gen3 only".
- **Why:** four upright drives need 4 x 73 mm, so the far drives cannot be within 50 mm of the
  fingers. Gen3 at 8 GT/s has about half the loss per millimetre and a 22 dB budget, so these lanes
  are comfortable there, and a PM1735a at Gen3 x4 still does about 3.5 GB/s.

| Alternative | For | Against | Availability |
| --- | --- | --- | --- |
| Retimer on lanes 8 to 15 (planned 4th board) | Gen4 on all four, compliant | DS160PT801 is a 332-ball BGA, needs 0.9 V and 1.8 V rails, EEPROM config, about $40 per chip, not hot-air friendly | TI, stock not checked |
| Linear redriver (DS160PR810 class, QFN) | cheaper, hand-solderable | not defined by the PCIe spec, tuning needed, cannot be called compliant | TI, stock not checked |
| Low-loss laminate at PCBWay (IT-170GRA, FR408HR) | roughly doubles the allowed length, so drive C reaches Gen4 | PCBWay costs about 1.9x JLC before the laminate surcharge; drive D still too far | on quote |
| Two x8 cards instead of one x16 card | every drive within 50 mm, all Gen4, fully passive | needs two slots that bifurcate x4x4 | the x8 card exists |
| Leave C and D to train at Gen4 on their own | free | drive C may work, D will very likely fall back or throw errors; unknown until measured | |

- **Verdict: Keep,** and state it plainly: for four drives at Gen4 without a retimer, two x8 cards are
  the better build. The x16 passive card is the one-slot option that accepts Gen3 on two drives. After
  assembly, lane margining on drive C will show whether Gen4 holds there.

### A4. Host bifurcation, no switch

- **Choice:** the slot is set to x4x4 (x8 card) or x4x4x4x4 (x16 card) in the BIOS.
- **Why:** keeps the boards passive. The 3-drive card also works at x8x4x4 since lanes 12 to 15 are unused.
- **Alternative:** a PCIe switch removes the BIOS requirement, at the cost named in A1.
- **Verdict: Keep.** Requirement to check per motherboard: the slot must offer the bifurcation mode.

### A5. Boards generated by Python on KiCad 7

- **Choice:** every board is produced by a script (`gen/*.py`) through `pcbnew`; nobody edits a board by hand.
- **Why:** the three slot cards share one sideband block, one card kit and one rule set, so a fix lands on
  all boards at once, and every revision is reproducible and reviewable as a diff.
- **Against:** no schematic file, so the netlist lives in the scripts and a human reviewer has to read
  code. Placement changes are slower than dragging parts.
- **Alternative:** hand layout in KiCad with a schematic. Easier for a one-off, harder to keep four boards in step.
- **Verdict: Keep.** Worth adding later: a generated netlist or schematic PDF per board for review.

---

## 2. Stackup, routing rules and fabrication

### B1. Six layers, JLC06161H-3313, 1.6 mm

- **Choice:** 6 layers on JLC's 3313 stackup for all slot cards and the cage board.
- **Why:** the 0.099 mm outer prepreg gives an 85 ohm pair at 0.157/0.152 mm, which necks into
  0.5 mm-pitch pads. Six layers give two high-speed layers that each have their own ground plane, a
  full 12 V plane and a layer for the sideband trunks.

| Alternative | For | Against | Price (JLC, x8 card, 5 pcs) |
| --- | --- | --- | --- |
| 4 layers, JLC04161H-3313 | fewer layers | not cheaper at JLC for this board size, loses the 12 V plane or the trunk layer, L4 high-speed would sit over power | about the same |
| 6 layers, JLC06161H-2116 | same price | 85 ohm pairs become 0.30 mm wide and do not neck into the connectors | same |
| 8 layers | stripline lanes, more shielding | about +$150, striplines need backdrill or more vias, no benefit at these lengths | about +$150 |
| Mid-loss laminate (PCBWay only) | half the loss | price, see A3 | PCBWay about 1.9x JLC plus surcharge |

- **Verdict: Keep.**

### B2. Layer use: L1 lanes, L2 GND, L3 low-speed, L4 12 V, L5 GND, L6 lanes

- **Why:** L6 must reference ground, so L5 is ground. L3 is 0.109 mm from L4 and 0.55 mm from L2, so
  anything on L3 references the 12 V plane. That is fine for SMBus and resets and wrong for PCIe, so
  L3 carries only low-speed nets.
- **Alternative:** L3 GND and L4 split power/signal gives a third ground plane but no trunk layer.
- **Verdict: Keep.**

### B3. Lanes only on L1 and L6, at most two vias, no backdrill

- **Why:** a through via from L1 to L6 has no stub, so no backdrill is needed. Two vias cost about 0.2 dB.
- **Alternative:** inner striplines with backdrill: better isolation, about $30 to $60 more per order
  and a tighter fab process.
- **Verdict: Keep.**

### B4. Via sizes: 0.25/0.55 mm on lanes, 0.20/0.50 mm elsewhere

- **Why:** small via pads fit between the 0.8 to 1.0 mm via-pair pitch and keep antipads small.
- **Alternative:** 0.30 mm drills everywhere. JLC charges about $19 for 0.2 mm vias, and the cost thread
  measured $19 to $25 saved per order with 0.3 mm. The rule set already allows 0.25 to 0.30 mm on lanes.
- **Verdict: Open.** Worth doing in the sideband blocks if the maze router still closes with 0.3/0.6 mm
  vias. It is a layout-thread job because it touches `router.py`.

### B5. 85 ohm lanes, 100 ohm REFCLK

- **Why:** CEM add-in cards are 85 ohm. The 9DBL0442 has 100 ohm terminations built in (datasheet), so
  the clock pairs are 100 ohm (0.128/0.254 mm).
- **Alternative:** 9DBL0452, the same buffer with 85 ohm terminations, would let the clock use the lane
  geometry. No gain at 100 MHz, and one more variant to source.
- **Verdict: Keep.** If the buffer part changes (D2), check that its termination is still 100 ohm.

### B6. Loss budget: 50 mm per lane on direct-attach cards

- **Why:** the conservative reading of CEM 4.0 leaves 4.0 dB at 8 GHz for our hardware: fingers 0.3,
  two vias 0.2, receptacle 1.0, copper 2.5 dB, which is about 50 mm on JLC's FR-4.
- **Alternative reading:** if the SFF-8639 module spec grants the host side more than the CEM split
  implies, the limit relaxes. That needs the PCI-SIG document.
- **Verdict: Keep.** x8 lanes are at most 49.5 mm; x16 drive B runs to 54 mm (documented exception).

### B7. Fab: JLCPCB

- **Why:** cheapest by a wide margin (x8 card, 5 boards: $140.76) with a published impedance stackup.

| Alternative | For | Against |
| --- | --- | --- |
| PCBWay | hard-gold fingers, thickness tolerance to CEM, low-loss laminates | about 1.9x; hard gold adds about $380 |
| NextPCB | | about 2.2x, no advantage found |
| EU fabs | short shipping, no import handling | several times the price for 6-layer impedance boards |

- **Verdict: Keep.** The rule set passes both JLC and PCBWay, so the Gerbers do not tie Max to one fab.

### B8. Finger finish: ENIG

- **Why:** JLC offers gold fingers only with ENIG. Max decided on 2026-11-09 that the cards are inserted
  once, so the faster wear of soft gold is accepted.
- **Alternative:** electroplated hard gold at PCBWay, the finish CEM expects, for about $380 more.
- **Verdict: Keep.** Revisit only if a card is going to be replugged often.

### B9. Impedance control option on the order

- **Why:** $33 at JLC buys a fab-tuned trace width and a coupon. Our own solver puts the nominal
  geometry at 89 to 91 ohm, so the tuning is what brings it to 85.
- **Alternative:** drop the option and save $33. The x8 card at under 50 mm would very likely still work;
  the x16 card's long lanes have no margin to give away.
- **Verdict: Keep** for the x16 cards and the first x8 order. A repeat x8 order can drop it.

---

## 3. Connectors

### C1. U.3 receptacle: Amphenol PSAS4F2130021TR (right angle, SMT)

- **Why:** right-angle SFF-8639 receptacle whose drawing we have and whose footprint is built and
  checked. It lets a drive stand on the card.
- **Caveat:** Amphenol lists the PSAS4F21 family for U.2; U.3 uses the same connector with different
  wiring, so this is a wiring question and not a mechanical one, but the part is not vendor-qualified
  "U.3".

| Alternative | For | Against | Availability |
| --- | --- | --- | --- |
| PSAS4F2130021TR (chosen) | footprint done | thin stock | LCSC 16 pcs (C22454449); not at Mouser or Digi-Key |
| PSAS4F2130201TR | same family, in stock in the EU | different footprint: NPTH 1.45 mm, plated hold-downs 0.80 mm in 2.60 mm pads, pad span 39.36 mm; needs a new footprint and a re-route near the pads | Digi-Key 271 pcs, 7.36 EUR |
| PSAS5F3130021TR (vertical) | vendor-listed for U.3 at 32 GT/s | drive would point away from the card, so it only fits the backplane | LCSC C5382954, stock not visible |
| Other vendors (TE, Molex, Foxconn SFF-8639) | second source | new drawing and footprint each; not looked at in detail | not checked |

- **Verdict: Open.** The x8 and both x16 cards together need 9 receptacles for one of each, and LCSC has
  16. Buying them now covers a first build. For any second build, add the PSAS4F2130201TR footprint as a
  board option.

### C2. Aux power: Molex Mini-Fit Jr 45558-0003, PCIe 6-pin

- **Why:** the standard PCIe 6-pin gives 75 W, enough for the drives that exceed the slot's 66 W, and
  every PSU has the cable. In stock.

| Alternative | For | Against |
| --- | --- | --- |
| PCIe 8-pin (2x4) | 150 W | 6 mm wider; only needed above 3 drives on aux (the backplane uses it) |
| SATA power | small | 12 V limited to 4.5 A, connector breaks easily |
| Molex 4-pin peripheral | simple | 2 pins for 12 V, loose fit |
| 12VHPWR / 12V-2x6 | future PSUs | far oversized, sense pins |

- **Verdict: Keep.** Do not confuse the PCIe 6-pin with the EPS/CPU 4+4 cable: they are keyed
  differently but have opposite polarity. Worth a silkscreen note.

### C3. 12 V source selection: one 3-pin jumper per drive

- **Why:** a single shunt can never join slot 12 V and aux 12 V, it costs cents, and each drive can be
  moved to aux on its own to stay under 66 W from the slot.

| Alternative | For | Against |
| --- | --- | --- |
| Ideal-diode OR per drive (LM74700 + FET, or LM66200-style for 12 V) | automatic | the supply with the higher voltage wins, so the slot limit is not respected; more parts |
| Solder jumper | free | needs an iron to change, easy to bridge both |
| All drives always on aux | simplest | the card will not work without the cable |
| eFuse with two inputs | automatic and protected | such parts are QFN, costly, and still share by voltage |

- **Verdict: Keep.**

### C4. Cage board: OCuLink 4i (Amphenol G14A421211112HR)

- **Why:** OCuLink 4i carries exactly one x4 port with REFCLK, PERST# and SMBus, and x16-to-4x-OCuLink
  host cards are common and cheap.
- **Alternatives:** SlimSAS 4i (SFF-8654 4i) and MCIO 4i carry the same signals; cables are a little
  better specified for Gen4 but host cards are rarer. The backplane uses SlimSAS 8i (J1).
- **Verdict: Keep** for the cage board, which only matters if cabled single drives come back.

### C5. Card edge: KiCad `BUS_PCIexpress` pad pattern, L2 voided under the fingers

- **Why:** a known pattern; the void raises the finger impedance from about 39 ohm to about 94 ohm.
- **Verdict: Keep.**

---

## 4. Reference clock

### D1. One buffered REFCLK per drive

- **Why:** the slot supplies one 100 MHz clock and each bifurcated port needs its own point-to-point
  copy. HCSL cannot be split passively.
- **Alternatives:** relying on SRIS (separate clocks with independent spread) needs host and drive
  support and cannot be assumed. A local oscillator with spread off has the same problem.
- **Verdict: Keep.**

### D2. Buffer part: Renesas 9DBL0442BKILF

- **Why it was chosen:** 4 LP-HCSL outputs, PCIe Gen1 to Gen5, 100 ohm terminations built in, one
  3.3 V supply at about 40 mA, 5x5 mm QFN-32. Additive jitter in fan-out mode is 0.092 ps typical
  and 0.156 ps maximum for Gen4 (datasheet).
- **Problem:** the B revision is obsolete. LCSC shows 0 stock, with 100 pieces from "other suppliers"
  at $7.72 and a minimum order of 100.

| Alternative | For | Against | Availability |
| --- | --- | --- | --- |
| 9DBL0442**C**KILF | the successor revision of the same part | 33-week lead time; pin compatibility with B is expected but was not read from the C datasheet | Mouser, 33 weeks |
| 9DBL0442BKILF from LCSC "other suppliers" | the part the footprint was drawn for | $772 for 100 when 6 are needed; broker stock | 100 pcs |
| Diodes PI6CB33401ZHIEX-13R | in stock, cheaper; 4 outputs, 100 ohm default, 5x5 mm QFN-32, 0.05 ps additive jitter on the product page | pinout, bypass mode and delay could not be read (Diodes and Mouser block automated fetching), so it is not known to be a drop-in | Mouser 2,200 pcs, 3.27 EUR |
| 9DBL0452 (85 ohm version) | same pinout family | clock traces are 100 ohm; stock not checked | not checked |
| Skyworks Si53204, TI CDCDB400 (from memory) | other 4-output PCIe buffers | different pinouts, not checked | not checked |
| One 8-output buffer for the x16 card (9DBL08xx class) | removes the chain (D4) | long clock pairs under three drive blocks, bigger QFN | not checked |

- **Verdict: Change.** First choice is the PI6CB33401 if a pin-by-pin check against its datasheet
  passes, because it is the only one of these in stock at a normal distributor. The check has to be done
  by a person with the PDF (Max, or a thread whose network can reach diodes.com). If it is not a
  drop-in, give the boards the footprint of whichever part can be bought. Do not order boards with the
  9DBL0442B footprint before a buffer is in hand or on order.

### D3. Buffer mode: fan-out (bypass), pin 1 open

- **Why:** pin 1 is `HIBW_BYPM_LOBW#`, a three-level input: open is fan-out mode, low is the low-bandwidth
  PLL, high is the high-bandwidth PLL (datasheet). Fan-out mode has the lowest added jitter and no PLL
  to lock. Rev C and D tie pin 1 to GND, which puts the part in PLL mode with the feedback pins and the
  analog supply not laid out for it.
- **Alternative:** PLL (zero-delay) mode on purpose: needs a clean VDDA and adds 0.26 ps typical at Gen4.
- **Verdict: Change,** accepted by the layout thread for rev E: pin 1 open on the first buffer (U1) and on U40.

### D4. x16 clock distribution: chain of buffers

- **Choice:** U1 at the fingers feeds drive A and U40; U40 feeds drive B and U41; U41 feeds C and D.
- **Why:** only one clock pair ever passes under a sideband block and every pair stays short.
- **Limit:** each stage in fan-out mode delays the clock by 2.5 to 4.5 ns, and PCIe allows 12 ns between
  the clock at the host and at the device. Two stages (9 ns worst case) fit; three (13.5 ns) do not.
- **Rev E resolution:** U41 runs in zero-delay mode (pin 1 to GND, own filtered VDDA through FB41), which
  adds about 0 ns instead of 4.5 ns.

| Alternative | For | Against |
| --- | --- | --- |
| Star from U1 to all four drives | one stage, lowest jitter | clock pairs of 100 to 250 mm under the drive blocks; U1 has exactly 4 outputs, so no spare |
| Two stages: U1 feeds A, B and U40; U40 feeds C and D | all fan-out mode, 9 ns | one more long pair under drive B's block |
| U41 as zero-delay buffer (chosen for rev E) | keeps the routed chain | PLL adds jitter (0.26 ps typical, 0.48 ps maximum at Gen4 in high-bandwidth mode; the low-bandwidth figure was not read); acceptable because drives C and D run at Gen3, whose limit is 1.0 ps |

- **Verdict: Keep the rev E plan,** with the condition written on the board documentation: it is valid
  while C and D are Gen3. A Gen4 retimer card must use the two-stage arrangement.

### D5. CLKREQ# tied low

- **Why:** the host then always drives REFCLK, as on any card without clock power management. Four
  drives' CLKREQ# cannot share one slot pin.
- **Alternative:** wire-OR the drives' CLKREQ# to the slot: enables L1 substates, risks a drive losing
  its clock when another one asks to stop it.
- **Verdict: Keep.**

---

## 5. Power

### E1. Per-drive protection: TI TPS259824ONRGER eFuse

- **Why:** one part gives soft start (a 25 W drive has a large input capacitance), a 3 to 4 A circuit
  breaker so one failed drive cannot pull down the slot, overvoltage cut-off at 16.9 V, and a
  power-good output that holds that drive in reset. 2.7 mohm, so no heat. The "O" suffix trips and
  latches instead of limiting, which is right for a load that should never be current-limited.
- **Problem:** out of stock at Mouser and Digi-Key until February 2027. Also a 4x4 mm QFN-24 with a
  split pad on a custom footprint that has not been checked against TI's land pattern.

| Alternative | For | Against | Availability |
| --- | --- | --- | --- |
| TPS259824ONRGER (chosen) | as above | stock | LCSC "other suppliers" 3,000 at $5.84, 9 to 11 days |
| TPS259827ONRGER | same footprint and pinout, cheap | the "7" has no overvoltage cut-off (datasheet ordering table); everything else the same | LCSC C2155761, 10,000 at $3.02 |
| TPS25982xL (current-limit versions) | rides through short overloads | limits instead of tripping, so a faulty drive heats the FET | not checked |
| TPS2421-1 | HSOP-8 with a pad, easy with hot air; 3 to 20 V; power-good and fault pins | power-good is active low so the reset gate needs the other polarity, higher resistance, current set by ISET (100k is 3 A) | not checked |
| PTC fuse + SOT-23 voltage supervisor (backplane plan) | no QFN at all, cents | no soft start, slow, trips late and derates with temperature | in stock |
| Nothing | free | one shorted drive takes down the 12 V rail of the machine | |

- **Verdict: Open.** Either buy the chosen part from LCSC's supplier stock now, or accept the
  TPS259827 and lose overvoltage protection, which matters little on a regulated PSU rail. If Max
  hand-solders, the TPS2421-1 is the part to redesign around; that is a layout change and not a drop-in.

### E2. eFuse settings

| Setting | Value | Why | Alternative |
| --- | --- | --- | --- |
| Current limit resistor | **390R** gives 3.85 A (rev E; was 470R, 3.22 A) | a 25 W drive draws about 2.1 A continuously and is allowed short peaks above that; 3.22 A nominal, less tolerance, was too close to those peaks for a breaker that latches off | 330R gives 4.5 A, looser |
| ITIMER capacitor | **4.7 nF** (rev E; was none) | lets short load steps pass without a trip | open: trips at once on any spike |
| dV/dt capacitor | 1 nF, about 4.6 V/ms, 12 V in 2.6 ms | inrush about 0.5 A into 100 uF | 3.3 nF for a gentler start if the slot rail sags |
| Enable divider | 100k / 15k: on at 9.2 V rising, off at 8.4 V | keeps the drive off while 12 V is still rising | |
| Retry | latch off (RETRY_DLY to GND) | a real fault should stay off until power is cycled | auto-retry with a capacitor: recovers alone, keeps hammering a short |
| IMON resistor | 1k (rev E; was 10k) | 246 uA/A, so 0.25 V/A and 0.95 V at the trip point; accurate only above 3 A | INA3221 for real measurement (feature 13) |

- **Verdict: Change,** accepted for rev E.

### E3. Card 3.3 V for the sideband logic: TPS2116 power mux

- **Why:** the logic must run from 3.3Vaux when the slot provides it (so reset and SMBus work before main
  power) and from slot 3.3 V when there is no aux. The TPS2116 switches without back-feeding either rail.
- **Rev E change:** priority on slot 3.3 V with 3.3Vaux as fallback. Slot 3.3Vaux is limited to 375 mA,
  and to 20 mA when wake is not enabled, so it must not carry the logic and LEDs in normal running.

| Alternative | For | Against | Availability |
| --- | --- | --- | --- |
| TPS2116DRLR (chosen) | priority mode, 40 mohm, SOT-583 | 0.5 mm pitch, small | in stock (C3235557) |
| LM66200 dual ideal diode (from memory) | automatic, no priority pin to get wrong | highest voltage wins, so it cannot prefer main over aux | not checked |
| Two Schottky diodes (BAT54C class) | cents, SOT-23, easy to solder | 0.3 V drop: 3.0 V logic rail | in stock |
| Slot 3.3 V only | no part | no aux: PERST# gating and SMBus dead in standby | |

- **Verdict: Change,** accepted for rev E.

### E4. 12 V planes: L4 split into slot 12 V and aux 12 V

- **Why:** the two supplies must never be joined, and each needs a low-resistance path for up to 9 A.
- **Alternative:** wide traces on outer layers: takes the room the lanes need.
- **Verdict: Keep.** Rev D already keeps the planes off the bracket screw holes.

### E5. Capacitors on the 12 V path

- **Choice:** 22 uF 25 V X5R as bulk, 10 uF 50 V X5R at the eFuse input, 100 nF at every IC.
- **Why:** 25 V parts on 12 V keep about half their capacitance under bias; 50 V at the connector side
  for cable inductance spikes.
- **Alternatives:** polymer or aluminium bulk capacitors hold their value under bias and damp ringing,
  but are tall and add a hand-placed part. A TVS (SMBJ15A at the 6-pin, chosen as an extra) handles
  the hot-plug spike better than more ceramic.
- **Verdict: Keep,** plus the TVS.

---

## 6. Sidebands

### F1. SMBus: one switch per card plus one per drive

- **Choice:** TCA9548A at the card (0x77, movable with solder jumpers) puts everything on a card-local
  bus; each drive has a TCA9543A (0x70 + n) in front of its own SMBus.
- **Why:** all drives answer at the same addresses (0x6A, and 0x53 for VPD), so they cannot share a
  bus. The card-level switch keeps 0x70 to 0x73 and 0x20 to 0x23 off the host's segment, where DIMM
  SPD hubs and BMC devices often live.

| Alternative | For | Against |
| --- | --- | --- |
| One TCA9548A or TCA9546A, a channel per drive, expanders on the upstream side | 4 fewer ICs | expanders sit on the host's bus; a trunk per drive instead of one shared trunk |
| Zero-ohm links, one drive connected | no ICs | only one drive readable |
| No SMBus | simplest | no out-of-band temperature or health, no control of the expanders |
| PCA9546A instead of TCA | same function | TCA parts work down to 1.65 V and are stocked |

- **Verdict: Keep.** All three parts are in stock (TCA9548APWR C130026, TCA9543APWR C2653307,
  TCA9554PWR C477924) and are TSSOP, which solders by hand. A simpler single-switch layout is the
  fallback if board space runs out.

### F2. Per-drive IO expander: TCA9554

- **Why:** lets software read PRSNT#, IfDet#, IfDet2# and WAKE#, and drive PWRDIS, DualPortEn#, a reset
  hold and the locate LED. Pull resistors set safe defaults, so the card works with no software at all.

| Alternative | For | Against |
| --- | --- | --- |
| One TCA9535 (16 bit) per two drives | fewer ICs | signals cross between drive blocks, breaks the identical-block layout |
| Resistor straps only | cheapest | no power cycling of a single drive, no presence readback, no locate LED |
| PCA9554 / PCA9554A | same pinout, second source | other address range on the A version |

- **Verdict: Keep.**

### F3. PERST# gate: 74LVC1G11 (3-input AND)

- **Why:** a drive leaves reset only when the slot releases PERST#, its own 12 V is good, and software
  has not asked to hold it. Without the power-good term a drive on aux 12 V could see reset released
  before its supply is up.
- **Alternatives:** PERST# straight through (works when all 12 V comes from the slot); a reset
  supervisor per drive (adds a defined delay, another part); an open-drain wired-AND with a pull-up
  (slow edge, cheap).
- **Verdict: Keep.** The gate has a 100k pull-down on its output, so a drive stays in reset when the
  card logic is unpowered.

### F4. WAKE#: 74LVC1G07 open-drain buffer per drive

- **Why:** wire-ORs the drives onto the slot's WAKE# and keeps an unpowered drive from pulling it low.
- **Alternative:** leave WAKE# unconnected. NVMe drives in a NAS almost never use it. That would save
  one SC-70 part per drive.
- **Verdict: Keep,** but it is the first part to drop if a block needs room. It can also be left unpopulated.

### F5. Strap defaults

| Pin | Default | Why | Alternative |
| --- | --- | --- | --- |
| S15 HPT0 | GND | tells the drive the host is U.3; floating selects the U.2 lane map and the drive does not link | none |
| PWRDIS | 10k pull-down | drive powers on with no software | pull-up would need software to start |
| DualPortEn# | pull-up (single port) | the cards are single-port x4 | low only on dual-port hosts |
| REFCLK1, port B lanes | not connected | single port | |
| IfDet#, IfDet2#, PRSNT# | read only | the drive drives them | |

- **Verdict: Keep.**

### F6. Trunks on L3 with one tap per drive block

- **Why:** SMBus, 3.3 V, PERST# and WAKE# run the length of the card once, under the lanes' ground
  plane, and each block taps them with a via.
- **Verdict: Keep.**

### F7. LEDs

- **Choice:** green KT-0603YG (C2289) for power and activity, yellow for locate.
- **Problem:** the yellow C72038 has 0 stock. **Change** to XL-1608UYC-06 (C965802).
- **Alternative:** one bicolour LED per drive saves a footprint and costs more.

---

## 7. Signal integrity details

### G1. AC coupling: 220 nF only on PER0 and PER1

- **Why:** SFF-TA-1001 reuses the SAS lanes for PCIe lanes 0 and 1 in U.3, and on those two lanes the
  drive's transmitter has no capacitors, so the host side must carry them. PER2, PER3 and all PET
  lanes already have capacitors (in the drive and on the motherboard); a second one only adds a
  discontinuity. 220 nF is the middle of the allowed 176 to 265 nF.
- **Part:** 0402 X7R 16 V (C16772), ground void under the pads. 0201 has less parasitic capacitance
  and is not practical by hand; 0402 with a void is the usual compromise.
- **Verdict: Keep.** This was missing on the cage board (rev A) and is added in rev B.

### G2. Polarity inversion allowed, lane reversal not used

- **Why:** receivers correct P/N inversion by themselves, so pairs are swapped where that avoids a
  crossing. Lane reversal is optional for hosts on bifurcated x4 ports, so it is never relied on.
- **Verdict: Keep.**

### G3. Return vias and antipads

- **Why:** each lane via pair gets two ground vias within 1.0 mm so the return current can change planes.
- **Open item:** the cage board's REFCLK layer change has no return vias, because they did not fit the
  0.5 mm clearance next to the OCuLink pads. At 100 MHz this is harmless.
- **Verdict: Keep.**

### G4. Glass weave

- **Why:** long straight runs on 3313 can put one half of a pair over glass and the other over resin.
  The rule asks for 5 to 10 degrees of angle on straight runs over 25 mm.
- **Verdict: Keep.** It matters most on x16 drives C and D.

### G5. Passive size: 0402, parts on both sides

- **Why:** density. The sideband block sits in the strip beside each receptacle; a 4-drive card has
  about 94 parts in 0402.
- **Alternative:** 0603 and everything except the receptacles on one side. Easier by hand and cheaper
  to assemble (one-sided assembly), needs about 40 % more area per passive.
- **Verdict: Open.** If JLC assembles the boards, keep 0402. If Max solders them, the layout thread
  should move what fits to 0603 and one side; resistor arrays (4x0603) stay as they are.

---

## 8. Mechanics and cooling

### H1. Drive pitch 73 mm, drives B to D raised 5.7 mm

- **Why:** a 2.5 inch drive is 69.85 mm wide, so 73 mm leaves 3 mm for the printed shroud walls. Drive
  B's pads sit above fingers 8 to 15, so those lanes run under drive B and the receptacles from B on
  are raised to make room.
- **Alternative:** a wider pitch does not fit four drives in 312 mm.
- **Verdict: Keep.**

### H2. Card cut away behind the drives

- **Why:** air has to pass along both faces of each drive.
- **Verdict: Keep.** The extra M3 holes Max chose give the printed shroud something to hold on to.

### H3. Cooling: one 92x38 mm server-class fan

- **Why:** the thermal model needs about 25 CFM for two drives and 43 CFM for four through 5 mm gaps to
  hold a 70 C case at 35 C intake. A quiet 92x25 mm fan cannot do that against the pressure drop.
- **Alternatives:** 3 mm gaps (15 and 26 CFM, but more pressure); two 80 mm fans; relying on case airflow
  (not enough for 25 W drives).
- **Verdict: Keep.** The 4-pin fan header Max chose lets the fan run from the card's 12 V.

### H4. Cage board: M3 slots and drive-side edge

- **Why:** slots along the insertion axis absorb the tolerance between the printed cage and the seated
  drive. Rev B pulls the drive-side board edge back to 2.35 mm from the pad row so the drive seats
  fully against the receptacle and not against the PCB.
- **Open:** the drive's height relative to the receptacle should be measured on a real part before a
  cage is printed.

---

## 9. OCuLink cage board specifics

| # | Choice | Why | Alternatives | Verdict |
| --- | --- | --- | --- | --- |
| I1 | 12 V in on a PCIe 6-pin | one 25 W drive; OCuLink carries no power | SATA power (smaller, 4.5 A limit); barrel jack (no PSU cable) | Keep |
| I2 | PTC fuse mSMD300-16V (C6851473), 1812 | cheap short-circuit protection for one drive | eFuse as on the cards (soft start and power-good, QFN); nothing | Keep; no soft start is the price |
| I3 | 3.3 V aux from HT7533-1 in SOT-89 (alt MCP1703AT-3302E/MB) | the load is a few mA of pull-ups and LEDs; 30 V input rating (MCP1703A: 16 V) against a 12 V rail; SOT-89 solders by hand | AMS1117-3.3 (rev A): 15 V maximum input is close to 12 V plus spikes, needs a minimum load and wastes 5 to 10 mA; a small buck: pointless at this current | Changed in rev B; pinout to be verified (section 12). HT7533 is LCSC only; the MCP1703A is the Mouser/Digi-Key part |
| I4 | PERST# 100k pull-down | drive stays in reset with no cable | buffer with Ioff (protects against back-feeding, one more part) | Keep |
| I5 | Activity LED through 2N7002 | the drive's LED pin cannot sink an LED directly on 3.3 V | direct drive | Keep |
| I6 | Lane 0 length about 30 mm with skew bumps | lane 0 is on the front pin row | | Keep, documented exception |
| I7 | AC caps on PER0/PER1, on the bottom next to the vias | G1 | on the host card instead: depends on which host card is bought | Keep on the cage board; then the host card must not have them on those lanes |

The cage board is a cabled design, so it cannot be compliant at Gen4 without a retimer on the host
card (design rules, section 9). It will very likely train at Gen4 with a short good cable.

---

## 10. Backplane plan (4 drives on 2x SlimSAS 8i)

Owned by the backplane thread; recorded here so the reasons are in one place.

| # | Choice | Why | Alternatives | Verdict |
| --- | --- | --- | --- | --- |
| J1 | SlimSAS 8i (SFF-8654), SFF-9402 pinout | two sideband sets per 8i, so each x4 has its own REFCLK and PERST#; Gen4 cables and host cards are common | MCIO 8i: one sideband set per 8i, so the backplane would need a clock buffer and shared reset; dearer cables. 4x OCuLink 4i: four cables | Keep |
| J2 | Receptacle Amphenol U10 series, right angle | Digi-Key part with a drawing | vertical U10B (cable leaves into the airflow) | Keep |
| J3 | Drive receptacle PSAS5F3130021TR, vertical | vendor-listed for U.3, the server-backplane geometry | right-angle PSAS4F213 (drives would lie on the board) | Keep; check LCSC stock |
| J4 | PCIe 8-pin power | 4 x 25 W is 100 W, over a 6-pin's 75 W | two 6-pins; a 12V-2x6 | Keep |
| J5 | Per-drive 3 A PTC + SOT-23 supervisor for power-good | no QFN, hot-air friendly, in stock | TPS25982 as on the cards (better protection, stock problem); TPS2421-1 (leaded eFuse, the best of both if a redesign is acceptable) | Keep; TPS2421-1 is the upgrade |
| J6 | SMBus switch with reset and IO expanders | same reason as F1 | zero-ohm links | Keep |
| J7 | PERST# gated with drive power-good, 100k pull-down | F3 | straight through | Keep |
| J8 | 220 nF on PER0/PER1 on the backplane | G1 | on the host card | Keep; the host card must then have none there |
| J9 | 20 mm drive pitch, 80 mm module pitch, milled air slots | matches the thermal model's 5 mm gap; modules tile | 18 mm pitch with a high-pressure fan | Keep |
| J10 | Host card: three designs (passive, linear redriver, retimer), plus a card to buy (Max, 2026-11-13) | passive is cheapest and likely works at 0.5 m; the redriver is hand-solderable; only the retimer is compliant | buy a retimer card (C-Payne class) | Max's decision; recommendation is to buy the retimer card and build the passive one |
| J11 | Cables "PCIe 4.0, 85 ohm, with sidebands", e.g. 3M 8ES8-1DF21 | SAS-only and 100 ohm versions of the same cable exist and do not work | | Keep; ring out every cable |

---

## 11. Minisforum MS-01 / MS-A2

| # | Choice | Why | Alternatives | Verdict |
| --- | --- | --- | --- | --- |
| K1 | Route A first: a bought U.3-wired x4 card in the PCIe slot | works today with the Cablecc card; a 15 mm drive on a thin card fits the MS-01 | custom x4 card: only if nothing bought fits | Keep |
| K2 | Route B: custom M.2 board, 4 layers 0.8 mm (JLC04081H-3313), lanes on L1 with no vias | replaces the stock U.2-wired adapter | flexible M.2 riser to a cage board | Open: waits on Max's measurements and Minisforum's answer |
| K3 | M.2 board power | an M.2 slot has no 12 V; the stock adapters get 12 V through pins or a cable that Minisforum has not documented | a separate 12 V feed from the DC jack | Open, blocks the design |
| K4 | SMBus level | M.2 SMBus is 1.8 V (from memory, to verify) and U.3 is 3.3 V, so a level shifter or no SMBus | leave SMBus off the M.2 board | Leave it off unless needed |
| K5 | Physical limit | the internal bay takes 7 mm drives and the PM1735a is 15 mm | case modification or a cabled-out drive | this makes route B a poor fit for these drives |

---

## 12. Not verified, check before ordering

| Item | Risk if wrong | How to check |
| --- | --- | --- |
| SOT-89 pinout of HT7533-1 and MCP1703A (cage rev B uses 1 GND, 2 VIN, 3 VOUT, from memory; the datasheets could not be fetched from here) | regulator dead or shorted | first page of either datasheet |
| PI6CB33401 pinout against the 9DBL0442 footprint | buffer does not work | compare the two pin tables |
| 9DBL0442C pin and mode compatibility with B | same | Renesas product change notice |
| TPS25982 custom footprint against TI's RGE land pattern | poor soldering of the split pad | TI drawing RGE0024 |
| 9DBL0442 jitter in low-bandwidth PLL mode | U41 choice (D4) | datasheet table |
| M.2 SMBus voltage | level shifter needed or not | PCI-SIG M.2 spec |
| PSAS4F21 use for U.3 | none expected, the wiring is ours | buzz out against the Cablecc card |
| Drive height above the receptacle | cage does not fit | measure a drive |

## 13. Extras Max chose on 2026-11-13 (for rev E or F)

| Extra | Why it earns its place | Alternative left out |
| --- | --- | --- |
| I2C header on the card bus | debug the switches and expanders with a $5 adapter, no host needed | USB bridge on the card (cost, a chip) |
| Test points for 12 V per drive, power-good, IMON, 3.3 V, PERST#, GND | first power-up without probing QFN pins | none |
| Power-good LED per drive | shows at a glance which drive's eFuse tripped | read it over SMBus only |
| 4-pin fan header | fan power where the drives are | fan controller IC (feature 12, not chosen) |
| Extra M3 holes | fix the printed shroud | clips on the board edge |
| Supply LEDs, TVS on the 6-pin, silkscreen address table, ID EEPROM (24C02 at 0x50) | cents each; the TVS protects against cable hot-plug | INA3221 current monitor and temperature sensors (features 11 and 13, not chosen: the drives report both themselves) |

## Sources

- `docs/fab-cost-options.md` (PR #13) and `docs/fab-quotes.md` (PR #11): stock, prices, fab options, 2026-11-13.
- `docs/reviews/full-review-2026-11-13.md`: datasheet readings for 9DBL0442, TPS25982, TPS2116, TPS2421, INA3221.
- `design-rules/README.md` Rev E: stackups, impedance, loss budget, fab comparison.
- `designs/u3-backplane/README.md` (PR #7), `designs/minisforum-u3/README.md`, `docs/research.md`.
- Diodes PI6CB33401 product page (diodes.com/part/view/PI6CB33401), read 2026-11-13; the datasheet itself could not be fetched.
