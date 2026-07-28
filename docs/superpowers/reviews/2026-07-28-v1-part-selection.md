# v1 Part Selection: 5.0 V LDO, VBUS TVS, Barrier Stitching Capacitor (Task 2)

**Date:** 2026-07-28
**Scope:** select and datasheet-verify three parts v1 needs that v2 does not carry (or carries
incorrectly): the ISO_5V LDO, the VBUS ESD/TVS diodes (D5, D6), and the barrier stitching
capacitor CY1. No schematic wiring performed in this task — selection, symbol/footprint
resolution, and pin-table extraction only.

Barrier requirement carried into every part check below: **8.3 mm creepage/clearance**, set by
the ADuM4165 in its RI-20-1 package (self-validated in Task 10 of the v2 build,
`E - 2L = 8.28 mm`; see `docs/superpowers/reviews/2026-07-26-schematic-review.md:436`).

---

## 1. LDO — ISO_5V regulator

### Requirements checked against datasheet

| Requirement | Value needed | TLV76750 (first candidate) | MIC29302WU (fallback, chosen) |
|---|---|---|---|
| Output | Fixed 5.0 V | 5.0 V option exists on the die (TLV767 family, 50 mV steps 0.8-6.6 V) | Adjustable, set to 4.97 V by R divider (VREF x (1+R1/R2)) |
| Output current | >= 400 mA | 1 A (die rating) | 3 A (MIC2930x family) |
| Dropout @ 315 mA | <= 0.6 V | Not orderable in the required package (see below) — not evaluated further | ~0.1-0.2 V typ, <0.3 V worst case (interpolated, see pin-table doc) |
| Input range incl. 5.5-6.5 V | required | 2.5-16 V (would cover it) | Vin_max = 26 V continuous; Vin_min = Vout+Vdo ~5.1-5.2 V (covers it) |
| Package | SOT-23-5 or SOT-223, hand-solderable | **Fails** — 5.0 V fixed option only ships in DGN (HVSSOP-8) and DRV (WSON-6); SOT-23-5 (DBV) is only orderable for the 8.0 V fixed variant (TLV76780DBVR) | TO-263-5 (D2Pak) — larger than required, but SMD and hand-solderable; already used in v2 |

### Why TLV76750 was rejected

Downloaded `ti.com/lit/ds/symlink/tlv767.pdf` (SLVSE84D). The datasheet's own **Package Materials
Information** table (p.32) lists every orderable TLV767-family part number by package. For the
5.0 V fixed option, only these exist:

```
TLV76750DGNR   HVSSOP  DGN  8   2500  366.0 364.0  50.0
TLV76750DRVR   WSON    DRV  6   3000  210.0 185.0  35.0
TLV76750DRVR   WSON    DRV  6   3000  205.0 200.0  33.0
TLV76750DRVRG4 WSON    DRV  6   3000  210.0 185.0  35.0
TLV76750DRVT   WSON    DRV  6    250  210.0 185.0  35.0
```

A full-text scan of the datasheet for `DBV` (SOT-23-5) turns up exactly one orderable device in
that package across the entire TLV767 family: **`TLV76780DBVR`** — the **8.0 V** fixed option, not
5.0 V. So the brief's "TLV76750, SOT-23-5" candidate does not exist as an orderable part: the
5.0 V die is only bonded out in WSON-6 (leadless, thermal-pad-only — not hand-solderable) and
HVSSOP-8 (fine-pitch, smaller than the brief's package requirement). This fails the package
requirement row outright, so dropout/thermal analysis for TLV76750 was not pursued further.

**Decision: take the documented fallback, MIC29302WU**, per the brief's explicit instruction to
do so when the first candidate fails any requirement row. This is not a design regression — it's
the already-proven v2 part (`U6` in `isolator.kicad_sch`), oversized on current capability
(3 A vs. the 315 mA load) but the only reason v1 tried to replace it was board area, not
performance.

### MIC29302WU dropout margin at the v1 operating point

Downloaded `ww1.microchip.com/downloads/en/devicedoc/20005685a.pdf` (DS20005685A). Table 1-1
(p.5) gives dropout for the MIC2930x (3 A) family at two measured points:

| I_OUT | V_DO typ | V_DO max |
|---|---|---|
| 100 mA | 80 mV | 175 mV |
| 1.5 A | 250 mV | (not specified) |
| 3 A | 370 mV | 600 mV |

`DCDC_RAW` sags to ~5.8 V at 315 mA load; `ISO_5V` must be 5.0 V, so the dropout budget is
0.8 V. Interpolating between the 100 mA and 1.5 A rows for 315 mA gives dropout in the
~100-200 mV range typical — an order of magnitude under the 0.6 V requirement, since 315 mA is
only ~10% of this part's 3 A rating.

### Pin table and symbol

Full pin table extracted to `datasheets/extracted/MIC29302WU-pins.md` (ground truth for Task 4).
Summary:

| Pin # | Name | Function |
|---|---|---|
| 1 | EN | Enable, active-high |
| 2 | VIN | Regulator input <- `DCDC_RAW` |
| 3 | GND | Ground (also = package tab) |
| 4 | VOUT | Regulator output -> `ISO_5V` |
| 5 | ADJ | Feedback tap for R-divider |

**`lib_id`: `Regulator_Linear:MIC29302WU`** (KiCad stock symbol, confirmed present at
`/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/Regulator_Linear.kicad_sym:111788`,
pin names/numbers verified to match the datasheet exactly — no project library edit needed).

**Footprint: `Package_TO_SOT_SMD:TO-263-5_TabPin3`** (KiCad stock footprint, same one v2 uses).

**Output divider (reuse v2's proven values):** R1 (VOUT->ADJ) = 30.1 kOhm, R2 (ADJ->GND) =
10 kOhm. VREF = 1.240 V typ (Table 1-1, "Reference - MIC29xx2/MIC29xx3" row). Check:
`1.240 x (1 + 30.1/10) = 4.972 V` ~= 4.97 V, matching the brief.

---

## 2. VBUS TVS (D5, D6)

### Requirements

Unidirectional TVS, V_RWM >= 5.5 V (capacitance unconstrained — this sits on a power rail, not a
data line).

### Candidates evaluated

The brief named two candidates. Both were checked against real datasheets and **both failed**:

| Candidate | Package | Type | V_RWM | Result |
|---|---|---|---|---|
| ESD441DPLR (TI) | X2SON-2, 0.3 x 0.6 mm | — | — | **Rejected**: only 2 units in stock at LCSC/JLC (`jlcsearch.tscircuit.com` query), and the package is smaller than 01005 — not hand-solderable on a 2-layer hand-assembled board. |
| PESD5V0S1BA (Nexperia) | SOD-323 | **Bidirectional** | 5.0 V max | **Rejected**: datasheet (`assets.nexperia.com/documents/data-sheet/PESD5V0S1BA.pdf`) confirms this is a **bidirectional** ESD diode ("Bidirectional ESD protection diode", p.1) — wrong topology for a unidirectional VBUS clamp. Also V_RWM = 5.0 V (max column, no margin), below the 5.5 V requirement even if topology were acceptable. |
| PESD5V0S1UB (Nexperia) | SOD-523 | Unidirectional | 5.0 V | Checked as the likely intended part (correct topology, matches "SOD-523" in the brief). Datasheet (`assets.nexperia.com/documents/data-sheet/PESD5V0S1UB.pdf`) confirms unidirectional but **V_RWM = 5.0 V** ("reverse standoff voltage... Max: 5", p.1/p.4) — still below the 5.5 V floor. **Rejected.** |

### Chosen: T6V0S5A-7 (Diodes Incorporated)

Datasheet: `www.diodes.com/datasheet/download/T3V3S5A_T5V0S5A_T6V0S5A_T12S5A.pdf` (DS43793 Rev. 2,
Oct 2023), Electrical Characteristics table (p.2):

| Requirement | Value needed | T6V0S5A-7 |
|---|---|---|
| Type | Unidirectional | Unidirectional (title: "UNIDIRECTIONAL SURFACE-MOUNT TVS") |
| V_RWM | >= 5.5 V | **6.0 V min** |
| Breakdown voltage V_BR | — | 6.8 V typ (6.0-... range) |
| Clamping voltage | — | 17 V @ I_PPM = 8 A (8/20 us), 13 W typ peak pulse power |
| Package | small SMD | SOD523 (1.7 x 1.25 mm typ body, per family) |
| ESD rating | — | IEC 61000-4-2 +-30 kV air/contact, HBM 8 kV |

This is the only one of the three candidates that actually meets both the topology (unidirectional)
and standoff-voltage (>=5.5 V) requirements against real datasheet numbers — the brief's two named
candidates were disqualified on inspection (one bidirectional, one under-voltage; see table above).

**Stock check:** not listed on LCSC/JLCPCB (`jlcsearch.tscircuit.com` returns zero hits for
`T6V0S5A`), but RS Components lists 2,980 units in stock, and this exact part number appears in
active DigiKey/Mouser PCN (Product Change Notification) tracking documents, indicating both
distributors carry it as an active line. **Re-verify live stock at BOM lock-down** — this is
web-search-level confirmation, not a live distributor query.

**Symbol: `Device:D_TVS`** (KiCad stock symbol, generic 2-pin TVS diode — confirmed present in
`Device.kicad_sym`). **Footprint:** use a stock `Diode_SMD:D_SOD-523` footprint (standard KiCad
library, not separately verified in this task — Task 3/4 should confirm pad geometry against the
T6V0S5A-7 mechanical drawing before layout).

No project library changes needed for D5/D6 — both symbol and a matching footprint family exist
in stock KiCad libraries.

---

## 3. Barrier stitching capacitor (CY1)

### Why v2's C49 cannot be reused — read this before touching CY1's footprint

v2 carries `C49`: **1 nF, 2 kV, `Capacitor_SMD:C_2220_5750Metric`, DNP** (marked "Y-class-style
barrier stitching capacitor, GND1-GND2, DNP (EMI provision only)" —
`isolator.kicad_sch:14559-14628`). That 2220 metric package body measures **5.7 x 5.0 mm** — the
"5750" in the footprint name is the body length in tenths of mm (5.7 mm). In v2 this part is DNP
(not populated), so the undersized footprint never mattered.

**v1 POPULATES this capacitor.** If v1 reused the same `C_2220_5750Metric` footprint, the
capacitor body itself — sitting directly across the isolation barrier — would cap the barrier's
real-world creepage/clearance at 5.7 mm, well under the 8.3 mm the ADuM4165's RI-20-1 package
requires. The capacitor would become the weakest point in the isolation, silently undoing the
barrier work done elsewhere in the design. **Do not carry the 2220 footprint into v1.**

### Selection process (see full search trail below — several parts were checked and rejected)

Requirement: through-hole Y2-rated safety capacitor, 470 pF - 1 nF, lead spacing >= 10 mm, own
creepage rating >= 8.3 mm, verified against datasheet/agency rating.

Several manufacturer families were checked for an *explicit numeric* creepage-distance figure
(KEMET C700/KJY, Vishay DN/VY2, Murata DE-series safety discs) — none of their public datasheets
publish a literal "creepage distance" line item for their small-value (sub-nF to few-nF) Y2 disc
capacitors; they rely on IEC 60384-14 agency certification plus mechanical lead-spacing dimensions
instead. (Murata *does* publish an explicit "10 mm min" creepage spec for its newer **EVA series**
— but that series is SMD, not through-hole, so it doesn't fit the footprint requirement here.)

### Chosen: TDK / EPCOS B32021A3102M289 (1 nF, Y2, 10 mm lead spacing)

Datasheet: `www.tdk-electronics.tdk.com/inf/20/20/db/fc_2009/Y2_B32021_026.pdf` (B3202*A3/B3/C3
EMI Suppression Capacitors, June 2026 rev).

| Requirement | Value needed | B32021A3102M289 |
|---|---|---|
| Capacitance | 470 pF - 1 nF | 1.0 nF (0.0010 uF), +-20% (M) |
| Rating | Y2 | Y2, 300 V AC (also X1 440/400 V AC rated on some variants; this exact family is Y2/300 V AC) |
| Certification | IEC 60384-14 | EN cert 40018909 (TUV/VDE), UL E97863, CSA — p.3 |
| Lead spacing | >= 10 mm | **10.0 mm** (B32021 type code; family also offers 15/22.5/27.5/37.5 mm) |
| Max body envelope at 1 nF | — | 4.0 mm (w) x 9.0 mm (h) x 13.0 mm (l) — p.5, ordering table |
| Max continuous voltage | — | 480 V AC / 1500 V DC (<=85 degC) |

**Creepage verification (dimensional + agency-cert basis — no single "creepage distance" line
item was found in any manufacturer's public datasheet for parts in this capacitance/voltage
class; this is stated plainly rather than assumed away):**

1. **Geometric argument from the datasheet's own mechanical table.** Lead spacing (terminal
   pitch) is 10.0 mm +-0.4 mm. The case body is only 4.0 mm wide at this capacitance value —
   less than half the lead pitch. Because the leads exit the bottom of a case narrower than
   their spacing, there is no surface path from one solder joint to the other that is shorter
   than approximately (lead spacing - lead diameter) = 10.0 - 0.6 = **9.4 mm**. This exceeds the
   8.3 mm barrier requirement with ~1.1 mm of margin.
2. **Agency certification basis.** The part is certified to IEC 60384-14 Y2 at 300 V AC working
   voltage (EN 40018909, UL E97863) specifically in this 10 mm-lead-spacing construction — the
   standard's own creepage/clearance requirements for the certified working-voltage class are a
   condition of that certification, not a claim TDK could pass testing on without meeting them.

Both points support >= 8.3 mm; margin over the requirement is real but not large (~1.1 mm by the
geometric argument), so **Task 4/5 should keep CY1 laid out with its leads running straight
across the barrier gap with no other copper closer than the barrier keepout**, and a human should
confirm the physical part against its outline drawing before fab, same as the RI-20-1 caution
already on record for U1.

**Stock check:** `jlcsearch.tscircuit.com` query for `B32021A3102` returns three orderable SKUs;
the taped variant **B32021A3102M289** has 8,132 units in stock at LCSC (lcsc 125374) — healthy
stock, real listing.

**`lib_id`: `Device:C`** (generic 2-pin capacitor, KiCad stock symbol — no polarity, matches this
part).

**Footprint: `Capacitor_THT:C_Rect_L13.0mm_W4.0mm_P10.00mm_FKS3_FKP3_MKS4`** — this is a KiCad
stock footprint (confirmed present in `Capacitor_THT.pretty`) whose dimensions (13.0 x 4.0 mm
body, 10.00 mm pin pitch) match the B32021A3102's own mechanical table almost exactly. **No
custom footprint was needed** — the brief anticipated possibly having to create one in
`isolator-lib.pretty`, but a matching stock footprint already exists (it's generated from the
generic WIMA FKS3/FKP3/MKS4 box-film-capacitor family, which is mechanically the same case style
TDK uses for the B32021).

---

## Summary table for Task 3-5

| Ref | Part | MPN | `lib_id` | Footprint |
|---|---|---|---|---|
| LDO (U6-equivalent) | Adjustable LDO, TO-263-5 | MIC29302WU | `Regulator_Linear:MIC29302WU` | `Package_TO_SOT_SMD:TO-263-5_TabPin3` |
| D5, D6 | Unidirectional TVS, SOD-523 | T6V0S5A-7 | `Device:D_TVS` | `Diode_SMD:D_SOD-523` (confirm in Task 3/4) |
| CY1 | Y2 barrier stitching cap, THT | B32021A3102M289 | `Device:C` | `Capacitor_THT:C_Rect_L13.0mm_W4.0mm_P10.00mm_FKS3_FKP3_MKS4` |

No changes were made to `isolator-lib.kicad_sym` or `isolator-lib.pretty` — every symbol and
footprint needed for all three parts already exists in KiCad's stock libraries, registered
through the machine-global KiCad library table
(`~/Library/Preferences/kicad/10.0/sym-lib-table` -> nested `KiCad` table ->
`/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/sym-lib-table`), which v1's
project-level `sym-lib-table`/`fp-lib-table` do not override.

**Pin table for Task 4:** `datasheets/extracted/MIC29302WU-pins.md`.

**Open item carried forward, not blocking:** TVS distributor stock (T6V0S5A-7) and CY1's
footprint-against-part-outline (both flagged above) should get a final live check at BOM
lock-down / before fab, consistent with how the project already treats the RI-20-1 footprint on
U1.
