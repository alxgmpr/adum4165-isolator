# TLV76750DGNR (TI) — Pin Table

Source: `datasheets/tlv767.pdf` (SLVSE84D, "TLV767 1-A, 16-V Precision Linear Voltage
Regulator", TI, Dec 2017 rev. Jul 2021), Section 5 "Pin Configuration and Functions"
(Table 5-1 and Figure 5-4, p.4) and the Package Materials Information table (p.32,
confirming `TLV76750DGNR` is an orderable HVSSOP-8 SKU).

**Package used in this design: TLV767 fixed 5.0 V, DGN (HVSSOP-8) package, 8 leaded pins
plus one exposed thermal pad.** This replaces the fallback `MIC29302WU` selected in the
first pass of Task 2 — see `docs/superpowers/reviews/2026-07-28-v1-part-selection.md`
"Fix round 1" section for the full candidate survey and why this part won.

## Pin-number -> name -> function (TLV76750DGNR, HVSSOP-8, Fixed 5.0V)

| Pin # | Name | I/O | Function |
|---|---|---|---|
| 1 | OUT | O (power) | Regulator output -> `ISO_5V`. Place the output capacitor close to OUT/GND. |
| 2 | SNS | I | Output sense pin (fixed-voltage devices only). Connect to OUT, or to the load for remote sensing. Do not float. |
| 3 | NC | — | No internal connection. |
| 4 | GND | — | Ground. |
| 5 | EN | I | Enable, active-high. Internal pull-up; can float to enable, or tie to IN. |
| 6 | GND | — | Ground (second GND pin, bonded to the same net as pin 4). |
| 7 | NC | — | No internal connection. |
| 8 | IN | I (power) | Regulator input <- `DCDC_RAW`. Place the input capacitor close to IN/GND. |
| 9 (pad) | PAD | — | Exposed thermal pad. Datasheet: "Connect this pad to ground or leave floating. Connect the thermal pad to a large-area ground plane for best thermal performance." Task 4/5 should tie it to GND and give it a copper pour/via array — this is where nearly all of this part's thermal advantage over a no-pad SOT-23-5 comes from. |

This matches the custom KiCad symbol added to `isolator-lib.kicad_sym`
(`lib_id isolator-lib:TLV76750DGNR`) pin-for-pin: pins 1/2/3/4/5/6/7/8/9 =
OUT/SNS/NC/GND/EN/GND(hidden dup)/NC/IN/PAD.

## Key electrical parameters at the v1 operating point

Source: Table 6.5 "Electrical Characteristics" (p.6) and Section 8.3.2 "Dropout Voltage"
(p.15), which gives TI's own documented dropout-scaling relationship:
`R_DS(ON) = V_DO(rated) / I_RATED`, valid because "if the linear regulator operates at
less than the rated current, the dropout voltage for that current scales accordingly."

| Parameter | Condition | Value |
|---|---|---|
| Dropout, DGN package | V_IN >= 3.0V, I_OUT = 1A | 0.9 V typ / 1.5 V max |
| Derived R_DS(ON), DGN | — | 0.9 Ohm typ / 1.5 Ohm max |
| **Dropout at 315 mA (derived)** | `R_DS(ON) x 0.315A` | **0.28 V typ / 0.47 V max** |
| Input voltage range | Recommended Operating Conditions | 2.5 V to 16 V |
| Output current range | Recommended Operating Conditions, V_IN >= 3V | 0 to 1 A |
| Thermal resistance, R_thJA (DGN, HVSSOP-8) | Table 6.4 | 60.1 degC/W |

At the v1 operating point (Vin sags to 5.8V, Vout=5.0V, Iout=315mA max): dropout budget is
0.8V; the derived worst-case dropout of 0.47V leaves ~0.33V of margin. Thermal: P_D =
(5.8-5.0)V x 0.315A = 0.252W; with R_thJA = 60.1 degC/W (thermal pad soldered to a ground
pour), Tj rise over ambient is only ~15 degC — a large margin against the 125 degC max
junction temperature limit even at high ambient.

## Package / footprint

**Footprint: `Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm`** (KiCad stock
footprint, present in `Package_SO.pretty`). Courtyard measured from the footprint's
`F.CrtYd` layer geometry: bounding box `x[-3.13,3.13] y[-1.75,1.75]` = **6.26 x 3.50 mm
= 21.9 mm^2** (vs. `TO-263-5_TabPin3`'s 16.65 x 11.3 mm = 188.1 mm^2 for the fallback
MIC29302WU — an ~8.6x area reduction).
