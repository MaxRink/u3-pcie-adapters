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

## Recommendation

1. Order one **MB324V4P-B** and one SlimSAS 8i cable now and run the test above with one PM1735.
2. If the drive comes up at Gen4 x4: the U.2-compatibility worry is gone. Consider 3 x MB324V4P-B (or the cheaper
   RAC-BP-304N in a printed cage) instead of fabbing the backplanes. Keep the host card, since it is needed either way.
3. If the drive does not come up: return the cage. Our own U.3-wired backplane stays the plan, and the result
   confirms the S15 decision documented in [design-decisions.md](design-decisions.md).

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
