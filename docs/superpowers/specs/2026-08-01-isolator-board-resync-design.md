# Isolated-Side Board Resync and Re-place — Design Spec

**Date:** 2026-08-01
**Project:** `isolator` — the single KiCad project at the repo root
**Status:** Approved
**Scope:** `isolator.kicad_pcb` and a new gate. The schematic is now frozen.
**Completes:** `2026-07-31-iso-net-split-decoupling-design.md`, whose Out of
Scope section defers exactly this work

## Overview

The schematic now carries eight per-owner branch nets joined at three net ties,
plus two capacitors the board has never seen. The board still holds the
pre-split netlist. This spec brings the board to the schematic, and takes the
opportunity — explicitly chosen rather than defaulted into — to re-place and
re-route the whole isolated side rather than patch around the existing layout.

The reason the larger scope was chosen: three of the capacitors that must move
(C12 by 26 mm, C14 and C15 by ~11 mm) are not small nudges, and the star-point
topology the net ties define is a different shape from the daisy-chained rails
the current layout grew from. Patching would leave a layout that satisfies the
netlist while still reading as the old topology.

## What is frozen

- **Board outline and the three keepouts.** Barrier x 142.72–151.03, full
  height; copper band y 78.70–124.70 (2 mm pullback from both long edges).
- **J1 and J2**, end-launched with mating faces flush to the plastic end
  panels. Their x position is set by the enclosure, not by routing convenience.
- **U1, T1 and CY1.** These three *are* the barrier crossing. Moving any of
  them re-derives the 8.3 mm creepage the whole isolation argument rests on.
- **H1–H4 and FID1–3.** Enclosure and fabrication references.
- **The entire host side**, with two localised exceptions below.
- **The schematic.** If the layout reveals an electrical problem, stop and
  report it. Do not edit `isolator.kicad_sch`.

## What is free

Everything isolated-side: U5, U6, U3, D1, D2, D6, C8–C16, NT1–NT3, R3–R10, Q1,
D3, D4.

Two host-side exceptions, both localised and neither part of the re-place:
C6 moves inboard of C7 at U4 pin 2, and C17 is placed new at T1's centre tap.

## Coordinates

`tools/place.py` works in **board-local** millimetres with the origin at the
top-left corner of the outline. Absolute = local + (86.88, 76.70). The file's
`aux_axis_origin` is (86.875, 126.7034) — bottom-left — and is *not* the origin
`place.py` uses. State which frame every coordinate is in; mixing them silently
moves parts by 50 mm.

## Placement strategy

Power flows west→east and the layout should read that way:

```
  T1 secondary ─> D1/D2 rectifier ─> NT2 ─> U5 ─> NT1 ─┬─> C12 ─> U1.20
   (barrier)          + C8            + C9   + C10/C11 ├─> C16 ─> U6 ─> NT3 ─> J2
                                                       │                + C14/C15
                                                       └─> R4/R5/R6 (south strip)
```

The three star points are placed **first**, because their position is a
topology decision rather than a proximity one; everything else hangs off a pin.
The indicator cluster (R4–R6, D3, D4, Q1, R9, R10) stays roughly where it is in
the southern strip, fed by the long `/ISO_5V_IND` branch — that branch carries
single-digit milliamps and its length is deliberately not optimised.

## The ownership budget

This table is the specification of `tools/gates/decoupling.py`. Distances are
pad-centre to pad-centre, in millimetres.

| Cap | Owns | Budget | Current | Note |
|---|---|---|---|---|
| C12 | U1.20 VBUS2 | ≤ 3.0 | **26.46** | ADuM4165 Rev. B, 10 mm lead budget |
| C13 | U1.18 VDD2 | ≤ 3.0 | 2.45 | already compliant |
| C16 | U6.1 IN | ≤ 3.0 | *new* | SLVS841F §10.2.1.2.4 |
| C15 | U6.6 OUT | ≤ 3.0 | **12.49** | SLVS841F §12.1 |
| C14 | U6.6 OUT | ≤ 6.0 | **10.87** | must be **outboard** of C15 |
| C11 | U5.1 OUT | ≤ 3.0 | 2.18 | |
| C10 | U5.1 OUT | ≤ 4.0 | 2.37 | must be **outboard** of C11 |
| C9 | U5.8 IN | ≤ 3.5 | 3.18 | |
| C8 | nearer of D1.1 / D2.1 | ≤ 4.0 | **8.08** | reservoir at the rectifier |
| C6 | U4.2 VCC | ≤ 2.5 | 4.23 | must be **inboard** of C7 |
| C7 | U4.2 VCC | ≤ 3.5 | 2.80 | |
| C17 | T1.2 centre tap | ≤ 4.0 | *new* | SLLSEP9I §11.1 |
| C4 | U1.1 VBUS1 | ≤ 3.5 | 3.11 | host side, unchanged |
| C5 | U1.3 VDD1 | ≤ 4.0 | 3.72 | host side, unchanged |

The gate asserts the distances **and** the three ordering rules (C10 outboard
of C11, C14 outboard of C15, C6 inboard of C7).

C6-inboard-of-C7 follows SN6505B §10, "a 0.1 µF by-pass capacitor should be
connected as close as possible to the device VCC pin". §11.1's competing
"bulk closest to VIN" is satisfied by C17 at the centre tap instead — that is
why C17 exists, and the two clauses stop conflicting once it does. The
schematic's `Description` properties on C6, C7 and C17 already say this; the
gate must not contradict them.

## Routing topology

Each branch net is fed **only** through its net tie. That is the whole point of
the ties and it is the one rule that cannot be traded against routing
convenience:

- `/ISO_5V` — U5.1/U5.2, C10, C11, NT1.1
- `/ISO_5V_VBUS2` — NT1.2 → C12 → U1.20
- `/ISO_5V_SW` — NT1.3 → C16 → U6.1/U6.3
- `/ISO_5V_IND` — NT1.4 → R4/R5/R6, south strip, 0.2 mm
- `/DCDC_RECT` — D1.1/D2.1, C8, NT2.1
- `/DCDC_RAW` — NT2.2 → C9 → U5.5/U5.8
- `/PORT_VBUS` — U6.6, C15, C14, NT3.1
- `/PORT_VBUS_J2` — NT3.2 → J2, D6, U3.5, R7, R8

`PWR` netclass members route at 0.5 mm; `/ISO_5V_IND` stays at the `ISO_SIDE`
default 0.2 mm. GND2 keeps its In1/In2 plane and its stitching.

## Verification

All five gates plus DRC. The re-place re-opens three that currently pass, so
none of them may be taken on trust:

1. `barrier.py` — ≥ 8.3 mm HOST_SIDE↔ISO_SIDE separation, every layer.
2. `edge_pullback.py` — no copper within 1 mm of the outline.
3. `diffpair.py` — `/PORT_D±` and `/HOST_D±` skew ≤ 0.15 mm, 90 Ω.
4. `netclass_coverage.py` — every net in exactly one side class.
5. `decoupling_nets.py` — the eight-net membership table.
6. **`decoupling.py`** — new; the ownership budget above.
7. `kicad-cli pcb drc --severity-error --schematic-parity --refill-zones`
   exits 0. Parity is meaningful now: `missing_footprint` and `net_conflict`
   were promoted to errors at the end of the schematic pass precisely so this
   step cannot pass while the board and schematic disagree.

## Risks

- **`/PORT_D±` is the exposure.** Gate 3 passes today on tuned length matching.
  Re-placing U3 or changing J2's approach re-opens it, and U3 must additionally
  stay within 5 mm of the J2 pins it protects. Keep U3 and the `/PORT_D±`
  corridor as close to their current geometry as the re-place allows, and treat
  any change there as a deliberate decision with its own verification, not as
  incidental fallout.
- **The barrier gate is creepage-aware and non-obvious.** It measures around
  the routed slot under T1 rather than straight-line on F.Cu. Nothing in this
  spec should move T1 or that slot, but a re-placed part drifting west toward
  the barrier can fail it in ways a straight-line intuition will not predict.
- **Three star points are three new single points of failure.** A tie whose pad
  is unrouted on one side leaves a branch floating. DRC catches an unrouted
  net; it does not catch a tie routed on only one of its two pads if the other
  is fed by a pour. Route ties explicitly, never by pour.
- **The board's zone fills are stored.** `kicad-cli pcb drc` checks against the
  stored fill, so a wave of clearance or dangling errors after moving parts
  usually means stale fills. Refill before judging.

## Out of Scope

- Any schematic change. The schematic is frozen for this pass.
- Fabrication outputs. Gerbers, drill, CPL and stencil are a later step.
- R3's trip band, and the R9-DNP/R10-populated PGOOD arrangement. Both are
  documented decisions carried to bring-up.
- The host side beyond C6's move and C17's placement.
