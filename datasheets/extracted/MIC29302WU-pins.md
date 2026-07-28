# MIC29302WU (Microchip) — Pin Table

Source: `datasheets/MIC29302WU.pdf` (DS20005685A, "MIC2915X/30X/50X/75X High-Current
Low Dropout Regulators", (c) 2016 Microchip Technology Inc.), Section "Package Types"
(p.1-2, package `MIC29302/502 5-Lead TO-263 (D2Pak) Adj. Voltage (U)`) and
`TABLE 1-1: ELECTRICAL CHARACTERISTICS` (p.5).

**Package used in this design: MIC29302WU — 5-pin TO-263 (D2Pak), adjustable-voltage
version, "U" suffix = surface-mount TO-263.** This is the same part and footprint v2
already uses (`U6` in `isolator.kicad_sch`). v1 reuses it unmodified as the fallback
LDO — see `docs/superpowers/reviews/2026-07-28-v1-part-selection.md` for why
TLV76750 (the SOT-23-5 candidate) was rejected.

## Pin-number -> name -> function (MIC29302, 5-Lead TO-263 D2Pak Adjustable)

| Pin # | Name | I/O | Function |
|---|---|---|---|
| 1 | EN | I | Enable, active-high logic input. Tie to VIN if ON/OFF control is not needed (internal pull-up not guaranteed floating-safe per datasheet; tie explicitly). |
| 2 | VIN | Power in | Regulator input, connects to `DCDC_RAW`. |
| 3 | GND | — | Ground. Also electrically bonded to the package tab (BAT/exposed pad) per the "Top View" package drawing. |
| 4 | VOUT | Power out | Regulator output, connects to `ISO_5V`. |
| 5 | ADJ | I | Adjust/feedback input. Output voltage set by external resistor divider from VOUT to GND, tap to ADJ: `VOUT = VREF x (1 + R1/R2)`, VREF = 1.24 V typ (from the functional diagram, "REFERENCE" block, p.3). |

Notes:
- This matches the KiCad stock symbol `Regulator_Linear:MIC29302WU` exactly:
  pin 1 = EN, pin 2 = VIN, pin 3 = GND, pin 4 = VOUT, pin 5 = ADJ (verified
  against `Regulator_Linear.kicad_sym` in the KiCad 10.0.5 stock library).
- Package tab (BAT = "battery"/back-metal tab on the D2Pak) is internally
  tied to GND — do not treat it as a separate net.

## Output-setting resistor divider (v2's proven values, reusable in v1)

v2 wires U6 adjustable with **R_top = 30.1 kOhm** (VOUT to ADJ) and
**R_bottom = 10 kOhm** (ADJ to GND), for:

`VOUT = 1.24 V x (1 + 30.1k/10k) = 1.24 V x 4.01 = 4.97 V`

This is documented here as ground truth for Task 4; do not re-derive from memory.

## Key electrical parameters (MIC2930x family = MIC29300/29301/29302/29303, 3 A)

Source: `TABLE 1-1: ELECTRICAL CHARACTERISTICS`, p.5. Conditions: V_IN = V_OUT + 1V,
T_J = +25 degC unless noted; bold values in the original table apply -40 to +125 degC.

| Parameter | Condition | Min | Typ | Max | Unit |
|---|---|---|---|---|---|
| Dropout voltage | MIC2930x, I_OUT = 100 mA | - | 80 | 175 | mV |
| Dropout voltage | MIC2930x, I_OUT = 1.5 A | - | 250 | - | mV |
| Dropout voltage | MIC2930x, I_OUT = 3 A | - | 370 | 600 | mV |
| Current limit | MIC2930x, V_OUT = 0 V | 4.5 | - | 5.0 | A |
| Line regulation | I_OUT = 10 mA, (V_OUT+1V) <= V_IN <= 26V | - | 0.06 | 0.5 | % |
| Load regulation | V_IN = V_OUT+1V, 10 mA <= I_OUT <= I_FL | - | 0.2 | 1 | % |
| Output accuracy | I_OUT = 10 mA | -1 | - | 1 | % |

Absolute max input voltage: -20 V to +60 V (transient, <100 ms, <=1% duty);
continuous operating max V_IN = 26 V (p.4, `1.0 ELECTRICAL CHARACTERISTICS`).
No explicit minimum V_IN row; effective floor is `V_OUT + V_DO`, i.e. ~5.0-5.6 V.

**Dropout at the v1 operating point (I_OUT = 315 mA, between the 100 mA and 1.5 A
table points):** interpolating linearly between the MIC2930x 100 mA row
(80 typ / 175 max mV) and the 1.5 A row (250 typ mV, no max given) puts dropout
at roughly 100-200 mV typical, worst case well under 300 mV — comfortably inside
the brief's <=600 mV budget with wide margin, since 315 mA is only ~10% of the
part's 3 A rating.
