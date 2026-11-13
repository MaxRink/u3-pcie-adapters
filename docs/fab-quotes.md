# Fab quotes: x8 and x16 U.3 cards (2026-11-13)

Online instant quotes from JLCPCB (cart.jlcpcb.com/quote) and PCBWay (pcbway.com/orderonline.aspx), taken on
2026-11-13 in USD. Prices exclude shipping, import VAT and duties. Both sites say the final price is set after
their file review, so treat these as estimates.

## What was quoted

| | x8 card | x16 card, 3 drives | x16 card, 4 drives |
| --- | --- | --- | --- |
| Board | `boards/x8` | `boards/x16p3` | `boards/x16p` |
| Size | 190.1 x 111.25 mm | 239.1 x 111.25 mm | 312.1 x 111.25 mm |
| BOM lines / placements | 28 / 88 | 28 / 127 | 28 / 166 |
| SMT joints / THT joints | 515 / 10 | 764 / 12 | 1013 / 14 |

Common spec: 6 layers, 1.6 mm, FR-4 TG150-155, 1 oz outer / 0.5 oz inner, green mask, ENIG 1 u", impedance
control +-10 % on the JLC06161H-3313 stackup, gold fingers with 30 degree bevel, minimum via hole 0.2 mm,
single boards (no panel).

## Bare PCB

| Board | Qty | JLCPCB | PCBWay, ENIG fingers | PCBWay, hard-gold fingers |
| --- | --- | --- | --- | --- |
| x8 | 5 | $140.76 | $266.70 | $642.22 |
| x8 | 10 | $161.42 | $297.91 | $688.75 |
| x16, 3 drives | 5 | $146.14 | $280.85 | $660.18 |
| x16, 3 drives | 10 | $172.16 | $320.13 | $718.39 |
| x16, 4 drives | 5 | $153.99 | $301.95 | $686.80 |
| x16, 4 drives | 10 | $187.86 | $363.91 | $762.97 |

- JLCPCB build time 7-8 days, PCBWay 5-6 days. Shipping estimate to the default (US) address: $26-38 at
  JLCPCB (UPS, 0.5-1.3 kg), $27-40 at PCBWay (DHL). Shipping to Germany was not quoted.
- JLCPCB only offers ENIG on the fingers (no hard gold). The JLC06161H-3313 stackup comes out at
  1.538 mm +-10 %; CEM wants 1.57 +-0.13 mm, so the low end of JLC's tolerance is 0.06 mm under the CEM minimum.
- JLCPCB breakdown for the x8, 5 pcs: engineering $33.00, board $13.70, ENIG $19.00, impedance control $33.08,
  0.2 mm vias $19.16, 4-wire Kelvin test $17.94 (added automatically), TG155 material $3.83, production file
  confirmation $1.05. Epoxy-filled and capped vias are free on 6 layers.
- PCBWay's price did not change with via size (0.2 / 0.25 / 0.3 mm) or track/space (4/4 to 6/6 mil).
  Impedance control is $35.78 of the x8 price. Gold fingers add about $65 with ENIG and about $440 with hard gold.

### Cheaper options checked

| Change | Effect at JLCPCB | Effect at PCBWay |
| --- | --- | --- |
| Minimum via 0.3 mm instead of 0.2 mm | saves $19-25 per order | none |
| Minimum via 0.25 mm | saves about $3 | none |
| 4 layers (JLC04161H-3313) instead of 6 | $14-19 **more** (x8, 5 pcs: $154.89) because filled vias are charged on 4 layers; an estimated $5 less than 6 layers with tented vias | $95-108 less (x8, 5 pcs: $172.13; x16 4 drives, 5 pcs: $201.44) |

A 4-layer stackup would lose the dedicated 12 V plane and the low-speed layer, and save nothing at JLCPCB, so
the cards stay on 6 layers. The boards use 0.2 mm vias on the low-speed sideband nets (about 750 on the
4-drive card) and 0.25 mm vias on the PCIe lanes. Saving the roughly $20 via surcharge at JLCPCB would mean
0.3 / 0.6 mm vias everywhere, which needs the sideband blocks rerouted and larger lane vias, so it was not done.

### 4, 6 and 8 layers

Same spec, only the layer count and matching stackup changed (JLC04161H-3313 / JLC06161H-3313 / JLC08161H-3313).

| Board | Qty | JLCPCB 4L | JLCPCB 6L | JLCPCB 8L | PCBWay 4L | PCBWay 6L | PCBWay 8L |
| --- | --- | --- | --- | --- | --- | --- | --- |
| x8 | 5 | $154.89 | $140.76 | $290.14 | $172.13 | $266.70 | $326.65 |
| x8 | 10 | $177.84 | $161.42 | $316.97 | $198.19 | $297.91 | $367.96 |
| x16, 3 drives | 5 | $160.92 | $146.14 | $296.93 | n/q | $280.85 | $344.60 |
| x16, 3 drives | 10 | $189.77 | $172.16 | $330.34 | n/q | $320.13 | $396.46 |
| x16, 4 drives | 5 | $169.68 | $153.99 | $307.80 | $201.44 | $301.95 | $371.33 |
| x16, 4 drives | 10 | $207.29 | $187.86 | $349.98 | $255.40 | $363.91 | $439.05 |

PCBWay prices are with ENIG fingers. 8 layers would ease the sideband routing and let the x16 clock pass under
the sideband blocks without the two repeater buffers, but it does not shorten the lanes to drives C and D, and
PCIe lanes on inner layers would need back-drilled vias. 6 layers at JLCPCB is the cheapest of the six options.

## Assembly

Neither site gives an assembly quote without uploaded Gerber, BOM and placement files, so these are built from
their published numbers.

**JLCPCB (Standard PCBA, both sides)** from the fee table at jlcpcb.com/help/article/pcb-assembly-price
(22 Oct 2026): setup $51.12, stencils $16.42, fixtures $16.42, feeder loading $1.53 per BOM line, $0.0016 per SMT
joint, hand soldering $3.58 + $0.0164 per joint, X-ray per QFN, packing and placement confirmation.
Parts are LCSC list prices at the order quantity.

| Board | Qty | Bare PCB | Assembly fees | Parts | Total | Per card |
| --- | --- | --- | --- | --- | --- | --- |
| x8 | 5 | $140.76 | $148.57 | $186.68 | $476.01 | $95.20 |
| x8 | 10 | $161.42 | $165.81 | $353.72 | $680.95 | $68.10 |
| x16, 3 drives | 5 | $146.14 | $158.93 | $276.74 | $581.81 | $116.36 |
| x16, 3 drives | 10 | $172.16 | $186.52 | $525.68 | $884.36 | $88.44 |
| x16, 4 drives | 5 | $153.99 | $169.28 | $372.77 | $696.04 | $139.21 |
| x16, 4 drives | 10 | $187.86 | $184.13 | $695.32 | $1067.31 | $106.73 |

**PCBWay (turnkey)** from the assembly estimator on the quote page (28 unique parts, 87 / 126 / 165 SMD parts,
8 / 12 / 16 fine-pitch ICs, 1 through-hole part). The estimate is labour only; PCBWay prices the parts after
reviewing the BOM, so the parts column reuses the LCSC figures.

| Board | Qty | Bare PCB (ENIG fingers) | Assembly labour | Parts (LCSC prices) | Total | Per card |
| --- | --- | --- | --- | --- | --- | --- |
| x8 | 5 | $266.70 | $92.30 | $186.68 | $545.68 | $109.14 |
| x8 | 10 | $297.91 | $159.25 | $353.72 | $810.88 | $81.09 |
| x16, 3 drives | 5 | $280.85 | $121.97 | $276.74 | $679.56 | $135.91 |
| x16, 3 drives | 10 | $320.13 | $218.58 | $525.68 | $1064.39 | $106.44 |
| x16, 4 drives | 5 | $301.95 | $151.64 | $372.77 | $826.36 | $165.27 |
| x16, 4 drives | 10 | $363.91 | $277.92 | $695.32 | $1337.15 | $133.72 |

Parts cost is dominated by three parts: the U.3 receptacle ($7.50 each), the 9DBL0442 clock buffer ($5.22-6.07)
and the TPS25982 eFuse ($3.08-3.50).

## Parts availability (LCSC, 2026-11-13)

| Part | LCSC | Stock | Needed for 5 cards (x8 / x16-3 / x16-4) |
| --- | --- | --- | --- |
| Amphenol PSAS4F2130021TR U.3 receptacle | C22454449 | 16 | 10 / 15 / 20 |
| Renesas 9DBL0442BKILF clock buffer | C1540554 | 0 | 5 / 10 / 15 |
| TI TPS259824ONRGET eFuse | C2155759 | 2 | 10 / 15 / 20 |
| Everlight yellow LED 19-213/Y2C | C72038 | 0 | 10 / 15 / 20 |

- C22454449 is not listed in JLCPCB's assembly parts library, so the receptacles would have to be pre-ordered
  through JLCPCB global sourcing, consigned, or soldered by hand.
- The clock buffer, the eFuse and the LED need a pre-order, another distributor (Mouser / DigiKey), or an
  in-stock alternative before an assembly order can go through. Every other BOM line is in stock.
- The BOM names the eFuse TPS259824ONRGER; LCSC stocks the same part as ...RGET (small reel).
