# Isolator PCB Layout — Design Spec

**Date:** 2026-07-30
**Project:** `isolator` — the single KiCad project at the repo root
**Status:** Approved
**Branch:** `layout`
**Predecessor:** schematic complete, ERC-clean, footprinted, MPN-populated
(`docs/superpowers/reviews/2026-07-28-v1-schematic-review.md`)

## Scope

Place and route the 43-component single-port USB isolator on a 120 × 50 mm
4-layer board for a Hammond 1455C1202 extrusion. Ends at a DRC-clean, routed,
plane-poured board with three scripted verification gates passing. No
fabrication outputs — Gerbers, drill, CPL and JLCPCB BOM are a follow-on.

**The schematic does not change.** It is the authority on connectivity. If
layout reveals an electrical problem, stop and report rather than edit the
schematic.

## Authority

The schematic carries a `LAYOUT CONSTRAINTS -- BINDING` text block. That block
is authoritative; this spec elaborates it and must not contradict it. Where
this document gives a number the constraints block does not, the number is
derived here and marked as such.

## Findings that shape the design

Five conditions were measured before design, not assumed. Each changes what
gets built.

### 1. U1 hits 8.3 mm exactly; T1 is 0.79 mm short in straight line

Measured pad-edge to pad-edge across the barrier, from the real `.kicad_mod`
files:

| Part | Footprint | Pad-edge gap | vs 8.3 mm |
|---|---|---|---|
| U1 ADuM4165 | `isolator-lib:ADI_SOIC_IC_20_RI-20-1` | **8.3000 mm** | passes, zero margin |
| CY1 stitching cap | `isolator-lib:C_Disc_D7.0mm_W5.5mm_P14.00mm` | 12.0000 mm | passes |
| T1 transformer | `isolator-lib:WE_750313638` | **7.5100 mm** | short by 0.79 mm |

U1's pad rows sit at x = ±4.150 relative to its origin — the land pattern was
drawn to land on 8.3 mm exactly. Consequence: **no DRC rule may demand more
than 8.3 mm across the barrier**, or U1 fails by construction. The barrier
keepout is therefore exactly 8.3 mm wide and U1's pads sit on its boundary.

T1's 7.51 mm is a *clearance* figure, and clearance is not creepage. Constraint
4 requires a routed slot under T1 precisely because of this: the slot removes
substrate, so the surface creepage path runs around the slot and exceeds
8.3 mm while the straight-line clearance stays 7.51 mm. The existing
`.kicad_dru` already encodes the distinction with a separate 7.4 mm T1
clearance rule.

**This changes the barrier gate.** A gate that measures naive Euclidean
copper-to-copper distance and asserts ≥ 8.3 mm fails at T1 by design. See
Gate 1.

### 2. Thirteen live nets escape the barrier DRC rules entirely

The barrier rules in `.kicad_dru` fire on `A.hasNetclass('HOST_SIDE') &&
B.hasNetclass('ISO_SIDE')`. Netclass membership is assigned by pattern in
`isolator.kicad_pro`, and those patterns were written for the 4-port design.
Checked against this design's actual 34 nets, 13 live nets match neither
`HOST_SIDE` nor `ISO_SIDE`:

| Net | Nodes | True domain (from connectivity) |
|---|---|---|
| `/PP_A` | T1.3 U4.1 | HOST_SIDE |
| `/PP_B` | T1.1 U4.3 | HOST_SIDE |
| `/RECT_A` | D1.2 T1.6 | ISO_SIDE |
| `/RECT_B` | D2.2 T1.4 | ISO_SIDE |
| `/PORT_VBUS` | C14 C15 D6 J2 R7 R8 U6 … | ISO_SIDE |
| `/PORT_D+` | J2.A6 J2.B6 U1.12 U3.1 U3.6 | ISO_SIDE |
| `/PORT_D-` | J2.A7 J2.B7 U1.13 U3.3 U3.4 | ISO_SIDE |
| `/PORT_CC1` | J2.A5 R7.2 | ISO_SIDE |
| `/PORT_CC2` | J2.B5 R8.2 | ISO_SIDE |
| `/nFAULT` | D4.1 R4.2 U6.4 | ISO_SIDE |
| `/FAULT_LED_A` | D4.2 R5.2 | ISO_SIDE |
| `/PG_LED_A` | D3.2 R6.2 | ISO_SIDE |
| `/PG_LED_K` | D3.1 Q1.3 | ISO_SIDE |

`/PP_A`, `/PP_B`, `/RECT_A` and `/RECT_B` are the transformer primary and
secondary. They land on T1's pads and are the closest copper to the barrier
anywhere on the board — exactly the nets the rule most needs to police, and
exactly the ones it currently ignores.

This is a project-settings gap, not a schematic defect. Connectivity is
correct; only the netclass patterns are stale.

### 3. The downstream differential pair is not in the 90 Ω netclass

`USB_DIFF90` patterns cover `/HOST_D*` and `/ISO_D*`. The downstream pair is
named `/PORT_D+` / `/PORT_D-`, which matches neither, so it falls through to
`Default` — 0.2 mm track, 0.25 mm gap. That geometry is not 90 Ω on this
stackup. Left alone, half the USB path would be routed to the wrong impedance
and Gate 3 would fail.

### 4. The board carries no stackup; the impedance target has no substrate

`isolator.kicad_pcb` is a 794-byte skeleton: four copper layers declared, no
`(stackup …)` block, no outline, no footprints, no nets. The `USB_DIFF90`
geometry (0.21 mm / 0.127 mm) was tuned against JLCPCB **JLC04161H-7628**,
recorded on branch `4port-archive` (commit `5c56d3e`). Without that block,
"90 Ω" is not checkable against anything.

### 5. `.kicad_dru` is the 4-port's and is stale three ways

- `barrier-creepage` floor is **8 mm**, not the binding 8.3 mm.
- The header comment reasons about `C49`, a 4-port part that was DNP. This
  design's equivalent is `CY1`, and it is **populated**.
- `connector-neckdown` enumerates `J1`–`J6`. Only `J1` and `J2` exist.

## Board geometry

Rectangle **120 × 50 mm**, origin at the top-left corner, x along the 120 mm
length, y across the 50 mm width. KiCad's y axis increases downward.

**Copper band: y ∈ [2, 48].** Constraint 2 requires ≥ 1 mm pullback from both
long edges, target 2 mm, every layer, full length. Implemented as two
all-layer keepout strips (`y ∈ [0,2]` and `y ∈ [48,50]`) rather than a global
DRC edge-clearance rule — a global rule would also push copper off the 50 mm
**end** edges, where constraint 6 requires J1 and J2 to sit flush. Derived: the
2 mm target is used, leaving 1 mm of margin against the 1 mm floor.

**No mounting holes.** The 1455C retains the board in the extrusion's slots.
A hole would also have to respect the pullback band.

## Isolation barrier

**Barrier centre at x = 60 mm**, the board's midpoint. Keepout spans
**x ∈ [55.85, 64.15]** — exactly 8.3 mm — across the full 50 mm width, on all
four copper layers. Derived: the chain needs ~38 mm host-side and ~37.4 mm
isolated-side against 55.85 mm available each way, so centring leaves ~18 mm
of routing slack per side, balanced.

Three components straddle the keepout and are the only permitted crossings
(constraint 4):

- **U1** at x = 60, long axis along y. Pins 1–10 (GND1) land at x = 55.1,
  pins 11–20 (GND2) at x = 64.9; pad inner edges sit exactly on the keepout
  boundary at x = 55.85 / 64.15.
- **T1** at x = 60. Pad rows at x = 55.29 / 64.71, inner edges at
  x = 56.245 / 63.755 — **T1's pads necessarily intrude 0.395 mm into the
  keepout on each side**, because the land pattern is 7.51 mm across and the
  keepout is 8.3 mm. A **routed slot** in `Edge.Cuts` runs beneath it.
- **CY1** at x = 60, 14 mm lead pitch along x, pads at x = 53 and x = 67,
  pad inner edges at x = 54 / 66 — 12 mm of gap, clear of the keepout.

**The keepout therefore excludes tracks, vias and copper pour, but not pads.**
A blanket no-copper-of-any-kind zone would reject T1's own pads, which are a
permitted crossing. Pad-to-pad separation for the three crossing parts is
policed by the per-footprint `.kicad_dru` rules and by Gate 1, not by the
keepout.

### T1 slot sizing

The slot is what converts T1's 7.51 mm clearance into ≥ 8.3 mm of creepage:
it removes substrate so the surface path must detour around the slot's ends
rather than run straight between the pad rows.

Starting geometry: a rounded slot centred on x = 60, 2 mm wide in x, extending
in y at least 2 mm beyond T1's pad rows at each end. **Gate 1 is the authority
on the final dimensions** — the slot is widened or lengthened until the
measured creepage path clears 8.3 mm. It is not correct to assume a starting
geometry passes; the gate reports the achieved path length.

Stacked along y within the 46 mm copper band: U1 (16.04 mm), T1 (9.64 mm),
CY1 (6.00 mm) — 31.68 mm of parts, ~4.7 mm of gap between each.

## Layer stack

JLC04161H-7628, ported verbatim from `4port-archive:isolator.kicad_pcb`:

| Layer | Type | Thickness | Er |
|---|---|---|---|
| F.Cu | copper | 0.035 | — |
| dielectric 1 | prepreg (7628) | 0.2104 | 4.4 |
| In1.Cu | copper | 0.0152 | — |
| dielectric 2 | core | 1.065 | 4.6 |
| In2.Cu | copper | 0.0152 | — |
| dielectric 3 | prepreg (7628) | 0.2104 | 4.4 |
| B.Cu | copper | 0.035 | — |

Total 1.6 mm, matching the `(thickness 1.6)` already declared.

**Both inner layers are split ground**, not GND + PWR. In1.Cu and In2.Cu each
carry a GND1 pour on the host side of the barrier and a GND2 pour on the
isolated side, with the 8.3 mm keepout between. The skeleton's inherited layer
names `"GND"` / `"PWR"` are retired — a single continuous plane on either
inner layer would bridge the barrier and violate constraint 4.

Consequence: power rails route as tracks on F.Cu and B.Cu. Acceptable — there
are few of them and the whole board draws under ~350 mA. In exchange every
signal on F.Cu references In1.Cu ground and every signal on B.Cu references
In2.Cu ground, which is what the differential pairs need.

## Netclass and design-rule corrections

### Netclass patterns

Rewrite `net_settings.netclass_patterns` in `isolator.kicad_pro` for this
design's net names. Every one of the 13 nets in Finding 2 gets its true domain.
`/PORT_D*` is added to `USB_DIFF90`. The 4-port patterns (`/P1_*`…`/P4_*`,
`/EXT_*`, `Net-(T1*`) are removed — they match nothing here, and `Net-(T1*`
was wrong in principle since T1 spans both domains.

**Invariant, checked by Gate 1:** every net carrying copper is in exactly one
of `HOST_SIDE` or `ISO_SIDE`. The six `unconnected-*` nets are exempt: they
have a single pad each and no routed copper.

### `.kicad_dru`

- `barrier-creepage` floor 8 mm → **8.3 mm**.
- `barrier-clearance-U1` stays at 8 mm. It must not be raised to 8.3 mm:
  U1's pads sit exactly on 8.3 mm, and a rule at the same value risks
  a floating-point boundary failure on the part it is meant to permit.
- `barrier-clearance-T1` stays at 7.4 mm, with the comment rewritten to
  explain the slot rather than reference `C49`.
- `connector-neckdown` reduced to `J1` and `J2`.

## Placement

Signal flow runs J1 (x = 0) to J2 (x = 120). Zone budgets are the design
spec's, with courtyards measured in
`docs/superpowers/reviews/2026-07-28-v1-mechanical-feasibility.md`.

| Zone | x range | Contents |
|---|---|---|
| 1 | 0 – 18 | J1 end-launched; U2 ESD; D5 VBUS TVS; C3 J1-entrance bulk |
| 2 | 18 – 55.85 | U1 Side 1, Y1 + loads, U4 SN6505B, C4 at U1 pin 1, C6 + C7 at U4 pin 2 / T1 centre-tap |
| — | 55.85 – 64.15 | **barrier keepout**; U1 / T1 / CY1 straddle |
| 4 | 64.15 – 102 | D1 ‖ D2 rectifier, U5 LDO, U6 TPS2553, R3 ILIM, LEDs D3/D4, Q1 |
| 5 | 102 – 120 | D6 VBUS TVS; U3 ESD; J2 end-launched |

Binding placement rules carried from the constraints block:

- **J1, J2 end-launched**, mating faces flush with the outer face of the
  plastic end panels (constraint 6).
- **U2, U3 within 5 mm** of the connector pins they protect; array GND pin on
  its **own via straight to plane**, never daisy-chained; pair routed in-line
  through pins 1/3 → 6/4 with no stubs (constraint 3).
- **D1 and D2 side by side, not in series** (constraint 7). In series the zone
  overruns 20 mm by 3.36 mm.
- **U1 bypass within 10 mm total lead length** (constraint 5), returning to
  GND1 via pins 2/10 and GND2 via pins 11/19 **only** — pins 4, 7, 15, 16, 17
  are ground-only and unsuitable for bypass current (constraint 8,
  datasheet Table 12 p.12).
- **VBUS_HOST's four caps serve two ICs** (constraint 9). C7 is the SN6505B's
  mandatory ≥ 4.7 µF VCC bypass and sits with C6 at U4 pin 2 / T1 centre-tap.
  C4 sits at U1 pin 1. C3 stays at the J1 entrance. Clustering all four at U1
  satisfies the netlist and starves the DC-DC.

## Routing

Hand-routed throughout. `tools/autoroute.py` is not used to place copper: its
Freerouting stage has no model of the barrier or the edge pullback, and those
are the two things that decide whether this board works. It stays available as
an after-the-fact connectivity checker.

**Differential pairs.** Two, both `USB_DIFF90` after the pattern fix:
`/HOST_D±` (J1 → U2 → U1 pins 8/9) and `/PORT_D±` (U1 pins 12/13 → U3 → J2).
0.21 mm width, 0.127 mm gap, on F.Cu over In1.Cu. Neither pair crosses the
barrier — U1 crosses it internally, which is the entire point of the part.
Intra-pair length match target **≤ 0.15 mm**, well inside the USB 2.0
high-speed skew budget.

**Power.** `PWR` netclass, 0.5 mm tracks. `VBUS_HOST` from J1 to U1/U4;
`DCDC_RAW` from the rectifier to U5; `ISO_5V` from U5 to U6 and `PORT_VBUS`
onward to J2.

**Planes.** GND1 and GND2 pours on In1.Cu and In2.Cu, and local pours on F.Cu
and B.Cu where they help returns. Every pour is clipped by the barrier keepout
and the two edge strips.

## Verification gates

DRC clean is necessary but not sufficient. Three scripted gates, each run from
the committed board file, each failing loudly.

### Gate 1 — barrier

For every copper layer, find the minimum separation between HOST_SIDE copper
and ISO_SIDE copper and assert **≥ 8.3 mm**.

Creepage-aware on F.Cu: where the straight line between two copper features
crosses a routed slot or board cutout, the measured path runs around the
cutout, since that is the surface path a contaminant film would follow. This
is what lets T1's 7.51 mm land pattern pass on the strength of its slot rather
than by exemption. On In1.Cu, In2.Cu and B.Cu — where T1 has no pads — the
assertion is straight-line, since creepage is a surface phenomenon and inner
layers face solid dielectric.

The gate also asserts the Finding 2 invariant: every copper-carrying net is in
exactly one of `HOST_SIDE` / `ISO_SIDE`. A net in neither is a silent hole in
the rule and fails the gate.

### Gate 2 — edge pullback

Assert no copper on any layer — track, via, pad or zone fill — comes within
**1 mm** of either long edge (y = 0, y = 50). Reported against the 2 mm target
so erosion toward the floor is visible before it becomes a violation. The
50 mm end edges are deliberately excluded: J1 and J2 sit flush there.

### Gate 3 — differential pairs

Two assertions:

1. **Length match.** Intra-pair skew ≤ 0.15 mm for `/HOST_D±` and `/PORT_D±`.
2. **Impedance.** Recompute differential impedance from the **actual stackup
   in the board file** — trace width, gap, prepreg thickness and Er read from
   `isolator.kicad_pcb`, not from nominal values — and assert 90 Ω ± 10 %.
   Reading the real stackup is the point: it is what catches the board being
   built on a substrate the geometry was never tuned for.

## Carried into bring-up

Documented decisions, not defects. Neither is to be "fixed" during layout.

- **FAULT will not assert on a normal overload.** R3 = 93.1 kΩ gives a
  252–324 mA trip band against a supply delivering ~243 mA, so the DC-DC sags
  before the switch trips. Deliberate.
- **PGOOD is push-pull**, per ADuM4165 Table 18 p.15. R10 is populated, R9 is
  a DNP alternate. Removing R10 is an available simplification for a future
  spin, not this one.

## Out of scope

Gerbers, drill files, CPL/position output, JLCPCB BOM, panelisation, 3D
render, and any schematic change.
