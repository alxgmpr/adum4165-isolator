# Isolated 4-Port USB 2.0 Hub — Design Spec

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

The existing schematic core (ADuM4165 + 24 MHz crystal + 8 pF load caps +
NUP4202 ESD array) matches the eval board reference design and is retained.

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
- **Data:** D+/D− → NUP4202 ESD array → `UD+`/`UD−`.
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
  load) → `DCDC_5V`. Usable budget
  ≈ 700 mA; after isolator Side 2 (~60 mA in HS) and hub (~150 mA),
  roughly 400–500 mA remains for downstream devices.
- **External path:** J2 power-only USB-C receptacle, dedicated dual
  5.1 kΩ Rd. Two TLV7041 open-drain comparators (one per CC line, outputs
  wire-ORed, threshold 1.23 V from a divider off the 3.3 V rail) detect a
  3 A source advertisement on whichever CC line is active. When no 3 A
  advertisement is present, a small NMOS holds the TPS2121's PR1 priority
  input low so the mux stays on the DC-DC — a weak brick is never
  silently overloaded. "External active" indication comes from the
  TPS2121 ST status pin driving an LED.
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
- **Protection:** NUP4202 per downstream port on D+/D−.
- **Indicators:** PGOOD LED (ADuM4165 Side-2 PGOOD), power-source LEDs
  (bus-powered / external / external-3A).

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
- Bus-powered mode is a light-load mode (~400 mA total for devices).
- The hub declares self-powered regardless of actual power source
  (strap-only config cannot switch descriptors dynamically). In
  bus-powered mode (no external supply) this is a USB descriptor-honesty
  deviation; per-port TPS2553 limits, the TPS2121 3A limit, and the
  MIC29302 current limit bound the actual draw. Rated 500 mA/port
  operation requires the external supply.
- L1 sleep is not supported by the ADuM4165 (L2 suspend is).

## Verification plan

1. Host side alone: VDD1 present, 24 MHz oscillation.
2. Isolated supplies: DC-DC output voltage/ripple, mux switchover under
   load, LDO rails.
3. Hub enumerates through the isolator at high speed (`lsusb -t` / USB tree).
4. Each port with real LS/FS/HS devices (mouse, serial adapter, flash drive).
5. Per-port overcurrent: shorted load → hub reports fault, other ports
   unaffected.
6. Barrier withstand sanity check with an insulation tester (if available).
