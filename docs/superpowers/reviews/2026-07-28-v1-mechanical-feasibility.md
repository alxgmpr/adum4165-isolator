# Mechanical Feasibility Gate (Task 1)

> **Repo note (2026-07-30):** the design this document calls "v1" is now simply
> **the isolator** — the single, shipping project at the repo root
> (`isolator.kicad_sch` / `.kicad_pcb` / `.kicad_pro`). It is no longer a
> sub-project under `v1/`, and paths below have been updated accordingly. What
> this document calls "v2" is the **archived 4-port design**, now on branch
> `4port-archive`. Past-tense passages comparing the two are kept as written —
> they record why decisions were made and only make sense in that tense.

**Date:** 2026-07-28 (originally); updated 2026-07-28 in Task 2 fix round 1; **rewritten
2026-07-30 in Task 7 fix round 1 — the verdict changed. Read "Verdict" before treating any
earlier number in this document's history as current.**

**Scope:** go/no-go check on whether the isolator's component set fits the
target enclosure.

**Target envelope: Hammond 1455C1202 — 120 mm (length) x 50 mm (width).** Usable copper area for
component placement is 120 x 50 mm minus a 2 mm copper pullback on each long edge:
**120 x 46 = 5520 mm²**.

**This document previously gated against the 1455C802 (80 mm).** Task 7's footprint audit
replaced every placeholder/nominal dimension in the length-chain and area checks with courtyards
measured from the real `.kicad_mod` files now assigned in `isolator.kicad_sch`, and the
80 mm chain no longer closes (see "Verdict"). The design moved to the 1455C1202 at 120 mm — an
edge-cut-only change already documented as the fallback in the original version of this
document and in the design spec — rather than gamble a board spin on a chain with negative
worst-case margin. See "Update history" for the full before/after.

---

## Method

Two checks, run as a standalone Python (stdlib only) script — see command and full output below.

1. **Area utilization.** Sum of courtyard footprint areas (width x height, mm) for **every one
   of the 43 real BOM components**, using the courtyard measured from the actual `.kicad_mod`
   file assigned to each part in the schematic — no nominal package sizes, no generic "N passives
   at X mm² each" placeholder. Compared against the 5520 mm² usable area (120 mm envelope).
   Target: comfortably under 45% utilization.
2. **Length chain.** A linear dimension chain of the zones that must sit in series along the
   long axis, using the design spec's 5-zone budget
   (`docs/superpowers/specs/2026-07-28-usb-isolator-v1-design.md`), with real measured courtyards
   substituted into every zone where a chain formula exists (zones 1, 4, 5). Reported as an
   optimistic/worst-case range because a courtyard's two in-plane axes can be measured either way
   depending on component orientation, and orientation is not yet decided (no placement pass has
   happened).

All courtyards below were measured directly from `F.CrtYd` geometry in the real `.kicad_mod`
files — stock KiCad footprint libraries plus the project's `isolator-lib.pretty` — not from
datasheet nominal package envelopes. This is a change from the previous revision of this
document, which still used unmeasured nominal sizes for J1/J2, U2/U3/U4, Y1, D1/D2, and the bulk
passives.

## Command run

```bash
python3 - <<'EOF'
# Fully-itemized recompute. Every one of the 43 real BOM components uses its actual assigned
# footprint's measured F.CrtYd courtyard -- zero nominal/placeholder sizes anywhere.
parts = {
    'C_0603_1608Metric (R/C 0603)':   (2.96, 1.46, 20, 'R1-R10, C1,C2,C4,C5,C6,C9,C11,C12,C13,C15'),
    'C_0805_2012Metric':              (3.40, 1.96, 3,  'C3,C7,C14'),
    'C_1210_3225Metric':              (4.60, 3.20, 2,  'C8,C10'),
    'USB_C_Receptacle_HRO_TYPE-C-31-M-12': (10.64, 9.42, 2, 'J1,J2'),
    'Crystal_SMD_3225-4Pin_3.2x2.5mm':(4.20, 3.50, 1,  'Y1'),
    'D_SMA':                          (7.00, 3.50, 2,  'D1,D2'),
    'D_SOD-523':                      (2.50, 1.40, 2,  'D5,D6'),
    'LED_0603_1608Metric':            (2.96, 1.46, 2,  'D3,D4'),
    'HVSSOP-8-1EP_3x3mm_..._EP1.57x1.89mm': (6.26, 3.50, 1, 'U5'),
    'SOT-23':                         (3.86, 3.40, 1,  'Q1'),
    'SOT-23-6':                       (4.10, 3.40, 4,  'U2,U3,U4,U6'),
    'isolator-lib:ADI_SOIC_IC_20_RI-20-1': (11.80, 16.04, 1, 'U1'),
    'isolator-lib:C_Disc_D7.0mm_W5.5mm_P14.00mm': (16.50, 6.00, 1, 'CY1'),
    'isolator-lib:WE_750313638':      (13.20, 9.64, 1,  'T1'),
}
total = sum(w*h*c for w, h, c, _ in parts.values())
usable = 120 * 46
print(f"total component courtyard area: {total:.2f} mm^2")
print(f"utilization vs 120mm envelope (5520 mm^2): {100*total/usable:.1f}%")

# 5-zone length chain, real measured parts, optimistic/worst-case orientation range.
gap = 1.0
j_depth = 9.42
esd_opt, esd_worst = 3.40, 4.10       # SOT-23-6 short/long axis
tvs_opt, tvs_worst = 1.40, 2.50       # SOD-523 short/long axis
zone15_opt   = j_depth + esd_opt   + tvs_opt   + 2*gap
zone15_worst = j_depth + esd_worst + tvs_worst + 2*gap

d_sma, ldo, tps = 7.00, 6.26, 4.10
zone4        = d_sma + ldo + tps + 2*gap                # D1/D2 side by side (required)
zone4_serial = 2*d_sma + ldo + tps + 3*gap               # D1/D2 in series (do not use)

zone2, zone3 = 20.0, 8.3   # held at spec budget -- see "Verdict" for why this is conservative

len_opt   = zone15_opt   + zone2 + zone3 + zone4 + zone15_opt
len_worst = zone15_worst + zone2 + zone3 + zone4 + zone15_worst
print(f"\nlength chain: {len_opt:.2f} - {len_worst:.2f} mm")
print(f"  vs 80.0 mm (historical target):  {80-len_opt:+.2f} to {80-len_worst:+.2f} mm margin")
print(f"  vs 120.0 mm (current envelope): {120-len_opt:+.2f} to {120-len_worst:+.2f} mm margin")

print(f"\nRectifier+LDO+TPS2553 zone, 20mm budget:")
print(f"  D1||D2 side by side (required): {zone4:.2f} mm (margin {20-zone4:+.2f} mm)")
print(f"  D1+D2 in series (do not use):   {zone4_serial:.2f} mm (margin {20-zone4_serial:+.2f} mm)")
EOF
```

## Output (real, unedited)

```
total component courtyard area: 921.98 mm^2
utilization vs 120mm envelope (5520 mm^2): 16.7%

length chain: 80.10 - 83.70 mm
  vs 80.0 mm (historical target):  -0.10 to -3.70 mm margin
  vs 120.0 mm (current envelope): +39.90 to +36.30 mm margin

Rectifier+LDO+TPS2553 zone, 20mm budget:
  D1||D2 side by side (required): 19.36 mm (margin +0.64 mm)
  D1+D2 in series (do not use):   27.36 mm (margin -7.36 mm)
```

Full itemized area breakdown (14 distinct footprints, all 43 components, all measured):

| Footprint | w × h (mm) | Count | Refs | Subtotal (mm²) |
|---|---|---|---|---|
| `C_0603_1608Metric` (R/C 0603) | 2.96 × 1.46 | 20 | R1–R10, C1,C2,C4,C5,C6,C9,C11,C12,C13,C15 | 86.43 |
| `C_0805_2012Metric` | 3.40 × 1.96 | 3 | C3,C7,C14 | 20.00 |
| `C_1210_3225Metric` | 4.60 × 3.20 | 2 | C8,C10 | 29.44 |
| `USB_C_Receptacle_HRO_TYPE-C-31-M-12` | 10.64 × 9.42 | 2 | J1,J2 | 200.46 |
| `Crystal_SMD_3225-4Pin_3.2x2.5mm` | 4.20 × 3.50 | 1 | Y1 | 14.70 |
| `D_SMA` | 7.00 × 3.50 | 2 | D1,D2 | 49.00 |
| `D_SOD-523` | 2.50 × 1.40 | 2 | D5,D6 | 7.00 |
| `LED_0603_1608Metric` | 2.96 × 1.46 | 2 | D3,D4 | 8.64 |
| `HVSSOP-8-1EP_3x3mm..._EP1.57x1.89mm` | 6.26 × 3.50 | 1 | U5 | 21.91 |
| `SOT-23` | 3.86 × 3.40 | 1 | Q1 | 13.12 |
| `SOT-23-6` | 4.10 × 3.40 | 4 | U2,U3,U4,U6 | 55.76 |
| `isolator-lib:ADI_SOIC_IC_20_RI-20-1` | 11.80 × 16.04 | 1 | U1 | 189.27 |
| `isolator-lib:C_Disc_D7.0mm_W5.5mm_P14.00mm` | 16.50 × 6.00 | 1 | CY1 | 99.00 |
| `isolator-lib:WE_750313638` | 13.20 × 9.64 | 1 | T1 | 127.25 |
| **Total (43 parts)** | | | | **921.98** |

## Verdict: moved to the 1455C1202 (120 mm) — not a hard failure of 80 mm, a judgment call

**Area utilization is not the constraint.** 921.98 mm² of fully-measured component courtyard
against the 120 mm envelope's 5520 mm² usable area is **16.7% utilization** — 28 points of
headroom under the 45% target. (For reference, against the historical 80 mm/3680 mm² envelope
the same fully-measured area is 25.1% — also nowhere near 45%.) This check has never been close
to failing, at either envelope size.

**The length chain is what moved.** Using real measured courtyards in every zone that has a
chain formula (1, 4, 5) instead of the nominal placeholders the original Task 1 check used:

| Zone | Original placeholder budget | Real measured (optimistic – worst case) |
|---|---|---|
| J1 + ESD array + VBUS TVS | 15 mm | 16.22 – 18.02 mm |
| ADuM4165 Side 1 + crystal + SN6505B | 20 mm | held at 20 mm — **not re-derived, see caveat below** |
| Barrier zone | 8.3 mm | 8.3 mm (fixed creepage requirement, unchanged) |
| Rectifier + LDO + TPS2553 | 20 mm | 19.36 mm (D1/D2 **must** sit side by side — see below) |
| ESD array + VBUS TVS + J2 | 15 mm | 16.22 – 18.02 mm |
| **Total** | **~78.3 mm** | **80.10 – 83.70 mm** |

Against the historical 80.0 mm target that is **-0.10 mm to -3.70 mm margin — the chain no
longer closes**, even in the optimistic case. Two measured deltas drive this: the USB-C
receptacle is 9.42 mm deep into the board, not the 9.0 mm originally assumed, and `D_SMA`
(D1/D2) is 7.0 mm on its pad-to-pad axis, not the 5.0 mm placeholder Task 2 explicitly flagged
as unmeasured and out of scope at the time.

**Caveat on zone 2 — this chain is conservative, not exact.** Zone 2 ("ADuM4165 Side 1 +
crystal + SN6505B") is held at its original 20 mm budget above because, unlike zones 1/4/5,
there has never been a component-by-component chain formula for it in this document to
re-derive. Two of its parts also grew under measurement — the crystal `Y1` (4.2 × 3.5 mm real,
vs. 3.2 × 2.5 mm originally assumed) and `U4` SN6505 (SOT-23-6, 4.1 × 3.4 mm real, vs. 3.0 × 3.0
mm originally assumed) — so holding zone 2 at 20 mm almost certainly **understates** the true
chain, not overstates it. The 80.10–83.70 mm range above should be read as a floor, not a
ceiling.

**Rectifier + LDO + TPS2553 zone, specifically:** closes at 19.36 mm against its 20 mm budget
(+0.64 mm margin) **only if D1 and D2 are placed side by side**, not in series — in series the
zone overruns to 27.36 mm (-7.36 mm). This is unchanged in kind from the previous revision of
this document (which used an unmeasured 5.0 mm D_SMA placeholder and reported +2.64 mm margin);
substituting the real 7.0 mm D_SMA dimension shrinks the true margin to +0.64 mm. **D1/D2
side-by-side placement remains a load-bearing layout constraint** — it is what the schematic's
"LAYOUT CONSTRAINTS -- BINDING" text block (item 7) now records for the PCB placement task,
independent of which enclosure is used, since this zone's internal geometry doesn't change with
board length.

**Why this is a judgment call, not a proof of impossibility.** This whole check is a
**one-dimensional chain model of a two-dimensional board**. At 16.7% area utilization on a
50 mm-wide panel there is substantial lateral room, and nothing in the design forces every part
into a single row along the centerline — the "5-zone chain" is a simplifying assumption for a
quick go/no-go gate, not a placement result. An 80 mm board is **not proven impossible** by this
check; a real placement pass (with routing keepouts, connector/mounting-hole tolerances, and
actual 2-D component arrangement) could plausibly still fit it, particularly since only zones
1/4/5 were re-derived and zone 2 is a conservative placeholder rather than a proven bound.

**The decision was made anyway to move to the 1455C1202 (120 mm)** rather than gamble a board
spin on a chain sitting at -0.10 to -3.70 mm margin before any real placement has been attempted.
This is an edge-cut-only change to `isolator.kicad_pcb` — no schematic or architectural
change — and buys roughly 36–40 mm of slack (see the "vs 120.0 mm" margins above), comfortably
clearing every zone including the conservative zone-2 placeholder. Revisiting 80 mm on a later
board spin, once real 2-D placement is known, remains open; it was not closed off by this
decision, just not worth risking now.

## Update history

**2026-07-28, Task 2 fix round 1** (in response to review Critical 3): the LDO changed from
`MIC29302WU` (TO-263-5, 16.65 x 11.3 mm = 188.1 mm² courtyard) to `TLV76750DGNR` (HVSSOP-8,
6.26 x 3.50 mm = 21.9 mm² courtyard). D3/D4/D5/D6 were split from combined to per-part entries,
D5/D6 and CY1 courtyards were measured for the first time, and the length-chain model was
replaced with the spec's real 5-zone budget (78.3 mm total, 1.7 mm margin against 80 mm) instead
of an ad hoc 4-zone model that had silently dropped 6.3 mm of budget. Verdict at the time: GO,
tight (1.7 mm margin), full detail in the file history / git log for this document.

**2026-07-30, Task 7 fix round 1 (this revision):** Task 7's footprint audit measured real
courtyards for the four parts still using nominal placeholders after Task 2 — J1/J2 (USB-C
receptacle), D1/D2 (`D_SMA`), U2/U3/U4 (`SOT-23-6`), and Y1 (crystal) — plus, for this rewrite,
every remaining part in the BOM (0603/0805/1210 passives, LEDs, Q1) so the area check now has
**zero** placeholders left anywhere. Two things changed as a result:

1. **The length chain no longer closes against 80 mm** (80.10–83.70 mm real vs 78.3 mm
   placeholder). The design moved to the **1455C1202 (120 mm)** enclosure. The design spec
   (`docs/superpowers/specs/2026-07-28-usb-isolator-v1-design.md`) and implementation plan
   (`docs/superpowers/plans/2026-07-28-isolator-v1-schematic.md`) were updated in commit
   `7366d81` to match; this document is the corresponding rewrite of the feasibility record
   itself, which that commit did not touch.
2. **A utilization-arithmetic error was caught and corrected.** An intermediate draft of this
   round's area recompute mixed measured values for some parts (the four newly-flagged deltas,
   plus an inconsistent, undocumented substitution of measured 1210/passive counts for others)
   into what was otherwise still the original placeholder dictionary, producing an unreproducible
   919.6 mm² / 25.0% (against the 80 mm/3680 mm² envelope) that didn't match a clean recomputation
   from the same stated substitutions (871.9 mm² / 23.7%, using the flagged deltas only and
   leaving every other entry — `C bulk in`, `C raw/iso 47u`, D3/D4, and the generic 25-passives
   estimate — exactly as the original script had it). **Neither of those numbers is used in this
   revision.** This revision instead measures every one of the 43 real BOM parts individually —
   no generic passive-count estimate, no unmeasured entries of any kind — giving **921.98 mm²**,
   which is **16.7%** against the current 120 mm/5520 mm² envelope (or 25.1% against the
   historical 80 mm/3680 mm² envelope, shown for continuity with the numbers above). This is the
   number to treat as current; the 919.6/25.0% and 871.9/23.7% figures were both intermediate and
   are superseded.

## Notes for later tasks

- This is still a coarse, courtyard-sum feasibility check, not a placement study. It does not
  account for routing channels, keepout rings around the ADuM4165 isolation barrier,
  mounting-hole clearance, or connector cutout tolerances. The 120 mm envelope's ~36–40 mm of
  chain slack comfortably absorbs this, unlike the 80 mm envelope's near-zero/negative margin.
- Zone 2 ("ADuM4165 Side 1 + crystal + SN6505B") was **not** re-derived component-by-component
  in this revision — it is held at the spec's original 20 mm budget, which is now known to be
  conservative (Y1 and U4 both measure larger than originally assumed) but has not been replaced
  with a real chain formula the way zones 1/4/5 were. A future revision should derive one before
  relying on zone 2's number for anything tighter than the current 120 mm envelope.
- The D1/D2-side-by-side requirement for the rectifier zone is independent of enclosure length —
  it is a fixed local-geometry constraint, not a length-budget one, and is recorded in the
  schematic's "LAYOUT CONSTRAINTS -- BINDING" text block (item 7) for exactly that reason.
- KiCad install used for verification: `kicad-cli` 10.0.5 at
  `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`.
