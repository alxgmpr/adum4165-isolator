# Isolated USB 2.0 Cable v1 — Schematic Design Review

**Project:** `v1/isolator-v1` (KiCad 10.0.5, single flat sheet, **no PCB layout yet**)
**Date:** 2026-07-30
**Branch / commit basis:** `claude/isolator-v1-simplified-909ae9`, after Task 8 (MPNs, BOM, review)
**Analyzers run:** `analyze_schematic.py` (run `2026-07-30_1616`, `analysis-v1/`), `kicad-cli sch erc`, `kicad-cli sch export netlist --format kicadxml`, `kicad-cli sch export bom`, jlcsearch (LCSC) live catalogue lookups
**Analyzers not run:** `analyze_pcb.py`, `analyze_gerbers.py`, `analyze_emc.py`, `analyze_thermal.py`, SPICE, `--lifecycle` (no distributor API keys in this environment) — no PCB exists yet, so anything layout-scoped is out of reach; see [Not Performed](#not-performed--open-items-for-layout).

---

## Verdict

**Schematic is release-ready for PCB layout. No blockers.**

ERC at `--severity-error` exits 0. Every BOM line carries a manufacturer part number (25/25 grouped BOM lines, 42/42 in-BOM component instances, `sourcing_audit.mpn_percent = 100.0`). All seven spec requirements called out in the Task 8 brief are satisfied, verified directly against the exported netlist rather than against the analyzer's own (occasionally mistaken) summaries. Two known gaps from earlier tasks — C3's missing MPN and the unverified R3–R8 LCSC codes — are closed in this task. No wiring changes were made; this task only added sourcing properties and verification artifacts.

| Gate | Target | Result |
|---|---|---|
| `kicad-cli sch erc --severity-error` | exit 0 | **0 violations, exit 0** |
| `kicad-cli sch erc` (all severities) | baseline | **1 warning — `lib_symbol_mismatch` on U4, pre-existing, not fixed (see below)** |
| BOM MPN coverage | every line | **25/25 grouped lines, 42/42 components (`analysis-v1` `bom_coverage.mpn_pct = 100.0`)** |
| Isolation bridge check (`ALLOWED={U1,T1,CY1}`) | prints nothing | **clean — printed nothing** |
| CY1 on both grounds | yes | **confirmed: `CY1` present in both `GND1` and `GND2` node lists** |
| Spec walk | all points satisfied | **7/7 satisfied, 0 deviations** |

---

## Overview

A single-port inline USB 2.0 isolator: USB-C in (`J1`, UFP), USB-C out (`J2`, DFP), bus-powered, no hub, built around the same **ADuM4165BRIZ** (`U1`) core as the 4-port v2 design. Host-side power (`VBUS_HOST`) feeds the ADuM4165 Side 1 and an **SN6505BDBVR** push-pull driver (`U4`) into Würth **750313638** transformer `T1`, Schottky-rectified (`D1`/`D2`, `SS34`) to `DCDC_RAW`, regulated by a fixed 5.0 V **TLV76750DGNR** LDO (`U5`) to `ISO_5V`. `ISO_5V` feeds the ADuM4165 Side 2 (`VBUS2`, internal LDO generates `VDD2`) and a **TPS2553DBVR** current-limited switch (`U6`, ILIM ≈ 250 mA via `R3` = 93.1 kΩ) to downstream port `J2`. Two ground domains, `GND1` (host) and `GND2` (isolated), bridged only by `U1`, `T1` (magnetically, not conductively), and the barrier-stitching capacitor `CY1` (1 nF, Y1-rated, populated). ESD protection on data pairs via `U2`/`U3` (USBLC6-2SC6) and dedicated VBUS TVS diodes `D5`/`D6` (T6V0S5A-7); CC lines are deliberately unprotected. 43 placed components (42 in-BOM, `R9` DNP).

Design intent auto-classified as prototype / IPC class 2 / hobby (`design_intent.confidence` 0.3, all fields `auto` — expected for a first-run analyzer pass on a new project).

---

## Step 1 — MPN population

**Starting state:** 38 of 43 components already carried an MPN, inherited from v2 or set during Tasks 2–7. Gaps found by direct audit of every `(property "MPN" ...)` in the schematic:

| Ref | Gap | Resolution |
|---|---|---|
| `C3`, `C7` | No MPN/Manufacturer/LCSC (stripped in Task 3 when `C3`'s value changed 10 µF → 4.7 µF; `C7` — 4.7 µF, same footprint, U4 VCC bypass — was never populated either, a second instance of the same gap the brief only named once) | `GRM21BR71E475KA73L` (Murata, 0805, 4.7 µF X7R 25 V), LCSC `C162427` — same GRM21 family already used for the design's other 0805 MLCC (`C14`, 22 µF), live-verified in stock (7,880 units at time of lookup) |
| `C8`, `C10` | No MPN/Manufacturer/LCSC (47 µF, 1210, DCDC_RAW bulk / ISO_5V bulk) | Reused v2's exact part for the same value/footprint: `TMK325ABJ476MM-P` (Taiyo Yuden), LCSC `C90142`, live-verified in stock (14,611 units) |
| `U5` | MPN present, no LCSC | `C3752807` — live-verified present but **low stock (86 units)**, flagged as an open item below |
| `R3`–`R8` (known gap) | MPN present, LCSC never verified against a live catalogue | Verified every YAGEO `RC0603FR-07*` MPN against the jlcsearch/LCSC catalogue directly: `R3` 93.1 kΩ → `C273780`; `R4` 100 kΩ → `C14675` (matches v2's `R19` exactly); `R5` 330 Ω → `C105881`; `R6` 3.01 kΩ → `C137732`; `R7`/`R8` 56 kΩ → `C114630` (matches v2's `R31` exactly) |
| `R9`, `R10` | Same 100 kΩ part as `R4`, no LCSC (not explicitly named in the brief, closed for consistency since the audit was already touching this value) | `C14675`, same as `R4` |

**Not given an LCSC code, correctly:** `D5`, `D6` (T6V0S5A-7, Diodes Inc.) and `T1` (Würth 750313638) — neither part exists in the LCSC/JLCPCB catalogue (confirmed via live jlcsearch query, zero results for both MPNs). This is expected; these are Digikey/Mouser parts, not JLC-stocked, and the schematic already carries `Manufacturer` + `Datasheet` for both, which is sufficient provenance.

**Untouched, deliberately:** every component that already had a correct, complete MPN/Manufacturer/LCSC set (`R1`/`R2`, `U1`–`U4`, `U6`, `CY1`, `D1`–`D4`, `J1`/`J2`, `Q1`, `Y1`, all 100 nF/8 pF/22 µF caps) — per the brief, "this is largely an audit; do not churn what is already right."

**One pre-existing data-quality note, out of scope:** `C14`'s MPN (`GRM21BR61A226ME44L`, a Murata part number) carries `Manufacturer = "Samsung Electro-Mechanics"` — an inherited mismatch from v2 (confirmed identical in `isolator.kicad_sch`), not introduced by v1 and not one of the two named gaps. Left as-is per "reuse v2's MPNs where the part is identical" and the instruction not to churn what's already right; flagged here for visibility rather than silently reproduced.

---

## Step 2 — BOM export

```
$KCLI sch export bom --fields "Reference,Value,Footprint,MPN" --group-by "Value,Footprint,MPN" \
  -o v1/isolator-v1-bom.csv v1/isolator-v1.kicad_sch
```

**25 grouped BOM lines, every line carries an MPN** (verified programmatically — zero rows with an empty `MPN` field). `R9` (the DNP PGOOD pull-up alternative) correctly does **not** appear in the BOM: it carries `(dnp yes)` and `(in_bom no)`, and its `Description` property preserves the design intent for a reader who never sees the DNP flag directly — *"PGOOD2 pull-up to VDD2 -- DNP by design. Populate ONLY if bring-up shows PGOOD is open-drain; never populate together with R10 (see schematic note)"* — confirmed present verbatim in the schematic and cross-checked against a companion note that documents the same rule beside the symbol. `sourcing_audit.total_bom_components = 42` (43 placed − 1 DNP), `mpn_coverage = "42/42"`.

`v1/isolator-v1-bom.csv` committed alongside the schematic.

---

## Step 3 — Analyzer run

```
python3 $KH/kicad/scripts/analyze_schematic.py v1/isolator-v1.kicad_sch --analysis-dir analysis-v1/
```

Output: `analysis-v1/2026-07-30_1616/schematic.json`. 29 findings: 3 error, 3 warning, 23 info. `bom_coverage`: 25/25 components with MPN, 100.0%. `provenance_coverage_pct`: 96.6.

All 6 non-info findings were triaged against direct netlist/schematic evidence — see [False Positives](#false-positives--reviewer-overrides). **None is a real defect.**

---

## Step 4 — Spec walk

Each point from the Task 8 brief, checked against `kicad-cli sch export netlist --format kicadxml` output (`/tmp/v1-t8.xml`), which is authoritative over the analyzer's own net summaries where the two disagree.

### 1. Power budget — `ISO_5V` unchanged beyond U1 VBUS2, U6, indicators

```
/ISO_5V : [('C10','1'), ('C11','1'), ('C12','1'), ('R4','1'), ('R5','1'), ('R6','1'),
           ('U1','20'), ('U5','1'), ('U5','2'), ('U6','1'), ('U6','3')]
```
`U5.1`/`U5.2` = the LDO's own output/sense pins (already-existing rail content, not a new load). `U1.20` = VBUS2 (~70 mA, ADuM4165 Side 2). `U6.1`/`U6.3` = TPS2553 IN/EN. `R4`/`R5`/`R6` = the FAULT pull-up, FAULT-LED series resistor, and PGOOD-LED series resistor — the "indicators" the spec explicitly allows. `C10`/`C11`/`C12` are bypass/bulk, no DC draw. Nothing else present. **Satisfied.** The ≈240 mA port budget (2.5 W host − ADuM Side 1 − converter loss − ADuM Side 2 (~70 mA) − indicators (~2 mA)) still holds.

### 2. ESD

- `U2.5` on `VBUS_HOST`, `U3.5` on `PORT_VBUS` — confirmed via netlist (`VBUS_HOST` contains `('U2','5')`; `PORT_VBUS` contains `('U3','5')`). **Satisfied.**
- `D5`/`D6` present, not DNP (`dnp no` / `in_bom yes` on both). Orientation: `D5.Description` = *"pin1(cathode)->VBUS_HOST, pin2(anode)->GND1"*, and the netlist confirms `VBUS_HOST` contains `('D5','1')` and `GND1` contains `('D5','2')` — cathode to VBUS as required. `D6` mirrors this on the downstream side: `PORT_VBUS` contains `('D6','1')`, `GND2` contains `('D6','2')`, `D6.Description` = *"pin1(cathode)->PORT_VBUS, pin2(anode)->GND2"*. **Satisfied.**
- CC lines: `HOST_CC1`/`HOST_CC2` (unnamed nets `('J1','A5')`+`('R1','1')` and `('J1','B5')`+`('R2','1')`) and `PORT_CC1`/`PORT_CC2` carry only the Rd/Rp resistors, no ESD device. Deliberately unprotected per spec, and this task did **not** add protection — the brief is explicit that "fixing" this would be wrong for v1. **Satisfied, correctly left alone.**

### 3. CY1 populated, on both grounds

`CY1.dnp = no`, `CY1.in_bom = yes`. Isolation-check script (below) confirms `CY1` in both `GND1` and `GND2` node lists. **Satisfied.**

### 4. Exactly 0.1 µF on VDD1 and VDD2, nothing else but R9 (DNP) on VDD2

```
/VDD1 : [('C5','1'), ('U1','3')]
/VDD2 : [('C13','1'), ('R9','1'), ('U1','18')]
```
`C5` and `C13` are both `100n` (0.1 µF). `VDD1` has nothing beyond the one cap and the IC pin. `VDD2` has the one cap, the IC pin, and `R9` — which is DNP, exactly as the brief describes. **Satisfied, word for word.**

### 5. Dedicated Rd/Rp per CC pin

```
/Net-(J1-CC1): [('J1','A5'), ('R1','1')]     R1 = 5.1k, R1.2 -> GND1
/Net-(J1-CC2): [('J1','B5'), ('R2','1')]     R2 = 5.1k, R2.2 -> GND1
/PORT_CC1:     [('J2','A5'), ('R7','2')]     R7 = 56k, R7.1 -> PORT_VBUS
/PORT_CC2:     [('J2','B5'), ('R8','2')]     R8 = 56k, R8.1 -> PORT_VBUS
```
Four separate CC nets, four separate resistors, no sharing. **Satisfied.**

### 6. `VBUS_HOST` total capacitance ≤ 10 µF

```
/VBUS_HOST: C3(4.7) + C4(0.1) + C6(0.1) + C7(4.7) = 9.6 uF
```
Confirmed independently by the analyzer's own USB-compliance module: `usb_compliance.connectors[J1].vbus_capacitance_detail.total_uf = 9.6`. **Satisfied**, 0.4 µF of margin under the USB 2.0 §7.2.4.1 limit.

### 7. Two ground domains, exactly three permitted crossings

```python
ALLOWED = {'U1', 'T1', 'CY1'}
d1 = nets['GND1'] - ALLOWED; d2 = nets['GND2'] - ALLOWED
# d1 & d2, and any non-ground net spanning both -> printed nothing
```
Ran against the current netlist: **printed nothing**. `CY1` independently confirmed present in both `GND1` and `GND2` node lists. `U1` is on both grounds (it *is* the isolator IC, both sides are its own pins). `T1` sits only on `GND2` electrically (its GND2-side center-tap pin `T1.5`); the primary winding couples across the barrier magnetically, not by a shared ground node, exactly as the topology requires — a copper connection from `T1` to `GND1` would be a real defect, and there isn't one. **Satisfied.**

### 8. TPS2553 ILIM ≈ 250 mA

`R3 = 93.1k`, confirmed both in the `Value` property and the netlist (`/ILIM_SET: [('R3','1'), ('U6','5')]`, `U6` pin 5 = ILIM) — value cross-checked against Task 5's ILIM calculation, unchanged since. **Satisfied.**

**Spec-walk result: 8/8 checked points satisfied, 0 deviations.** (The brief lists 7 bullet items; ESD splits into three sub-checks above for clarity, giving 8 total lines but the same 7 topic areas.)

---

## False Positives / Reviewer Overrides

All 6 non-info analyzer findings were triaged. **None is a real defect** — all trace to one root cause: the analyzer's power-source detector does not treat `power:PWR_FLAG` symbols as valid net sources on this schematic, a gap already identified, investigated, and formally accepted in Task 6's PWR_FLAG audit (see `task-6-report.md`, section 2).

| Rule | Sev | Count | Refs | Why it is a false positive |
|---|---|---|---|---|
| `PP-001` | error | 3 | `U1.20` (ISO_5V), `U5.8` (DCDC_RAW), `U6.1` (ISO_5V) | Claims "no DC path to a power rail." For `DCDC_RAW`: fed by `D1`/`D2` (Schottky rectifier cathodes), whose pins are typed `passive` in the embedded `Device:D_Schottky` symbol — same gap Task 6 already found and accepted for the connector-fed `VBUS_HOST` case. For `ISO_5V`: this is the more striking case, because `U5.1` (OUT) is directly on `ISO_5V` and is typed `power_out` in the embedded `isolator-lib:TLV76750DGNR` symbol — confirmed by reading the pin definition directly (`(pin power_out line ... (number "1"))`). `U1.20` and `U6.1` are on the *identical* net node as `U5.1` per the official `kicad-cli` netlist export — zero hops, not two. The analyzer's own `RS-001` rail-source detector (a separate, deterministic-confidence check) correctly recognizes `ISO_5V` as sourced and does **not** flag it, so `PP-001` disagrees with the analyzer's own `RS-001` result on the same net — internal inconsistency in the tool, not a schematic defect. **Dismissed**, corroborated by `kicad-cli sch erc` returning 0 errors. |
| `RS-001` | warning | 2 | `DCDC_RAW`, `VBUS_HOST` | "No declared source." Both nets carry a `power:PWR_FLAG` (`#FLG05` on `DCDC_RAW`, `#FLG02` on `VBUS_HOST` per Task 6's audit table), but the exported netlist XML omits PWR_FLAG components from every net's node list entirely (confirmed: grep for `FLG` in `/tmp/v1-t8.xml` returns nothing, for *any* of the four flags, including the two ERC clearly relies on for `GND1`/`GND2`). This is a `kicad-cli` netlist-export quirk, not a wiring gap — ERC (which reads the schematic directly, not the exported netlist) is unaffected. **Dismissed.** |
| `pwr_flag_warnings` | (informational field) | 1 | `GND1` | Same root cause as `RS-001` above — claims `GND1` has no `PWR_FLAG`, contradicting Task 6's confirmed `#FLG01` on `GND1` and ERC's 0-error result. **Dismissed**, same evidence. |
| `signal_integrity` (EN missing pull-up) | warning | 1 | `U5` EN | `U5.5` (EN) is wired directly to `U5.8` (IN) — both on `DCDC_RAW` — the standard always-enabled configuration for a fixed-output LDO with no external enable control, confirmed in Task 4's report ("`DCDC_RAW` has ... `U5.8`(IN)/`U5.5`(EN)"). A pull-up to a net the pin is already shorted to would be meaningless. Same pattern v2's review dismissed for its MIC29302 EN pin. **Dismissed.** |
| `usb_compliance.cc*_pulldown_5k1` | fail | 2 | `J2` (CC1, CC2) | `J2` is the **downstream-facing** port (DFP). A DFP presents Rp (pull-**up**), not Rd (pull-down) — `R7`/`R8`, 56 kΩ to `PORT_VBUS`, is exactly the Default-USB-Power advertisement the spec calls for. The check hard-codes the UFP/sink pattern and has no DFP-aware branch. Same class of false positive v2's review already documented for its own downstream ports (J5/J6). **Dismissed.** |
| `statistics.dnp_parts = 0` | (stat, not a finding) | — | — | `R9` correctly carries `(dnp yes)` in the schematic and is correctly excluded from `sourcing_audit`'s 42-component BOM count, but the top-level `statistics.dnp_parts` counter still reports 0. v2's own review recorded the identical counter bug ("the analyzer's `statistics.dnp_parts` counter reports 0; the per-component `dnp` flags are set correctly ... so the counter is wrong, not the schematic"). **Dismissed, tool bug, not new.** |
| `crystal` (info, heuristic) "load capacitance marginal (7.0pF vs 8.0pF target)" | info | 1 | `Y1` | `C1`/`C2`/`Y1` were lifted verbatim (unchanged position, value, footprint) from the proven v2 design in Task 3 — not a v1-specific change. The two-cap Pierce-oscillator effective-load-capacitance heuristic (`C1·C2/(C1+C2) + C_stray`) is an estimate that depends on an assumed board-parasitic `C_stray`; it is not a hard failure and was not flagged in v2's own review of the identical circuit. Carried forward to bring-up verification (Verification plan step 1: "24 MHz oscillation on the Side-1 crystal") rather than resolved here, since it is not something Task 8's scope (sourcing/BOM/review) can adjudicate without a scope or the crystal's actual datasheet `CL` spec in hand. |

---

## ERC

```
$KCLI sch erc v1/isolator-v1.kicad_sch --output /tmp/erc-t8.rpt --severity-error --exit-code-violations
Found 0 violations
exit=0
```

```
$KCLI sch erc v1/isolator-v1.kicad_sch --output /tmp/erc-t8-all.rpt
Found 1 violations
[lib_symbol_mismatch]: Symbol 'SN6505BDBV' doesn't match copy in library 'Power_Management'
    @(60.96 mm, 139.70 mm): Symbol U4 [SN6505BDBV]
 ** ERC messages: 1  Errors 0  Warnings 1
```

Matches the expected baseline exactly: 0 errors, exactly 1 `lib_symbol_mismatch` warning on U4. This is pre-existing library drift across the whole project — v2 has seven of the same class of warning (see v2's own review, "False Positives" table), already investigated in Tasks 3–6 and confirmed to be a structural/flattened-vs-`extends` library representation difference, not a connectivity defect. **Not touched** — a prior attempt to fix this class of warning introduced 11 new connectivity violations and was reverted (per the Task 8 brief); this task made no attempt to repeat that.

---

## Isolation Check

```python
ALLOWED = {'U1', 'T1', 'CY1'}
nets = {...}  # from kicad-cli sch export netlist --format kicadxml
d1 = nets.get('GND1', set()) - ALLOWED
d2 = nets.get('GND2', set()) - ALLOWED
# check d1 & d2, and any non-ground net spanning both domains
```
**Printed nothing.** `CY1` positively confirmed present in both `GND1` and `GND2` net node lists (`('CY1','2')` in `GND1`, `('CY1','1')` in `GND2`).

---

## Open Items for Layout / Bring-Up

None of these are blockers to starting PCB layout; all are either already-known items or genuinely deferred to a stage this task cannot resolve.

1. **`U5` (TLV76750DGNR) LCSC stock is low** (86 units at the time of this review's live lookup, LCSC `C3752807`). Not a schematic defect, but worth a stock re-check before placing a production order — carry forward to the BOM/procurement step ahead of fab.
2. **`Y1` crystal effective load capacitance** — analyzer heuristic estimates 7.0 pF against an assumed 8.0 pF target; unchanged from the proven v2 circuit (Task 3 lifted `C1`/`C2`/`Y1` verbatim). Verify at bring-up per the spec's own Verification plan step 1 (24 MHz oscillation check on the Side-1 crystal) rather than adjudicated here.
3. **`lib_symbol_mismatch` on U4** — accepted, tracked, explicitly not to be "fixed" per prior direction; a fix attempt previously introduced 11 connectivity violations and was reverted.
4. **80 mm vs. 120 mm enclosure decision** — already an explicit open item in the spec itself (Mechanical section), not something Task 8 touches; carried forward here only for completeness of the layout hand-off.
5. **`--lifecycle` audit not run** — no `DIGIKEY_CLIENT_ID` / `MOUSER_SEARCH_API_KEY` / `ELEMENT14_API_KEY` in this environment. LCSC stock/price was checked live via jlcsearch (no key required) for every MPN that has an LCSC presence, but active/NRND/EOL status and operating-temperature coverage were not audited. Recommend running `--lifecycle` before committing to a production order.

---

## Not Performed / Review Limits

- **No PCB exists for this project yet** (`v1/isolator-v1.kicad_pcb` is present but unpopulated/unrouted at this stage of the plan) — `analyze_pcb.py`, `analyze_gerbers.py`, DRC, and all placement/routing/creepage checks are out of scope for a schematic-stage review and belong to the separate PCB layout plan referenced in the Task 8 brief's Follow-on section.
- **EMC/thermal/SPICE analyzers** not run — no simulation models attached to this project, and thermal is called out in the spec itself as "not a constraint: roughly 1 W total dissipation in an aluminum enclosure."
- **Component lifecycle audit** not run (see Open Items above).
- **kicad-happy:kicad skill full interactive review** — this document performs the equivalent analysis manually (analyzer JSON + direct netlist/XML cross-checks against the schematic's raw properties and pin types), since the skill's output would summarize the same evidence gathered here; every finding above was independently verified against `kicad-cli`-exported ground truth rather than taken at the analyzer's word.

---

## Summary

| Category | Count |
|---|---|
| Spec points checked | 8 (7 topic areas) |
| Spec points satisfied | 8 |
| Spec points deviated | 0 |
| Analyzer findings (total) | 29 (3 error, 3 warning, 23 info) |
| Analyzer findings triaged as false positive | 6 of 6 non-info findings |
| Real defects found | 0 |
| BOM lines | 25, all with MPN |
| BOM components (in-BOM, non-DNP) | 42, all with MPN (100%) |
| DNP parts | 1 — `R9` (100 kΩ, PGOOD2 alternate pull-up), design intent preserved in `Description` and schematic note |
| ERC errors | 0 |
| ERC warnings | 1 (`lib_symbol_mismatch` on U4, pre-existing, accepted) |
| Isolation bridge check | clean |
| New MPNs sourced this task | `C3`/`C7` (Murata `GRM21BR71E475KA73L`), `C8`/`C10` (Taiyo Yuden `TMK325ABJ476MM-P`, reused from v2) |
| LCSC codes added this task | `C3`, `C7`, `C8`, `C10`, `U5`, `R3`–`R10` (10 refs) |
