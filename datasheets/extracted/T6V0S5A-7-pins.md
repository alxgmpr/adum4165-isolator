# T6V0S5A-7 (Diodes Incorporated) — Pin/Pad Table

Source: `datasheets/T3V3S5A_T5V0S5A_T6V0S5A_T12S5A.pdf` (Document number DS43793 Rev. 2-2,
October 2023, Diodes Incorporated), "Mechanical Data" and "Device Schematic" (p.1),
"Package Outline Dimensions" (p.4, package **SOD523**).

**Package used in this design: SOD523, matches the KiCad footprint
`Diode_SMD:D_SOD-523`** used for D5/D6 in `v1/isolator-v1.kicad_sch`. This closes the gap
flagged as open in Task 2's report ("D5/D6 footprint identified as existing in the stock
library but not pad-geometry-checked against the T6V0S5A-7's specific mechanical drawing")
and never subsequently closed by Tasks 3/4/7 (which verified courtyard/body size only, not
pad polarity). D1/D2 (`SS34`) got this exact treatment in Task 4 — see
`datasheets/extracted/SS34-pins.md` — this file does the same for D5/D6.

## 1. Electrical terminal identification, from the datasheet

**Mechanical Data (p.1), verbatim:**
> "Package: SOD523 ... Terminal Connections: **Cathode Band**"

The physical part carries a visible band marking; the band identifies the cathode lead.

**Device Schematic (p.1)** shows the two-terminal symbol drawn left to right as:

```
Pin 2 ─o───▷|───o─ Pin 1
```

The triangle (anode arrowhead) sits on the **Pin 2** side; the bar immediately past the
arrowhead (cathode mark) touches **Pin 1**. **Pin 1 = cathode, Pin 2 = anode** — this is the
datasheet's own numbering convention for the cathode-banded terminal, and it applies to the
whole family sharing this datasheet (T3V3S5A/T5V0S5A/**T6V0S5A**/T12S5A all use the identical
SOD523 package and terminal convention; only the breakdown-voltage electrical row differs
between part numbers).

This matches Task 5's independent re-derivation of the same page for D6 ("Investigation 1 —
D6 polarity", `task-5-report.md`), reproduced here as part of closing the loop with the
footprint rather than only the symbol.

## 2. Footprint pad identification, from `Diode_SMD:D_SOD-523.kicad_mod`

Read directly:
`/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Diode_SMD.pretty/D_SOD-523.kicad_mod`

Pad geometry:
```
(pad "1" smd roundrect (at -0.7 0 180) (size 0.6 0.7) ...)
(pad "2" smd roundrect (at  0.7 0 180) (size 0.6 0.7) ...)
```
Pad 1 sits at the negative-x end, pad 2 at the positive-x end. Both pads are identical
roundrects — polarity is **not** encoded in pad shape (no beveled/chamfered pad), so it has
to come from the fab-layer diode glyph the footprint author drew, on `F.Fab`:

```
(fp_line (start -0.2 0)    (end -0.35 0))     ; stub toward pad 1
(fp_line (start -0.2 0)    (end 0.1 0.2))     ; triangle edge -> apex at x=-0.2
(fp_line (start -0.2 0.2)  (end -0.2 -0.2))   ; cathode bar, at the apex, x=-0.2
(fp_line (start 0.1 -0.2)  (end -0.2 0))      ; triangle edge -> apex at x=-0.2
(fp_line (start 0.1 0)     (end 0.25 0))      ; stub toward pad 2
(fp_line (start 0.1 0.2)   (end 0.1 -0.2))    ; triangle base (flat edge), x=0.1
```
Reconstructing the glyph: the two diagonal lines and the `x=0.1` vertical line form a
triangle with its apex at `x=-0.2` and its flat base at `x=0.1` — i.e. the triangle **points
left**, toward pad 1. A second, separate vertical line sits exactly at the apex (`x=-0.2`,
same span as the triangle's height) — the classic "arrowhead touching a perpendicular bar"
diode symbol, where the bar is the cathode mark. That bar is on the **pad-1 side** (the stub
at `-0.35` to `-0.2` continues toward pad 1's pad center at `-0.7`), while the triangle's open
flat base and the opposite stub (`0.1` to `0.25`) lead toward pad 2's pad center at `0.7` —
the anode side.

**Footprint conclusion: Pad 1 = cathode, Pad 2 = anode.** This is the same convention already
confirmed for `Diode_SMD:D_SMA` (D1/D2, Task 4) and is KiCad's standard convention across its
stock diode footprints — pad "1" pairs with the cathode-marked terminal.

## 3. Symbol → footprint → net, D5 and D6

`Device:D_TVS`'s own pins are generic and carry no polarity: both `A1`/`A2` are typed
`passive` in the embedded symbol (`v1/isolator-v1.kicad_sch:2715-2748`), numbered `"1"`/`"2"`.
KiCad pairs symbol pin numbers to footprint pad numbers by exact text match — pin `"1"` binds
to pad `"1"`, pin `"2"` to pad `"2"`, with no remapping present in this schematic (verified:
neither D5 nor D6 carries an `(alternate)` pin-function override).

| Ref | Symbol pin | Footprint pad | Physical terminal (datasheet) | Net (this schematic) |
|---|---|---|---|---|
| D5 | 1 | 1 | Cathode (band) | `VBUS_HOST` |
| D5 | 2 | 2 | Anode | `GND1` |
| D6 | 1 | 1 | Cathode (band) | `PORT_VBUS` |
| D6 | 2 | 2 | Anode | `GND2` |

Netlist confirms (`kicad-cli sch export netlist --format kicadxml`):
```
/VBUS_HOST  contains ('D5','1')
/GND1       contains ('D5','2')
/PORT_VBUS  contains ('D6','1')
/GND2       contains ('D6','2')
```
Both D5's and D6's `Description` properties independently state the same mapping in prose
("pin1(cathode)->VBUS_HOST, pin2(anode)->GND1" / "pin1(cathode)->PORT_VBUS,
pin2(anode)->GND2"), consistent with the netlist.

## Outcome

**Confirms, not contradicts, the current wiring.** The chain is complete end to end:
datasheet cathode-band terminal = symbol pin 1 (datasheet's own convention, re-derived
independently in both this file and Task 5) → symbol pin 1 binds to footprint pad 1 (KiCad's
number-matching pin/pad convention, no override present) → footprint pad 1 sits under the
fab-layer's cathode-bar glyph (confirmed by reading `D_SOD-523.kicad_mod` directly, not
assumed) → footprint pad 1 is wired to `VBUS_HOST` (D5) / `PORT_VBUS` (D6) in the schematic.
Cathode lands on the VBUS-side net on both parts, as the spec requires. **No schematic change
needed or made.**
