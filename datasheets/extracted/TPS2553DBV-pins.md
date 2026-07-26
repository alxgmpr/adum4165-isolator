# TPS2553 (TI) — Pin Table

Source: `datasheets/TPS2553DBVR.pdf` (SLVS841F, TPS2552/TPS2553/TPS2552-1/TPS2553-1
combined datasheet, Rev F Aug 2016), Section 6 "Pin Configuration and Functions"
(p.5) and Section 9.5.1 "Programming the Current-Limit Threshold" (p.15).

**Package used in this design: TPS2553 in DBV (SOT-23-6).**
(A WSON-6 (DRV) package option also exists with different pin numbering — not used
here.)

## Pin-number -> name -> function (TPS2553, SOT-23-6, DBV package)

| Pin # (DBV/SOT-23) | Name | I/O | Function |
|---|---|---|---|
| 1 | IN | I | Input voltage. Connect a >=0.1 uF ceramic capacitor from IN to GND, as close to the IC as possible. |
| 2 | GND | — | Ground connection; connect externally to PowerPAD. |
| 3 | EN | I | Enable input, **logic HIGH turns on power switch** (TPS2553; TPS2552 is the active-low, EN-bar variant — do not confuse the two). Compatible with TTL and CMOS levels. |
| 4 | FAULT (active-low, open-drain) | O | Asserted (pulled low) during overcurrent, overtemperature, or reverse-voltage conditions. |
| 5 | ILIM | O (sets threshold) | External resistor from ILIM to GND sets the current-limit threshold; recommended range 15 kOhm <= R_ILIM <= 232 kOhm. |
| 6 | OUT | O (power) | Power-switch output. |

Note: PowerPAD (thermal pad) is not a numbered pin on the DBV/SOT-23-6 package
(the PowerPAD pin number 7-equivalent only exists on the DRV/WSON-6 package,
where it is labeled "PAD" and internally tied to GND). On DBV, GND (pin 2) is
the sole ground connection.

## EN polarity — CONFIRMED

- **TPS2552: EN-bar (active-LOW)** — logic low on EN-bar turns the switch on.
- **TPS2553: EN (active-HIGH)** — logic high on EN turns the switch on. **This is
  the part used in this design (TPS2553DBVR) — EN is active-high.**
- (The "-1" suffix variants, TPS2552-1/TPS2553-1, are latch-off versions with the
  same EN polarity as their non-"-1" counterpart; not used in this design.)

## ILIM equations (Section 9.5.1, "Current-Limit Threshold Equations (I_OS)")

Valid over 15 kOhm <= R_ILIM <= 232 kOhm (1% resistor recommended for stability
of the internal regulation loop):

```
I_OSmax (mA) = 22980 / R_ILIM^0.94      [R_ILIM in kOhm]
I_OSnom (mA) = 23950 / R_ILIM^0.977     [R_ILIM in kOhm]
I_OSmin (mA) = 25230 / R_ILIM^1.016     [R_ILIM in kOhm]
```

These give the resulting overcurrent threshold (accounting for TI's characterized
max/nom/min spread due to temperature and process — but NOT external resistor
tolerance, which must be budgeted separately). A special case: tying ILIM directly
to IN (bypassing the resistor) gives a fixed ~75 mA (typical) current-limit
threshold; low-ESR ceramic capacitance from IN to GND may be needed in that
configuration to prevent noise coupling into the ILIM circuitry.

Device also supports a fixed 1.5 A max continuous load current, up to 1.7 A
(typical) current-limit accuracy of +/-6% at the higher settings, 85 mOhm
high-side MOSFET, and fast overcurrent response (2 us typical).
