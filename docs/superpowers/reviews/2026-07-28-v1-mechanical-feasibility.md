# v1 Mechanical Feasibility Gate (Task 1)

**Date:** 2026-07-28 (originally); **updated 2026-07-28 in Task 2 fix round 1** — see "Update
history" at the end. The verdict is still GO, but the margin is materially tighter than first
reported; read the "Rectifier + LDO + TPS2553 zone" section before treating this as comfortable.

**Scope:** go/no-go check on whether the v1 (single-port USB isolator) component set fits the
target enclosure, before any v1 schematic work begins.

**Target envelope:** Hammond 1455C802, internal usable board area 80 mm (length) x 50 mm (width).
Usable copper area for component placement is 80 x 50 mm minus a 2 mm copper pullback on each long
edge: **80 x 46 = 3680 mm²**.

**Fallback (documented, not triggered):** if either check below fails, the design moves to the
**1455C1202** enclosure — same 1455C profile, same 50 mm board width, 120 mm length — by editing
only the board outline in the PCB file. No schematic or architecture change is implied by the
fallback.

---

## Method

Two checks, run as a standalone Python (stdlib only) script — see command and full output below.

1. **Area utilization.** Sum of courtyard footprint areas (width x height, mm) for every part in
   the v1 BOM, plus an estimate for ~25 passive 0603 R/C parts (1.6 x 0.8 mm each), compared
   against the 3680 mm² usable area. Target: comfortably under 45% utilization.
2. **Length chain.** A worst-case linear dimension chain of the zones that must sit in series
   along the 80 mm long axis, compared against the 80 mm available length. **This revision uses
   the 5-zone budget from `docs/superpowers/specs/2026-07-28-usb-isolator-v1-design.md`
   ("Length budget for the 80 mm target" table) instead of the original 4-zone model** — see
   "Update history" for why.

Courtyard sizes for U1 (ADuM4165) and T1 (750313638 transformer) were taken from the footprints
already present in the shared `isolator-lib.pretty` (measured, not datasheet nominal). U5 (LDO),
U6 (TPS2553), D5/D6 (TVS), and CY1 courtyards are now also measured from real footprint `F.CrtYd`
geometry (see below) as of this revision. All other sizes remain standard package envelopes
(SOT-23, 0603, USB-C receptacle, SMA diode) that were not touched by Task 2 and have not been
re-measured.

## Command run

```bash
python3 - <<'EOF'
parts = {
    'J1 USB-C':        (9.0, 7.5),   'J2 USB-C':        (9.0, 7.5),
    'U1 ADuM4165':     (11.8, 16.04),'T1 750313638':    (13.2, 9.64),
    'U2 USBLC6':       (3.0, 3.0),   'U3 USBLC6':       (3.0, 3.0),
    'U4 SN6505':       (3.0, 3.0),
    'U5 LDO (TLV76750DGNR, HVSSOP-8, measured F.CrtYd)': (6.26, 3.50),
    'U6 TPS2553 (SOT-23-6, measured F.CrtYd)': (4.1, 3.4),
    'Y1 crystal':      (3.2, 2.5),
    'D1 SMA':          (5.0, 3.0),   'D2 SMA':          (5.0, 3.0),
    'C bulk in':       (2.0, 1.25),  'C raw 47u':       (7.3, 4.3),
    'C iso 47u':       (7.3, 4.3),
    'CY1 (Q07F3Z102M, custom C_Disc_D7.0mm_W5.5mm_P14.00mm, measured)': (16.5, 6.0),
    'D3 LED':          (3.2, 1.6),   'D4 LED':          (3.2, 1.6),
    'D5 TVS (T6V0S5A-7, SOD-523, measured F.CrtYd)': (2.5, 1.4),
    'D6 TVS (T6V0S5A-7, SOD-523, measured F.CrtYd)': (2.5, 1.4),
}
area = sum(w*h for w, h in parts.values())
passives = 25 * (1.6 * 0.8)   # ~25 0603 R/C
total = area + passives
usable = 80 * 46
print(f"component area   {total:7.1f} mm^2")
print(f"usable area      {usable:7.1f} mm^2")
print(f"utilization      {100*total/usable:6.1f} %   (target < 45%)")

# Zone budget corrected to match docs/superpowers/specs/2026-07-28-usb-isolator-v1-design.md
# (5-zone table, "Length budget for the 80 mm target") instead of the earlier 4-zone
# collapse, which merged two spec zones into one and silently dropped 6.3 mm of budget.
chain = [
    ('J1 + ESD array + VBUS TVS', 15),
    ('ADuM4165 Side 1 + crystal + SN6505B', 20),
    ('Barrier zone', 8.3),
    ('Rectifier + LDO + TPS2553', 20),
    ('ESD array + VBUS TVS + J2', 15),
]
length = sum(v for _, v in chain)
print(f"\nlength chain (spec 5-zone) {length:6.1f} mm  (available 80.0 mm, margin {80-length:4.1f} mm)")
for n, v in chain: print(f"    {n:<38} {v:5.1f}")

# Real-component check for the "Rectifier + LDO + TPS2553" zone specifically,
# since this is the zone that changed (new LDO) and the one flagged for review.
d_sma = 5.0       # D1/D2, unmeasured (out of Task 2 scope), placeholder retained
ldo = 6.26        # TLV76750DGNR, HVSSOP-8, measured
tps = 4.1         # TPS2553DBV, SOT-23-6, measured
gap = 1.0         # assumed minimum inter-component keepout within the zone

parallel = d_sma + ldo + tps + 2*gap   # D1 || D2 (center-tap pair, side by side in Y)
serial   = 2*d_sma + ldo + tps + 3*gap  # D1 + D2 both in series in X (worst case)
print(f"\nRectifier+LDO+TPS2553 real check against 20 mm budget:")
print(f"    D1 || D2 (parallel, center-tap pair): {parallel:5.2f} mm  (margin {20-parallel:+.2f} mm)")
print(f"    D1 + D2 (serial, worst case):         {serial:5.2f} mm  (margin {20-serial:+.2f} mm)")
EOF
```

## Output (real, unedited)

```
component area     765.9 mm^2
usable area       3680.0 mm^2
utilization        20.8 %   (target < 45%)

length chain (spec 5-zone)   78.3 mm  (available 80.0 mm, margin  1.7 mm)
    J1 + ESD array + VBUS TVS               15.0
    ADuM4165 Side 1 + crystal + SN6505B     20.0
    Barrier zone                              8.3
    Rectifier + LDO + TPS2553               20.0
    ESD array + VBUS TVS + J2               15.0

Rectifier+LDO+TPS2553 real check against 20 mm budget:
    D1 || D2 (parallel, center-tap pair): 17.36 mm  (margin +2.64 mm)
    D1 + D2 (serial, worst case):         23.36 mm  (margin -3.36 mm)
```

## Verdict: GO, but with a materially tighter margin than first reported

- **Area:** 765.9 mm² of component courtyard against 3680 mm² usable = **20.8% utilization**,
  still well under the 45% target (24 points of headroom). This check is not close to failing.
- **Length (corrected 5-zone chain):** 78.3 mm against 80.0 mm available = **1.7 mm margin**.
  This is the design spec's own budget (`docs/superpowers/specs/2026-07-28-usb-isolator-v1-design.md`),
  not a new number — the original version of this document used a different 4-zone model that
  collapsed two of the spec's zones together and arrived at a falsely comfortable 8.0 mm margin.
  See "Update history" below.
- **Rectifier + LDO + TPS2553 zone, specifically:** fits the 20 mm budget with **+2.64 mm margin**
  only if D1 and D2 (the secondary-side rectifier diodes) are placed side by side (parallel in the
  cross-board direction) rather than literally chained one after the other along the board's long
  axis. This is the physically correct placement for a center-tap rectifier pair fed from a
  push-pull transformer secondary (each diode's anode comes from a different secondary tap; both
  cathodes join at `DCDC_RAW`) — it is not a stretch or a workaround, it is how this topology is
  normally laid out. If D1/D2 were forced into strict series placement instead, the zone would
  overflow by 3.36 mm. **This is now a load-bearing layout constraint, not a nice-to-have: Task
  4/5 must place D1/D2 side by side in this zone, not in series.**

The 1455C802 (80 x 50 mm) envelope remains mechanically feasible for the v1 single-port design as
scoped, but the 1.7 mm overall length margin (down from the 8.0 mm this document previously
claimed) means there is very little room left for routing detours, via keepouts around the
isolation barrier, or connector/mounting-hole tolerance stack-up. Treat this as a **tight GO**,
not a comfortable one.

**Fallback restated:** if a later, more detailed placement pass (real footprints, real routing
keepouts, connector/mounting-hole clearances) erodes this margin below zero, move to the
**1455C1202** enclosure (120 mm length, same 50 mm width, same 1455C profile) by editing only the
`Edge.Cuts` outline in `v1/isolator-v1.kicad_pcb` — this requires no schematic or architectural
change, since the extra 40 mm of length is pure placement slack. Given the 1.7 mm margin found
here, **Task 4/5 should treat this fallback as a live option to revisit, not a remote one.**

## Update history

**2026-07-28, Task 2 fix round 1** (in response to review Critical 3): the LDO changed from
`MIC29302WU` (TO-263-5, 16.65 x 11.3 mm = 188.1 mm² courtyard) to `TLV76750DGNR` (HVSSOP-8,
6.26 x 3.50 mm = 21.9 mm² courtyard) as part of the Task 2 fix (see
`docs/superpowers/reviews/2026-07-28-v1-part-selection.md`). The review that triggered this fix
also caught that the *previous* version of this document (which still assumed
`'U5 LDO': (3.0, 3.0)` = 9 mm², neither the old nor the new real part) understated the LDO
courtyard, and separately noted the reviewer's own measurement of the `TO-263-5` courtyard
(188.1 mm², utilization 23.9%) as what utilization would have been had `MIC29302WU` stayed the
pick. Since the LDO changed to a much smaller part instead, utilization actually **improved** to
20.8%, not degraded to 23.9% — both numbers are noted here so this isn't read as silently
disagreeing with the reviewer without explanation.

While fixing the LDO number, three more issues were found and corrected in the same pass:

1. **D3/D4 (LEDs) and D5/D6 (TVS) were each a single dict entry representing two physical
   parts**, undercounting total placed area by one LED and one TVS footprint. Split into
   separate `D3`/`D4` and `D5`/`D6` entries.
2. **D5/D6 now use the real T6V0S5A-7 SOD-523 courtyard** (2.5 x 1.4 mm, measured from the stock
   `Diode_SMD:D_SOD-523` footprint) instead of the earlier (2.0, 1.2) placeholder.
3. **CY1 now uses the real custom footprint courtyard** (16.5 x 6.0 mm, measured from
   `isolator-lib:C_Disc_D7.0mm_W5.5mm_P14.00mm`) instead of the earlier (10.0, 6.0) placeholder —
   CY1's lead spacing grew from 10 mm to 14 mm in the same fix round for creepage-margin reasons
   (see the part-selection review), which is most of why this footprint got bigger.
4. **The length-chain model was replaced.** The original 4-zone chain (`J1 + ESD + bulk`: 16 mm,
   `ADuM4165 barrier zone`: 16 mm, `rectifier + LDO + TPS2553`: 18 mm, `ESD + J2`: 12 mm, total
   62 mm + 10 mm inter-zone spacing = 72 mm) does not match the design spec's own 5-zone budget
   (`J1 + ESD array + VBUS TVS`: 15 mm, `ADuM4165 Side 1 + crystal + SN6505B`: 20 mm,
   `Barrier zone`: 8.3 mm, `Rectifier + LDO + TPS2553`: 20 mm, `ESD array + VBUS TVS + J2`: 15 mm,
   total 78.3 mm, no separate inter-zone spacing term). The old model's "ADuM4165 barrier zone"
   entry (16 mm) appears to have merged the spec's `ADuM4165 Side 1 + crystal + SN6505B` (20 mm)
   and `Barrier zone` (8.3 mm) into one number that is smaller than either spec zone alone — how
   that number was arrived at is not recoverable from the original document. This revision
   replaces the ad hoc 4-zone model with the spec's real 5-zone budget, which is why the length
   margin drops from a claimed 8.0 mm to the spec's own 1.7 mm. **The spec's ~78 mm total was
   already documented as tight against the 80 mm target before this fix round; the earlier
   version of this feasibility document was simply computing a different, looser number than the
   spec it was supposed to be checking against.**

## Notes for later tasks

- This is a coarse, courtyard-sum feasibility check, not a placement study. It does not account for
  routing channels, keepout rings around the ADuM4165 isolation barrier, mounting-hole clearance, or
  connector cutout tolerances. Given the length margin is now 1.7 mm (not 8.0 mm), this caveat is no
  longer academic — a real placement pass could plausibly erode 1.7 mm just from via/keepout
  clearance around U1/T1's barrier slot alone.
- Sizes for J1/J2, U2/U3/U4, Y1, D1/D2, and the bulk/47uF capacitors remain nominal package
  envelopes, not measurements of specific chosen footprints (those parts are outside Task 2's
  scope). Treat them with the same caution as before.
- KiCad install used for verification: `kicad-cli` 10.0.5 at
  `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`.
