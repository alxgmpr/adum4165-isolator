# Part Selection: 5.0 V LDO, VBUS TVS, Barrier Stitching Capacitor (Task 2)

> **Repo note (2026-07-30):** the design this document calls "v1" is now simply
> **the isolator** — the single, shipping project at the repo root
> (`isolator.kicad_sch` / `.kicad_pcb` / `.kicad_pro`). It is no longer a
> sub-project under `v1/`, and paths below have been updated accordingly. What
> this document calls "v2" is the **archived 4-port design**, now on branch
> `4port-archive`. Past-tense passages comparing the two are kept as written —
> they record why decisions were made and only make sense in that tense.

**Date:** 2026-07-28 (originally); **updated 2026-07-28 in fix round 1** — the LDO and CY1
sections were superseded after review (Critical 1 and Critical 2); the VBUS TVS section (D5, D6)
was reviewed and approved unchanged. Read the "Fix round 1" notes inline in each section for what
changed and why.
**Scope:** select and datasheet-verify three parts the isolator needs that the 4-port design does not carry (or carries
incorrectly): the ISO_5V LDO, the VBUS ESD/TVS diodes (D5, D6), and the barrier stitching
capacitor CY1. No schematic wiring performed in this task — selection, symbol/footprint
resolution, and pin-table extraction only.

Barrier requirement carried into every part check below: **8.3 mm creepage/clearance**, set by
the ADuM4165 in its RI-20-1 package (self-validated in Task 10 of the 4-port design build,
`E - 2L = 8.28 mm`; see `docs/superpowers/reviews/2026-07-26-schematic-review.md:436`).

---

## 1. LDO — ISO_5V regulator

**Fix round 1 supersedes this section's original pick.** The first pass took the brief's package
row ("SOT-23-5 or SOT-223") literally, disqualified TLV76750 outright once it turned out not to
be orderable in either package, and jumped straight to the documented fallback (MIC29302WU)
without surveying other small-package candidates. Review ruled that the brief's package row was
a proxy for the spec's real intent — "roughly 1 A class, fixed 5.0 V, physically smaller than a
DPAK" — and required a proper survey. That survey is below; **MIC29302WU is still fully valid and
stays documented** (`datasheets/extracted/MIC29302WU-pins.md` is unchanged) as the fallback of
last resort, but it is no longer the pick.

### Candidate survey against the real operating point

Fixed requirements checked against real datasheets for every candidate:
- V_in: `DCDC_RAW`, ~6.1 V unloaded sagging to ~5.8 V at 315 mA
- V_out: 5.0 V fixed
- Dropout at 315 mA: must be well under ~0.8 V (the actual budget; lower is better)
- I_out: >= 400 mA
- Package: smaller than TO-263-5's 16.65 x 11.3 mm = 188.1 mm² courtyard (measured from the stock
  footprint's `F.CrtYd` layer — see the mechanical-feasibility doc); leaded preferred over leadless

| Candidate | Package(s) checked | V_in max (rec. operating) | 5.0V fixed option? | Dropout @ 315mA (derived) | Verdict |
|---|---|---|---|---|---|
| **TLV76750DGNR** (TI) | HVSSOP-8 (DGN), leaded, thermal pad | 16 V | Yes | 0.28 V typ / 0.47 V max (derived, see below) | **Chosen** |
| TLV76750DRVR (TI) | WSON-6 (DRV), leadless | 16 V | Yes | 0.28 V typ / 0.44 V max (derived) | Passes electrically, but leadless — DGN preferred per review guidance |
| AP2114 (Diodes Inc / BCD Semi) | SOT-223, TO-263-3, TO-252, SOIC-8, PSOP-8 | **6.0 V** (rec. op.), 6.5 V abs max | No — fixed options are 1.2/1.5/1.8/2.5/3.3 V only; would need ADJ + divider | not evaluated further | **Rejected**: V_in ceiling (6.0 V rec. op., 6.5 V abs max) leaves no real margin against a 6.1 V unloaded `DCDC_RAW` |
| AP7361C (Diodes Inc) | SOT89-5, SOT223, TO252, SO-8EP, U-DFN3030-8 | **6.0 V** (rec. op.), 6.5 V abs max | No — fixed options up to 3.3 V; ADJ tops out at 5.0 V but still V_in-limited | not evaluated further | **Rejected**: identical V_in ceiling problem to AP2114 |
| TLV757P (TI) | SOT-23-5 (DBV/DYD), WSON-6 | **5.5 V** | Yes (0.6-5V in 50mV steps) | not evaluated further | **Rejected**: input range tops out at 5.5 V — below even the ~5.8 V sagged operating point, let alone the 6.1 V unloaded value or the 6.5 V ceiling requirement |
| MIC5219-5.0BM5 (Microchip/Micrel) | SOT-23-5, leaded, no thermal pad | 12 V | Yes | ~0.26 V typ / ~0.39-0.49 V max (interpolated, see below) | Passes electrically and is the smallest leaded option (13.94 mm² courtyard) — close second, see "why not MIC5219" below |
| NCP1117/NCV1117 (onsemi) — "the 1117 class" | SOT-223, DPAK | 20 V | Yes (nine fixed options incl. 5.0V) | **1.07 V typ / 1.20 V max @ 800 mA** (datasheet Table, not derived) | **Rejected**: dropout alone rules it out — even at 800mA the datasheet's own number is already 34-50% over the 0.8V budget, and 315mA would still be roughly 0.9-1.0V given this BJT topology's much flatter dropout-vs-current curve than a MOSFET pass device |
| MIC29302WU (Microchip) | TO-263-5, leaded, tab | 26 V | No — ADJ + divider (as already wired in the 4-port design) | 0.1-0.2 V typ (order of magnitude under budget) | Passes electrically with the most margin of any candidate, but package is 8.6x the area of the HVSSOP-8 winner — **documented fallback, not the pick** |

Sources: TLV767 family — `datasheets/tlv767.pdf` (SLVSE84D), Table 6.5 p.6 and Section 8.3.2 p.15
(dropout-scaling formula). AP2114 — `datasheets/AP2114.pdf`, "Recommended Operating Conditions"
p.7 (`V_IN 2.5 to 6.0 V`) and "Absolute Maximum Ratings" p.7 (`V_IN 6.5 V`). AP7361C —
`datasheets/AP7361C.pdf`, p.4 (`V_IN` recommended 2.2-6.0 V, absolute max 6.5 V). TLV757P —
`datasheets/tlv757b.pdf`, p.1 Features ("Input voltage range: 1.45V to 5.5V"). MIC5219 —
`datasheets/MIC5219.pdf`, p.4 Electrical Characteristics and p.9-10 thermal design section.
NCP1117 — `datasheets/ncp1117.pdf` (ON Semiconductor DS, via Octopart-hosted copy), p.4
Electrical Characteristics dropout-voltage row. MIC29302WU — as in the original pass, unchanged.

### Why TLV76750DGNR won

**Dropout, derived from TI's own documented scaling formula (Section 8.3.2, p.15):**
`R_DS(ON) = V_DO(rated) / I_RATED`, explicitly stated to hold at any lower operating current. DGN
package rated dropout is 0.9 V typ / 1.5 V max at 1 A, giving R_DS(ON) = 0.9/1.5 Ohm. At 315 mA:
`0.9 x 0.315 = 0.28 V` typ, `1.5 x 0.315 = 0.47 V` max — this leaves ~0.33 V of margin against the
0.8 V budget even at the manufacturer's own worst-case number, not an interpolation between two
unrelated measured points.

**Thermal, with the exposed pad tied to a ground pour:** `R_thJA = 60.1 degC/W` (Table 6.4, DGN
package). At the isolator operating point, `P_D = (5.8-5.0)V x 0.315A = 0.252 W`, so junction temperature
rise over ambient is only `0.252 x 60.1 ~= 15 degC` — this essentially removes thermal risk from
the decision regardless of enclosure ambient.

**Package, measured from the real footprint:** HVSSOP-8 (`Package_SO:HVSSOP-8-1EP_3x3mm_
P0.65mm_EP1.57x1.89mm`, stock KiCad footprint) courtyard is 6.26 x 3.50 mm = **21.9 mm²**,
measured from the footprint's `F.CrtYd` layer geometry — an **8.6x reduction** from
MIC29302WU's TO-263-5 courtyard (188.1 mm²), and leaded (gull-wing), matching the review's stated
preference for leaded over leadless packages.

**Why not MIC5219-5.0BM5, the closest competitor:** MIC5219 in SOT-23-5 is smaller still
(13.94 mm² courtyard vs. HVSSOP-8's 21.9 mm²) and is a true fixed-5.0V leaded part with a wide
2.5-12V input range, so it was seriously considered. Two things tipped the decision to TLV76750DGNR
instead: (1) its dropout-at-315mA number is *derived from the manufacturer's own documented
formula* rather than *interpolated* between two datasheet-measured points 150mA apart (both are
legitimate engineering methods, but the former carries less inferential risk); and (2) MIC5219's
own datasheet is explicit that "the MIC5219 is designed to provide 200 mA of continuous current"
in the SOT-23-5 minimum-footprint layout, with 500 mA requiring "proper design" (larger copper
area) — worked out from the datasheet's own thermal formula, 315 mA continuous is safely inside
the SOT-23-5 thermal envelope even at the worst-case `R_thJA = 220 degC/W` (minimum footprint) up
to roughly Ta=70 degC, and comfortably so with the "recommended" 1" square copper heat sink
(`R_thJA = 170 degC/W`) — but this requires a calculation to prove, whereas TLV76750DGNR's thermal
pad makes the same conclusion immediate and far less layout-sensitive (`R_thJA = 60.1 degC/W`
regardless of surrounding copper generosity). Given the review's explicit note that "a thermal pad
is acceptable," this tips the choice to the part where thermal safety doesn't depend on getting
the copper pour right. MIC5219-5.0BM5 remains a legitimate second choice if HVSSOP-8 hand
assembly proves troublesome in practice.

### Pin table and symbol

Full pin table: `datasheets/extracted/TLV76750DGNR-pins.md` (ground truth for Task 4). Summary
(DGN, Fixed 5.0V, 8 leads + thermal pad):

| Pin # | Name | Function |
|---|---|---|
| 1 | OUT | Regulator output -> `ISO_5V` |
| 2 | SNS | Output sense (fixed-voltage devices) — connect to OUT |
| 3 | NC | No connection |
| 4 | GND | Ground |
| 5 | EN | Enable, active-high |
| 6 | GND | Ground (second pin, same net as pin 4) |
| 7 | NC | No connection |
| 8 | IN | Regulator input <- `DCDC_RAW` |
| 9 (pad) | PAD | Exposed thermal pad — tie to GND, give it a copper pour/via array |

**`lib_id`: `isolator-lib:TLV76750DGNR`** — **new custom symbol, added to
`isolator-lib.kicad_sym`** (no stock KiCad symbol exists for TLV76750 in the DGN/HVSSOP-8
package — only `TLV76750DRVx` (WSON) and `TLV76750QWDRBxQ1` (automotive) exist in
`Regulator_Linear.kicad_sym`). Built following the pin table above, styled to match the existing
`TPS2553DBV`/`TPS2121` entries in the same file, and validated by exporting it with
`kicad-cli sym export svg` (succeeded, no errors).

**Footprint: `Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm`** (KiCad stock footprint,
present in `Package_SO.pretty` — no custom footprint needed, only the symbol).

**No output divider needed** — TLV76750DGNR is a true fixed-5.0V part (SNS pin tied to OUT), unlike
MIC29302WU's adjustable-plus-divider arrangement.

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

### Why the 4-port design's C49 cannot be reused — read this before touching CY1's footprint

The 4-port design carries `C49`: **1 nF, 2 kV, `Capacitor_SMD:C_2220_5750Metric`, DNP** (marked "Y-class-style
barrier stitching capacitor, GND1-GND2, DNP (EMI provision only)" —
`4port-archive:isolator.kicad_sch:14559-14628`). That 2220 metric package body measures **5.7 x 5.0 mm** — the
"5750" in the footprint name is the body length in tenths of mm (5.7 mm). In the 4-port design this part is DNP
(not populated), so the undersized footprint never mattered.

**The isolator POPULATES this capacitor.** If the isolator reused the same `C_2220_5750Metric` footprint, the
capacitor body itself — sitting directly across the isolation barrier — would cap the barrier's
real-world creepage/clearance at 5.7 mm, well under the 8.3 mm the ADuM4165's RI-20-1 package
requires. The capacitor would become the weakest point in the isolation, silently undoing the
barrier work done elsewhere in the design. **Do not carry the 2220 footprint into the isolator.**

### Selection process (see full search trail below — several parts were checked and rejected)

Requirement: through-hole Y2-rated safety capacitor, 470 pF - 1 nF, lead spacing >= 10 mm, own
creepage rating >= 8.3 mm, verified against datasheet/agency rating.

Several manufacturer families were checked for an *explicit numeric* creepage-distance figure
(KEMET C700/KJY, Vishay DN/VY2, Murata DE-series safety discs) — none of their public datasheets
publish a literal "creepage distance" line item for their small-value (sub-nF to few-nF) Y2 disc
capacitors; they rely on IEC 60384-14 agency certification plus mechanical lead-spacing dimensions
instead. (Murata *does* publish an explicit "10 mm min" creepage spec for its newer **EVA series**
— but that series is SMD, not through-hole, so it doesn't fit the footprint requirement here.)

**Fix round 1 supersedes the original pick (TDK/EPCOS B32021A3102M289, 1 nF Y2, 10 mm lead
spacing).** That pick's creepage justification was reviewed and found to rest entirely on a
geometric inference (lead spacing minus lead diameter, ~1.1 mm of margin over 8.3 mm) plus a
non-numeric "the agency wouldn't have certified it otherwise" argument — not a quoted datasheet
or agency creepage figure, which is exactly what the task's original instructions called for.
What follows is the redo.

**Searching for a genuinely wider lead pitch at this capacitance (the review's route (b)):**
KEMET C700/KJY, Vishay VY2, and Kamaya/Pan Overseas AC-type (X1/Y2) disc-capacitor catalogs were
all checked specifically for lead spacings above 10 mm at capacitance values near 470 pF-1 nF.
**None of them stock anything above 12.5 mm for this capacitance range in practice** — 15 mm and
22.5 mm options exist in these same manufacturers' catalogs, but only for capacitance values in
the multi-nF range (the body has to be physically larger before a longer lead-bend becomes a
standard, tape-and-reel-friendly SKU). A live stock query (`jlcsearch.tscircuit.com`, which
mirrors a large distributor catalog) for 1 nF Y2/X1 disc capacitors returned zero hits above
10 mm pitch across every manufacturer in the catalog — confirming this isn't just these three
vendors' limitation. **This is reported plainly because the review's suggested fix (a 15 mm or
22.5 mm part) turned out not to exist as a real, stocked part at this capacitance — the honest
finding is that 10 mm is the practical stocked ceiling for basic Y2-class discs this small, not
a bigger number.**

**The route that actually worked: Y1 instead of Y2, which also happened to unlock a wider pitch.**
IEC 60384-14 classifies safety capacitors used for line-to-ground bridging into Y1 (rated up to
500 V AC, 8 kV impulse, used for **reinforced/double insulation**) and Y2 (rated to 300 V AC,
5 kV impulse, **basic/supplementary insulation only**). CY1 bridges a reinforced isolation
barrier — the same role the ADuM4165 itself fills — so **Y1 is the electrically-correct
classification for this part, not Y2**; the original brief's "Y2" spec undersold what the part
actually needs to be rated for. Multiple independent engineering references (not the primary IEC
text, which is paywalled — this is flagged as a secondary-source claim, not a primary-standard
quote) consistently report the **Y1 subclass minimum creepage/clearance distance as 8 mm**, vs.
~4 mm for Y2 — meaning a real Y1-certified part starts from a stricter standards floor that is
already close to the project's 8.3 mm target before any part-specific margin is added.

Searching LCSC for Y1-rated (not Y2) small-value safety capacitors surfaced a **genuinely
different, wider-pitch product line** that doesn't exist in the Y2 catalogs checked above:
Songtian Electronics' "CD Series (Y1)". Its part-number scheme has an explicit lead-spacing
digit (`D` = 10.0 mm, `H` = 11.0 mm, **`Z` = 14.0 mm**), and a 1 nF, 14 mm-pitch SKU is a real,
stocked, in-catalog part.

### Chosen: Songtian (STE) Q07F3Z102MA5B0S0N0 (1 nF, Y1, 400 V AC, 14 mm lead spacing)

Datasheet: `datasheet.lcsc.com/datasheet/pdf/72294672594803dd6c35ea194e227910.pdf` (Songtian "安规
陶瓷电容器-CD 系列(Y1)" / "Safety ceramic capacitor — CD series (Y1)", rev. 2018-04-29), part-number
decoding table p.2, dimension table p.3.

| Requirement | Value needed | Q07F3Z102MA5B0S0N0 |
|---|---|---|
| Capacitance | 470 pF - 1 nF | 1.0 nF ("102" code), +-20% (M) |
| Rating | Y2 (brief) / **Y1 (corrected, see above)** | **Y1**, 400 V AC — a stricter class than the brief asked for, not a weaker one |
| Certification | IEC 60384-14 | UL E208107, VDE/ENEC 40025754, CQC CQC06001018610, KTL SU03031-7002, IEC-CB US-21746-UL — p.1 |
| Lead spacing | >= 10 mm | **14.0 mm** (`Z` code in the part number; jlcsearch/LCSC confirm package `P=14mm` for this exact SKU) |
| Body envelope (same electrical part at the 10mm-pitch base SKU, Y5V dielectric, p.3) | — | D=7.0 mm max, T=5.0-5.5 mm max — the 14mm-pitch variant is the same body with a longer lead bend, not a different capacitor |
| Max operating voltage | — | 400 V AC rated (per LCSC listing); dielectric strength 4000 V AC per datasheet p.2 |

**Creepage verification — honest about what's derived vs. quoted, per the review's explicit
instruction:**

No manufacturer in this capacitance class (KEMET, Vishay, TDK, Kamaya, or Songtian) publishes a
literal numeric "creepage distance" line in their datasheet — this was true across every family
checked in both rounds of this search. The verification here rests on two independent arguments,
both stated as what they are:

1. **Geometric, from the datasheet's own mechanical dimensions (not assumed):** body diameter is
   7.0 mm max; lead spacing is 14.0 mm. Since the body is exactly half the lead pitch, the leads
   exit a case that is far narrower than their spacing — there is no surface path from one solder
   joint to the other shorter than approximately (lead spacing - lead diameter) =
   `14.0 - 0.65 = 13.35 mm`. This clears the 8.3 mm requirement by **+5.05 mm (61% margin)** — a
   materially different, much less fragile number than the original 10 mm pick's +1.1 mm.
2. **Standards classification, cited as a secondary-source claim (not verified against the
   primary IEC 60384-14 text directly, which requires a paid standards subscription this task
   did not have access to):** Y1 subclass certification carries an 8 mm minimum creepage/clearance
   floor by the standard itself, independent of this specific part's construction — meaning even
   the *class minimum* a Y1-certified part must clear is already close to the 8.3 mm target,
   before adding the part-specific ~13.35 mm geometric figure above.

**Residual risk, stated plainly:** neither of these is a manufacturer- or agency-quoted "X.X mm
creepage" figure for this exact part. The geometric argument is real and derived directly from
the datasheet's own dimension table (not assumed), and the margin (+5.05 mm) is now large enough
that meeting it requires only that TI's own printed dimensions be roughly accurate, not that a
thin 1-2 mm margin survive real-world tolerance stack-up. **Task 4/5 or a human reviewer should
still request the actual UL/VDE test certificate for this part before fab** — agency certificates
(as opposed to plain datasheets) typically do list the tested creepage/clearance value explicitly,
and that is the authoritative number this write-up was unable to obtain directly.

**Stock check:** LCSC part C2914611, 1,720 units in stock, MOQ 10 pieces (confirmed via
`lcsc.com/product-detail/C2914611.html`).

**`lib_id`: `Device:C`** (generic 2-pin capacitor, KiCad stock symbol — no polarity, matches this
part; unchanged from the original pick).

**Footprint: `isolator-lib:C_Disc_D7.0mm_W5.5mm_P14.00mm`** — **new custom footprint, added to
`isolator-lib.pretty`**. No stock KiCad footprint exists at 14 mm pin pitch for any through-hole
disc capacitor (the stock `Capacitor_THT.pretty` library tops out at `P10.00mm` for the `C_Disc_*`
family). Built by adapting the stock KiCad footprint generator's own geometry (courtyard, pad
sizing, silkscreen conventions copied from `C_Disc_D9.0mm_W5.0mm_P10.00mm.kicad_mod`) to the
14.0 mm pitch and the datasheet's 7.0 x 5.5 mm body envelope, and validated with
`kicad-cli fp export svg` (succeeded; visually confirmed two pads at the correct 14 mm spacing
with the body centered between them).

---

## Summary table for Task 3-5 (updated, fix round 1)

| Ref | Part | MPN | `lib_id` | Footprint |
|---|---|---|---|---|
| LDO (U6-equivalent) | Fixed 5.0V LDO, HVSSOP-8 | **TLV76750DGNR** | `isolator-lib:TLV76750DGNR` (new custom symbol) | `Package_SO:HVSSOP-8-1EP_3x3mm_P0.65mm_EP1.57x1.89mm` (stock) |
| D5, D6 | Unidirectional TVS, SOD-523 | T6V0S5A-7 (unchanged, approved) | `Device:D_TVS` | `Diode_SMD:D_SOD-523` (confirm in Task 3/4) |
| CY1 | Y1 barrier stitching cap, THT | **Q07F3Z102MA5B0S0N0** | `Device:C` | `isolator-lib:C_Disc_D7.0mm_W5.5mm_P14.00mm` (new custom footprint) |

Two library additions this round (both validated with `kicad-cli` export, no errors):
- `isolator-lib.kicad_sym`: added `TLV76750DGNR` (no stock symbol exists for TLV767 in the
  HVSSOP-8/DGN package — only WSON and an automotive DRB variant do).
- `isolator-lib.pretty`: added `C_Disc_D7.0mm_W5.5mm_P14.00mm.kicad_mod` (no stock KiCad
  footprint exists at 14 mm through-hole disc-capacitor pin pitch; the stock library tops out
  at `C_Disc_*_P10.00mm`).

D5/D6 (TVS) needed no library changes and no rework this round — both symbol and a matching
footprint family exist in stock KiCad libraries, and the part choice itself was reviewed and
approved without changes.

**Pin tables for Task 4:** `datasheets/extracted/TLV76750DGNR-pins.md` (the part now used) and
`datasheets/extracted/MIC29302WU-pins.md` (kept, documents the fallback path per the review's
explicit instruction, even though MIC29302WU is no longer the pick).

**Open items carried forward, not blocking:**
- TVS distributor stock (T6V0S5A-7) — web-search-level confirmation only, re-verify at BOM
  lock-down.
- CY1's footprint-against-part-outline and, especially, **CY1's actual UL/VDE test certificate**
  (which should state the tested creepage/clearance number directly — this write-up could not
  obtain it) should be requested and checked before fab.
- D5/D6's `D_SOD-523` footprint pad geometry against the T6V0S5A-7 mechanical drawing (Task 3/4).
- The the isolator mechanical-feasibility record (`docs/superpowers/reviews/2026-07-28-v1-mechanical-feasibility.md`)
  was updated in this same fix round to reflect the new LDO/CY1/TVS footprints — see that
  document; the headline change is that the board's overall length margin is 1.7 mm, not the
  8.0 mm originally claimed, and D1/D2 (rectifier diodes) must be placed side by side rather than
  in series for the "Rectifier + LDO + TPS2553" zone to fit its 20 mm budget.
