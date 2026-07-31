# Isolated-Side Net Split and Decoupling Ownership — Design Spec

**Date:** 2026-07-31
**Project:** `isolator` — the single KiCad project at the repo root
**Status:** Draft, awaiting review
**Scope:** `isolator.kicad_sch` and `isolator.kicad_pro` only. No board edits.
**Builds on:** `2026-07-28-usb-isolator-v1-design.md` (electrical design),
`2026-07-30-isolator-pcb-layout-design.md` (layout, whose "the schematic never
changes" constraint this spec deliberately lifts for one pass)

## Overview

Three isolated-side power nets each carry more than one functional node under a
single name. Because a net name is the only thing tying a decoupling capacitor
to the pin it serves, nothing in the design files distinguishes "C11 is U5's
output cap" from "C12 is U6's input cap" — they are both just `/ISO_5V`. The
router is free to satisfy either from either end, and on the current board it
partly has.

This spec splits those nets into per-owner branches joined at explicit star
points (KiCad net ties), adds three missing capacitors, and gives every
decoupling capacitor an ownership `Description` property. After this change,
a capacitor cannot be routed to the wrong pin without the netlist itself being
wrong, which ERC and the existing gates will catch.

**This pass is schematic-only.** The board still carries the old netlist when
this spec is implemented; resynchronising and rerouting is deferred to a
follow-on plan (see Out of Scope).

## Problem

### Measured state

Distances below are pad-centre to pad-centre on the committed board
(`e9c8dc7`), computed from `isolator.kicad_pcb` with footprint rotation
applied — not footprint-origin approximations.

**1. `/ISO_5V` spans four independent loads across ~30 mm.**

| Load | Pin location | Caps on it | Distance |
|---|---|---|---|
| U5 TLV767 output | (171.78, 88.68) | C11 100n / C10 47µ | 2.18 / 2.37 mm |
| U1 ADuM4165 VBUS2 | (151.78, 95.99) | *none* | nearest is 21.90 mm |
| U6 TPS2553 input | (179.74, 100.75) | C12 100n | 2.01 mm |
| R4/R5/R6 indicators | y ≈ 116–121 | n/a | — |

**2. U1 pin 20 (VBUS2) has no bypass capacitor at all.** The ADuM4165 data
sheet (Rev. B, Table 12 and the PCB Layout section) requires 0.1 µF on each of
VBUS1, VDD1, VBUS2 and VDD2, with total lead length under 10 mm. Three are
satisfied — C4 at VBUS1 (3.11 mm), C5 at VDD1 (3.72 mm), C13 at VDD2
(2.45 mm). VBUS2 has nothing, and no fourth 100 nF exists in the BOM for it.
The schematic's own `LAYOUT CONSTRAINTS -- BINDING` block, item 8, already
refers to a "VBUS2/VDD2 bypass" returning via pins 11/19, so this is an
omission rather than a decision.

**3. U6 (TPS2553) has no output capacitor near OUT.** C14 (22 µ) sits 10.87 mm
from pin 6 and C15 (100 n) 12.49 mm; both are down at J2/U3. SLVS841F §12.1
asks for a high-value capacitor *and* a 100 nF bypass on the output pin.

**4. `/DCDC_RAW` names two different nodes.** It is simultaneously the
rectifier output (D1/D2 cathodes, wanting the 47 µF reservoir) and the LDO
input (U5 pins 5/8, wanting a 100 nF). Both capacitors currently sit at the
LDO: C8 is 8.08 mm from D1's cathode but 3.76 mm from U5's input.

**5. C6 and C7 serve two pins that each want their own bulk capacitor.**
SN6505B Table 5-1 requires ≥4.7 µF low-ESR at VCC; §11.1 separately requires
1–10 µF low-ESR at the transformer centre tap. Today one 4.7 µF (C7) and one
100 nF (C6) cover both. C7 is 2.80 mm from U4 pin 2 and 5.57 mm from T1 pin 2;
C6 is 4.23 mm and 3.84 mm respectively.

### Why the left side did not drift

C3, C4, C6 and C7 each carry a hand-written `Description` property naming the
pin they serve and warning against the plausible-but-wrong placement. Every
capacitor on the isolated side carries the stock library string "Unpolarized
capacitor, small symbol". The left side held because it was documented; the
right side drifted because it was not. Restoring that convention is part of
this change, not a nicety.

### Parallel ordering

The general rule — smaller package nearer the pin — holds at U5 but is
inverted or moot elsewhere:

| Pin | smaller | larger | verdict |
|---|---|---|---|
| U5 IN | C9 100n 3.18 | C8 47µ 3.76 | ordered, but 0.58 mm apart — effectively tied |
| U5 OUT | C11 100n 2.18 | C10 47µ 2.37 | ordered, but 0.19 mm apart — effectively tied |
| U6 OUT | C15 100n 12.49 | C14 22µ 10.87 | inverted, and both far |
| J2 VBUS | C15 100n 14.05 | C14 22µ 16.03 | ordered |
| U4 VCC | C6 100n 4.23 | C7 4.7µ 2.80 | inverted by the general rule, **correct per SN6505B** — TI wants the bulk nearest VCC |
| T1 centre tap | C6 100n 3.84 | C7 4.7µ 5.57 | wrong part nearest; the centre tap wants bulk |

The U5 pairs are ordered but the margin is smaller than placement tolerance,
so the ordering is not currently *enforced* by anything. Post-split it will be,
because each pair sits on its own branch net.

## Design

### Net decomposition

Three star points, each a KiCad net tie. All new net names fall under existing
`ISO_SIDE` netclass patterns (`/ISO_*`, `/DCDC_*`, `/PORT_*`), so
`tools/gates/barrier.py` continues to classify every net without modification.

**NT1 — `/ISO_5V` star at U5's output.** `Device:NetTie_4` +
`NetTie:NetTie-4_SMD_Pad0.5mm`.

| Net | Members |
|---|---|
| `/ISO_5V` | U5.1, U5.2 · C10 47µ · C11 100n · NT1.1 |
| `/ISO_5V_VBUS2` | U1.20 · **C16 100n (new)** · NT1.2 |
| `/ISO_5V_SW` | U6.1, U6.3 · C12 100n · NT1.3 |
| `/ISO_5V_IND` | R4.1 · R5.1 · R6.1 · NT1.4 |

`/ISO_5V_IND` groups the nFAULT pull-up with the two LED series resistors
because they occupy the same physical corner and draw single-digit milliamps
between them. Its branch from NT1 is a ~30 mm run at 0.2 mm; the resulting
drop is negligible at that current, and the isolation it buys is the point —
indicator current can never share copper with the LDO's output capacitors or
the current limiter's input.

**NT2 — `/DCDC_RAW` split at the rectifier.** `Device:NetTie_2` +
`NetTie:NetTie-2_SMD_Pad0.5mm`.

| Net | Members |
|---|---|
| `/DCDC_RECT` | D1.1, D2.1 · **C8 47µ (reassigned here)** · NT2.1 |
| `/DCDC_RAW` | U5.5, U5.8 · C9 100n · NT2.2 |

**NT3 — `/PORT_VBUS` split at U6's output.** `Device:NetTie_2` +
`NetTie:NetTie-2_SMD_Pad0.5mm`.

| Net | Members |
|---|---|
| `/PORT_VBUS` | U6.6 · **C14 22µ (reassigned here)** · **C17 100n (new)** · NT3.1 |
| `/PORT_VBUS_J2` | J2.A4/A9/B4/B9 · D6 · U3.5 · R7.1 · R8.1 · C15 100n · NT3.2 |

NT3 carries the full downstream port current. The TPS2553's limit with
R3 = 93.1 kΩ is 252/286/324 mA min/nom/max (SLVS841F), against a
`NetTie-2_SMD_Pad0.5mm` whose 0.5 mm pads sit on a solid 1.5 × 1.5 mm copper
square — the same width as the existing `PWR` netclass track, so the tie adds
no constriction the rail did not already have.

**The left side keeps single nets.** `/VBUS_HOST` is not split. Its capacitor
assignments are already documented and correct; the change there is
capacitance, not topology.

### New and reassigned components

| Ref | Value | Footprint | MPN | Role |
|---|---|---|---|---|
| C16 | 100n | `Capacitor_SMD:C_0603_1608Metric` | CC0603KRX7R9BB104 | **New.** ADuM4165 VBUS2 bypass at U1 pin 20 |
| C17 | 100n | `Capacitor_SMD:C_0603_1608Metric` | CC0603KRX7R9BB104 | **New.** TPS2553 output bypass at U6 pin 6 |
| C18 | 4.7uF | `Capacitor_SMD:C_0805_2012Metric` | GRM21BR71E475KA73L | **New.** T1 centre-tap bulk, per SN6505B §11.1 |
| C8 | 47uF | unchanged | unchanged | Moves from `/DCDC_RAW` to `/DCDC_RECT` |
| C14 | 22u | unchanged | unchanged | Moves from `/PORT_VBUS_J2` to `/PORT_VBUS` |
| C6 | 100n | unchanged | unchanged | Ownership narrows to U4 pin 2 only (C18 takes the centre tap) |
| NT1 | NetTie_4 | `NetTie:NetTie-4_SMD_Pad0.5mm` | — | `/ISO_5V` star |
| NT2 | NetTie_2 | `NetTie:NetTie-2_SMD_Pad0.5mm` | — | `/DCDC_*` star |
| NT3 | NetTie_2 | `NetTie:NetTie-2_SMD_Pad0.5mm` | — | `/PORT_VBUS*` star |

All three new capacitors reuse MPNs already on the BOM, so `isolator-bom.csv`
gains quantity on three existing lines and no new line items. The net-tie
footprints ship with `exclude_from_bom` and `exclude_from_pos_files` already
set in their `attr` field, so they appear in neither the BOM nor the CPL.

After this change the ordering table reads:

| Pin | nearest | next | rationale |
|---|---|---|---|
| U5 IN | C9 100n | C8 47µ — now on `/DCDC_RECT`, not this net | reservoir moves to the rectifier where the pulsed current is |
| U5 OUT | C11 100n | C10 47µ | unchanged, now enforced by net membership |
| U6 IN | C12 100n | — | sole cap on `/ISO_5V_SW` |
| U6 OUT | C17 100n | C14 22µ | matches SLVS841F §12.1 |
| J2 VBUS | C15 100n | — | connector-local HF only |
| U4 VCC | C6 100n | C7 4.7µ | C6 moves inboard of C7; bulk still within TI's guidance |
| T1 CT | C18 4.7µ | — | dedicated bulk, per §11.1 |
| U1 VBUS2 | C16 100n | — | closes the datasheet gap |

At U4 the general "smallest nearest" rule and TI's "bulk closest to VCC" both
end up satisfiable, because C18 relieves C7 of centre-tap duty and C7 can stay
where it is while C6 moves inboard.

### Netclass patterns

`isolator.kicad_pro`, `net_settings.netclass_patterns`. `ISO_SIDE` needs no
change — its wildcards already cover every new name. `PWR` uses exact strings
and must gain four:

```
PWR  /ISO_5V_VBUS2
PWR  /ISO_5V_SW
PWR  /DCDC_RECT
PWR  /PORT_VBUS_J2
```

`/ISO_5V_IND` is deliberately **not** added to `PWR`. It carries a few
milliamps; the `ISO_SIDE` default of 0.2 mm is the correct width, and putting
it on the 0.5 mm `PWR` class would waste routing channel in the busiest corner
of the board.

### Documentation carried in the schematic

Every capacitor gains a `Description` property in the style already used for
C3/C4/C6/C7: the owning pin, the datasheet clause that requires it, and the
plausible-but-wrong placement to avoid. This is the mechanism that kept the
left side correct and its absence is why the right side drifted.

The `LAYOUT CONSTRAINTS -- BINDING` text block is updated:

- **Item 5** gains VBUS2 explicitly, naming C16.
- **Item 9** is rewritten: C6 alone at U4 pin 2, C18 at the T1 centre tap,
  C7 remaining as the VCC bulk. The current wording, "C6+C7 cluster at U4
  pin 2 / T1 center-tap", becomes wrong the moment C18 exists.
- A **new item 10** states the three star points and that a branch net may
  only be fed through its net tie — the rule the ties exist to encode, written
  where a layout worker will read it.

### Schematic layout

Per the standing rules for this project: GND symbols point down, rail symbols
point up, no symbol/wire/text overlap, PWR_FLAGs stay in their dedicated area,
and each subsystem keeps its graphic box. The three net ties are placed inside
the boxes for the blocks they serve, not in a separate area — a star point is
part of its circuit. C16 is drawn adjacent to U1 pin 20 inside the isolator
box, C17 adjacent to U6 pin 6, C18 adjacent to T1 pin 2.

## Verification

1. **ERC clean.** `kicad-cli sch erc --severity-error --exit-code-violations`
   exits 0. This project's ERC config treats `power_pin_not_driven` as an
   error, so each new branch net must be reachable from a driver through its
   tie; a missing or mis-wired tie fails here rather than silently.
2. **Netlist membership probes.** Export the netlist and assert each of the
   eight nets in the decomposition tables has exactly the listed members —
   no more, no less. This is the check that would have caught the original
   drift, so it is the check that must exist afterwards.
3. **Net-tie recognition.** Confirm KiCad reads `net_tie_pad_groups` on all
   three footprints, so DRC will later treat the shorts as intentional.
4. **Netclass coverage.** `tools/gates/netclass_coverage.py` against the new
   netlist. It already asserts every net resolves to exactly one of
   `HOST_SIDE` / `ISO_SIDE`; it reads the netlist rather than the board, so it
   is valid during a schematic-only pass. Extend it with one assertion: the
   four new `PWR` members resolve to `PWR`, and `/ISO_5V_IND` does not.
5. **Visual.** Export the sheet to PDF and confirm no overlapping symbols,
   wires or text, per the standing layout rules.

`barrier.py` (Gate 1), `edge_pullback.py` (Gate 2) and `diffpair.py` (Gate 3)
operate on the board and are **not** expected to pass mid-change — the board
still holds the old netlist until the follow-on plan runs. `run_all.py` is not
a meaningful signal for this pass. `netclass_coverage.py` reads the netlist
rather than the board, which is why it appears as check 4 above.

## Out of Scope

- **All board work.** Placement of C16/C17/C18 and NT1–NT3, relocation of C6,
  C8 and C14, rip-up and reroute of `/ISO_5V`, `/PORT_VBUS` and `/DCDC_RAW`.
  This needs its own plan, and the board's gate suite is the acceptance
  criterion there, not here.
- **`/VBUS_HOST` topology.** Not split. Revisit only if the isolated-side
  split proves out and the same failure mode appears on the left.
- **R3 and the FAULT trip band, the PGOOD R9/R10 arrangement.** Both are
  documented decisions carried to bring-up; untouched.
- **A decoupling-distance gate.** Attractive, but it is a board-level check
  and belongs with the board plan. The net split plus the `Description`
  properties are what this pass delivers.

## Risks

- **Connector-local bulk on the port.** Moving C14 to U6's output leaves J2
  with C15 (100 n) and D6 only, with the 22 µF ~11 mm upstream. This follows
  TI's guidance and the TPS2553's soft-start covers the inrush case, but if
  bring-up shows droop on hot-plug, the fix is a second bulk capacitor at J2
  rather than moving C14 back. There is board room for it.
- **Net ties and future ERC/DRC surprises.** Net ties are well-supported in
  KiCad 10 but they are the least-exercised construct in this project. If any
  of the three proves troublesome, the fallback is to drop that tie and keep
  the single net plus the `Description` properties — the documentation half of
  this change stands on its own.
- **The board diverges from the schematic until the follow-on runs.** This is
  intended and bounded, but it means the repo is in a state where
  `run_all.py` is not a meaningful signal. The follow-on plan should be the
  next piece of work, not deferred indefinitely.
