# Cost options and other manufacturers (2026-11-13)

Follow-up to [fab-quotes.md](fab-quotes.md). Same spec unless a row says otherwise: 6 layers, 1.6 mm
(JLC06161H-3313), ENIG, impedance ±10 %, gold fingers with 30° bevel, 0.2 mm minimum via, single boards.
Prices are online instant quotes from 2026-11-13 in USD (EUR where a German distributor was used), without
VAT. Nothing in the layout files was changed for this document.

## Summary

- **JLCPCB stays the cheapest fab by a wide margin.** NextPCB is about 2.2x and PCBWay about 1.9x the JLCPCB
  price. The European fabs either have no 6-layer service (Aisler), no gold fingers (OSH Park), or no instant
  price for this spec (Multi-CB, Eurocircuits).
- **Most of the JLCPCB price is fixed per order**, not per board area: engineering $33, impedance control $33,
  ENIG $19, 0.2 mm vias $19, Kelvin test $18. The 312 mm card costs only $13 more than the 190 mm card. Trimming
  the board outline or panelizing saves almost nothing.
- **Two levers cut the bare-board price by about a third:** 0.3 mm minimum vias (saves $19-25 per order, needs a
  layout change) and ordering the JLC06161H-3313 stackup without the impedance-control test (saves $33 per
  order, with no change to the boards).
- **Parts are the bigger risk than price.** The 9DBL0442BKILF clock buffer is obsolete, the TPS259824 eFuse is out
  of stock at Mouser and Digi-Key until February 2027, and no Western distributor stocks the U.3 receptacle in the
  footprint the boards use.
- **Hand assembly** with parts from Mouser or Digi-Key saves the JLCPCB assembly fees ($149-186 per order of 5).
  The boards are not one-sided today: the receptacles, the clock buffer and some capacitors sit on the bottom.

## 1. Bare PCB at JLCPCB: what the money is for

JLCPCB charge breakdown, x8 card, 5 pcs ($140.76):

| Item | Cost | Can it go? |
| --- | --- | --- |
| Engineering fee | $33.00 | No, fixed per order |
| Impedance control ±10 % | $33.08 | Yes, see 1.2 |
| ENIG | $19.00 | No; the quote tool would not drop ENIG with gold fingers and the stackup |
| Min via 0.2 mm | $19.16 | Yes, with 0.3 mm vias (layout change), see 1.1 |
| 4-wire Kelvin test | $17.94 | No, added automatically on 6 layers |
| Board (area) | $13.70 | Barely; scales with area |
| TG155 material | $3.83 | Stays (the TG135 option did not apply with this stackup) |
| Production file confirmation | $1.05 | Optional |

### 1.1 and 1.2: vias and impedance control (all three cards, quoted)

| Board | Qty | Today | 0.3 mm vias | 0.3 mm vias, no impedance test | Saving |
| --- | --- | --- | --- | --- | --- |
| x8 | 5 | $140.76 | $121.60 | $88.52 | $52 (37 %) |
| x8 | 10 | $161.42 | $139.63 | $106.55 | $55 (34 %) |
| x16, 3 drives | 5 | $146.14 | $126.30 | $93.22 | $53 (36 %) |
| x16, 3 drives | 10 | $172.16 | $149.02 | $115.94 | $56 (33 %) |
| x16, 4 drives | 5 | $153.99 | $133.14 | $100.06 | $54 (35 %) |
| x16, 4 drives | 10 | $187.86 | $162.70 | $129.62 | $58 (31 %) |

Without any via change, dropping only the impedance test takes the x8 / 5 pcs from $140.76 to $107.68. A
0.25 mm minimum via saves just $0.87, so the step has to go all the way to 0.3 mm / 0.45 mm pads.

- **Impedance test.** JLCPCB still builds the specified JLC06161H-3313 stackup when impedance control is set to
  "No requirement"; it only stops measuring the coupon and trimming widths. The trace widths come from JLC's own
  calculator for that stackup, so the boards should land close to 85 Ω. The risk is that no one checks it. For a
  first run of 5 boards this is a reasonable trade; for a run that must be PCIe 4.0 compliant, keep it.
- **0.3 mm vias.** About 750 sideband vias on the 4-drive card are 0.2 mm and the lane vias are 0.25 mm. Moving
  to 0.3 / 0.45 mm needs the sideband blocks rerouted (the other thread's router) and slightly larger lane vias.
  It pays back on every order, so it is worth doing if the cards will be ordered more than once.

### 1.3 Panelizing, board size and shape

- **Panelizing does not help.** A 2-up x8 panel (200.1 x 224.5 mm), 5 panels = 10 boards, quoted $163.97, against
  $161.42 for 10 single boards. The fixed fees are per order, and gold fingers with a bevel have to sit on an
  outside edge anyway.
- **Board size barely matters.** The 4-drive card (312 mm) is $13 more than the x8 (190 mm) at 5 pcs, $26 more at
  10 pcs. Cutting 20 mm off a card would save $1-3.
- **Airflow windows and cut-outs are free** at JLCPCB, so they can stay.
- **Ordering 10 instead of 5** costs $21-34 more per order, i.e. $4-7 per extra board.

### 1.4 Shipping to Germany and import costs

JLCPCB to Germany (x8 / x16 orders, 0.5-1.3 kg):

| Method | x8, 5 pcs (0.49 kg) | 10 pcs (0.86-1.33 kg) | Time |
| --- | --- | --- | --- |
| DHL Express (DDP) | $23.52 | $26.97-30.67 | 2-4 business days |
| FedEx Express (DDP) | $23.09 | n/q | 3-5 business days |
| EuroPacket | $13.37 | n/q | 4-7 business days |
| Global Standard Direct Line | $10.69 (order ≤ $150, ≤ 1.5 kg) | n/a | 9-11 business days |

- PCBs (HS 8534) have 0 % EU customs duty. Import VAT is 19 %. With a DDP method JLCPCB collects it up front, so
  there is no courier advance fee on delivery. With a non-DDP courier, DHL / UPS collect the VAT plus their own
  handling fee on delivery.
- Choosing EuroPacket instead of DHL saves about $10 per order if a week of transit is acceptable.

## 2. Assembly cost levers

From the JLCPCB fee table already used in fab-quotes.md:

| Lever | Saving per order | What it needs |
| --- | --- | --- |
| Put every SMD part on the top side and leave the four receptacles for hand soldering | about $26 setup + one stencil side (double-sided setup is $51.12 vs $25.56 single-sided) | Move the bottom-side caps and U1 (13 parts on x8, 34 on x16-4) to the top. The receptacles stay on the bottom because they set the drive orientation. Also fixes the receptacle not being in JLC's assembly library. |
| Do not let JLCPCB place the receptacles at all | Avoids global-sourcing / consignment for C22454449 | Mark JA-JD as DNP in the JLCPCB BOM; solder them by hand (hot air with a preheater, or hot plate) |
| Consigned parts | Not worth it at 5-10 cards | Shipping parts to Shenzhen costs more than the parts' margin |
| "Extended" part fee | $0 on Standard PCBA | Standard PCBA charges $1.53 feeder loading per line for basic and extended parts alike; the extended-part surcharge only applies to Economic PCBA |
| Economic PCBA | setup $8.18 instead of $25.56-51.12 | Single-sided only and a size limit; probably not usable for 6-layer cards of this size. Not quoted. |

## 3. Parts: availability and substitutes

Checked on 2026-11-13 at LCSC, Mouser.de and Digi-Key.de.

| Part (BOM) | LCSC | Mouser.de | Digi-Key.de | Substitute |
| --- | --- | --- | --- | --- |
| U.3 receptacle PSAS4F2130021TR | 16 in stock ($7.50); 270 at other suppliers (MOQ 270, 9-14 days) | not available | not listed | **PSAS4F2130201TR**: Digi-Key 271 in stock, €7.36 / €6.25 @10 / €5.86 @25. Same family, 68 contacts, U.2/U.3, PCIe 4.0. **Different footprint**: NPTH pegs Ø1.45 instead of Ø1.78, plated hold-downs Ø0.80 with Ø2.60 pads, pad span 39.36 mm (drawing psas4f213020xxx Rev 1). Needs a new footprint. |
| Clock buffer 9DBL0442BKILF | 0; 460 at other suppliers with MOQ 100 at $7.72 ($772 minimum) | restricted | **obsolete** | 9DBL0442CKILF (the C revision): Mouser 33-week lead time, Digi-Key no backorders. Diodes **PI6CB33401ZHIEX-13R** (4-output, 3.3 V, PCIe, 5x5 QFN-32): Mouser 2,200 in stock, €3.27; LCSC 0. **Pin compatibility with the 9DBL0442 is not verified**; check before swapping. |
| eFuse TPS259824ONRGER | C2155759 (…RGET) 2; C2155766 0 in stock, 3,000 at other suppliers at $5.84, 9-11 days | 0, next 18 Feb 2027 | 0, next 1 Feb 2027 | Same part from LCSC "other suppliers" is the simplest fix. TPS259827ONRGER (C2155761): 10,000 at other suppliers at $3.02, 9-11 days; same package, but the -7 variant has different protection thresholds, so check the variant table before swapping. |
| Yellow LED 19-213/Y2C (C72038) | 0 | restricted | 0 | XINGLIGHT XL-1608UYC-06 (C965802), 1.1 M in stock, $0.007 |
| SN74LVC1G07DCKR | 11,709 | backorder | see note | fine at LCSC |
| SN74LVC1G11DCKR | 11,230 | backorder | see note | fine at LCSC |
| TCA9548APWR | 17,735 | backorder | 33,578 | fine |
| TCA9543APWR | 1,029 | price shown, stock not read | 1 | fine at LCSC |
| TCA9554PWR | 5,482 | price shown, stock not read | 15,344 | fine |
| TPS2116DRLR | in stock (fab-quotes) | price shown | 46,058 | fine |
| Molex 45558-0003 | in stock (fab-quotes) | €0.98 | 74,808 | fine |

Digi-Key started rate-limiting and Mouser blocked the session part way through, so a few Western stock numbers
are missing; the prices that were read are in section 4.

## 4. Hand assembly with Mouser / Digi-Key parts

**Does the current design allow it?** Partly. All parts are SMD, 0402 and larger, with no BGA. But the boards are
two-sided: on the x8 the bottom has JA, JB, U1 (clock buffer) and 10 capacitors; on the 4-drive x16 it has JA-JD,
U1 and 29 capacitors. Hot air can do both sides one part at a time, but a hot plate or a single stencil pass needs
one side. The hardest parts by hand are:

- the U.3 receptacles: 68 SMD contacts at 0.8 mm pitch and a large plastic body (stencil plus hot plate or
  preheater; plain hot air risks the housing),
- the TPS259824 (VQFN-24, 0.5 mm pitch, split exposed pad) and the clock buffer (QFN-32 5x5, exposed pad): both
  need a stencil or very careful paste.

To make hand assembly practical, move everything except the receptacles to the top side (same change as in
section 2). Then: stencil and hot plate for the top side, receptacles by hot air with a preheater from below.

**Parts cost per card at Mouser / Digi-Key prices** (EUR, quantities for 5 cards, passives estimated):

| Card | Mouser / Digi-Key | LCSC (fab-quotes.md, USD) |
| --- | --- | --- |
| x8 | about €34 | $37 |
| x16, 3 drives | about €50 | $55 |
| x16, 4 drives | about €67 | $75 |

This assumes the PSAS4F2130201TR receptacle (needs the footprint change), the Diodes clock buffer (unverified)
and the TPS259824 at its backorder price.

**Per-order comparison, 5 cards of the 4-drive x16:**

| | JLCPCB assembled | DIY |
| --- | --- | --- |
| Bare PCB | $153.99 (or $100.06 with section 1 changes) | same |
| Assembly fees | $169.28 | stencil about $10-15 with the PCB order |
| Parts | $372.77 (LCSC) | about €334 (Mouser / Digi-Key) |
| Labour | none | about 1-1.5 h per card |

DIY saves about $150-185 per order of 5 in assembly fees, minus the stencil. It does not solve the shortages: the
eFuse and the clock buffer are just as hard to get at Mouser and Digi-Key as at LCSC.

## 5. Other manufacturers

| Fab | Where | x8 5 / 10 | x16-3 5 / 10 | x16-4 5 / 10 | Build time | Shipping to DE | Gold fingers | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **JLCPCB** | Shenzhen | $140.76 / $161.42 | $146.14 / $172.16 | $153.99 / $187.86 | 7-8 days | $10.69-30.67, DDP available | ENIG only, 30° / 45° bevel | Cheapest. Stackup 1.538 mm ±10 %, slightly under CEM minimum at the low end. |
| PCBWay | Shenzhen | $266.70 / $297.91 | $280.85 / $320.13 | $301.95 / $363.91 | 5-6 days | DHL, not quoted to DE | ENIG or hard gold (+ about $380), 20-60° bevel | Prices from fab-quotes.md, ENIG fingers |
| NextPCB | Shenzhen | $314.24 / $355.98 | $325.08 / $376.99 | $340.87 / $409.30 | 6 days | DHL $25.86-35.73 ($10 less on the first order), 2-5 days | ENIG or hard gold, 20/30/45/60° bevel | Quoted with its own 06161HA4-1080 stackup, so widths would need checking; first order is $20 cheaper |
| Multi-CB | Germany | no instant price | | | from 4 working days | domestic | Hard gold, 20° standard / 30° special bevel | Any 6-layer order with a custom stackup and impedance control goes to a manual quote. Sells only to businesses and public institutions. Defined 6L-01 pool stackup is 1.55 mm. |
| Eurocircuits | Belgium / Hungary | not quoted (calculator needs an account) | | | 5 working days (impedance pool) | EU, no import | Hard gold, 30° standard bevel | DEFINED IMPEDANCE pool covers 6 layers at 1.55 mm with gold edge connectors; impedance is designed to their stackup, not tested to a tolerance |
| OSH Park | USA | about $490 for 3 x8 boards | | | 12-21 days | | **No gold fingers or bevel** | $15 / sq in, multiples of 3. Unsuitable. |
| Aisler | Germany | — | | | | | | 6-layer service discontinued |
| Seeed Fusion, ALLPCB, Elecrow | Shenzhen | not quoted | | | | buyer pays VAT on delivery | Seeed: ENIG / hard gold, bevel; ALLPCB: bevel listed; Elecrow: no hard gold, 0.3 mm min drill | Capability pages only; no reason to expect them under JLCPCB |

A European fab would avoid import VAT handling but not the VAT itself (19 % either way), and none of them gave an
instant price for this spec. Multi-CB is the one to ask if hard-gold fingers or a German supplier matter; send it
the Gerbers for a manual quote.

## 6. Recommendations

1. **Order bare boards from JLCPCB** and ship with DHL Express DDP (or EuroPacket to save $10).
2. **For the first run, order the JLC06161H-3313 stackup without the impedance test**: $33 less per order, no
   design change. Keep the test for a run that has to be compliant.
3. **Ask the layout thread for two changes before the next fab run:**
   - 0.3 / 0.45 mm minimum vias (saves $19-25 on every JLCPCB order),
   - every part except the receptacles on the top side (single-sided JLCPCB assembly, or hot-plate DIY).
4. **Fix the parts before ordering assembly:**
   - eFuse: buy TPS259824ONRGER from LCSC other suppliers (9-11 days), or check whether a TPS25982x variant
     that is in stock fits the 12 V protection levels;
   - clock buffer: verify the Diodes PI6CB33401 pinout against the 9DBL0442, or pick another in-stock
     4-output PCIe buffer and adjust the footprint;
   - receptacle: keep C22454449 if 16 + 270 at LCSC covers it, otherwise switch the footprint to
     PSAS4F2130201TR (Digi-Key stock);
   - LED: XL-1608UYC-06 (C965802).
5. **Hand assembly is worth it** if you are fine with about an hour per card: it saves $150-185 per order of 5.

Estimated effect for 5 cards of the 4-drive x16 with recommendations 1-3 applied and JLCPCB assembly:
bare PCB $154 → $100, assembly fees $169 → about $143, total from $696 to about $616 before shipping.
