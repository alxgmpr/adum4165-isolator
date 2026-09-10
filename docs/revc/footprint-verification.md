# Rev C component and land review

This is the library checkpoint, before schematic visual cleanup and PCB placement.
The original single-port library is unchanged. `tools/revc/footprints.py` copies
stock lands into `hub-lib.pretty` and generates the four additional packages with
the official KiCad Library Tools. The ISOUSB211 generator is separate.

`symbol-pad-net-audit.csv` records every land number, function, expected net,
position and size. `symbol-pad-net-audit.json` checks the exported schematic
against the electrical source and checks that every connected pin has a land.
All 286 physical symbols have an assigned local footprint. Test pads are PCB
features excluded from purchasing. Removable shield covers are specified by
`CoverMPN` and `CoverQuantity` on the corresponding frame symbol.

## Custom lands

| Part | Drawing used and dimensional check |
|---|---|
| U1 ISOUSB211DPR | [TI SLLSFC5D](https://www.ti.com/lit/ds/symlink/isousb211.pdf), DP0028A-C02 HV option, p40, 4231707/A. 28 lands, 0.65 pitch, 1.65 × 0.45, centers at ±4.925. Nominal opposing copper clearance is **8.200 mm**. No claim of 8.3 mm is made at this package. |
| U11 USB2514B-I/M2 | [Microchip DS00001692E](https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf), p48. 36 peripheral lands on 0.5 pitch, 0.28 × 0.90, 4.65 inner gap; exposed pad 37 is **3.70 × 3.70**. A generic footprint with a 4.1 mm exposed pad was rejected. Nine paste windows provide about 69% coverage. |
| U8 TPS2121RUXR | [TI SLVSEA3F](https://www.ti.com/lit/ds/symlink/tps2121.pdf), RUX0012A p39, 4224010/A. Four 1.05 × 0.40 power lands centered at x=±0.675, y=±0.35; eight 0.20 × 0.60 signal lands at y=±1.15 on 0.50 pitch. |
| U28 TPS552892RYQR | [TI SLVSH28A](https://www.ti.com/lit/ds/symlink/tps552892.pdf), RYQ0021A p33–34, 4226658/A. Peripheral pin order and all five long power lands follow the drawing. PGND pin 9 has a 0.33-wide central region and 0.25-wide ends. Three 1.00-long paste windows per strip follow TI's stencil example. Duplicate pin-9 copper shapes describe one continuous land. |
| L1/L2/L4 XFL4020 | [Coilcraft document 745](https://www.coilcraft.com/getmedia/50632d43-da1b-4cdb-8ab4-3029cab51df3/xfl4020.pdf), 2026-03-10. Two 0.98 × 2.37 lands on 3.40 centers; maximum body 4.3 × 4.3 × 2.1 mm. |

No thermal vias were added, including inside footprints. TI drawings that show
example vias are placement references, not permission to route the board.

## Retained and copied packages

- T1 `WE_750313638`: manufacturer drawing and existing local STEP retained.
  The [Wurth drawing](https://www.we-online.com/components/products/datasheet/750313638.pdf)
  has six terminals; the local pattern has 9.41 mm opposing pad clearance.
  The transformer stays outside the small primary shield because its maximum
  height is 7.62 mm.
- U6 `TPS630701RNM_VQFN-HR-15`: existing project-local RNM15 lands retained;
  they are independent of the new TI RYQ21 package. VSEL pin 15 remains GND2.
- U3/U7/U20/U21: stock TI RWB12 pattern checked against TUSB320LAI p36.
  Left/right pads are 0.70 × 0.20; top/bottom pads 0.20 × 0.50, 0.40 pitch.
- TPS62162 and TPS22975 use TI DSG0008A, including exposed pad 9. INA300
  uses DGS10/MSOP-10, 3 × 3 mm, 0.50 pitch, with **no exposed pad**.
  SOT-23-5/-6, SOT-23, SOIC-8, SMA, SOD-323/-523 and commodity passive
  geometries are copied from the installed KiCad library.
- [HRO TYPE-C-31-M-12](https://datasheet.lcsc.com/datasheet/pdf/9e56b777c022540fcce7c7f67825f55e.pdf?productCode=C165948)
  drawing visually checked: 16 contacts, 0.50 pitch, 0.30 signal lands,
  four slotted shield terminals and two locating holes. Body 8.94 × 7.35 mm;
  3.26 mm height. A/B D+ and D− are explicitly paired in the schematic.
- [Wurth 614004134726](https://www.we-online.com/components/products/datasheet/614004134726.pdf)
  revision 003, 2022-04-28, visually checked: **upright, right-angle** USB-A;
  four data/power holes on 2 mm pitch, 0.92 mm drill; four shield holes,
  1.50 mm drill. Body 19.3 ±0.3 by 7.1 ±0.2 mm, approximately 14.5 mm
  above the PCB. Reserve 15 mm above the board. The stock 2.72 mm shield
  offset differs from the 2.71 drawing nominal by 0.01 mm, inside its 0.05
  recommended hole-pattern tolerance.
- CY1 Songtian Q07F3Z102MA5B0S0N0: the manufacturer CD(Y1) sheet supplied
  with [C2914611](https://www.lcsc.com/product-detail/safety-capacitors_ste-songtian-elec-q07f3z102ma5b0s0n0_C2914611.html)
  was visually checked. Q=Y1, Z=14 mm pitch, 102=1 nF. The Y5V 102M body
  table gives 7 mm maximum diameter and 5 mm maximum thickness. The local
  14 mm-pitch, 5.5 mm-wide envelope provides body margin. Its generic family
  table shows a 10 mm lead option; the **Z ordering code** establishes the
  selected 14 mm formed-lead variant. Do not substitute a 10 mm-pitch SKU.
- SH1 [BMI-S-201-F](https://www.laird.com/sites/default/files/bmi-s-201-sales.pdf):
  drawing visually checked; 12.70 × 13.66 ±0.10 mm, frame height
  2.54 ±0.10 mm, assembled nominal height 2.67 mm. The old catalog's
  12.10 width is superseded by this specific drawing.
- SH2 [BMI-S-209-F](https://www.laird.com/products/custom-precision-metal-stamping-emi-non-emi/board-level-shields/two-piece-board-level-shields/bmi-s-209-f):
  29.36 × 18.50 mm, frame height 7.00 mm. Its frame is GND2; SH1 is GND1.
  Both library courtyards have inner contours so components can occupy the
  empty frame interiors. Covered height must also be checked during placement.

## Models and reproducibility

Model paths are project-relative. Installed KiCad models and the original T1/CY1
models are copied without changing their geometry. Missing small-package models,
USB-A and shield frames use explicitly labeled dimensional review envelopes;
they are not manufacturer assembly models. The 1210 envelope includes the
selected Murata capacitor's 2.7 mm maximum height, which a generic nominal model
can understate. Dimensions and courtyards govern clearance checks.

The HRO STEP is from
[Nabu Casa's published Yellow model library](https://github.com/NabuCasa/yellow-3dshapes),
which attributes it to ai03's Type-C library, converted with FreeCAD/KiCadStepUp.
Its geometry is for visualization; the manufacturer drawing governs the land
pattern and mechanical dimensions. The DSG8 model uses KiCad's geometrically
matching generic WSON8 model under its original name.

KiCad library copies retain upstream authorship; KiCad libraries use CC BY-SA
4.0 with the standard design-use exception. See the
[KiCad library license](https://www.kicad.org/libraries/license/).
`footprint-provenance.json` records the source and input file hashes.

This library review does not certify insulation, assembly yield, enclosure fit,
thermal behavior, signal integrity or the final routed board. Those checks have
separate evidence and explicit bench/routing handoff items.
