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

Three host-side exceptions, all localised and none part of the re-place:
C6 moves inboard of C7 at U4 pin 2, C17 is placed new at T1's centre tap, and
**C7 moves ~3.5 mm north to let C6 take the inboard slot**.

C7's move was not in the original freeze list; it was added on 2026-08-01 when
placement proved the ordering rule unsatisfiable with C7 fixed. C7 sat 2.06 mm
from U4.2 and an exhaustive 0.02 mm / 1° sweep put C6's floor at 2.19 mm — short
by 0.13 mm, with no rotation closing it. Unfreezing C7 is sound because the
freeze existed to protect *working host routing*, and `/VBUS_HOST` carries no
routed copper at this point in the plan — it was ripped wholesale in Task 3. The
arrangement is also what the schematic's own `Description` properties on C6 and
C7 already specify, so the placement was the thing contradicting the design
record, not the rule.

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
pad-centre to pad-centre, in millimetres, as `pcbnew` reports them — an earlier
draft carried hand-parsed figures that were off by up to 0.9 mm, and the gate's
numbers supersede them.

**C8 is measured to the *farther* of the two diode cathodes, not the nearer.**
D1.1 and D2.1 sit 6.21 mm apart and both feed the reservoir, so a "nearest
wins" rule would let C8 hug one diode while sitting 5.6 mm from the other and
still report compliant. The farther-of rule is what actually expresses
"reservoir at the cathode junction". D1 and D2 are both free parts, so the
placement task can also close that 6.21 mm gap rather than only moving C8.

| Cap | Owns | Budget | Current | Note |
|---|---|---|---|---|
| C12 | U1.20 VBUS2 | ≤ 3.0 | **26.21** | ADuM4165 Rev. B, 10 mm lead budget |
| C13 | U1.18 VDD2 | ≤ 3.0 | 2.45 | already compliant |
| C16 | U6.1 IN | ≤ 3.0 | *new* | SLVS841F §10.2.1.2.4 |
| C15 | U6.6 OUT | ≤ 3.0 | **11.93** | SLVS841F §12.1 |
| C14 | U6.6 OUT | ≤ 6.0 | **10.04** | must be **outboard** of C15 |
| C11 | U5.1 OUT | ≤ 3.0 | 2.18 | |
| C10 | U5.1 OUT | ≤ 4.0 | 2.55 | must be **outboard** of C11 |
| C9 | U5.8 IN | ≤ 3.5 | 3.48 | |
| C8 | **farther** of D1.1 / D2.1 | ≤ 4.5 | **5.62** | reservoir at the cathode junction |
| C6 | U4.2 VCC | ≤ 2.5 | 3.87 | must be **inboard** of C7 |
| C7 | U4.2 VCC | ≤ 3.5 | 2.06 | |
| C17 | T1.2 centre tap | ≤ 4.0 | *new* | SLLSEP9I §11.1 |
| C4 | U1.1 VBUS1 | ≤ 3.5 | 2.40 | host side, unchanged |
| C5 | U1.3 VDD1 | ≤ 4.0 | 3.06 | host side, unchanged |

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

All six gates plus DRC. The re-place re-opens three of them, so none may be
taken on trust:

1. `barrier.py` — ≥ 8.3 mm HOST_SIDE↔ISO_SIDE separation, every layer.
2. `edge_pullback.py` — no copper within 1 mm of the outline.
3. `diffpair.py` — `/PORT_D±` skew ≤ 0.15 mm at 90 Ω. `/HOST_D±` is a known
   pre-existing failure (~2.9 mm) on frozen host routing; see Risks.
4. `netclass_coverage.py` — every net in exactly one side class.
5. `decoupling_nets.py` — the eight-net membership table.
6. **`decoupling.py`** — new; the ownership budget above.
7. `kicad-cli pcb drc --severity-error --schematic-parity --refill-zones`
   exits 0. Parity is meaningful now: `missing_footprint` and `net_conflict`
   were promoted to errors at the end of the schematic pass precisely so this
   step cannot pass while the board and schematic disagree.

## Risks

- **Gate 3 does not pass today, and never did.** An earlier draft of this spec
  claimed it did. On `main`, before any of this work, it reports ~2.9 mm
  intra-pair skew on **both** pairs against its 0.15 mm limit —
  `/HOST_D±` 49.071 vs 51.980 mm, `/PORT_D±` 49.283 vs 52.146 mm. The pairs
  were never length-matched.

  **Ruling (2026-08-01):** `/PORT_D±` is ripped by this plan anyway, so Task 6
  routes it to meet the 0.15 mm limit. `/HOST_D±` stays frozen — it is working
  host-side routing this plan deliberately does not touch — and remains a known,
  recorded failure. Task 7's acceptance is therefore "Gate 3 passes on
  `/PORT_D±`", not "Gate 3 passes".

  For scale: 2.9 mm is roughly 19 ps at USB high speed, comfortably inside
  USB 2.0's real intra-pair budget. The 0.15 mm limit is a self-imposed rule
  from the original layout spec, not a USB requirement. That is context for a
  future decision about the host pair — it is **not** a licence to relax the
  gate, which stays where it is.

### Ruling (2026-08-01): the D+ layer hop at U3 stands

`/PORT_VBUS_J2` descends the 0.95 mm lane between U3's pad columns to reach
U3.5, leaving 0.475 mm where a 0.21 mm pair leg needs 0.505 — short by 0.030 mm,
both ends pad edges. D+ therefore hops 1.450 mm on B.Cu with two vias, and the
crossover dip was moved onto D− and sized to match, so both legs carry two vias
and 1.450 mm of B.Cu.

Freeing the lane was assessed in detail: delete the 2.353 mm descent, place a
via-in-pad at U3.5, run 1.988 mm of B.Cu east to the existing `/PORT_VBUS_J2`
spine at x 196.000. It works geometrically. It is **not** adopted, because:

1. **Total pair vias stay at four either way.** Removing D+'s hop puts D− at two
   vias against D+'s zero — the same asymmetry inverted — so restoring parity
   needs a balancing dip on D+ regardless. The only gain is that both dips sit
   in open corridor and the pair stays coupled through U3.
2. **It requires via-in-pad**, which means filled-and-capped or tented vias plus
   a paste-aperture reduction — a fabrication-specification change. The original
   layout avoided this with a 0.5 mm via in the lane, which no longer fits now
   that the `PWR` netclass specifies 0.7/0.35.
3. The hop sits **after U3's ESD clamp and ~4 mm from the connector**, where a
   discontinuity is far less consequential than one mid-run.

A modest coupling improvement is not worth a fab-spec change here. Revisit only
if bring-up shows a real signal-integrity problem on the downstream port.

- **`/PORT_D±` remains the exposure for a different reason.** U3 must stay
  within 5 mm of the J2 pins it protects, and the re-place can easily make a
  0.15 mm match harder than it needs to be. Keep U3 and the `/PORT_D±` corridor
  close to their current geometry, and treat any change there as a deliberate
  decision with its own verification.
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
