# Isolated USB 2.0 Cable — v1 Design Spec

**Date:** 2026-07-28
**Project:** `isolator` — new sub-project `v1/isolator-v1`
**Status:** Approved
**Supersedes:** nothing. The 4-port design in
`2026-07-25-usb-isolator-design.md` continues in parallel and is referred to
here as **v2**.

## Overview

A single-port inline USB 2.0 isolator: one USB-C in, one USB-C out, no
external power input, no hub. Built on the same ADuM4165 core as v2 and
housed in a Hammond 1455C extruded enclosure.

v1 has two jobs at once, and both are first-class:

1. **It ships.** An enclosed bench tool that breaks a ground loop between a
   host and one USB device.
2. **v2 inherits it.** Every block in v1 is a block v2 already needs. v1
   validates them on real hardware — including two numbers v2's spec
   currently only estimates (see Verification, steps 3 and 6).

Primary references:

- ADuM4165/ADuM4166 data sheet **Rev. B** (`datasheets/adum4165-4166.pdf`)
- EVAL-ADuM4165/EVAL-ADuM4166 user guide UG-2027
  (`datasheets/eval-adum4165-4166-ug-2027.pdf`)
- ST USBLC6-2 data sheet, Doc ID 11265 Rev 5
- TI SLVAF82B, *ESD and Surge Protection for USB Interfaces*

## Requirements

- USB 2.0 low speed (1.5 Mbps), full speed (12 Mbps), and high speed
  (480 Mbps) pass-through.
- Galvanic isolation between host and device.
- Bus-powered only. No external power jack, no CC current-advertisement
  sensing on the upstream port. The design is budgeted against a plain
  500 mA host and works on legacy USB-A-to-C cables.
- One downstream USB-C port, USB 2.0 data, 5 V only.
- Downstream port current limit with soft-start and a visible fault
  indication.
- Fits a Hammond 1455C extrusion with plastic end panels.

## Architecture

```
 HOST SIDE (GND1)            ║ barrier ║            ISOLATED SIDE (GND2)
                             ║         ║
 J1 USB-C ──VBUS──┬──────────║         ║
 (UFP, 2× Rd 5.1k)│          ║         ║
                  ├─> ADuM4165 VBUS1   ║
                  │   (24 MHz xtal, Side 1)
                  │          ║         ║
                  └─> SN6505B ─> T1 ═══║══> 2× Schottky ─> ~6.1 V ─> LDO 5.0 V
                             ║ (750313638)                            │
                             ║         ║                      ┌───────┴──────┐
                             ║         ║                      │              │
   D+/D− ─ USBLC6 ─> UD± ════║═════════║══> DD± ─ USBLC6 ─┐  ADuM VBUS2  TPS2553
                             ║         ║                   │  (Side 2)   ILIM≈250mA
                             ║   CY 1nF Y1                  └──> J2 USB-C <───┘
                             ║  (populated)                      (DFP, 2× Rp 56k)
```

The ADuM4165 (not the '4166) remains correct: its clock input is on Side 1,
and ADI recommends the '4165 with a Side-1 crystal for isolator boxes with no
local controller, since host power is always present there.

## What changed from v2

**Deleted:** USB2514B hub and its crystal / RBIAS / CRFILT network; three of
the four TPS2553 port switches; the AP2112K-3.3 LDO (nothing needs 3.3 V once
the hub is gone — the ADuM4165's `VBUS2` pin feeds its own internal LDO for
`VDD2`); the TPS2121 priority mux; both TLV7041 CC comparators and the
`n3A_DET` lockout NMOS; the external-power USB-C receptacle; 2× USB-A and 1×
USB-C downstream receptacles; the power-source indicator LEDs. Roughly 125
footprints down to ~50.

**Kept unchanged, and these are the blocks v2 inherits back:** the ADuM4165
core with Side-1 24 MHz crystal and 8 pF loads; the `VBUS1`/`VDD1` bypass
rules (exactly 0.1 µF at `VDD1`, total lead length under 10 mm); the SN6505B +
Würth 750313638 + Schottky isolated supply; USBLC6-2SC6 arrays in
flow-through orientation; the barrier geometry including the routed slot
under T1.

**Substituted:** MIC29302 (3 A, DPAK, adjustable) replaced by a fixed-5.0 V
low-dropout regulator of roughly 1 A class, e.g. TLV76750 in SOT-23-5. The
bus-powered path cannot exceed ~315 mA even in v2, so the 3 A part was always
oversized. If v1 validates the substitute, fold it back into v2.

*Part-selection constraint to verify:* dropout at 315 mA against a
`DCDC_RAW` that sags under load. v2's spec records the winding DCR holding
`DCDC_RAW` ≥ 5.49 V at 635 mA, so expect roughly 5.8 V at 315 mA, leaving a
~0.8 V dropout budget. A 1117-class part at 1.2 V dropout does not fit; a
300–400 mV part does, with margin.

**Changed from DNP to populated:** the barrier-stitching capacitor. See ESD
protection below.

**Added:** one dedicated VBUS TVS per connector.

## Power budget

The ceiling is the host port's 500 mA obligation.

| Term | Value |
|---|---|
| Host budget | 2.5 W |
| less ADuM4165 Side 1 | −0.35 W |
| × converter efficiency ~90 % | 1.94 W secondary |
| at `DCDC_RAW` ≈ 6.15 V | ≈ 315 mA through the LDO |
| less ADuM4165 Side 2 (`IDD2(H)`, high speed) | −70 mA |
| less PGOOD / FAULT indicators | −~2 mA |
| **available at the downstream port** | **≈ 240 mA** |

TPS2553 ILIM is set to ~250 mA typical, so its tolerance band tops out near
the DC-DC ceiling rather than above it. The LDO's own current limit is the
backstop.

For comparison, v2's bus-powered mode budgets ≈ 75 mA shared across all four
ports. Dropping the hub is what buys the difference.

T1 has ample headroom at this current: Würth's thermal curve runs to 1.2 A.
The "100 mA" figure against 750313638 in TI's Table 9-3 is an
application-column characterization point, not a rating.

## Upstream side (GND1 domain)

- **J1:** USB 2.0-only USB-C receptacle, 16-pin. CC1 and CC2 each get a
  dedicated 5.1 kΩ Rd to GND1 — never shared, or orientation detection
  breaks. A6/B6 and A7/B7 tied at the connector. SBU1/SBU2 unconnected.
- **Power:** VBUS → ADuM4165 `VBUS1` and the SN6505B input. Bulk on VBUS
  sized to stay under the USB 2.0 §7.2.4.1 bus-powered limit of 10 µF / 50 µC
  at hot-plug — v1 has far less to bypass than v2, so meeting the limit is
  expected rather than waived. Confirm the total at schematic capture.
- **Data:** D+/D− → USBLC6-2SC6 → `UD+`/`UD−`.
- **Clock:** 24 MHz crystal on XI₁/XO₁ with 8 pF load caps. ≤50 ppm total
  tolerance, ≤100 ppm stability, CL ≈ 10 pF, start-up within 0.3 ms.

## Isolation barrier

- ADuM4165 in 20-lead wide-body SOIC_IC (RI-20-1), 8.3 mm creepage/clearance.
- T1 (Würth 750313638, 1:1.3, 5 kVrms) is the second crossing. Its
  recommended land pattern yields 7.51 mm; a routed slot beneath it restores
  margin.
- The barrier-stitching capacitor is the third and only other crossing.
- No other copper bridges the barrier, on any layer.

## Isolated side (GND2 domain)

- SN6505BDBV push-pull driver (420 kHz, spread spectrum) → T1 → Schottky
  rectification → `DCDC_RAW` ≈ 6.1 V → fixed 5.0 V LDO → `ISO_5V`.
- `ISO_5V` feeds the ADuM4165 `VBUS2` pin (internal LDO generates `VDD2`) and
  the TPS2553.
- **TPS2553** with ILIM ≈ 250 mA, permanently enabled, soft-start relied upon
  to let a device with bulk input capacitance charge without collapsing the
  DC-DC into a restart loop. FAULT drives an LED.
- **J2:** USB 2.0-only USB-C receptacle, 16-pin, as a DFP. CC1 and CC2 each
  pull up to 5 V through a dedicated 56 kΩ Rp (Default USB Power).
  SBU1/SBU2 unconnected.
- **Indicators:** PGOOD LED from the ADuM4165 Side-2 PGOOD pin; FAULT LED
  from TPS2553.

## ESD protection

Assessed against TI SLVAF82B, the ST USBLC6-2 data sheet, and the ADuM4165
Rev B absolute maximum ratings.

### D+/D− — USBLC6-2SC6, unchanged

| SLVAF82B §3.2 requirement | Target | USBLC6-2SC6 | |
|---|---|---|---|
| V_RWM | ≥ 3.3 V | 5.25 V | pass |
| Capacitance | < 4 pF | 2.5 pF typ, 3.5 pF max (I/O–GND) | pass |
| IEC 61000-4-2 | ≥ 8 kV contact, 15 kV air | 8 kV contact (Level 4), 15 kV air | pass |
| Clamping voltage | below downstream abs max | 12 V @ 1 A, 17 V @ 5 A | see below |

The IEC row uses the data sheet's front-page Level 4 *compliance* claim
(±15 kV air, ±8 kV contact), which is the conservative reading and lands
exactly on SLVAF82B's minimum. Table 1 of the same data sheet lists ±15 kV
contact as an *absolute rating*, so real margin is likely better than the
table shows. Design to the compliance number.

The USBLC6-2SC6 also specifies **ΔC(I/O–GND) = 0.015 pF**. SLVAF82B Figure
3-2 recommends two *separate* single-channel diodes on D+ and D−, which
carries part-to-part capacitance spread onto a 480 Mbps differential pair. On
a high-speed pair, matching matters more than absolute value: 2.5 pF into a
45 Ω single-ended line is τ ≈ 112 ps against USB 2.0's ~500 ps edge.

ADI independently confirms this class of part. The Rev B data sheet, PCB
Layout and EMI section, recommends Würth **82402304** to reach "Level 4 IEC
61000-4-2 ESD performance of ±8 kV contact discharge and ±15 kV air
discharge," and the EVAL board BOM (UG-2027) uses **NUP4202W1T2G**. WE
82402304, NUP4202, and USBLC6-2SC6 are the same architecture — a quad
steering-diode bridge to a rail pin plus a ~5–6 V transil, in SOT-23-6. The
USBLC6-2SC6's `Vbus` pin (pin 5) connects to the local VBUS rail on both
arrays.

### The clamping row is designed around, not fixed

The ADuM4165's absolute maximum on UD±/DD± is **−0.5 V to V_DDx + 0.5 V**,
i.e. **+3.8 V** with the internal 3.3 V regulator. No rail-clamp TVS
approaches that during a strike. ST's own §2.2 works the example: 10 mm of
track ≈ 6 nH, which at 24 A/ns adds **±144 V** on top of the clamp.

The ADuM4165's pin-level rating is **HBM ±4 kV** only. The ±8 kV IEC figure on
its front page is footnoted *"GND1 to GND2 or GND2 to GND1 across the
isolation barrier"* — a **barrier** rating, not a pin rating. The external
array is therefore load-bearing, and layout is the real specification.

**Hard layout constraints, DRC-checkable where possible:**

- ESD array within 5 mm of the connector pins it protects.
- Array GND pin on its own via directly to plane. Never daisy-chained
  through another component's ground.
- Pair routed *in-line through* the array — in on pins 1/3, out on pins 6/4 —
  with no stubs.

### GND2 has no ESD return path — stitching capacitor populated

SLVAF82B assumes a single ground throughout. This design has two, and GND2
floats. A strike into the downstream connector is clamped to GND2, and the
charge then has nowhere to go except across the barrier, through the
ADuM4165's die capacitance and T1's interwinding capacitance. The GND2 plane
lifts and the strike becomes a common-mode transient across the barrier —
which the ADuM4165 absolute maximum table caps at **±100 kV/µs**.

v1 therefore **populates** the barrier-stitching capacitor that v2 marks DNP:

- 1 nF, safety-rated **Y1**, 14 mm lead pitch, single point in the barrier gap.
  (The spec originally called for Y2. Task 2 reclassified it: CY1 bridges a
  *reinforced* barrier — the same role as the ADuM4165 — and Y1 is the class
  rated for that. The reclassification is also what surfaced a stocked 14 mm-pitch
  part, taking the geometric creepage margin from +1.1 mm to +5.05 mm.)
- Select a part whose body creepage and clearance clear the 8.3 mm barrier
  gap, so the capacitor does not become the weakest link in the barrier.
- Negligible at DC and mains frequency: 1 nF is 2.7 MΩ at 60 Hz, so the
  ground-loop breaking that is the product's purpose is unaffected.
- ADI's own EMI guidance uses the same capacitor for radiated emissions.

### VBUS

The USBLC6-2SC6's `Vbus` pin has a real transil to GND (V_BR = 6 V min), so
VBUS is already clamped. v1 adds one dedicated 5.5 V V_RWM TVS on each
connector's VBUS for peak-current headroom, per SLVAF82B §3.3.

### CC1/CC2 — deliberately unprotected in v1

In v1, CC connects only to a 5.1 kΩ Rd upstream and a 56 kΩ Rp downstream.
No IC pin sits behind them, there is no PD controller, and the design is
5 V only, so SLVAF82B §8.3's short-to-VBUS case pushes about 1 mA through a
resistor. Protection is not justified here.

This does **not** carry over to v2 — see the v2 finding recorded in
`docs/superpowers/reviews/2026-07-28-v2-cc-esd-finding.md`.

## Mechanical

**Enclosure:** Hammond **1455C802** — 80 × 54 × 23 mm, extruded aluminum body,
**plastic end panels**. Fallback **1455C1202** at 120 mm: same profile, same
board width, reached by editing the board outline only.

**Board:** 50 mm wide (the 1455C slot dimension), 80 mm target length,
4 layers, 90 Ω differential pairs on every USB segment.

Length budget for the 80 mm target:

| Zone | Approx. |
|---|---|
| J1 + ESD array + VBUS TVS | 15 mm |
| ADuM4165 Side 1 + crystal + SN6505B | 20 mm |
| Barrier zone | 8.3 mm |
| Rectifier + LDO + TPS2553 | 20 mm |
| ESD array + VBUS TVS + J2 | 15 mm |
| **Total** | **~78 mm** |

The barrier runs across the 50 mm width with the ADuM4165 (12.8 mm) and T1
(13.2 mm) straddling it side by side, leaving room for the routed slot and
the stitching capacitor.

### Enclosure and the isolation barrier

The extrusion is bonded to **neither** ground. It floats, giving
GND1 → gap → body → gap → GND2, two gaps in series.

**This makes edge copper pullback a barrier requirement, not a preference.**
The extrusion's internal slots grip the board's long edges in aluminum. If
plane copper reaches those edges, GND1 and GND2 both contact the extrusion
and the enclosure shorts the barrier.

- **All copper pulled back ≥ 1 mm (target 2 mm) from both long board edges,
  for the full board length, on every layer.**
- No vias or plane stitching near those edges.

Both receptacles are end-launched with mating faces flush to the outer face
of the plastic end panels. The slot height is chosen to center the opening
against the connector standoff. Verify with a 3D-printed end panel before
committing to machined panels.

Thermals are not a constraint: roughly 1 W total dissipation in an aluminum
enclosure.

### Accepted consequence

The effective barrier becomes the internal enclosure clearance, not the
ADuM4165's 5.7 kVrms rating. Two series air gaps inside a 54 mm box is a
few kV, which suits a bench instrument. A design needing the chip's full
rating end to end requires a non-conductive enclosure.

## Project layout

v1 is a **separate KiCad project inside this repository**:

```
v1/isolator-v1.kicad_pro
v1/isolator-v1.kicad_sch
v1/isolator-v1.kicad_pcb
```

It shares the existing `isolator-lib.pretty`, `isolator-lib.kicad_sym`,
`datasheets/`, and `tools/` (including the Freerouting pipeline). The
existing 4-port project files stay where they are and are untouched, so both
designs remain buildable and diffable. Proven blocks are copied forward into
v2 as hierarchical sheets.

## Known limitations (accepted)

- **≈ 240 mA at the downstream port**, while the 56 kΩ Rp advertises Default
  USB Power. This is the same descriptor-honesty deviation v2 carries,
  bounded here by the 250 mA TPS2553 limit and the LDO's current limit.
- A transparent isolator inherently draws host power that the downstream
  device never declared, because the host negotiates with the device, not
  with the isolator. This is intrinsic to the topology.
- The effective isolation is set by enclosure clearance, not by the
  ADuM4165 rating. See Mechanical.
- USB 2.0 only, 5 V only. No PD, no SuperSpeed pairs, no alternate modes.
- Consumes a hub tier. Deeply cascaded hubs downstream may fail.
- L1 sleep is not supported by the ADuM4165. L2 suspend is.
- The stitching capacitor is a deliberate common-mode path across the
  barrier. Negligible at 60 Hz, real at RF.
- One port. No hub means one device.

## Verification plan

Steps 3 and 6 are where v1 pays for itself — both replace estimates in v2's
spec with measurements.

1. **Host side alone.** V_DD1 present, 24 MHz oscillation on the Side-1
   crystal.
2. **Isolated supply.** `DCDC_RAW` under load, LDO dropout margin at 315 mA,
   output ripple.
3. **Measure the actual downstream current ceiling** before the DC-DC folds.
   v2's spec currently estimates this number.
4. **Enumeration** at low, full, and high speed with real devices — mouse,
   serial adapter, flash drive.
5. **TPS2553 behavior.** Soft-start against a device with large input
   capacitance; overload → FAULT LED → recovery.
6. **ESD.** Contact discharge to both connector shells and to the enclosure,
   with and without the stitching capacitor populated. This settles the
   DNP-versus-populate question for v2 with measurements rather than
   argument.
7. **Barrier withstand** with the board assembled in the enclosure, which
   measures the number that actually applies to the finished product.
