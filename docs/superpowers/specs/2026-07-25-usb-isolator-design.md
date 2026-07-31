# Isolated 4-Port USB 2.0 Hub — Design Spec

> **Repo note (2026-07-30):** this document describes the **archived 4-port
> design**. That project no longer lives at the repo root — it was archived to
> branch `4port-archive` when the repository collapsed to the single-port
> isolator. Every bare `isolator.kicad_sch` / `isolator.kicad_pcb` /
> `isolator.kicad_pro` path below refers to the **archived** files as they stood
> on that branch, **not** to the files of those names at the root today, which
> are the single-port isolator. Retrieve them with
> `git show 4port-archive:isolator.kicad_sch`.

**Date:** 2026-07-25
**Project:** `isolator` (KiCad)
**Status:** Approved

## Overview

A USB isolator built around the Analog Devices ADuM4165 (5.7 kV rms USB 2.0
digital isolator, low/full/high speed with automatic detection and HS
retiming). Upstream: one USB-C port to the host. Downstream (isolated side):
a 4-port USB 2.0 hub fanning out to 2× USB-A and 2× USB-C receptacles.
Isolated-side power comes from an onboard isolated DC-DC (bus-powered light
loads) or an external power-only USB-C input, with automatic priority
switchover.

Primary references:

- ADuM4165/ADuM4166 data sheet Rev. B (`adum4165-4166.pdf`)
- EVAL-ADuM4165/EVAL-ADuM4166 user guide UG-2027 (`eval-adum4165-4166-ug-2027.pdf`)

The existing schematic core (ADuM4165 + 24 MHz crystal + 8 pF load caps)
matches the eval board reference design and is retained, with one deliberate
deviation: the eval board's NUP4202 ESD array is replaced by the
USBLC6-2SC6, whose flow-through pinout (I/O1 on pins 1 and 6, I/O2 on pins 3
and 4) lets each D+/D− pair enter one edge and leave the opposite edge at
constant spacing, keeping the high-speed pairs symmetric and routable.

## Requirements

- USB 2.0 low speed (1.5 Mbps), full speed (12 Mbps), and high speed
  (480 Mbps) pass-through.
- Galvanic isolation between host and all downstream ports; the power path
  must not undercut the ADuM4165's isolation barrier (transformer rated
  5 kVrms).
- 4 downstream ports: 2× USB-A, 2× USB-C (USB 2.0 data only, 5 V only).
- Dual isolated-side power: onboard isolated DC-DC from host VBUS, plus
  external USB-C power input with priority switchover.
- Per-port overcurrent protection with fault reporting through the hub.

## Architecture

```
 HOST SIDE (GND1)          ║ 5.7 kV barrier ║          ISOLATED SIDE (GND2)
                           ║                ║
 J1 USB-C ──VBUS──┬────────║──> SN6505B + 5kV xfmr ──> rect+LDO ──┐
 (upstream,       │        ║                ║                     v
  Rd 5.1k)        └─> ADuM4165 VBUS1        ║   J2 USB-C pwr ─> TPS2121 ─> ISO_5V
      │               (24 MHz xtal, Side 1) ║   (Rd + CC detect)  mux      │
      └─D+/D−─ ESD ─> UD± ══════════════════║══> DD± ─> USB2514B hub <─ 3.3V LDO
                           ║                ║          │
                           ║                ║   4× TPS2553 port switches
                           ║                ║   2× USB-A + 2× USB-C (Rp 56k)
```

The ADuM4165 (not the '4166) is correct for this topology: its clock input is
on Side 1, and ADI recommends the '4165 with a Side-1 crystal for isolator
boxes with no local controller, since host power is always present there.

## Upstream side (GND1 domain)

- **J1:** USB 2.0-only USB-C receptacle (16-pin). CC1 and CC2 each get a
  dedicated 5.1 kΩ Rd to GND1 (never shared — orientation detection breaks).
  A6/B6 and A7/B7 D+/D− pins tied at the connector.
- **Power:** VBUS → ADuM4165 `VBUS1` (internal LDO generates VDD1 = 3.3 V)
  and the SN6505B input. 10 µF bulk on VBUS; 0.1 µF at `VBUS1` and `VDD1`
  (exactly 0.1 µF at `VDD1` — larger disrupts start-up sequencing per data
  sheet), total lead length pin-to-cap under 10 mm.
- **Data:** D+/D− → USBLC6-2SC6 ESD array (flow-through: in on pins 1/3, out
  on pins 6/4) → `UD+`/`UD−`.
- **Clock:** 24 MHz crystal on XI₁/XO₁ with 8 pF load caps (existing).
  Crystal spec: ≤50 ppm total tolerance, ≤100 ppm stability, CL ≈ 10 pF,
  start-up within 0.3 ms (eval BOM class part). Short traces, tight
  placement.

## Isolation barrier

- ADuM4165 in 20-lead wide-body SOIC_IC, 8.3 mm creepage/clearance.
- The only other barrier-crossing component is the DC-DC transformer,
  rated 5 kVrms.
- Creepage targets: ≥8.3 mm at the ADuM4165 (RI-20-1 package basis); ≥7.5 mm
  at the transformer (Würth 750313638 recommended land pattern yields 7.51 mm
  — the part is rated 5 kVrms on this pattern; a routed slot under T1 at
  layout restores margin). No other copper bridges the barrier.
- Footprint provision for one barrier-stitching safety capacitor (DNP by
  default) for radiated-EMI margin.

## Isolated power (GND2 domain)

- **Bus-powered path:** SN6505BDBV push-pull driver (420 kHz, spread
  spectrum) + Würth 750313638 transformer (1:1.3, 5 kVrms) + Schottky
  rectifier → ~6 V raw → MIC29302 low-dropout LDO (3 A-class, adjustable,
  set to 5.0 V; chosen over a fixed 1117-class part because the ~6 V raw
  rail leaves too little headroom for a 1.2 V-dropout regulator under
  load) → `DCDC_5V`. **Budget (corrected 2026-07-26, Task 11 review DR-01):**
  the ceiling is the host port's 500 mA obligation, not the magnetics.
  2.5 W from the host, less ~0.35 W for ADuM4165 Side 1, times ~90 %
  converter efficiency ≈ 1.94 W; at `DCDC_RAW` ≈ 6.15 V that is ≈ 315 mA
  through the LDO, so **`ISO_5V` tops out at ≈ 310 mA**. Isolated-side
  self-draw is ≈ 235 mA (ADuM4165 Side 2 ~70 mA at `IDD2(H)`, hub ~155 mA
  at `IHCH1` base + 3 × 25 mA, plus indicator LEDs), which leaves
  **≈ 75 mA total for all four downstream ports combined** in bus-powered
  mode. T1 itself has headroom well past this — Würth's thermal curve runs
  to 1.2 A and the winding DCR holds `DCDC_RAW` ≥ 5.49 V at 635 mA; the
  "100 mA" against 750313638 in TI's Table 9-3 is an application-column
  characterization point, not a rating.
- **External path:** J2 power-only USB-C receptacle, dedicated dual
  5.1 kΩ Rd. Two TLV7041 open-drain comparators (one per CC line, outputs
  wire-ORed, threshold 1.23 V from a divider off the 3.3 V rail) detect a
  3 A source advertisement on whichever CC line is active. Their wire-ORed
  open-drain output `n3A_DET` is high (via a 100 kΩ pull-up to `ISO_3V3`)
  whenever no 3 A source is advertised, and low when one is. That single
  net drives **both** halves of the lockout: a small NMOS inverts it onto
  the TPS2121's PR1 priority input, **and it drives CP2 directly**. Both
  are required — grounding CP2 and relying on PR1 alone puts the TPS2121
  in VCOMP mode, which selects the *higher* input rather than IN2, so a
  weak brick sitting above `DCDC_5V` would win (TPS2121 Table 9-3; VCOMP
  is specified 0/280/600 mV). With CP2 ← `n3A_DET`: no 3 A ⇒ CP2 ≥ VREF
  and PR1 < VREF ⇒ OUT = IN2 unconditionally; 3 A detected ⇒ CP2 < VREF
  and PR1 ≥ VREF ⇒ OUT = IN1. A weak brick is never silently overloaded.
  (Fixed in Task 11 as review finding DR-06; the original wiring grounded
  CP2.) "External active" indication comes from the TPS2121 ST status pin
  driving an LED.
- **Priority mux:** TPS2121. IN1 = external 5 V (priority only when the
  CC detect confirms a 3 A source), IN2 = `DCDC_5V`, output = `ISO_5V`.
  Seamless switchover.
- **Rails from `ISO_5V`:** ADuM4165 `VBUS2` (internal LDO → VDD2), the four
  port switches, and an AP2112K-3.3 LDO for the hub.

## Hub and downstream ports (GND2 domain)

- **Hub:** USB2514B (QFN-36). 3.3 V supply, internal 1.8 V core regulator
  (CRFILT), own 24 MHz crystal, 12 kΩ RBIAS, default strap configuration
  (no SMBus/EEPROM). Upstream port ← ADuM4165 `DD+`/`DD−`.
- **Port power:** one TPS2553 per port, ILIM ≈ 600 mA, EN from hub PRTPWR,
  FAULT to hub OCS — overcurrent is reported upstream and other ports
  survive.
- **Connectors:** 2× USB-A, 2× USB-C. Each USB-C CC pin pulls up to 5 V
  through 56 kΩ (Rp = default USB power; deliberately not advertising
  1.5 A the 600 mA limit can't deliver).
- **Protection:** USBLC6-2SC6 per downstream port on D+/D−, oriented so the
  pair flows through from the connector edge to the hub side.
- **Indicators:** PGOOD LED (ADuM4165 Side-2 PGOOD), power-source LEDs: D6
  bus-powered, D4 external-active (post-lockout, external-selected implies a
  3 A source; "external present but locked out" reads as D4 off + D6 on).

## Layout rules

- 90 Ω differential impedance, length-matched pairs for every USB segment:
  J1→ADuM, ADuM→hub, hub→each port.
- Bypass placement per data sheet (<10 mm total lead length).
- Crystal loops minimized on both ADuM4165 and USB2514B.
- Barrier gap rules as in "Isolation barrier" above.

## Known limitations (accepted)

- The isolator adds one-to-two hub-tier delays; with the USB2514B this
  consumes ~3 of USB's 5 tiers. Deeply cascaded hubs downstream may fail.
- Downstream USB-C ports are USB 2.0 data, 5 V only. No PD, no SS pairs.
- Bus-powered mode is a light-load mode: **≈ 75 mA total for all four
  downstream ports combined** (see the corrected budget above). That is one
  low-power device — a debug probe, a serial adapter, a keyboard — not a
  populated hub. Anything beyond that requires the external supply.
- The hub declares self-powered regardless of actual power source
  (strap-only config cannot switch descriptors dynamically). In
  bus-powered mode (no external supply) this is a USB descriptor-honesty
  deviation; per-port TPS2553 limits, the TPS2121 3A limit, and the
  MIC29302 current limit bound the actual draw. Rated 500 mA/port
  operation requires the external supply.
- L1 sleep is not supported by the ADuM4165 (L2 suspend is).
- `VBUS_HOST` carries ~20 µF of input capacitance (C3 + C7 + bypass) with no
  inrush limiting — about 2× the USB 2.0 §7.2.4.1 bus-powered limit of
  10 µF/50 µC at hot-plug. Accepted for a prototype-class bench device (real
  hosts tolerate it); decide accept-vs-soft-start pad at layout.

## Verification plan

1. Host side alone: VDD1 present, 24 MHz oscillation.
2. Isolated supplies: DC-DC output voltage/ripple, mux switchover under
   load, LDO rails.
3. Hub enumerates through the isolator at high speed (`lsusb -t` / USB tree).
4. Each port with real LS/FS/HS devices (mouse, serial adapter, flash drive).
5. Per-port overcurrent: shorted load → hub reports fault, other ports
   unaffected.
6. Barrier withstand sanity check with an insulation tester (if available).
