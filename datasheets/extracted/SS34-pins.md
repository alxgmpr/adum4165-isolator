# SS34 (MDD / Microdiode Electronics) — Pin Table

Source: `datasheets/SS34.pdf` (LCSC part `C8678`, "SS32 THRU SS3200", Rev:2024A5,
Microdiode Electronics (`www.microdiode.com`)), "Mechanical Data" section (p.1) and
the package drawing captioned `DO-214AC/SMA` (p.1).

**Package used in this design: SS34, DO-214AC/SMA molded plastic body** — matches
the KiCad footprint `Diode_SMD:D_SMA` used for D1/D2 in `v1/isolator-v1.kicad_sch`.
This is the exact same LCSC part (`C8678`, manufacturer "MDD (Microdiode
Electronics)") already recorded in D1/D2's `MPN`/`Manufacturer`/`LCSC` properties,
copied from v2's already-reviewed D1/D2 instances (see Task 4 report) — this file
closes the loop by actually reading that part's own datasheet rather than only
citing v2's netlist and the generic `Device:D_Schottky` symbol convention.

## Terminal identification (2-terminal part — no pin numbers on the die, but the
KiCad symbol maps them to numbered pins)

Datasheet, "Mechanical Data" (p.1), verbatim:

> "Case: JEDEC DO-214AC/SMA molded plastic body
> Terminals: Solderable per MIL-STD-750, Method 2026
> **Polarity: Color band denotes cathode end**
> Mounting Position: Any"

The `Maximum Ratings` table (p.1) confirms this exact datasheet covers the SS32
through SS3200 family, with **SS34** in its own column (`VRRM` = 40 V,
`Marking Code` = "MDD SS34", `I(AV)` = 3.0 A, `VF` = 0.55 V max at 3.0 A).

## Mapping to the KiCad symbol/footprint

| Symbol pin | Datasheet terminal | Marking | Net in v1 |
|---|---|---|---|
| 1 (K) | Cathode | Color band end | `DCDC_RAW` |
| 2 (A) | Anode | Unmarked end | `RECT_A` (D1) / `RECT_B` (D2) |

`Device:D_Schottky`'s own pin table (already confirmed in Task 4) has pin 1 named
"K" and pin 2 named "A" — this datasheet confirms the **physical** cathode is the
banded end, matching pin 1. `Diode_SMD:D_SMA` is KiCad's standard 2-pad SMA
footprint, where pad "1" is universally the pin-1/cathode pad by KiCad convention
(same numbering the footprint shares with every other 2-pin diode footprint in the
stock libraries) — so pad 1 lands under the physical cathode band, consistent with
the datasheet.

## Outcome

This confirms, from the part's own datasheet rather than only the symbol
definition, that D1/D2's existing wiring in `v1/isolator-v1.kicad_sch`
(pin 1/cathode → `DCDC_RAW`, pin 2/anode → the transformer secondary via
`RECT_A`/`RECT_B`) is correct. No schematic change was needed or made — see
"Fix round 1" in `task-4-report.md`.
