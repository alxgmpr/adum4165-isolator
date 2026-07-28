# v1 Mechanical Feasibility Gate (Task 1)

**Date:** 2026-07-28
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
   against the 3680 mm² usable area. Target: comfortably under 45% utilization (45% is a rule-of-thumb
   ceiling that leaves room for routing channels, connector keepouts, and mounting hardware — utilization
   above that has historically led to un-routable boards in this project's v2 layout).
2. **Length chain.** A worst-case linear dimension chain of the four functional zones that must sit
   in series along the 80 mm long axis (input connector/ESD/bulk cap, isolation barrier, output
   rectifier/LDO/current-limit, output ESD/connector), plus 2 mm of inter-zone spacing before/after
   and between each zone, compared against the 80 mm available length.

Courtyard sizes for U1 (ADuM4165) and T1 (750313638 transformer) were taken from the footprints
already present in the shared `isolator-lib.pretty` (measured, not datasheet nominal). All other
sizes are standard package envelopes (SOT-23, 0603, USB-C receptacle, SMA diode, etc.).

## Command run

```bash
python3 - <<'EOF'
parts = {
    'J1 USB-C':        (9.0, 7.5),   'J2 USB-C':        (9.0, 7.5),
    'U1 ADuM4165':     (11.8, 16.04),'T1 750313638':    (13.2, 9.64),
    'U2 USBLC6':       (3.0, 3.0),   'U3 USBLC6':       (3.0, 3.0),
    'U4 SN6505':       (3.0, 3.0),   'U5 LDO':          (3.0, 3.0),
    'U6 TPS2553':      (3.0, 3.0),   'Y1 crystal':      (3.2, 2.5),
    'D1 SMA':          (5.0, 3.0),   'D2 SMA':          (5.0, 3.0),
    'C bulk in':       (2.0, 1.25),  'C raw 47u':       (7.3, 4.3),
    'C iso 47u':       (7.3, 4.3),   'CY1 Y2 disc':     (10.0, 6.0),
    'D3/D4 LEDs':      (3.2, 1.6),   'D5/D6 TVS':       (2.0, 1.2),
}
area = sum(w*h for w, h in parts.values())
passives = 25 * (1.6 * 0.8)   # ~25 0603 R/C
total = area + passives
usable = 80 * 46
print(f"component area   {total:7.1f} mm^2")
print(f"usable area      {usable:7.1f} mm^2")
print(f"utilization      {100*total/usable:6.1f} %   (target < 45%)")

chain = [('J1 + ESD + bulk', 16), ('ADuM4165 barrier zone', 16),
         ('rectifier + LDO + TPS2553', 18), ('ESD + J2', 12)]
spacing = 2.0 * (len(chain) + 1)
length = sum(v for _, v in chain) + spacing
print(f"\nlength chain     {length:6.1f} mm  (available 80.0 mm)")
for n, v in chain: print(f"    {n:<32} {v:5.1f}")
EOF
```

## Output (real, unedited)

```
component area     699.3 mm^2
usable area       3680.0 mm^2
utilization        19.0 %   (target < 45%)

length chain       72.0 mm  (available 80.0 mm)
    J1 + ESD + bulk                   16.0
    ADuM4165 barrier zone             16.0
    rectifier + LDO + TPS2553         18.0
    ESD + J2                          12.0
```

## Verdict: GO

Both checks pass with margin:

- **Area:** 699.3 mm² of component courtyard against 3680 mm² usable = **19.0% utilization**,
  well under the 45% target (26 points of headroom).
- **Length:** 72.0 mm worst-case chain against 80.0 mm available = **8.0 mm margin** along the
  long axis.

The 1455C802 (80 x 50 mm) envelope is mechanically feasible for the v1 single-port design as
scoped. No fallback action is needed at this stage.

**Fallback restated:** if a later, more detailed placement pass (real footprints, real routing
keepouts, connector/mounting-hole clearances) erodes this margin below zero, move to the
**1455C1202** enclosure (120 mm length, same 50 mm width, same 1455C profile) by editing only the
`Edge.Cuts` outline in `v1/isolator-v1.kicad_pcb` — this requires no schematic or architectural
change, since the extra 40 mm of length is pure placement slack.

## Notes for later tasks

- This is a coarse, courtyard-sum feasibility check, not a placement study. It does not account for
  routing channels, keepout rings around the ADuM4165 isolation barrier, mounting-hole clearance, or
  connector cutout tolerances. Treat 19.0% as an optimistic lower bound on real utilization.
- KiCad install used for verification: `kicad-cli` 10.0.5 at
  `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`.
