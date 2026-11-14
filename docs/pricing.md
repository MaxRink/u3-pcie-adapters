# Pricing for every board option and vendor (2026-11-13)

One place for what each board, variant and build route costs. It fills the gaps left by
[fab-quotes.md](fab-quotes.md) (x8 and x16 cards at JLCPCB and PCBWay), [fab-cost-options.md](fab-cost-options.md)
(cost levers, other fabs) and [part-options.md](part-options.md) (alternates, purchase plan): the backplanes, the host
card and the cage at all fabs, the front-side x16 card from its dimensions, the eFuse and clock variants, JLCPCB
assembly against hand soldering, DIY parts from the distributors, and the printed parts. No board file was changed.

## How to read the numbers

| Mark | Meaning |
| --- | --- |
| **Q** | Live instant quote from the fab's own page on 2026-11-13 (JLCPCB cart.jlcpcb.com/quote, PCBWay orderonline.aspx), driven from the built-in browser. The first x8 quotes were re-run and match fab-quotes.md to the cent. |
| **S** | Stock and unit price read live from LCSC (product detail API) or Digi-Key.de on 2026-11-13. |
| **E** | Estimate: built from a published fee table, a ratio or a typical price. Never an instant quote. |

- **Spec for every quote:** 6 layers, 1.6 mm, FR-4 TG155, JLC06161H-3313 stackup, 1 oz outer / 0.5 oz inner, ENIG
  (1 u"), green mask, tented vias, impedance control ±10 %, single boards. Cards and the host card also have gold
  fingers (ENIG fingers, 30° bevel at PCBWay; JLCPCB takes the bevel from the file, so the quote form has no line for it).
  Backplanes and the cage have no fingers.
- **Currency:** USD as quoted, EUR at 0.90481 per USD (ECB reference rate, 2026-11-13).
- **Shipping:** DHL Express to Germany as shown by the fab's quote page (JLCPCB: DDP, PCBWay: the page defaults to a
  US address, so its figure is a stand-in for Germany).
- **VAT:** 19 % German import VAT added on goods + shipping where a "landed" figure is given. Customs duty on PCBs is 0 %.
- **Variants A / B / C** of the bare board: **A** = today's files (0.2 mm minimum via, impedance test), **B** = 0.3 mm vias,
  **C** = 0.3 mm vias and no impedance test (the board is still built on the JLC06161H-3313 stackup).
  PCBWay does not charge for the via size, so only A and C are shown for it.
- Board sizes are from the Edge.Cuts layer of each board file. The front-side card is priced at 335 mm for the
  4-drive card, as given by the layout thread; its x8 and 3-drive sizes are not known yet and are scaled by +23 mm (**E**).
  The reversed-lane and the uncrossed version of a card have the same outline, so they cost the same.

## 1. Bare PCB

### JLCPCB (Q)

Board price, no shipping, no VAT. USD / EUR.

| Board | Size mm | Qty | A today | B 0.3 mm vias | C 0.3 mm vias, no impedance test | DHL Express to DE | Landed, A (shipping + 19 % VAT) | Landed, C |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| x8 card (2 drives) | 190.1 x 111.25 | 5 | $141 / €127 | $122 / €110 | $89 / €80 | $24 / €21 | $195 / €177 | $133 / €121 |
| x8 card (2 drives) | 190.1 x 111.25 | 10 | $161 / €146 | $140 / €126 | $107 / €96 | $27 / €24 | $224 / €203 | $159 / €144 |
| x16 card, 3 drives | 239.1 x 111.25 | 5 | $146 / €132 | $126 / €114 | $93 / €84 | $27 / €24 | $206 / €186 | $143 / €129 |
| x16 card, 3 drives | 239.1 x 111.25 | 10 | $172 / €156 | $149 / €135 | $116 / €105 | $31 / €28 | $241 / €218 | $174 / €158 |
| x16 card, 4 drives | 312.1 x 111.25 | 5 | $154 / €139 | $133 / €120 | $100 / €91 | $27 / €24 | $215 / €195 | $151 / €137 |
| x16 card, 4 drives | 312.1 x 111.25 | 10 | $188 / €170 | $163 / €147 | $130 / €117 | $31 / €28 | $260 / €235 | $191 / €173 |
| x16 card, 4 drives, front-side (335 mm) | 335 x 111.25 | 5 | $157 / €142 | $135 / €122 | $102 / €93 | $27 / €24 | $218 / €198 | $154 / €139 |
| x16 card, 4 drives, front-side (335 mm) | 335 x 111.25 | 10 | $193 / €174 | $167 / €151 | $134 / €121 | $31 / €28 | $266 / €241 | $196 / €177 |
| Backplane, 4 drives | 79.6 x 90.5 | 5 | $121 / €110 | $104 / €94 | $71 / €64 | $24 / €21 | $173 / €156 | $112 / €102 |
| Backplane, 4 drives | 79.6 x 90.5 | 10 | $139 / €126 | $121 / €109 | $88 / €79 | $24 / €21 | $193 / €175 | $132 / €120 |
| Backplane, 6 drives | 119.6 x 90.5 | 5 | $131 / €118 | $113 / €102 | $80 / €72 | $24 / €21 | $183 / €166 | $123 / €111 |
| Backplane, 6 drives | 119.6 x 90.5 | 10 | $141 / €128 | $122 / €110 | $89 / €81 | $24 / €21 | $196 / €177 | $134 / €121 |
| Host card, passive | 131 x 39.5 | 5 | $125 / €113 | $108 / €98 | $75 / €68 | $24 / €21 | $177 / €160 | $117 / €106 |
| Host card, passive | 131 x 39.5 | 10 | $130 / €118 | $112 / €102 | $79 / €72 | $24 / €21 | $183 / €166 | $122 / €111 |
| Cage, 1 drive | 56.5 x 37.65 | 5 | $120 / €108 | $103 / €93 | $70 / €63 | $24 / €21 | $171 / €154 | $111 / €101 |
| Cage, 1 drive | 56.5 x 37.65 | 10 | $136 / €123 | $118 / €107 | $85 / €77 | $24 / €21 | $189 / €171 | $130 / €117 |
| x8 card, front-side (about 213 mm) **E** | 213.1 x 111.25 | 5 | $143 / €130 | | $91 / €82 | $24 / €21 | $198 / €180 | $136 / €123 |
| x8 card, front-side (about 213 mm) **E** | 213.1 x 111.25 | 10 | $165 / €149 | | $110 / €100 | $27 / €24 | $229 / €207 | $163 / €148 |
| x16 card, 3 drives, front-side (about 262 mm) **E** | 262.1 x 111.25 | 5 | $149 / €134 | | $96 / €87 | $27 / €24 | $209 / €189 | $146 / €132 |
| x16 card, 3 drives, front-side (about 262 mm) **E** | 262.1 x 111.25 | 10 | $176 / €159 | | $120 / €108 | $31 / €28 | $246 / €222 | $179 / €162 |

- JLCPCB charges mostly per order (x8, 5 pieces: engineering $33, impedance control $33, ENIG $19, 0.2 mm vias $19,
  Kelvin test $18, board area $14). That is why the 56 x 38 mm cage costs $120 for 5 and the 335 mm card $157: size moves the price by about $0.11 per mm of length.
- Variant C saves about a third on every board ($49-55 for 5 pieces, $55-59 for 10).
- The host card's gold fingers cost nothing extra on the quote page. The 5 and 10 piece host card quotes are
  $5 apart because the area fee dominates.
- Build time 7-8 days. The 3-4 day and 2-3 day options cost $132 / $199 more on the x8 and were not priced for the other boards.

### PCBWay (Q)

Same spec with ENIG, ENIG gold fingers (cards and host card) and impedance control. PCBWay prices the via size the same at 0.2 and 0.3 mm.

| Board | Qty | A (impedance) | C (no impedance) | DHL shipping | Landed, A | vs JLCPCB A |
| --- | --- | --- | --- | --- | --- | --- |
| x8 card (2 drives) | 5 | $267 / €241 | $230 / €208 | $27 / €24 | $349 / €316 | 1.89x |
| x8 card (2 drives) | 10 | $298 / €270 | $253 / €229 | $29 / €26 | $389 / €352 | 1.85x |
| x16 card, 4 drives, front-side (335 mm) | 5 | $309 / €279 | $264 / €239 | $40 / €36 | $415 / €376 | 1.97x |
| x16 card, 4 drives, front-side (335 mm) | 10 | $374 / €339 | $329 / €298 | $40 / €36 | $493 / €446 | 1.94x |
| Backplane, 4 drives | 5 | $239 / €216 | $192 / €174 | $27 / €24 | $316 / €286 | 1.97x |
| Backplane, 4 drives | 10 | $250 / €226 | $203 / €184 | $27 / €24 | $329 / €298 | 1.80x |
| Backplane, 6 drives | 5 | $249 / €225 | $202 / €183 | $27 / €24 | $327 / €296 | 1.90x |
| Backplane, 6 drives | 10 | $256 / €232 | $219 / €198 | $27 / €24 | $336 / €304 | 1.81x |
| Host card, passive | 5 | $234 / €211 | $187 / €169 | $27 / €24 | $310 / €280 | 1.86x |
| Host card, passive | 10 | $241 / €218 | $195 / €176 | $27 / €24 | $319 / €289 | 1.85x |
| Cage, 1 drive | 5 | $225 / €204 | $179 / €162 | $27 / €24 | $300 / €271 | 1.88x |
| Cage, 1 drive | 10 | $229 / €207 | $182 / €165 | $27 / €24 | $304 / €275 | 1.69x |

- PCBWay is 1.7 to 2.0 times JLCPCB for every board. The earlier quotes for the x16 cards (fab-quotes.md) still stand: x16 3 drives $281 / $320, x16 4 drives $302 / $364.
- PCBWay's impedance option costs $37-47 per order, its gold-finger hard-gold option about $380 more (not needed, JLCPCB cannot do it either).
- PCBWay's shipping for the 335 mm card rises to $40 (volumetric weight).

### NextPCB, Eurocircuits, Multi-CB, others

| Fab | Result |
| --- | --- |
| NextPCB | Not re-quoted for the new boards. The x8 / x16 quotes from fab-cost-options.md ran at 2.2x JLCPCB ($314 / $356 for the x8). **E** by that ratio: backplane 4 drives about $271 / €245 for 5, backplane 6 drives about $291 / €264, host card about $279 / €253, cage about $267 / €242. Its quote uses its own 06161HA4-1080 stackup, so the trace widths would need checking. |
| Eurocircuits (Belgium / Hungary) | No instant price: the price calculator needs an account, and impedance boards use the DEFINED IMPEDANCE pool at 1.55 mm. Not quoted. Typical published pool prices for a 6-layer board of this size are several times JLCPCB's; ask for a quote with the Gerber zips from `fab/`. |
| Multi-CB (Germany) | Any 6-layer order with a custom stackup and impedance control is a manual quote, and it sells only to businesses. Not quoted. |
| OSH Park, Aisler | OSH Park has no gold fingers (unusable for the cards and the host card; the backplanes and the cage could use it, about $15 per square inch in multiples of 3, **E** at about $120-250 for 3 pieces). Aisler no longer offers 6 layers. |
| Seeed Fusion, ALLPCB, Elecrow | Not quoted; no reason to expect them below JLCPCB. |

No European fab gives a number without an account or a manual quote, so JLCPCB stays the recommendation on price, and Multi-CB or Eurocircuits are the ones to ask if a German supplier matters more than 2x the cost.

## 2. Assembled boards: JLCPCB assembly against hand soldering

**What is quoted and what is not.** JLCPCB gives an assembly price only after the Gerber, BOM and placement files are
uploaded and its parts library is matched, and that step was not done (it would put an order in the cart). The
assembly fees below are **E**, built from JLCPCB's published Standard PCBA fee table (22 Oct 2026, as in fab-quotes.md):
setup $51.12 double-sided or $25.56 single-sided, stencil $16.42 per side, fixtures $16.42, feeder loading $1.53 per BOM
line, $0.0016 per SMT joint, hand soldering $3.58 + $0.0164 per joint, plus about $5 per QFN for X-ray (fitted to the
three card quotes already in fab-quotes.md). The parts lines are **S** where a part has an LCSC or Digi-Key reading and **E**
where it has not (small logic, the MCP1703, connectors without a number).

Parts that cannot be bought at LCSC today (2026-11-13, **S**):

| Part | Where used | LCSC | Alternative bought |
| --- | --- | --- | --- |
| PSAS5F3130021TR vertical U.3 receptacle (C5382954) | backplanes | 0 in stock, $9.03 / $8.72 at 10 | Digi-Key 3,196 in stock: €9.78 / €8.31 at 10 / €7.79 at 25 |
| U10A474240T SlimSAS 8i | backplanes, host card | no LCSC number in the BOM | Digi-Key 713 in stock: €4.55 / €3.86 at 10 / €3.62 at 25 |
| PSAS4F2130021TR U.3 receptacle (C22454449) | cards, cage | 16 in stock, $7.68 / $7.50 at 10 | none; 201TR needs a new footprint |
| 9DBL0442BKILF clock buffer (C1540554) | host card, standard cards | 0 | PI6CB33401ZHIEX at Mouser, €3.27 (pinout unverified), or CDCDB400 on its own boards |
| TPS259824ONRGER (C2155766) | everything | 0 (the reel variant C2155759 has 2) | TPS259827ONRGER C2155761: 2,925 in stock, $4.81 / $4.26 at 10 / $3.94 at 30 |
| LED 19-217/GHC-YR1S2/3T (C72043, green 0603 on the backplanes) | backplanes | 0 | any 0603 green LED (KT-0603G class, about $0.01) |
| 10 k 0402 (C25744) | backplanes, cages | 0 | any 1 % 10 k 0402 at JLCPCB |

Because of this, every parts total below uses the **TPS259827** eFuse (the only deep-stock one) and the **PI6CB33401** clock
buffer where a card needs one; the "as quoted" figures from fab-quotes.md assumed parts that are now out of stock.

### 2.1 Boards that exist as backplane / host / cage

Quantities are boards. Parts column: receptacles and SlimSAS from Digi-Key (LCSC out of stock), eFuses TPS259827, logic and passives at LCSC-class prices (**E**), clock buffer PI6CB33401 (Mouser). Fees column: JLCPCB double-sided, and single-sided with the SlimSAS connectors on the bottom soldered by hand (the receptacles, all parts and the eFuses are on top).

| Board | Qty | Parts, whole order (S/E) | JLCPCB fees, both sides (E) | JLCPCB fees, bottom connectors by hand (E) | Total JLCPCB, both sides, landed | Total JLCPCB, bottom by hand, landed | DIY (hand solder), landed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Backplane, 4 drives | 5 | $357 / €323 | $157 / €142 | $116 / €105 | $793 / €718 | $745 / €674 | $692 / €626 |
| Backplane, 4 drives | 10 | $678 / €614 | $157 / €142 | $116 / €105 | $1,196 / €1,082 | $1,147 / €1,038 | $1,133 / €1,025 |
| Backplane, 6 drives | 5 | $500 / €452 | $167 / €151 | $127 / €115 | $987 / €893 | $939 / €850 | $890 / €805 |
| Backplane, 6 drives | 10 | $967 / €875 | $167 / €151 | $127 / €115 | $1,555 / €1,407 | $1,507 / €1,364 | $1,514 / €1,370 |
| Host card, passive | 5 | $69 / €62 | $103 / €93 | $65 / €59 | $391 / €354 | $346 / €313 | $319 / €289 |
| Host card, passive | 10 | $137 / €124 | $103 / €93 | $65 / €59 | $478 / €433 | $434 / €393 | $415 / €376 |
| Cage, 1 drive | 5 | $73 / €66 | $111 / €100 | n/a | $399 / €361 | n/a | $319 / €289 |
| Cage, 1 drive | 10 | $136 / €123 | $111 / €100 | n/a | $492 / €445 | n/a | $419 / €379 |

Totals include the variant-A bare board, the PCB shipping plus $8 for the heavier assembled parcel, 19 % VAT.
DIY adds a $12 stencil, 10 % on parts for cut-tape passives, and two distributor shipments (about $16 each, **E**).
The cage has bottom-side parts only for its connectors and was not priced single-sided.

**Per board and per drive at 5 boards (variant A bare PCB, JLCPCB both sides, landed):**

| Board | per board | per drive |
| --- | --- | --- |
| Backplane, 4 drives | $159 / €144 | $40 / €36 |
| Backplane, 6 drives | $197 / €179 | $33 / €30 |
| Host card, passive | $78 / €71 | $20 / €18 |
| Cage, 1 drive | $80 / €72 | $80 / €72 |

A 4-drive system is a backplane, a host card and two SlimSAS cables ($15 each from 10Gtek, **E**, see the backplane README); a 6-drive module is a backplane, 1.5 host cards and three cables.

### 2.2 x8 and x16 cards: all variants

Parts from fab-quotes.md with the specials recomputed (receptacle at LCSC, eFuse and clock as in the column), 5 and 10 cards per order. Fees are the fab-quotes.md assembly fees plus $12 for the four new rev F part types; rev F adds $1 per card of parts (**E**). Bare board variant A, DHL shipping + $8, 19 % VAT.

Variants:

- **Std + 827 + PI**: standard board, TPS259827 eFuse, Diodes PI6CB33401 clock buffer (recommended buy; the clock buffer is not at LCSC, so it is consigned or hand-fitted).
- **Std + 824 + PI**: same with the TPS259824 (LCSC C2155766, 0 in stock at the moment, price at 10 pieces).
- **Std + 827 + 9DBL0442B**: same with the original clock buffer (0 in stock, $6.07 / $5.22 at 10).
- **CDCDB400 + 827**: the `-cdcdb400` boards (same outline, same bare price), CDCDB400RHBR from Mouser / Digi-Key at $3.83 / $2.89 at 10. Only recommended for the x8 and 3-drive cards.
- **As quoted (fab-quotes.md)**: TPS259824 C2155759 at $3.08-3.50 and 9DBL0442BKILF; neither is purchasable now.

| Card | Qty | Variant | Parts, whole order | Assembly fees | Total landed, whole order | Per card, landed | Per drive, landed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| x8 card (2 drives) | 5 | Std + 827 + PI6CB33401 | $191 / €173 | $161 / €145 | $624 / €564 | $125 / €113 | $62 / €56 |
| x8 card (2 drives) | 5 | Std + 824 + PI6CB33401 | $184 / €167 | $161 / €145 | $615 / €557 | $123 / €111 | $62 / €56 |
| x8 card (2 drives) | 5 | Std + 827 + 9DBL0442B | $204 / €184 | $161 / €145 | $638 / €578 | $128 / €116 | $64 / €58 |
| x8 card (2 drives) | 5 | CDCDB400 + 827 | $192 / €174 | $161 / €145 | $625 / €565 | $125 / €113 | $62 / €57 |
| x8 card (2 drives) | 5 | As quoted (unavailable parts) | $192 / €173 | $161 / €145 | $624 / €565 | $125 / €113 | $62 / €56 |
| x8 card (2 drives) | 10 | Std + 827 + PI6CB33401 | $371 / €336 | $178 / €161 | $887 / €803 | $89 / €80 | $44 / €40 |
| x8 card (2 drives) | 10 | Std + 824 + PI6CB33401 | $357 / €323 | $178 / €161 | $870 / €787 | $87 / €79 | $44 / €39 |
| x8 card (2 drives) | 10 | Std + 827 + 9DBL0442B | $387 / €350 | $178 / €161 | $906 / €820 | $91 / €82 | $45 / €41 |
| x8 card (2 drives) | 10 | CDCDB400 + 827 | $364 / €329 | $178 / €161 | $879 / €795 | $88 / €79 | $44 / €40 |
| x8 card (2 drives) | 10 | As quoted (unavailable parts) | $364 / €329 | $178 / €161 | $878 / €795 | $88 / €79 | $44 / €40 |
| x16 card, 3 drives | 5 | Std + 827 + PI6CB33401 | $283 / €256 | $171 / €155 | $756 / €684 | $151 / €137 | $50 / €46 |
| x16 card, 3 drives | 5 | Std + 824 + PI6CB33401 | $273 / €247 | $171 / €155 | $743 / €673 | $149 / €135 | $50 / €45 |
| x16 card, 3 drives | 5 | Std + 827 + 9DBL0442B | $299 / €271 | $171 / €155 | $775 / €702 | $155 / €140 | $52 / €47 |
| x16 card, 3 drives | 5 | CDCDB400 + 827 | $276 / €250 | $171 / €155 | $748 / €676 | $150 / €135 | $50 / €45 |
| x16 card, 3 drives | 5 | As quoted (unavailable parts) | $282 / €255 | $171 / €155 | $754 / €682 | $151 / €136 | $50 / €45 |
| x16 card, 3 drives | 10 | Std + 827 + PI6CB33401 | $536 / €485 | $199 / €180 | $1,125 / €1,018 | $112 / €102 | $37 / €34 |
| x16 card, 3 drives | 10 | Std + 824 + PI6CB33401 | $517 / €467 | $199 / €180 | $1,102 / €997 | $110 / €100 | $37 / €33 |
| x16 card, 3 drives | 10 | Std + 827 + 9DBL0442B | $568 / €514 | $199 / €180 | $1,163 / €1,052 | $116 / €105 | $39 / €35 |
| x16 card, 3 drives | 10 | CDCDB400 + 827 | $521 / €472 | $199 / €180 | $1,107 / €1,002 | $111 / €100 | $37 / €33 |
| x16 card, 3 drives | 10 | As quoted (unavailable parts) | $536 / €485 | $199 / €180 | $1,125 / €1,018 | $112 / €102 | $37 / €34 |
| x16 card, 4 drives | 5 | Std + 827 + PI6CB33401 | $377 / €341 | $181 / €164 | $890 / €805 | $178 / €161 | $44 / €40 |
| x16 card, 4 drives | 5 | Std + 824 + PI6CB33401 | $363 / €328 | $181 / €164 | $873 / €790 | $175 / €158 | $44 / €39 |
| x16 card, 4 drives | 5 | Std + 827 + 9DBL0442B | $401 / €363 | $181 / €164 | $918 / €831 | $184 / €166 | $46 / €42 |
| x16 card, 4 drives | 5 | As quoted (unavailable parts) | $378 / €342 | $181 / €164 | $890 / €805 | $178 / €161 | $45 / €40 |
| x16 card, 4 drives | 10 | Std + 827 + PI6CB33401 | $716 / €648 | $196 / €177 | $1,355 / €1,226 | $135 / €123 | $34 / €31 |
| x16 card, 4 drives | 10 | Std + 824 + PI6CB33401 | $690 / €624 | $196 / €177 | $1,324 / €1,198 | $132 / €120 | $33 / €30 |
| x16 card, 4 drives | 10 | Std + 827 + 9DBL0442B | $748 / €677 | $196 / €177 | $1,393 / €1,261 | $139 / €126 | $35 / €32 |
| x16 card, 4 drives | 10 | As quoted (unavailable parts) | $705 / €638 | $196 / €177 | $1,342 / €1,215 | $134 / €121 | $34 / €30 |

The 4-drive CDCDB400 board is routed but the review recommends it only for the x8 and 3-drive cards (jitter and delay budget of three buffer stages), so no 4-drive row is shown.

**Front-side cards.** Not on main yet, so there are no BOM or placement files. Parts list and part count are assumed unchanged, so assembly and parts equal the rows above; only the bare board changes (4-drive card at 335 mm: $156.53 for 5, $192.85 for 10 at JLCPCB variant A; $135.37 / $167.06 at variant B; $102.29 / $133.98 at variant C, all **Q**). Moving the drives to the front may change which side the receptacles and their hold-down parts sit on and so the single-/double-sided setup fee (**E**, +/- $26 per order); this needs the real files.

### 2.3 Hand soldering (DIY) against JLCPCB assembly, cards

DIY = bare board variant A + shipping + $12 stencil, parts with the same specials but +25 % on the passives and small logic (cut tape at Mouser / Digi-Key instead of LCSC reels, **E**), two distributor shipments of about $16, 19 % VAT, 1 to 1.5 hours per card of labour not priced.

| Card | Qty | JLCPCB assembled, landed (variant Std + 827 + PI) | DIY, landed | Difference |
| --- | --- | --- | --- | --- |
| x8 card (2 drives) | 5 | $624 / €564 | $492 / €445 | $132 / €119 (21 %) |
| x8 card (2 drives) | 10 | $887 / €803 | $748 / €677 | $139 / €126 (16 %) |
| x16 card, 3 drives | 5 | $756 / €684 | $617 / €558 | $139 / €126 (18 %) |
| x16 card, 3 drives | 10 | $1,125 / €1,018 | $968 / €876 | $157 / €142 (14 %) |
| x16 card, 4 drives | 5 | $890 / €805 | $743 / €672 | $147 / €133 (16 %) |
| x16 card, 4 drives | 10 | $1,355 / €1,226 | $1,210 / €1,095 | $145 / €131 (11 %) |

The receptacles are the limit for all of this: LCSC has 16 of C22454449 (8 for x8 cards, 5 for 3-drive cards, 4 for 4-drive cards),
and neither Mouser nor Digi-Key lists it. For more than one order the PSAS4F2130201TR (Digi-Key, €7.36 / €6.25 at 10) needs its footprint first.

## 3. 3D-printed shrouds and cages (mech/)

**Method.** The STL volumes are measured from `mech/out/*/print/*.stl` (the files committed on main, so each assembly's own
rev F board), so the material is not a guess. A slicer at the repository's settings (0.4 mm nozzle, 4 perimeters, 20 % infill,
2.4 mm walls) fills 60-100 % of the solid volume of such thin-walled parts: the table gives that range at 1.27 g/cm3
(PETG, about the same for ASA). Filament prices are typical retail (**E**): PETG about €22/kg, ASA about €30/kg.
No online printing service was quoted (it needs an STL upload); a service such as JLC3DP or Craftcloud would be several times the filament cost.
Hardware is from each manifest: heat-set inserts about €0.06 each, M3 screws about €0.06 each, M4 fan screws about €0.03 each (**E**).
Fans are not in the table: 120x25 mm, €10-15 for a high-pressure fan such as the Arctic P12 Max class and €25-35 for the Noctua class (**E**), 60x25 for the cage about €8.

| Assembly | Parts | Solid volume | Filament, 60-100 % fill | PETG cost | ASA cost | Inserts and screws | Fans needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| x8 card, end fan | 4 | 263 cm3 | 201-335 g | €4.4-7.4 | €6.0-10.0 | 15 inserts, 29 screws, about €3 | 1 |
| x16, 3 drives, end fan | 5 | 336 cm3 | 256-426 g | €5.6-9.4 | €7.7-12.8 | 16 inserts, 34 screws, about €3 | 1 |
| x16, 4 drives, end fan | 8 | 418 cm3 | 319-531 g | €7.0-11.7 | €9.6-15.9 | 16 inserts, 38 screws, about €3 | 1 |
| x8 card, top-feed | 4 | 212 cm3 | 161-269 g | €3.5-5.9 | €4.8-8.1 | 15 inserts, 29 screws, about €3 | 1 |
| x16, 3 drives, top-feed | 6 | 275 cm3 | 209-349 g | €4.6-7.7 | €6.3-10.5 | 18 inserts, 40 screws, about €3 | 2 |
| x16, 4 drives, top-feed | 9 | 330 cm3 | 252-419 g | €5.5-9.2 | €7.5-12.6 | 20 inserts, 46 screws, about €4 | 2 |
| 3 x8 cards, shared end fan | 4 | 310 cm3 | 236-393 g | €5.2-8.6 | €7.1-11.8 | 45 inserts, 79 screws, about €7 | 1 |
| 3 x8 cards, shared hood | 4 | 238 cm3 | 182-303 g | €4.0-6.7 | €5.4-9.1 | 36 inserts, 70 screws, about €6 | 1 |
| 3 x16 4-drive cards, shared hood | 9 | 380 cm3 | 289-482 g | €6.4-10.6 | €8.7-14.5 | 39 inserts, 103 screws, about €9 | 2 |
| Cage, 4 drives (backplane) | 9 | 357 cm3 | 272-453 g | €6.0-10.0 | €8.2-13.6 | 18 inserts, 22 screws, about €2 | 1 |
| Cage, 6 drives (backplane6) | 9 | 378 cm3 | 288-481 g | €6.3-10.6 | €8.7-14.4 | 19 inserts, 23 screws, about €3 | 1 |
| Single-drive sled (cage board) | 3 | 120 cm3 | 91-152 g | €2.0-3.4 | €2.7-4.6 | 10 inserts, 20 screws, about €2 | 1 |

Printed parts are cheap next to the boards: one card's shroud is €5-14 of filament, the 6-drive cage about €6-13. The shared styles
print each distinct part once, so the three-card volumes above already include the repeats listed in each manifest's `print_each_per_card`.
Printing time is the real cost: about 300-400 g of filament is roughly 25-40 print hours per assembly on a typical bed-slinger (**E**).
The end-fan shroud parts are split below 250 mm for the print bed; a 4-drive end-fan duct needs a bed of at least 250 x 250 mm.

## 4. Cost of a complete drive position (5-piece orders)

Everything bought for the position, landed in Germany with 19 % VAT: JLCPCB bare board A + assembly (section 2, recommended parts), PETG print at the high end of the range and a 120 mm fan at €12 for the cards (the backplane cage uses the case's own front fan). Cables $15 each (10Gtek, **E**). Drives not included. The print and fan figures are **E** and are VAT-inclusive prices at German retail.

| Option | Boards + cables, landed | Print, hardware, fan (EUR) | Total | Per drive |
| --- | --- | --- | --- | --- |
| x8 card (2 drives) + end-fan shroud | $125 / €113 | €22 | $149 / €135 | $75 / €67 |
| x16 card, 3 drives + end-fan shroud | $151 / €137 | €24 | $178 / €161 | $59 / €54 |
| x16 card, 4 drives + end-fan shroud | $178 / €161 | €27 | $208 / €188 | $52 / €47 |
| 4-drive backplane + host card + 2 cables + printed cage | $267 / €241 | €12 | $281 / €254 | $70 / €63 |
| 6-drive backplane + 1.5 host cards + 3 cables + printed cage | $360 / €325 | €13 | $374 / €338 | $62 / €56 |
## 5. What is an estimate, and what to do next

| Item | Status |
| --- | --- |
| Bare board prices at JLCPCB and PCBWay, shipping lines | **Q**, live quotes 2026-11-13; the fabs fix the price after file review |
| Front-side x8 and 3-drive cards | **E**, scaled from the quotes at the current length; the 4-drive card at 335 mm is **Q** |
| NextPCB, Eurocircuits, Multi-CB, OSH Park | **E** / not quoted (no instant price) |
| JLCPCB assembly fees | **E** from the published fee table; the real quote needs the Gerber, BOM and CPL upload in the cart |
| Receptacle, SlimSAS, eFuse, CDCDB400, TCA9554 / TCA9548 prices | **S** (LCSC, Digi-Key.de, Mouser figures read 2026-11-13; stock moves daily) |
| Small logic, MCP1703, Mini-Fit and header prices on the backplanes | **E** at typical LCSC prices (those BOM lines have no LCSC number yet) |
| Printed parts: volumes **measured** from the STL files; filament, fan and hardware prices | volumes exact, prices **E** |
| EUR figures | 0.90481 EUR per USD (ECB, 2026-11-13) |

Before ordering: put the real Gerber/BOM/CPL files of each version into JLCPCB's cart (that gives a binding assembly quote and shows
the parts it would need consigned), fill in the missing LCSC numbers in the backplane and host BOMs, and re-read the stock of
C22454449 (16 pieces) and the Digi-Key receptacle.
