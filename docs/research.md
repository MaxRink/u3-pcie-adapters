# Research

The main research write-up is a living Claude Doc:
**[U.3 x16 adapter card: options and DIY feasibility](https://claude.ai/artifact/5RgLNSQjzHduuH5KvV6yFw)** (2026-11-09).

## Key findings

- Drives: HPE P50230-B21, 3.2 TB Gen4 mixed-use SFF U.3, PM1735a-based. They have **no U.2 fallback**:
  cheap U.2-wired adapters do not initialize them, so all wiring must be true SFF-TA-1001 (U.3).
- Known-good reference: single-drive Cablecc SFF-8639 "U.3 for PM1735" x4 adapter (amazon.de/dp/B0C3CLGZDK).
  Buzz it out to verify our pin map.
- No off-the-shelf passive multi-drive U.3-wired x16 card exists. Multi-drive cards/cables are U.2-wired.
  Single x4 U.3 AICs exist (StarTech PEX4SFF8639U3, Ableconn PEXU3-132). Broadcom 95xx/96xx tri-mode HBAs
  are the only native multi-U.3 route (not passive).
- Recommended direction: passive x16 → MCIO host card (e.g. C-Payne) + small custom U.3 breakout board
  per drive, or a monolithic x16 card for 2 drives.
- Minisforum MS-01 / MS-A2: the internal bay only fits 7 mm drives; the PM1735a is 15 mm. Routes:
  U.3-wired x4 card in the PCIe slot now, plus a custom U.3-wired M.2-slot board (needs measurements of
  the stock adapters).

Design rules and SI numbers: see [`../design-rules/README.md`](../design-rules/README.md).
