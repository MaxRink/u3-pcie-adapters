# Community input: GitHub and forums

Collected 2026-11-09 for the boards in this repo: the x8 2-drive card, the x16 3- and 4-drive cards
(passive and retimer), the OCuLink cage board, the SlimSAS 8i backplane and the Minisforum
MS-01 / MS-A2 adapter.

Sources are cited, not copied. Forum posts are single-user anecdotes unless noted. Nothing below
overrides the SFF-TA-1001 spec or the rules in [`../design-rules/`](../design-rules/); where a
forum claim and the spec disagree, the spec wins and the disagreement is called out.

## TL;DR: what changes or gets confirmed in our designs

| # | Finding | Applies to | Action |
| --- | --- | --- | --- |
| 1 | U.3 drives pick their lane map from HPT0 (S15). U.2-wired adapters often ground S14–S16 together, which tells a U.3 drive "SFF-TA-1001 host" while the lanes are wired U.2 → no link. Some U.3 drives also have **no working U.2 fallback** (an HPE engineer, via the TrueNAS forum). | all | **Confirms** our approach: S15 = GND **and** true SFF-TA-1001 lane wiring. A forum mod's advice to "leave S15 open" is for U.2-wired adapters only; do not apply it to our U.3-wired boards. |
| 2 | 4 Gen4 U.3 drives on a passive x16 card trained at Gen3 but threw "PCIe timing errors" under fio; fixed by a card with an extra 6/8-pin feed. Two drives per slot without aux power worked. | x16 passive / retimer, x16 3-drive | Keep aux 12 V **populated by default** on any card with 3+ drives (drives C/D, and C on the 3-drive card). The x8 2-drive card without aux is in line with what people report working. |
| 3 | Many cheap passive cards (Glotrends, 10Gtek, StarTech, some JEYI) fail at Gen4; the clean ones in a 24 h AER test were Delock 90081/90091/90092. Cables in an M.2→U.2 chain error at Gen4 and are clean at Gen3. | all, cage, backplane | Matches rules Rev E: cabled links need a retimer. Test plan must include **AER enabled in BIOS** and a 24 h load run, not just "it enumerates". |
| 4 | Commercial Gen4 x16 → SlimSAS redriver AIC (MicroSATA SLM-1773-8I) carries: SMBus switch at 0x70 with reset, SMBus I/O expander at 0x20, 100 MHz clock buffer at 0x6C, buffered PERST#/WAKE#/CLKREQ#/PWRBRK#, on-card 12 V→3.3 V buck (5.5 A). | x16 cards, backplane host side | Good reference architecture for "all sidebands wired": per-drive SMBus behind a mux (PCA9548/TCA9548-class) so identical drive/VPD addresses don't collide, buffered PERST# per port, one clock buffer. |
| 5 | SlimSAS 8i cables **flip rows A/B** end-to-end (mwrnd/KiCad_Libraries README). SlimSAS (SFF-8654) and MCIO (SFF-TA-1016) are **not interchangeable** (L1T). | backplane, any 8i host | Backplane pin map must be checked against a straight 8i–8i cable's row flip. Cable spec: "PCIe 4.0, 85 Ω, with sidebands", SFF-8654 both ends. |
| 6 | Broadcom/MicroSATA "8i → 8× U.3 tri-mode" cables (05-60006-00 etc.) are wired for tri-mode HBAs (x1 per drive, HBA lane map). | backplane, cage | **Do not buy** these for our boards. They are not PCIe x4 SFF-9402 cables. |
| 7 | U.3 drives hit 70 °C+ within ~2 min of load in an 8-fan desktop with no direct airflow; fix was a blower on the drive. Staggering drives (not back to back) helped another user. | all, shroud | Supports the thermal study (~25 CFM for 2 drives). Keep airflow windows behind drives; the shroud must duct air **between** drives. |
| 8 | Some BIOSes (Dell Precision 7875) hang on any third-party U.2/U.3 carrier; Gigabyte MCIO ports default to SATA mode; Supermicro H13SAE-MF offers only x4x4x4x4 on one slot. | all | Note in README: check the board's bifurcation menu (x4x4x4x4, x8x4x4 for the 3-drive card) before building; host quirks are not card bugs. |
| 9 | A Gen4 link that fails training may **not** fall back to Gen3 on its own (L1T). | all | Debug procedure: force Gen3 in BIOS first, then Gen4. |
| 10 | MS-01: a slim U.2-to-x4 card with the low-profile bracket fits in the PCIe slot with a 15 mm drive and still lets the case close. MS-A2 internal U.2 adapter fits ≤7 mm drives only. | Minisforum | Confirms the PCIe-slot route for the PM1735a (15 mm). That user's card was U.2-wired; ours must be U.3-wired. |

## 1. U.3 detection, HPT0 and U.2 fallback

- **TrueNAS forum, "Connecting U.3 SSD"** —
  <https://www.truenas.com/community/threads/connecting-u-3-ssd.114002>.
  User Stilez: U.2 drives worked on shim cards and SFF-8643 cables, two U.3 drives did not.
  Moderator HoneyBadger explains the U.3 Host Port Type sensing (SFF-TA-1001 §4.2): HPT0/HPT1 both
  open = legacy "Quad PCIe" (U.2) map, HPT0 grounded = "SFF-TA-1001 single x4" map. Original
  SFF-8639 defines S14 and S16 as GND but not S15, so many adapters ground all three. Ericloewe
  relays an HPE engineer saying some U.3 drives don't implement the required U.2 compatibility.
  - This matches Max's experience (U.2 adapters fail; the Cablecc "U.3 for PM1735" adapter works)
    and the review finding in [`reviews/cage-board-review.md`](reviews/cage-board-review.md).
  - Our boards are U.3-wired, so **S15 must be GND**. The "leave it open" advice in that thread is
    the right fix only for an adapter whose lanes are wired U.2.
- **StorageReview, "Evolving storage with SFF-TA-1001 (U.3)"** (Mar 2020) —
  <https://www.storagereview.com/news/evolving-storage-with-sff-ta-1001-u-3-universal-drive-bays>.
  States U.3 devices are *required* to be backward compatible with U.2 hosts; in practice (above)
  not all are. Per-slot PERST# and clocking are managed via UBM (SFF-TA-1005) in servers.
- **Level1Techs, "Kioxia CM6 U.3 not showing up …"** —
  <https://forum.level1techs.com/t/kioxia-cm6-u-3-drive-not-showing-up-in-bios-or-windows-w-pci-e-gen4-x4-adapter-in-x4-slot/210034>.
  A StarTech U.3 x4 card showed "x0" link width with a CM6; a no-name U.2 card worked with the same
  drive. So "U.3" on the box does not mean it works, and a CM6 (unlike the PM1735a) does fall back.
- **StarTech PEX4SFF8639U3 datasheet** —
  <https://media.startech.com/cms/pdfs/pex4sff8639u3_datasheet.pdf>. U.3-only card ("not compatible
  with U.2 drives"), drives up to 15 mm, no aux power, an unexplained 2-pin header. Useful as a
  second known-U.3-wired reference besides the Cablecc card.
- **SerialTek U.2/U.3 interposer (Amaze Electronics)** — <https://amaze-electronics.com/?p=11689>.
  Analyzer interposer; lists the full sideband set it passes through (IFDET#, IFDET2#, PRSNT#,
  PERST#, WAKE#, HPT0, HPT1), SMBus on a 2×5 0.1" header at 3.3 V, REFCLK on U.FL, power via
  Molex 87427-0602. Good checklist for "every sideband accounted for".
- **Quarch U.3→U.2 adapters** — <https://quarch.com/products/gen4-u-3-to-u-2-adapter/>.
  Reverse direction (U.2 drive in U.3 host). Their SMBus flex-cable tap with removable isolation
  headers is a neat idea for our debug builds: 0R/jumper pads that isolate each drive's SMBus from
  the host.

## 2. Power and slot power

- **L1T, "Are all U.3 PCIe cards a scam?"** —
  <https://forum.level1techs.com/t/are-all-u-3-pcie-cards-a-scam/239829>.
  - recontech: 4× Micron 7450 Pro U.3 on a Glotrends PU41 (passive x16): Gen3 OK, Gen4 under fio
    → "PCIe timing errors" in IPMI. Attributed to ~25 W/drive under load exceeding what the slot
    card delivers. A JMT ADT-R37 x16→4×U.2 card with an extra 6+ pin input ran x4x4x4x4 at Gen4
    (~18–21 GB/s).
  - dazagrt: stay under the 75 W slot ceiling or connect supplementary power; two 7450s per card
    worked without it, mounted so they were not back to back.
  - Leolo: a Dell Precision 7875 froze or showed "slot empty" with every third-party card tried
    (Glotrends PU13, NFHK U.3 rev 5.0, two JEYI x16), while the same cards worked in ASRock, MSI and
    Gigabyte MC12-LE0 boards. A BTBcoin AC5929 dual-U.2 x8 card used a Pericom PI6C20400B clock
    buffer, which is a Gen3 part.
  - **Takeaway:** the x16 4-drive and 3-drive cards need aux 12 V fitted by default (it is optional
    and DNP-able per Max's rule, but should ship populated for 3+ drives). Clock buffers must be
    Gen4/Gen5-rated (our 9DBL411 is; avoid PI6C20400-class parts).
- PM1735a/HPE P50230-B21 max power: not published on any page found (Samsung's PM1735 product
  page is gone; HPE's spec page didn't load in fetch). Keep the 25 W/drive design assumption from
  [`thermal/`](thermal/) and read the actual figure from the drive label or HPE QuickSpecs.

## 3. Gen4 signal integrity: cables, adapters, redrivers

- **L1T "A neverending story" (bifurcation/cable megathread)** —
  <https://forum.level1techs.com/t/a-neverending-story-pcie-3-0-4-0-5-0-bifurcation-adapters-switches-hbas-cables-nvme-backplanes-risers-extensions-the-good-the-bad-the-ugly/171428>
  - aBav.Normie-Pleb (post 15): passive M.2→SFF-8643→SFF-8639 chain gives bus errors at Gen4 under
    load, clean at Gen3. Same for M.2→OCuLink.
  - aBav (post 508, page 26): Delock 64216 (20 cm) and 62984 (50 cm) M.2→U.2 cables error at Gen4;
    fine at Gen3.
  - cmmcnamara (post 527, page 27): MicroSATA M.2→OCuLink **redriver** adapters with a 50 cm
    MicroSATA cable or a 25 cm LINKUP active cable worked; passive M.2→OCuLink adapters gave WHEA
    errors; a Cablecc OCuLink→M.2 adapter wasn't detected. martona (528): redrivers help "but only
    do so much"; a failed Gen4 link may not fall back to Gen3.
  - mwrnd notes elsewhere that 3M 8ES8-1DF21 SlimSAS is the most reliable 8i cable they found
    (see §6).
- **L1T, "Supermicro H13SAE-MF weird bifurcation U.2 problems"** —
  <https://forum.level1techs.com/t/supermicro-h13sae-mf-weird-bifurcation-u-2-problems/202217>.
  aBav: the only passive PCIe→U.2 cards he calls Gen4-clean over 24 h are **Delock 90081 (1×),
  90091 (2×), 90092 (4×)**; 10Gtek, StarTech and Glotrends were "trash". Recommends enabling AER in
  BIOS (on AM4 it only works on CPU lanes) to see correctable errors.
- **L1T, "U.2 → M.2 adapter test results"** —
  <https://forum.level1techs.com/t/u-2-m-2-adapter-test-results/238288>. Delock 62984 cable with
  Silverstone MUA01 (one unit flaky), StarTech u2m2e125 and ADT-Link R74B all reached Gen4 with
  consumer drives. Shows unit-to-unit variance in cheap adapters.
- **Takeaway for us:** our direct-attach budget (≤50 mm finger→U.3, rules Rev E) is far shorter
  than any of these chains, which is why the passive x8/x16 drives A/B should be fine. Drives C/D on
  the x16 passive variant (~110/170 mm) sit in the zone where people see Gen4 errors; the retimer
  variant is the right default for 4 drives.

## 4. Retimers and redrivers

- **TI DS160PT801 EVM user guide (SNLU254A)** — <https://www.ti.com/lit/pdf/SNLU254>, product page
  <https://www.ti.com/product/DS160PT801>.
  - 1.17 V + 1.8 V supplies; 8.5 × 13.4 mm FCCSP-332; common clock, SRNS and SRIS supported.
  - Config over I2C/SMBus up to 1 MHz **from an external EEPROM or a controller**. The EVM uses an
    AT24C16-class EEPROM; retimer SMBus addresses set by multi-level straps (EVM: 0x20 / 0x22,
    8-bit notation).
  - EVM clocking: an LMK00334 buffer fans the slot clock to each retimer and the endpoint
    (common clock default).
  - EVM: 12 layers, 62 mil, 85 Ω data / 100 Ω clock; AC caps 220 nF on main lanes; the guide's
    layout notes keep caps within 0.5 in of the gold finger / connector (from the guide's summary;
    verify in the PDF before relying on it).
  - **Implications:** the retimer card needs an EEPROM footprint (or a header to program it), strap
    resistors for its address, a REFCLK output from the 9DBL411 to each retimer, and the retimer's
    SMBus on the same muxed bus as the drives. Its PERST# input comes from the slot PERST#.
- **meta/OpenBIC** has a DS160PT801 SMBus driver (`common/dev/ds160pt801.c`) used on Meta Yosemite
  v3.5 platforms — <https://github.com/meta/OpenBIC>. A worked example of talking to this retimer
  from a BMC; not read in full (fetch was rate-limited).
- **MicroSATA SLM-1773-8I** (Gen4 x16 → 2× SlimSAS 8i, redriver) —
  <https://www.microsatacables.com/pcie-x16-gen4-with-redriver-to-slimsas-8i-dual-port-aic>.
  Redriver chip not named. On board: SMBus switch 0x70 with reset, I/O expander 0x20 for
  out-of-band management, 100 MHz clock buffer 0x6C, buffers on PERST#/WAKE#/CLKREQ#/PWRBRK#,
  12 V→3.3 V 5.5 A buck + 3.3 V load switch. Matching cable SLM-1778-1M. (Page partly read; specs
  beyond the first part come from a summary.)

## 5. Sidebands and SMBus

Forum threads say almost nothing about PERST#/REFCLK/SMBus wiring on DIY boards; the useful inputs
are the commercial and EVM designs above:

- Mux the SMBus per drive (MicroSATA: switch at 0x70). Drives share fixed addresses (NVMe basic
  management 0x6A and VPD EEPROM 0xA6, 8-bit notation), so a shared bus with 2–4 drives collides without a mux. This backs Max's rule
  that SMBus must be wired on every card.
- Buffer PERST# per port (MicroSATA buffers PERST#, WAKE#, CLKREQ#, PWRBRK#).
- Provide isolation for debugging (Quarch's removable SMBus headers): 0R links per drive.
- Use a Gen4-rated clock buffer, one output per drive and per retimer (Leolo's Gen3-only
  PI6C20400B card froze).

## 6. Connectors, cables and cable sourcing

- **SlimSAS row flip:** mwrnd/KiCad_Libraries README (GPL-3.0, footprints not copied) —
  <https://github.com/mwrnd/KiCad_Libraries>: "a SlimSAS 8x cable flips rows". Also has SlimSAS 8i
  RA footprints (Amphenol U10A474200T/U10A474240T) and an ATX 6-pin power footprint whose pegs
  need a lot of force. Recommends 3M 8ES8-1DF21 8i cables.
- **SlimSAS vs MCIO:** <https://forum.level1techs.com/t/mz73-lm0-rev-3-x-mcio-to-u-2-cable/229754>
  — SFF-8654 and SFF-TA-1016 are not interchangeable. Gigabyte MZ73-LM0 MCIO ports default to SATA
  mode; set them to x4x4/Auto.
- **Cables that fit our boards (EU sources; check amazon.de listings by these part numbers):**
  - SlimSAS 8i ↔ 8i straight, 85 Ω, PCIe 4.0: 10Gtek "24G Internal SlimSAS SFF-8654 to SFF-8654 8i,
    85 Ω" (<https://store.10gtek.com/de/24g-internal-slimsas-sff-8654-to-sff-8654-8i-cable-sas-4-0-85-ohm-0-5-1-meter/p-7863>).
    10Gtek also sells **100 Ω** versions of the same cable; pick the 85 Ω one.
  - SlimSAS 8i → 2× U.2 (for testing a drive off a commercial host card, not for our backplane):
    Delock 82296 (0.5 m, with power) —
    <https://www.dcp.lv/en/computer-components/i-o-cards/pci-express/82296-delock-pcie-4-0-cable-slim-sas-sff-8654-8i-to-2-x-u-2-sff-8639-female-power-connector-0-5-m-delock>.
    These are U.2-wired; check S15 before use with a PM1735a.
  - OCuLink SFF-8611 → U.2 SFF-8639, 50 cm: Delock 85802 —
    <https://www.delock.com/produkt/85802/merkmale.html>. Also U.2-wired.
  - Avoid: Broadcom 05-60006-00 / MicroSATA "SlimSAS 8i → 8× U.3 tri-mode" cables
    (<https://www.microsatacables.com/cables/slim-sas/slimsas-8i-s-ff-8654-to-8-x-sff-8639-u3-cable-1-meter>)
    — HBA tri-mode wiring, x1 per drive.
  - Note: amazon.de search pages could not be fetched from this environment, so no ASINs are given;
    the part numbers above are what to search for.

## 7. Thermal

- L1T CM6 thread (above): U.3 drive >70 °C after ~2 min of load in an 8-fan desktop; needed a
  blower on the drive. Forum consensus: these drives assume server airflow.
- L1T "scam" thread: dazagrt staggered drives so they were not back to back.
- Consistent with [`thermal/`](thermal/): plan on ducted airflow through each drive gap, not case
  airflow.

## 8. Bifurcation and host quirks

- Cards with no switch rely on the host to split lanes (recontech, scam thread).
- Supermicro H13SAE-MF: only x4x4x4x4 offered on slot 6, no x8x8 / x4x4x8 (thread 202217).
- Gigabyte MZ73-LM0: MCIO ports default to SATA (thread 229754).
- Tyan S8030: BIOS "1st" slot is the one farthest from the CPU (megathread post 4).
- Dell Precision 7875: hangs with third-party carriers (scam thread).
- For the **3-drive** card, check the host offers x4x4x8 or x8x4x4 in the right order, or wire it
  so x4x4x4x4 works with one quadrant unused.

## 9. Minisforum MS-01 / MS-A2

- **L1T, "MS-01 15 mm enterprise U.2/U.3 solution"** —
  <https://forum.level1techs.com/t/minisforum-ms-01-15mm-enterprise-u-2-u-3-solution/212765>.
  mrmasternode: a slim "U.2 to PCIe 4.0 x4" card (eBay seller Mu Ji Technology) with a low-profile
  bracket holds a 15 mm Intel P4610 in the MS-01's x16 slot, below the fans, and the case closes.
  Whether the StarTech PEX4SFF8639U3 fits was asked but never answered.
- **L1T, "E3.S SSD in a Minisforum MS-A2"** —
  <https://forum.level1techs.com/t/e3-s-ssd-in-a-minisforum-ms-a2/242625>. MS-A2's U.2 adapter only
  takes ~7 mm drives; a PCIe→E3.S card was ~3 cm too long; ADT-Link R89M (PCIe→MCIO x8) suggested
  as a cabled route; extra fans on the internal headers.
- **Takeaway:** the PCIe-slot x4 card stays the main MS-01/MS-A2 route. Make it no larger than the
  slim U.2 card that is known to fit (measure one or ask the thread), U.3-wired, with the drive's
  airflow path planned since the MS-01 fans sit right there.

## 10. Open-source designs on GitHub

No open-source U.2/U.3 drive adapter, U.3 backplane or PCIe retimer card was found on GitHub. The
closest relatives, all OCuLink:

| Repo | License | What's useful |
| --- | --- | --- |
| [antmicro/oculink-pcie-adapter](https://github.com/antmicro/oculink-pcie-adapter) | Apache-2.0 | KiCad 9 OCuLink x4 → x16 slot. Amphenol G14A421211112HR (same as our cage board), 4-layer stackup, optional clock generator for SRNS/SRIS, ideal-diode power OR-ing (LTC4412 + P-FET) for USB-PD / EPS / Nano-Fit. Good pattern for our "aux 12 V OR'd via ideal diode" rule. Our OCuLink footprint already derives from antmicro/hardware-components (license in `designs/x16-u3-card/docs/ref/`). |
| [Terrails/FW16-OCuLink](https://github.com/Terrails/FW16-OCuLink) | MIT | 4-layer OCuLink 8i board, JLC04121H-1080 stackup, 1.2 mm ENIG, NP-140F; config EEPROM BR24G32FVT-3GE2. |
| [williamyang98/oculink_m2_adapter](https://github.com/williamyang98/oculink_m2_adapter) | none stated | M.2 → OCuLink with openEMS simulations of the transition; worth reading for via/launch SI. No license → reference only, don't reuse files. |
| [dbozec/my-kicad-footprints](https://github.com/dbozec/my-kicad-footprints) | not checked | SlimSAS 8i straight (Amphenol U10BH74X2X01X) and MCIO-74p vertical footprints. Candidate starting points for the backplane; check license and verify against drawings before use. |
| [mwrnd/KiCad_Libraries](https://github.com/mwrnd/KiCad_Libraries) | GPL-3.0 | SlimSAS 8i RA footprints; row-flip note. GPL: cite, don't copy into this repo unless we accept GPL for those files. |
| [alphaonex86/FPGA-CPU](https://github.com/alphaonex86/FPGA-CPU) | not checked | Has an `OCuLink_4i_SFF-8612_RA` footprint. |
| [arnarg/f3_backplane](https://github.com/arnarg/f3_backplane) | not checked | NAS backplane adding NVMe, JLC04161H-7628, gold fingers with 30° chamfer, HASL; author reports no issues. |
| [mattmillman.com OCuLink/U.2 → PCIe x4](https://www.mattmillman.com/oculink-u-2-to-pcie-x4-adapter-design-files-released/) | not stated on page | Small OCuLink/U.2 to slot adapter; author warns pads under the connector need stencil + paste. |

## 11. Gaps

- No PM1735/PM1735a-specific forum reports were found (power states, 3.3 V aux use, thermal
  limits). Read the HPE QuickSpecs for P50230-B21 or the drive label.
- No forum or repo shows a DIY board that was taken to Gen4 with AER clean on a U.3 drive. Our
  boards would be the first public data point; plan to publish the AER results.
- Reddit, ServeTheHome and EEVblog searches returned nothing beyond the L1T/TrueNAS threads above
  (search engines index few of those threads; STH forum pages were not reachable).
