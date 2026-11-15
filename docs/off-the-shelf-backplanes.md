# Off-the-shelf U.2/U.3 backplanes and cages (research, 2026-11-15)

Question: is there an existing Gen4 U.2/U.3 backplane or drive cage we could reuse instead of building our own
([u3-backplane](../designs/u3-backplane)), needing only breakout cables (SlimSAS / MCIO / OCuLink) to the host card
or the H12SSL, plus 3D-printed mounting?

Target: Samsung PM1735(a) as HPE P50230-B21 (U.3, 15 mm, Gen4 x4), EPYC on Supermicro H12SSL, direct attach via
bifurcation, no tri-mode HBA.

## Short answer

Yes, a few usable units exist, and the best one is a cheap experiment. But **none of them says it is wired for
U.3-only operation**, and that is exactly the failure mode we already hit with cheap U.2 adapters. So buy one unit and
test it with one drive before deciding anything. Keep our own backplane as the fallback. It is still the only option
that is guaranteed to wire S15 (HPT0) to ground with PCIe on the SFF-TA-1001 pins, and the only one with per-drive
eFuses, top loading for the Jonsbo N5, and a 6-drive module.

Recommended order:

1. **ICY DOCK ExpressCage MB324V4P-B** (4 x 15 mm, 2 x SlimSAS 8i, one PCIe 8-pin, hot plug, about €300-350). This
   is the closest drop-in match: same host connector as our host card (SlimSAS 8i, SFF-9402 Rev 1.1), one power
   cable, 5.25" body that a printed bracket can hold. Test it first.
2. **SilverStone RAC-BP-304N** (bare 4-bay Gen4 backplane, 2 x SlimSAS 8i, about £126). Cheapest and closest
   to "a board plus a 3D print", since it has no shell or trays. It is only specified for U.2. Power connector,
   sideband and mounting holes are not on any page we could read.
3. **ICY DOCK ToughArmor MB699VP-B V3** (4 x 15 mm, 4 x OCuLink 4i, 2 x SATA power, about €300-400). Fallback if the
   ExpressCage fails, or if OCuLink cables suit better. Needs 4 cables instead of 2.

Server OEM backplanes (HPE, Lenovo, Dell, Supermicro) are not worth it for this build. Details are below.

## The U.3 compatibility problem

This decides everything else, so it comes first.

- By spec, a U.3 drive works in a U.2 bay. It sees HPT0 (S15) open and falls back to U.2 mode with PCIe on the
  E-pins. Our earlier test found that Max's HPE PM1735 drives **do not initialize** on cheap U.2 adapters. They
  only work on a U.3-wired adapter (S15 grounded, PCIe on the SAS-pin positions).
- A TrueNAS moderator explains the likely cause: some cheap U.2 adapters ground S15 together with S14/S16, which makes
  the drive pick the U.3 pinout while the lanes sit on the U.2 pins. An HPE engineer is also quoted as saying that
  "some U.3 disks do not actually implement the required compatibility with U.2"
  ([TrueNAS thread](https://www.truenas.com/community/threads/connecting-u-3-ssd.114002)). We cannot tell which case
  ours is without a test on a clean U.2 bay.
- Every retail cage below says "U.2/U.3" only in marketing text. None mentions SFF-TA-1001, HPT0/IfDet or U.3-only
  drives. The ICY DOCK FAQ says that with Broadcom or Intel tri-mode cards, U.2 drives need a "U.2 enabler cable"
  that "reverts the pinout back to standard U.2". That suggests the cage passes the host's lane mapping straight
  through, so on a direct-attach host it probably acts as a **U.2 bay**
  ([MB324V4P-B page](https://global.icydock.com/product_416.html)). This is an inference.
- So: if the PM1735s work in a clean U.2 bay, all the retail cages work. If they only work in U.3 wiring, none of the
  retail cages are a safe bet, and our own backplane (or a tri-mode HBA) is the answer.

**Test plan, about €350 at risk and returnable in the EU:** buy one MB324V4P-B from a shop with a 14-day return
(Scan UK, LDLC, Amazon.de). Connect it with one SlimSAS 8i to 8i cable to the passive host card, or to a bought
x16-to-SlimSAS card with SFF-9402 pinout. Set x4x4x4x4 bifurcation. Insert one PM1735, check that `lspci` shows it at
16 GT/s x4 and that `nvme list` works, then run a short fio run and check AER. If it fails, also try with S15
grounded on a known-good single adapter, to tell a wiring problem from a firmware one.

## Follow-up (2026-11-15): do tri-mode / U.3 bays work without a tri-mode HBA?

Max asked whether cages and backplanes sold explicitly as tri-mode or U.3 should just work. Short answer: a **real
x4 U.3 bay** is electrically the same thing as our backplane, so yes in principle. But the parts sold as "tri-mode
compatible" are mostly not U.3 bays, and the real U.3 bays (server spares) need four things sorted first.

**What a U.3 bay is.** SFF-TA-1001 puts PCIe lanes 0 and 1 on the SAS pin positions and lanes 2 and 3 on the E-pins,
with S15 (HPT0) grounded so the drive picks that map. A U.3 (tri-mode) backplane is passive copper from the cable
connector to those pins. Nothing in the bay itself needs an HBA.

**Why vendors still say "tri-mode controller required":**

1. **Lane count.** Many tri-mode bays are x1 or x2 per drive (HPE "x1 Tri-Mode" P27194-B21 / P39781-001, Lenovo
   "U.3 x1" mode). Only x4 bays are any use to us.
2. **AC coupling on lanes 0/1.** In U.3 mode the drive has no capacitors on its lane 0/1 transmitters, so the host
   must put them on its receive side (our [design-decisions.md](design-decisions.md) G1, 220 nF on PER0/PER1).
   Tri-mode HBAs have them. A motherboard root port or a plain SlimSAS riser does not, because normal PCIe puts the
   caps at the transmitter. So a U.3 bay cabled straight to the H12SSL would run lanes 0/1 DC-coupled: out of spec,
   likely no link or a degraded one. **Fix:** add the caps on our host card (it is ours, so that is a BOM change)
   or on a small inline board. Bought passive SlimSAS cards will not have them.
3. **Management (UBM, SFF-TA-1005).** HPE Gen10 Plus / Gen11 tri-mode backplanes carry a UBM controller that the
   tri-mode controller talks to. Whether PERST#, REFCLK and drive power pass straight through from the SlimSAS cable
   or are gated by the UBM controller is not documented publicly. If they are gated, the backplane needs a small
   I2C master to set it up. Unknown until we have one on the bench.
4. **Power and sideband connector.** OEM backplanes take power and sideband through a proprietary connector from
   the motherboard. Pinouts are not published, so we would have to buzz one out and build an adapter.

**What "tri-mode compatible" means on retail cages.** ICY DOCK's own advisory says certain Intel and Broadcom
tri-mode cards use "a different pinout" and that the U.2 enabler cable "reverts the pinout back to standard U.2"
([advisory](https://it.icydock.com/product/faq/icy_dock_nvme_enclosures_tri-mode_compatability_announcement_update_it.pdf)).
The cages are U.2 bays: they work with a tri-mode card only in NVMe mode, through a cable that converts the card's
output to U.2. So ICY DOCK's "U.2/U.3" and "tri-mode" labels do not mean U.3 wiring. With a plain root port they are
U.2 bays, and our drives would have to run in U.2 fallback, which is exactly what the test answers.

### ICY DOCK ToughArmor MB508V5P-B (Max's link)

[de.icydock.com/product_1417.html](https://de.icydock.com/product_1417.html):
8 x U.2/U.3 at 7 to 15 mm in two 5.25" bays, PCIe **Gen5** x4 per drive, 4 x MCIO 8i (SFF-TA-1016) with SFF-9402
Rev 1.1 pinout, power one PCIe 8-pin plus one PCIe 6-pin, hot plug, one 80 mm fan, 146 x 84 x 158.2 mm.
"Compatible with tri-mode HBA/RAID cards (NVMe mode only)", which is the same U.2-bay pattern as above.
**€989.90** on Amazon.de (sold by ICY DOCK Germany).

- For: 8 drives in one unit, Gen5 means more signal margin at Gen4, one big fan, good fit for 12 drives as 8 + 4.
- Against: about 2x the price per bay of the MB324V4P-B (€124 vs €66), MCIO instead of SlimSAS, so it needs
  SlimSAS-to-MCIO cables (about €28-50 each on Amazon.de) or an MCIO host card, and the same U.2-fallback question.
- Verdict: a good choice **after** the MB324V4P-B test passes, if you want 8 bays per box. Not a way around the test.

### Server spares, re-checked with adapters allowed

If we accept making an adapter for power and sideband, these become real options:

| Part | Lanes | Data connectors | Price (DE) | What we would have to adapt |
|---|---|---|---|---|
| **HPE DL380 Gen11 8SFF x4 Tri-Mode U.3 BC cage kit, P48814-B21** | x4 per drive, true U.3 | not confirmed for Gen11 (Gen10 Plus x4 boards have 4 x SlimSAS) | **€203.99 new**, [Tonitrus on eBay.de](https://www.ebay.de/itm/146543196497), 30-day returns; also [Vulpano €226.09](https://www.ebay.de/itm/287526552846) | Power + sideband connector (pinout unknown), UBM behaviour, caps on PER0/1 at the host card |
| HPE 8SFF U.3 x4 backplane + cage, DL380 Gen10 Plus, P24047-001 | x4, U.3 | 4 x SlimSAS (Gen10 Plus) | €384 used ([eBay.de](https://www.ebay.de/itm/226945721251)) | same |
| HPE 8SFF U.3 x4 backplane only, P31226-001 | x4, U.3 | 4 x SlimSAS | €67.50 refurb at [GEKKO](https://www.gekko-computer.de/en/p/HPE-NVME-Backplane-8x-SFF-U-3-x4-with-4-slimSAS-Ports-P31226-001-en) (sold out) | same, plus a printed cage and rails |
| HPE 4SFF U.3 "Premium" backplane Gen10 Plus, P25435-001 | probably x4 (not stated) | not stated | €104 refurb, [GEKKO on eBay.de](https://www.ebay.de/itm/377623511088), 30-day free returns | same |
| HPE x1 Tri-Mode U.3 (P27194-B21, P39781-001, P26431-B21) | **x1** | | €267-300 | not usable: one lane per drive, HPE says "No NVMe Direct Attach" |
| Lenovo AnyBay, Supermicro hybrid NVMe (BPN-SAS3-826A-N4, BPN-NVME4-*), HPE x4 U.2 (P26932-B21, 826689-B21 €94) | x4, **U.2** | SlimSAS / OCuLink | €30-100 | Same U.2-fallback question as the ICY DOCK cages. Supermicro uses plain 4-pin Molex power, so it is the easiest spare if the test passes. |

The HPE x4 U.3 cages are the most interesting find. They are true U.3 at x4, they take **HPE basic carriers**,
which is what Max's HPE P50230-B21 drives already sit in, and the Gen11 kit is new at about €204 with 30-day returns
from a German seller. The work left is the adapter: buzz out the power/sideband connector, add 220 nF on PER0/PER1
per drive on our host card, and check whether the UBM controller passes PERST# and REFCLK through on its own.
That is a much smaller job than our full backplane (no receptacles, eFuses or mux), but it is not zero, and the
pinouts are not public.

### x2 per drive, and what the H12SSL offers

Max said x2 per drive is enough for speed. The H12SSL manual (Rev 1.0a) offers only **Auto, x16, x8x8, x4x4x8 and
x4x4x4x4** on the x16 slots and **x4x4** on the x8 slots, with no x2 modes
([manual](https://janit.iki.fi/useful/MNL-2314.pdf); the option list comes from a summary of the BIOS chapter, so
confirm in the BIOS). So:

- An **x2 bay still works**: a x4 root port trains down to x2 on a bay that only wires two lanes. But it does not
  save lanes or slots, because the board cannot split a slot finer than 4 x4. With x2 you would still get 4 drives
  per x16 slot.
- Getting more than 4 drives per slot at x2 needs a **PCIe switch card** (Broadcom PEX88xxx / Microchip Switchtec
  class), not bifurcation. That is a different and more expensive part.
- x2 U.3 bays (for example HPE "x4/x2 Tri-Mode" cages) put both lanes on the SAS-pin positions, so the PER0/PER1
  cap problem applies to every lane they use.
- Conclusion: x2 spares are acceptable but give no saving on this board. Prefer x4 parts at the same price.

**Onboard SlimSAS on the H12SSL-i:** JNVMe0 is one SlimSAS x8 that carries 2 NVMe drives at x4 when jumper JCFG1 is
set to NVMe (pins 2-3). That is a free test port: one cable from JNVMe0 to the cage tests 2 drives without any
add-in card. The connector's pinout is not printed in the manual, so if the cage does not see a drive there, try
the add-in card before blaming the drive.

## Candidates

### Retail drive cages (5.25" bay)

| Unit | Bays / height | Gen | Host connectors | Power | Hot plug, LEDs, fans | Size (D x W x H) | Price |
|---|---|---|---|---|---|---|---|
| **ICY DOCK ExpressCage MB324V4P-B** (2025) | 4 x 15 mm | 4 | 2 x SlimSAS 8i (SFF-8654), SFF-9402 Rev 1.1, 2 drives per port | 1 x PCIe 8-pin | Hot plug yes (OS rescan); power/activity LED per bay; 2 x 40x40x20 fans on a 3-pin header | 146 x 150.2 x 41.3 mm, 643 g | £349.99 at Scan UK; also LDLC, Amazon |
| **ICY DOCK ToughArmor MB699VP-B V3** | 4 x 15 mm | 4 | 4 x OCuLink 4i (SFF-8612), SFF-9402 Rev 1.1 | 2 x SATA 15-pin | Hot plug yes; LEDs; 2 x 40x40x20 fans, 3-speed switch | 140.3 x 146 x 41.3 mm, 911 g | about €300-400 (LDLC, B&H) |
| ICY DOCK ToughArmor MB699VP-B V2 | 4 x 15 mm | 4 | 4 x OCuLink 4i, SFF-9402, "no Tri-mode support" | 2 x SATA | as V3, 8000 rpm fans | 150.3 x 146 x 41.3 mm | older, often cheaper used |
| ICY DOCK MB699VP-B (V1) | 4 x 15 mm | 4 | 4 x Mini-SAS HD (SFF-8643), legacy pinout | 2 x SATA | 4800 rpm fans | 140.3 x 146 x 41.3 mm | older |
| ICY DOCK ToughArmor MB998V4P-B | 8 x **7 mm** | 4 | 4 x SlimSAS 8i | 1 x PCIe 8-pin | hot plug | 150 x 146 x 41.3 mm | **too thin for 15 mm drives** |
| ICY DOCK flexiDOCK MB021VP-B | 1 x 15 mm | 4 | 1 x SlimSAS 4i | | | 3.5" bay | single bay, "no Tri-mode support" |
| Tekram TK-4U11 | 4 | 4 | 2 or 4 x OCuLink (the page contradicts itself) | 2 x SATA | 2 fans | 159 x 145 x 41.6 mm | MSRP $350 |
| Kingwin K-49NVMO / K-49NVMS | 4 | 4 | 4 x OCuLink, or 4 x SlimSAS (sources disagree) | 2 x SATA | 2 x 40x20 fans | 159 x 145.8 x 41.6 mm | $259 (AVADirect, US) |
| Delock 47235 | 4 x 15 mm | 4 | 4 x Mini-SAS HD (SFF-8643) | 1 x SATA | **no hot swap** (FAQ); 2 x 35 mm fans | 146 x 139 x 42 mm | EU retail, check price |
| StarTech 4U2525-SAS-BACKPLANE | 4 | 3 | 4 x Mini-SAS HD | | | 5.25" | Gen3, skip |

Notes:

- No retail cage documents any sideband signal (SMBus, PERST#, REFCLK handling, VPP). They pass PCIe lanes, refclk
  and PERST# through from the cable and drive LEDs locally. That is fine for direct attach, but nothing isolates the
  drives' shared SMBus address, and there is no per-drive power switching (no eFuse, unlike ours).
- Hot plug works only as far as the host supports it. EPYC on the H12SSL does surprise hot plug only when the BIOS
  enables it, and ICY DOCK says a manual OS rescan is still needed.
- All are front-loading 5.25" bodies about 146 mm deep. They do **not** match the top-loading N5 compartment layout
  in [u3-backplane](../designs/u3-backplane). A printed frame could hold one or two upright behind the front fans,
  with drives inserted from the side or top. That needs a fit check against the N5.

### Bare backplanes

| Unit | Bays | Gen | Host connectors | Power | Price | Notes |
|---|---|---|---|---|---|---|
| **SilverStone RAC-BP-304N** | 4 | 4 (x4 per drive) | 2 x SlimSAS 8i | not stated | £125.99 at Scan UK | For SilverStone RM21/RM22/RM43/RM61 rack chassis. Specified "U.2 (SFF-8639)" only. SilverStone's own page did not load, so power connector, mounting holes and sideband are unknown. Best fit for "board + print" if it is U.3-safe. |
| Athena BP-U24NVME8525 | 4 | ? | ? | ? | $199 (DigiKey marketplace) | "4Bay NVMe U.2" backplane; datasheet not read. US only. |

### Server OEM spares (eBay, refurbishers)

| Unit | What it is | Why not |
|---|---|---|
| HPE 8SFF U.3 **x1** Tri-Mode BC backplane (P39781-001, kit P26431-B21 etc.) | 8 bays with cage, $299 from Shenzhen on eBay, $590 refurbished in the US | x1 per drive for NVMe, UBM managed, and the kit says "No NVMe Direct Attach support". It needs an HPE tri-mode controller. Unusable. |
| HPE 8SFF Tri-Mode U.3 **x4** BC backplane kit | x4 per drive version | Still a UBM (SFF-TA-1005) backplane with HPE power and sideband harnesses. No public pinout. High risk for a small gain. |
| Lenovo ThinkSystem 8x2.5" AnyBay / U.3 backplanes | NVMe connectors per drive pair, separate SAS and power connectors | Lenovo's U.3 configurations route through an 8i SFF HBA/RAID adapter. The power connector is proprietary and not documented publicly. |
| Supermicro BPN-NVMe3 / BPN-NVME4 (e.g. BPN-NVME4-216N-S24, BPN-NVME4-HS119N-S4R) | U.2 direct-attach (Gen3/Gen4) with plain 4-pin Molex power and OCuLink/SlimSAS | Standard power, but they are U.2 wired (same open question as the retail cages) and sized for 1U/2U 24-bay chassis. The 4-slot 1U part (HS119N-S4R) is the only small one. Worth a look only if the U.2 test passes and it is cheaper than ICY DOCK. |
| Dell 14G/15G NVMe and "Universal" backplanes | | Proprietary power and sideband, often behind a PERC or PCIe switch. Skip. |

Community: the 45HomeLab "NVMe U.3 Backplane / solution" thread ended with no backplane. 45Drives staff said they had
no U.3 systems. The one working setup was a DIY SlimSAS-to-U.2 breakout cable with a Molex power tap and a printed
15 mm bracket, tested with U.2 drives only
([45HomeLab](https://forum.45homelab.com/t/nvme-u-3-backplane-solution/723)).

## Cables and host side

- MB324V4P-B and RAC-BP-304N take the same cable as our backplane: SlimSAS 8i (SFF-8654) to SlimSAS 8i, 85 ohm, with
  SFF-9402 pinout on both ends. ICY DOCK recommends at most 50 cm. Expect about €30-60 each from 10Gtek,
  Micro SATA Cables or C-Payne. Avoid Broadcom tri-mode cables (05-60006 and similar), which are wired for the HBA's
  pinout (see the community findings in PR #10).
- Our passive host card ([host.py](../designs/u3-backplane/gen/host.py)) already outputs 2 x SlimSAS 8i with the
  SFF-9402 Table 6-2 pinout, so either unit works with it unchanged (2 drives per port, 4 drives per x16 slot).
  The bought retimer card (LR-LINK LRNV9F24 class) also fits.
- MB699VP-B V3 needs 4 x OCuLink 4i cables, or 2 x SlimSAS 8i to 2 x OCuLink 4i splitters (ICY DOCK sells one).
- Power: one PCIe 8-pin per MB324V4P-B, or 2 x SATA per MB699VP-B V3. A PCIe 8-pin carries 150 W, which covers
  4 x 25 W drives. Check how many spare PCIe 8-pin leads the N5's PSU has.

## Cost against our own backplane

Prices from [pricing.md](pricing.md) (JLCPCB, landed, assembled).

| For 12 drives | Hardware | Cables | Approx. total | Notes |
|---|---|---|---|---|
| 3 x ICY DOCK MB324V4P-B | about €1,000-1,050 | 6 x SlimSAS 8i, about €200-300 | **€1,200-1,350** | Ready to use. U.3 compatibility not proven. Front-loading 5.25" bodies need a printed frame. |
| 3 x SilverStone RAC-BP-304N | about €450 | 6 x SlimSAS 8i, about €200-300 | **€650-750** plus a printed cage with trays/guides | Cheapest. Unknown power, mounting and U.3 behaviour. |
| Own 6-drive backplane, 5 boards assembled (use 2) | about €850-900 for the order | 6 x SlimSAS 8i | **€1,050-1,200** plus printed cage | Wiring is U.3-correct by design. Per-drive eFuse, PERST# gating and SMBus mux. Top-loading N5 layout. Not built or tested yet. |

Cost is roughly a wash. The real trade is **risk**. The retail parts may not work with these HPE drives at all, while
our board may have first-spin layout errors. A single MB324V4P-B test answers the first question for about €350 and
keeps the cage as a usable part even if we build our own boards (a 4-bay box for U.2 drives).

## Recommendation (updated after Max's follow-up)

Two parallel paths, both returnable:

1. **U.2-fallback test, Amazon.de (cart below, €333.04):** MB324V4P-B + passive x16 to 2 x SlimSAS 8i card + two
   SlimSAS 8i cables. One PM1735 on the H12SSL at x4x4x4x4. If it links at Gen4 x4, every U.2 cage and spare
   above is usable, including the MB508V5P-B for 8 bays.
2. **True U.3 path, eBay.de (about €204):** one HPE P48814-B21 x4 U.3 BC cage from Tonitrus. Buzz out the power and
   sideband connector, check which data connector Gen11 uses, and check the UBM behaviour. Drives go in with their
   HPE carriers. It needs caps on PER0/PER1 at the host, so test it with our host card (caps added) or a
   single-port adapter with caps, **not** with the bought passive card.

If (1) passes, buy cages. If (1) fails and (2) can be adapted, the HPE cage replaces most of our backplane design:
we would only build a host card with caps plus a small power/sideband adapter. If both fail, our own backplane stays
the plan.

## Shopping cart (Amazon.de, 2026-11-15)

All three items show "Returnable until Jan 15, 2027 or within 14 days from receipt (whichever is later)". The cart
is already filled in the built-in browser on Max's Mac (not signed in, nothing ordered).

| Item | Link | Seller | Qty | Price |
|---|---|---|---|---|
| ICY DOCK ExpressCage MB324V4P-B | [B0FNX34FXT](https://www.amazon.de/dp/B0FNX34FXT) | priz24 (third party) | 1 | €263.07 |
| HiFiber PCIe 4.0 x16 to 2 x SFF-8654 8i adapter (passive, needs x4x4x4x4) | [B0DPQ4499B](https://www.amazon.de/dp/B0DPQ4499B) | H!Fiber-EU, shipped by Amazon | 1 | €27.99 |
| HiFiber SFF-8654 8i to 8i cable, PCIe 4.0, 85 ohm, 0.5 m | [B0DPJRKXML](https://www.amazon.de/dp/B0DPJRKXML) | H!Fiber-EU, shipped by Amazon | 2 | €41.98 |
| **Total** | | | | **€333.04** (shipping may apply on the third-party cage) |

Options:

- Swap the HiFiber card for the **ICY DOCK EXLink MB308A** (x16 to 2 x SlimSAS 8i with redriver, SFF-9402 Rev 1.1,
  sold by ICY DOCK Germany, [B0FS7NKFRX](https://www.amazon.de/dp/B0FS7NKFRX), €277.90) if you want the vendor-matched
  pair. Total then €583.
- Retimer option: KALEA-INFORMATIQUE retimer card, 2 x SlimSAS 8i, sold by Amazon,
  [B0GTF8RRYD](https://www.amazon.de/dp/B0GTF8RRYD), €175.90.
- Power: the cage needs one **PCIe 8-pin** lead from the PSU. No adapter is in the cart. Do not feed it from a single
  SATA-to-PCIe adapter (4 x 25 W is too much for one SATA plug).
- Not in the cart because it is not on Amazon: HPE P48814-B21 cage at Tonitrus on eBay.de, €203.99, free shipping,
  30-day returns (buyer pays return shipping).

## Sources

- ICY DOCK MB324V4P-B: [product page](https://global.icydock.com/product_416.html),
  [manual](https://global.icydock.com/vancheerfile/files/installation_guide/MB324V4P-B_webpage_usermanual.pdf),
  [Scan UK](https://www.scan.co.uk/products/4-bay-icy-dock-expresscage-mb324v4p-b-4x-pcie-40-u2-u3-ssds-hot-swappable-2-x-slimsas-8i-sff-8654),
  [StorageNewsletter](https://www.storagenewsletter.com/2025/12/10/icy-dock-expresscage-mb324v4p-b-mobile-rack-for-4-pcie-4-0-u-2-u-3-nvme-ssds-in-external-5-25-inch-optical-drive-bay/)
- ICY DOCK MB699VP-B V3: [product page](https://global.icydock.com/product_326.html),
  [U.2/U.3 product list](https://global.icydock.com/products-c5-s47-i0-p2.html),
  MB998V4P-B [product page](https://global.icydock.com/product_423.html)
- SilverStone RAC-BP-304N: [Scan UK](https://www.scan.co.uk/products/4-bay-silverstone-rac-bp-304n-server-backplane-4x-25-35-pcie-40x4-nvme-u2-support)
- Tekram TK-4U11: [tekram.com](https://www.tekram.com/tk-4u11-u2-nvme-backplane-cage)
- Kingwin K-49NVMO: [kingwin.com](https://www.kingwin.com/?p=15489),
  [AVADirect K-49NVMS](https://avadirect.com/K-49NVMS-5-25-bay-for-4-x-2-5-U-2-Nvme-SlimSas/Product/17588047)
- Delock 47235: [delock.com](https://www.delock.com/produkt/47235/merkmale.html)
- Athena BP-U24NVME8525: [DigiKey](https://azcus.digikey.com/en/products/detail/athena-computer-power-corporation/BP-U24NVME8525/28009812)
- HPE: [ITCreations P39781-001](https://www.itcreations.com/product/134306),
  [eBay P39781-001](https://www.ebay.com/itm/388658696340),
  [P26431-B21](https://expresscomputersystems.com/products/hpe-proliant-dl360-gen10-plus-8sff-x1-tri-mode-24g-nvme-u-3-bc-backplane-kit-p26431-b21),
  [CDW x4 kit](https://cdw.com/product/hpe-8sff-tri-mode-u.3-x4-basic-carrier-backplane-kit-backplane/7300610)
- Lenovo: [SR665 V3 backplane connectors](https://pubs.lenovo.com/sr665-v3/internal_connectors_drive_backplanes),
  [SR635 V3 U.3 cabling](https://pubs.lenovo.com/sr635-v3/8_u.3_cabling)
- Supermicro: [BPN-NVMe3-216A-N4 manual](https://www.supermicro.com/manuals/other/BPN-NVMe3-216A-N4.pdf),
  [BPN-NVME4-HS119N-S4R](https://www.sabrepc.com/BPN-NVME4-HS119N-S4R-Supermicro-S5188229),
  [BPN-NVME4-216N-S24 on eBay](https://www.ebay.com/itm/158338596519)
- Community: [TrueNAS "Connecting U.3 SSD"](https://www.truenas.com/community/threads/connecting-u-3-ssd.114002),
  [45HomeLab U.3 backplane thread](https://forum.45homelab.com/t/nvme-u-3-backplane-solution/723)

Not verified: SilverStone RAC-BP-304N power, mounting and sideband (vendor page did not load); ICY DOCK's tri-mode and
cable compatibility PDFs; current EU prices for MB699VP-B V3 and Delock 47235; whether the H12SSL BIOS enables NVMe
hot plug.
