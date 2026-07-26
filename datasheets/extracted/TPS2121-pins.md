# TPS2121 (TI) — Pin Table

Source: `datasheets/TPS2121RUXR.pdf` (SLVSEA3F, TPS2120/TPS2121 combined datasheet,
Rev F Aug 2020), Section 6 "Pin Configuration and Functions" (p.4-5) and Section 7.5
"Electrical Characteristics" (p.7-8).

**Package used in this design: TPS2121 in RUX (VQFN-HR), 12-pin.**
(TPS2120 is a different package/pinout — WCSP-20 — and is NOT used here; do not
mix up pin numbers between the two variants.)

## Pin-number -> name -> function (TPS2121, VQFN-HR-12, RUX package)

| Pin # (TPS2121) | Name | I/O | Function |
|---|---|---|---|
| 1 | OUT | I/O (power) | Power Output (tied internally with pin 8) |
| 2 | IN2 | I | Power Input for Source 2 |
| 3 | CP2 | I | Enables comparator operation; compared to PR1 to set switchover voltage. Connect to GND if not required. **TPS2121 only** (no equivalent pin on TPS2120). |
| 4 | OV2 | I | Active-low enable/supervisor for IN2 overvoltage protection. Connect to GND if not required. |
| 5 | OV1 | I | Active-low enable/supervisor for IN1 overvoltage protection. Connect to GND if not required. |
| 6 | PR1 | I | Enables priority operation. Connect to IN1 to set switchover voltage. Connect to GND if not required. |
| 7 | IN1 | I | Power Input for Source 1 |
| 8 | OUT | I/O (power) | Power Output (tied internally with pin 1) |
| 9 | ST | O | Status output indicating which channel is selected. Connect to GND if not required (pull-up 6-20 kOhm, per Rec. Op. Cond.). |
| 10 | ILIM | O | Sets output current limit for both channels via external resistor (18 kOhm - 100 kOhm recommended range). |
| 11 | SS | O | Adjusts input settling delay time and output soft-start time (external cap to GND). |
| 12 | GND | — | Device ground |

Notes:
- SEL (manual input-source override, active-low) exists only on TPS2120 — **not present** on
  TPS2121 (no pin assignment in the TPS2121/VQFN-HR column).
- OUT is a dual-bonded pin (1 and 8 both = OUT) on the 12-pin VQFN-HR package.

## PR1 threshold voltage

PR1 (and CP2, OV1, OV2) share a common internal comparator reference, `V_REF,x`,
per Section 7.5 Electrical Characteristics (control pins PRI, SEL, OV1, OV2 row
"Internal Voltage Reference"):

| Parameter | Condition | Min | Typ | Max | Unit |
|---|---|---|---|---|---|
| V_REF,x rising | V_PR1, V_CP2, V_OV1, V_OV2 rising | 1.01 | 1.06 | 1.1 | V |
| V_REF,x falling | V_PR1, V_CP2, V_OV1, V_OV2 falling | 0.99 | 1.04 | 1.09 | V |

So **PR1 threshold ≈ 1.04 V typical** (1.01-1.1 V rising, 0.99-1.09 V falling), with
comparator offset voltage (TPS2121 only, PRI vs CP2) of 5/20/40 mV min/typ/max.
A resistor divider from IN1 to GND sets the priority/switchover voltage relative to
this ~1.04 V reference.

## Package

**TPS2121: RUX — 12-pin VQFN-HR**, body size 2.0 mm x 2.0 mm x 2.5 mm (per Device
Information table, p.1); On-resistance 56 mOhm typ; output current limit range 1-4.5 A
(via R_ILM 18.7 kOhm-80 kOhm); fastest switchover 5 us typical (fast-switchover
feature via CP2, TPS2121-only).
