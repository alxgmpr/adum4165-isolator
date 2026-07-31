# Isolated 4-Port USB 2.0 Hub — Schematic Implementation Plan

> **Repo note (2026-07-30):** this document describes the **archived 4-port
> design**. That project no longer lives at the repo root — it was archived to
> branch `4port-archive` when the repository collapsed to the single-port
> isolator. Every bare `isolator.kicad_sch` / `isolator.kicad_pcb` /
> `isolator.kicad_pro` path below refers to the **archived** files as they stood
> on that branch, **not** to the files of those names at the root today, which
> are the single-port isolator. Retrieve them with
> `git show 4port-archive:isolator.kicad_sch`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the KiCad schematic for the ADuM4165-based isolated 4-port USB 2.0 hub per `docs/superpowers/specs/2026-07-25-usb-isolator-design.md`, ending with a fully wired, ERC-clean, footprint-assigned, MPN-populated schematic that passes a kicad-happy design review.

**Architecture:** USB-C upstream → ADuM4165 (5.7 kV isolation, existing in schematic) → USB2514B 4-port hub → 2× USB-A + 2× USB-C downstream. Isolated power from SN6505B push-pull DC-DC (bus-powered) or external power-only USB-C, merged by a TPS2121 priority mux with CC-based weak-source lockout.

**Tech Stack:** KiCad 10.0.5 (`kicad-cli` on PATH), kicad-happy plugin analyzers, stock KiCad symbol/footprint libraries plus a project library `isolator-lib` for TPS2121, TPS2553, and the Würth 750313638 transformer.

## Global Constraints

Copied from the spec — every task implicitly includes these:

- Two ground domains only: `GND1` (host side), `GND2` (isolated side). No net, wire, or component other than U1 (ADuM4165) and T1 (transformer) may touch both domains.
- ADuM4165 bypass: exactly 0.1 µF at `VDD1` and `VDD2` (larger disrupts start-up sequencing); 0.1 µF at `VBUS1`/`VBUS2`; place-close note ≤10 mm.
- Crystal spec (both Y1 and hub Y2): 24 MHz, ≤50 ppm total tolerance.
- Downstream USB-C ports advertise default USB power: 56 kΩ Rp from each CC pin to that port's VBUS. Never advertise 1.5 A/3 A.
- Every upstream/downstream USB data pair gets ESD protection (NUP4202 class).
- Per-port current limit ≈600 mA via TPS2553 ILIM resistor.
- All new symbols placed with `(in_bom yes)`, unique reference designators, and Value/Footprint/MPN properties filled by the end of the plan.

## Working conventions (read once before any task)

**How edits are made:** The schematic is a single flat sheet `isolator.kicad_sch` (KiCad 10 s-expression format). Place symbols by (a) copying the full library symbol definition into the file's `lib_symbols` section (once per lib_id) and (b) adding a `(symbol (lib_id ...) (at x y rot) ...)` instance with Reference/Value/Footprint properties and a UUID. Wire with `(wire (pts (xy x1 y1) (xy x2 y2)))` and name nets with `(label "NET" (at x y))` or global labels. Grid is 1.27 mm (50 mil) — all pin endpoints must land on grid. See kicad-happy `references/file-formats.md` for field-by-field details. Prefer net labels over long wires: place a short wire stub from each pin and label it — connectivity is by label name.

**Reference designator allocation (fixed for the whole plan):**

| Refs | Part |
|---|---|
| U1 | ADuM4165 (existing) |
| U2 | NUP4202 host-side ESD (existing) |
| U3 | NUP4202 hub-upstream ESD (existing symbol, rewired) |
| U4 | USB2514B_Bi hub |
| U5 | SN6505BDBV |
| U6 | MIC29302 5 V LDO |
| U7 | TPS2121 priority mux |
| U8 | AP2112K-3.3 |
| U9–U12 | TPS2553 port switches (ports 1–4) |
| U13, U14 | TLV7041DBV CC comparators |
| U15–U18 | NUP4202 downstream port ESD (ports 1–4) |
| T1 | Würth 750313638 |
| Q1 | 2N7002 weak-source lockout FET |
| Y1 | 24 MHz ADuM crystal (existing) · Y2: hub crystal |
| J1 | upstream USB-C · J2: power-only USB-C · J3/J4: USB-A · J5/J6: downstream USB-C |
| D1, D2 | rectifier Schottky · D3: PGOOD LED · D4: EXT-active LED · D5: bus-power LED |
| C*/R* | continue numbering from existing C1/C2 |

**Net names (fixed):** `VBUS_HOST`, `HOST_DP`, `HOST_DM`, `GND1` — host domain. `DCDC_RAW`, `DCDC_5V`, `EXT_5V`, `EXT_CC1`, `EXT_CC2`, `n3A_DET`, `PR1_SENSE`, `ISO_5V`, `ISO_3V3`, `PGOOD2`, `ISO_DP`, `ISO_DM`, `P1_DP`…`P4_DP`, `P1_DM`…`P4_DM`, `P1_VBUS`…`P4_VBUS`, `PRTPWR1`…`4`, `nOCS1`…`4`, `P5_CC1/P5_CC2/P6_CC1/P6_CC2` (downstream C-port CC pins, named by connector), `GND2` — isolated domain.

**Verification tools (used in every task):**

```bash
KH=/Users/alex/.claude/plugins/cache/kicad-happy/kicad-happy/2.0.0/skills
SCH=/Users/alex/Documents/isolator/isolator.kicad_sch

# ERC — also validates the file still parses; must exit 0 at the end of every task
kicad-cli sch erc "$SCH" --output /tmp/erc.rpt --severity-error --exit-code-violations; echo "exit=$?"; cat /tmp/erc.rpt

# Analyzer — net/pin ground truth
python3 $KH/kicad/scripts/analyze_schematic.py "$SCH" --analysis-dir analysis/
```

Probe pattern (fill in net/pin per task):

```bash
python3 - <<'EOF'
import json, glob
d = json.load(open(sorted(glob.glob('analysis/*/schematic.json'))[-1]))
net = d['nets']['ISO_5V']
print([(p['component'], p['pin_name']) for p in net['pins']])
EOF
```

**ERC policy:** The board is ERC-clean at the end of every task *for the circuitry placed so far* — unconnected input pins on parts whose wiring belongs to a later task get explicit `(no_connect)` markers removed in that later task. Exit code 0 with `--severity-error` is the gate; warnings are triaged (two-domain designs legitimately warn about some cross-checks until PWR_FLAGs land in Task 9).

---

### Task 1: Project hygiene, baseline, and project library

**Files:**
- Modify: `.gitignore`, `isolator.kicad_sch` (annotation only)
- Create: `isolator-lib.kicad_sym`, `sym-lib-table`, `analysis/` (generated)

**Interfaces:**
- Produces: registered project symbol library named `isolator-lib`; baseline analyzer run in `analysis/`; all existing symbols annotated.

- [ ] **Step 1: Extend .gitignore** — append:

```
analysis/*/
datasheets/
*.rpt
```

(`analysis/manifest.json` stays tracked.)

- [ ] **Step 2: Create empty project symbol library and register it**

`isolator-lib.kicad_sym`:

```
(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") (generator_version "9.0"))
```

`sym-lib-table`:

```
(sym_lib_table
  (version 7)
  (lib (name "isolator-lib")(type "KiCad")(uri "${KIPRJMOD}/isolator-lib.kicad_sym")(options "")(descr "Project symbols"))
)
```

- [ ] **Step 3: Baseline analyzer + ERC** — run both commands from Working Conventions. Record (do not fix yet) the finding list. Expected: parse OK; annotation complete (U1–U3, Y1, C1, C2 are the only components); ERC likely reports unconnected pins on U1/U2/U3 — acceptable at baseline.

- [ ] **Step 4: Verify existing core against the spec** — probe the analyzer JSON: Y1 (24 MHz) must connect to U1 pins XI1/XO1 with C1/C2 (8 pF) to GND1; U1 must be `Isolator:ADUM4165`. If the crystal is wired to the wrong side (XI2/XO2 don't exist on the '4165 — clock is Side 1) or load caps reference GND2, fix now.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: project lib, gitignore, baseline analysis"
```

---

### Task 2: Datasheet acquisition

**Files:**
- Create: `datasheets/` (gitignored), `datasheets/manifest.json`

**Interfaces:**
- Produces: local PDFs for every IC used by later tasks: ADuM4165 (copy from `~/Downloads/adum4165-4166.pdf`), USB2514B, SN6505B, TPS2121, TPS2553, MIC29302, TLV7041, 2N7002, NUP4202, Würth 750313638.

- [ ] **Step 1: Copy the two PDFs already on disk** into `datasheets/` (`adum4165-4166.pdf`, `eval-adum4165-4166-ug-2027.pdf`).

- [ ] **Step 2: Sync the rest.** Preferred: kicad-happy sync scripts once MPNs exist — but MPNs land in Task 11, so at this stage download directly (WebFetch/curl from manufacturer sites: microchip.com for USB2514B, ti.com for SN6505B/TPS2121/TPS2553/TLV7041, micrel/microchip for MIC29302, we-online.com for 750313638). Name files by MPN.

- [ ] **Step 3: Extract the pin tables needed by Task 3.** For TPS2121, TPS2553DBV, and 750313638, read the pinout section of each PDF and write the pin-number→name→function table into `datasheets/extracted/<MPN>-pins.md`. These tables are the ground truth for the custom symbols — do not build symbols from memory.

- [ ] **Step 4: Commit** (manifest and extracted tables only; PDFs are gitignored — if `datasheets/extracted/` matters for review, force-add just that directory):

```bash
git add -f datasheets/extracted/ 2>/dev/null; git add -A && git commit -m "docs: datasheet pin tables for custom symbols"
```

---

### Task 3: Custom symbols — TPS2121, TPS2553, 750313638

**Files:**
- Modify: `isolator-lib.kicad_sym`

**Interfaces:**
- Produces: `isolator-lib:TPS2121`, `isolator-lib:TPS2553DBV`, `isolator-lib:750313638` — pin names/numbers exactly per the Task 2 extracted tables.

- [ ] **Step 1: Author the three symbols.** Requirements beyond the pin tables:
  - Pin types: supply inputs `power_in`; `OUT` of TPS2121 and TPS2553 `power_out`; comparator/enable/status pins `input`/`open_collector` per datasheet; transformer pins `passive`.
  - TPS2553DBV: 6 pins (IN, GND, EN, OUT, ILIM, FAULT̅). FAULT̅ is open-drain.
  - TPS2121: all pins from the datasheet pin table (IN1, IN2, OUT×n, GND, PR1, CL, ST, OV, D1/SS-class pins — exactly as the table says; do not guess names).
  - 750313638: 6 pins per the Würth drawing — primary A, primary center-tap, primary B on one side; secondary +, secondary −, (and NC if present) on the other. Draw the barrier gap visibly (primary pins on left, secondary on right).

- [ ] **Step 2: Verify the library parses and pins match**

```bash
python3 - <<'EOF'
import sys; sys.path.insert(0, '/Users/alex/.claude/plugins/cache/kicad-happy/kicad-happy/2.0.0/skills/kicad/scripts')
from sexp_parser import parse_file, find_all
doc = parse_file('/Users/alex/Documents/isolator/isolator-lib.kicad_sym')
for sym in find_all(doc, 'symbol'):
    name = sym[1]
    pins = [p for unit in find_all(sym, 'symbol') for p in find_all(unit, 'pin')]
    if isinstance(name, str) and '_' not in name.strip('"'):
        print(name, len(pins), 'pins')
EOF
```

Expected: `TPS2553DBV 6 pins`, `750313638` 5–6 pins, `TPS2121` matching its package pin count. Cross-check each pin number against `datasheets/extracted/*-pins.md` by eye.

- [ ] **Step 3: Commit** — `git add isolator-lib.kicad_sym && git commit -m "feat: project symbols TPS2121, TPS2553, WE 750313638"`

---

### Task 4: Upstream host section

**Files:**
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: existing U1, U2, Y1/C1/C2.
- Produces: nets `VBUS_HOST`, `HOST_DP`, `HOST_DM` fully wired; U1 Side-1 pins all terminated.

- [ ] **Step 1: Place and wire** per this table (new parts: J1 `Connector:USB_C_Receptacle_USB2.0_16P`, R1/R2 5.1 kΩ, C3 10 µF, C4 0.1 µF, C5 0.1 µF):

| From | To / net |
|---|---|
| J1 VBUS (all pins) | `VBUS_HOST` |
| J1 GND + SHIELD | `GND1` (shield via direct tie — single-board bench device) |
| J1 CC1 | R1 5.1k → `GND1` |
| J1 CC2 | R2 5.1k → `GND1` |
| J1 D+ (A6+B6, already common on this symbol) | `HOST_DP` |
| J1 D− (A7+B7) | `HOST_DM` |
| U2 (NUP4202) ch. 1/2 | `HOST_DP`, `HOST_DM`; U2 GND → `GND1`; U2 VBUS pin → `VBUS_HOST` |
| U1 VBUS1 | `VBUS_HOST`; C3 10 µF and C4 0.1 µF from `VBUS_HOST` → `GND1` |
| U1 VDD1 | C5 0.1 µF → `GND1` (VDD1 is LDO output — no other load) |
| U1 UD+ / UD− | `HOST_DP` / `HOST_DM` |
| U1 all GND1 pins | `GND1` |

- [ ] **Step 2: ERC + analyzer probe.** ERC exit 0 (add `no_connect` on U1 Side-2 pins still unwired — removed in Tasks 5/7/9). Probe: `nets['HOST_DP']` contains J1, U2, and U1(UD+); `nets['VBUS_HOST']` contains J1, U1(VBUS1), C3, C4, U2.

- [ ] **Step 3: Commit** — `git commit -am "feat(sch): upstream USB-C host section"`

---

### Task 5: Isolated DC-DC (bus-powered path)

**Files:**
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: `VBUS_HOST`, `GND1`, `isolator-lib:750313638`.
- Produces: net `DCDC_5V` (regulated 5 V, GND2 domain); `DCDC_RAW`.

- [ ] **Step 1: Place and wire.** U5 `Power_Management:SN6505BDBV`, T1 `isolator-lib:750313638`, D1/D2 `Device:D_Schottky` (SS34-class), U6 `Regulator_Linear:MIC29302` (verify stock symbol pin names: EN, IN, GND, OUT, ADJ), plus passives:

| Connection | Value/notes |
|---|---|
| U5 VCC ← `VBUS_HOST`; 0.1 µF + 10 µF to `GND1` | input bypass |
| U5 D1 → T1 primary A; U5 D2 → T1 primary B | push-pull drive |
| T1 primary CT → `VBUS_HOST` | |
| U5 EN ← `VBUS_HOST` (always on); U5 CLK → `GND1` (internal osc) | check pin names on stock symbol |
| T1 sec+ → D1(A); T1 sec− → D2(A); D1(K)+D2(K) → `DCDC_RAW` | **T1 secondary needs center tap to GND2 for this full-wave topology — if the 750313638 table (Task 2) shows no secondary CT, use a single Schottky half-wave/bridge per the SN6505 datasheet §app-circuit instead; follow the datasheet figure exactly** |
| `DCDC_RAW`: C 47 µF + 0.1 µF → `GND2` | |
| U6 IN ← `DCDC_RAW`; U6 EN ← `DCDC_RAW`; U6 GND → `GND2` | |
| U6 OUT → `DCDC_5V`; C 47 µF + 0.1 µF → `GND2` | |
| U6 ADJ ← divider from `DCDC_5V`: R 30.1 kΩ (top) / 10 kΩ (bottom, to GND2) | Vout = 1.240 × (1+30.1/10) ≈ 4.97 V — verify Vref in MIC29302 datasheet; adjust divider if Vref ≠ 1.240 V |

- [ ] **Step 2: ERC + probes.** ERC exit 0. Analyzer: power-regulator finding for U6 with Vout ≈ 5 V (`get_findings(d, Det.POWER_REGULATORS)`); `nets['DCDC_RAW']` and `nets['DCDC_5V']` contain the pins listed above; **isolation check:** no net may contain both a GND1-domain and GND2-domain component except T1's own pins split across `DCDC_*`/primary nets.

- [ ] **Step 3: Commit** — `git commit -am "feat(sch): SN6505B isolated DC-DC, 5V LDO"`

---

### Task 6: External power input, CC detect, priority mux

**Files:**
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: `DCDC_5V`, `ISO_3V3` (forward-declared — sourced in Task 7; label it now), `GND2`, `isolator-lib:TPS2121`.
- Produces: net `ISO_5V` — the master isolated rail all later tasks draw from; `EXT_5V`, `n3A_DET`.

- [ ] **Step 1: Place and wire.** J2 `Connector:USB_C_Receptacle_PowerOnly_6P`, R 5.1 kΩ ×2 (Rd), U13/U14 `Comparator:TLV7041DBV`, Q1 `Transistor_FET:2N7002`, U7 `isolator-lib:TPS2121`, D4 LED + R.

| Connection | Notes |
|---|---|
| J2 VBUS → `EXT_5V`; 10 µF + 0.1 µF → `GND2`; J2 GND/shield → `GND2` | |
| J2 CC1 → `EXT_CC1` + 5.1 kΩ → `GND2`; J2 CC2 → `EXT_CC2` + 5.1 kΩ → `GND2` | one Rd per CC pin |
| Threshold: divider `ISO_3V3` → R 16.9 kΩ → node `VTH` → R 10 kΩ → `GND2` | VTH ≈ 1.23 V |
| U13: IN+ ← `EXT_CC1`, IN− ← `VTH`; U14: IN+ ← `EXT_CC2`, IN− ← `VTH`; V+ ← `ISO_3V3`, V− ← `GND2`, 0.1 µF each | output HIGH-Z when CC > 1.23 V (3 A) — **check TLV7041 output truth sense in datasheet; we need: 3 A present ⇒ node released** |
| U13 OUT + U14 OUT wire-ORed → `n3A_DET`, pull-up 100 kΩ → `ISO_3V3` | open-drain OR: LOW = no 3 A source. If the truth sense comes out inverted, swap each comparator's +/− inputs — do not add gates |
| Q1 gate ← inverter sense: **goal:** PR1 grounded when `n3A_DET` says "no 3 A". With the wiring above (LOW = no 3 A), Q1 must conduct on LOW — so instead wire comparators as: IN− ← CC, IN+ ← `VTH` (output pulls LOW when CC > VTH... ) — **resolve polarity on paper against the TLV7041 datasheet before wiring; the invariant is the boxed goal, wire whichever input assignment satisfies it with Q1 as a plain NMOS (gate high ⇒ PR1 low)** | |
| U7 IN1 ← `EXT_5V` (+bypass per datasheet); U7 IN2 ← `DCDC_5V`; U7 OUT → `ISO_5V`; U7 GND → `GND2` | |
| U7 PR1 ← divider from `EXT_5V` sized per TPS2121 datasheet so PR1 > VREF when EXT present; Q1 drain → PR1 node, Q1 source → `GND2` | Q1 on ⇒ PR1 low ⇒ DC-DC selected |
| U7 CL/ILIM-class pins per datasheet defaults; U7 ST → R 1 kΩ → D4 LED → rail per ST polarity (open-drain: LED from `ISO_5V` through R into ST) | ST = "external input active" indicator |
| `ISO_5V`: bulk 47 µF + 0.1 µF → `GND2` | |

- [ ] **Step 2: ERC + probes.** ERC exit 0. Probe `nets['ISO_5V']` contains U7 OUT + caps; `nets['n3A_DET']` contains U13, U14, pull-up, Q1 gate path. Confirm `EXT_CC1`/`EXT_CC2` each have exactly 3 pins (J2, Rd, comparator input).

- [ ] **Step 3: Commit** — `git commit -am "feat(sch): external USB-C power, CC 3A detect, TPS2121 mux"`

---

### Task 7: ADuM Side 2, hub core, 3.3 V rail

**Files:**
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: `ISO_5V`, `GND2`, U1 Side-2 pins, U3 (existing NUP4202).
- Produces: `ISO_3V3` (sourced), `ISO_DP`/`ISO_DM`, `PGOOD2`, hub downstream pin nets `P1_DP`…`P4_DM`, `PRTPWR1-4`, `nOCS1-4` (labeled at the hub, consumed in Task 8).

- [ ] **Step 1: Wire ADuM Side 2.** U1 VBUS2 ← `ISO_5V` + 0.1 µF → `GND2`; U1 VDD2 → 0.1 µF → `GND2` (no other load); all GND2 pins → `GND2`; U1 DD+/DD− → `ISO_DP`/`ISO_DM`; U1 PGOOD → `PGOOD2`; rewire U3 (NUP4202) channels onto `ISO_DP`/`ISO_DM`, its VBUS pin → `ISO_5V`, GND → `GND2`. Remove Task-4 no_connects on Side-2 pins.

- [ ] **Step 2: Place U8 AP2112K-3.3.** IN ← `ISO_5V`, EN ← `ISO_5V`, OUT → `ISO_3V3`, GND → `GND2`, 1 µF in / 1 µF out + 0.1 µF.

- [ ] **Step 3: Place U4 USB2514B_Bi and support parts.** Per USB2514B datasheet (Task 2 PDF):
  - All VDD33-class pins ← `ISO_3V3` with 0.1 µF each; exposed pad + VSS → `GND2`.
  - CRFILT: cap per datasheet (typ 1 µF) → `GND2`. PLLFILT/analog filter pins per datasheet.
  - RBIAS: 12.0 kΩ 1% → `GND2`.
  - Y2 24 MHz (CL 12 pF) across XTALIN/XTALOUT, 22 pF each side → `GND2`.
  - RESET_N: 10 kΩ → `ISO_3V3` + 1 µF → `GND2` (RC power-on reset), verify polarity/threshold in datasheet.
  - VBUS_DET ← `PGOOD2` (hub sees "host present" only when the isolator reports both sides up + clock valid). **Verify VBUS_DET VIH ≤ 3.3 V-logic compatible in the datasheet; if it expects 5 V VBUS sensing via divider, feed it from `ISO_5V` through the datasheet divider and leave `PGOOD2` for the LED only.**
  - Strap pins (CFG_SEL/SMBus/NON_REM/LOCAL_PWR class): strap for "default configuration, no EEPROM/SMBus" exactly per the datasheet's configuration table — resistors as specified there, not from memory.
  - USBUP_DP/DM ← `ISO_DP`/`ISO_DM`. Downstream pairs → `P1_DP/P1_DM` … `P4_DP/P4_DM` (labels only; connectors in Task 8). PRTPWR1-4 → `PRTPWR1-4`; OCS_N1-4 ← `nOCS1-4` with 100 kΩ pull-ups → `ISO_3V3` (open-drain fault lines).
  - Unused pins (HS_IND, SUSP_IND, etc.): no_connect markers.

- [ ] **Step 4: ERC + probes.** ERC exit 0. Probes: `nets['ISO_DP']` = {U1 DD+, U3, U4 USBUP_DP}; `nets['ISO_3V3']` sourced by U8 with U4 + pull-ups attached; crystal finding for Y2 in analyzer (`Det` crystal circuits) with load-cap analysis ≈ 12 pF CL.

- [ ] **Step 5: Commit** — `git commit -am "feat(sch): ADuM side 2, USB2514B hub core, 3.3V rail"`

---

### Task 8: Downstream ports

**Files:**
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: `ISO_5V`, `P1_DP`…`P4_DM`, `PRTPWR1-4`, `nOCS1-4`.
- Produces: 4 fully-wired physical ports.

- [ ] **Step 1: Port power switches U9–U12 (TPS2553DBV, one per port).** For port N: IN ← `ISO_5V` (+0.1 µF), EN ← `PRTPWRn`, OUT → `Pn_VBUS` (+120 µF-class bulk? no — 10 µF + 0.1 µF per port; hub ports must not exceed 10 µF inrush per USB spec... use 10 µF), FAULT̅ → `nOCSn`, GND → `GND2`, ILIM → R_ILIM → `GND2`. **Compute R_ILIM from the TPS2553 datasheet equation for I_LIM ≈ 600 mA (acceptance: 600–700 mA typ); record the E96 value used in the schematic.**

- [ ] **Step 2: Connectors.**
  - J3, J4 `Connector:USB_A`: VBUS ← `P1_VBUS`/`P2_VBUS`, D± ← `P1_DP/DM`, `P2_DP/DM`, GND+shield → `GND2`.
  - J5, J6 `Connector:USB_C_Receptacle_USB2.0_16P`: VBUS ← `P3_VBUS`/`P4_VBUS`; D± ← `P3_*`/`P4_*`; CC1 → 56 kΩ → own port VBUS (`P3_VBUS` etc.); CC2 → 56 kΩ → own port VBUS; SBU n/c; GND+shield → `GND2`.
- [ ] **Step 3: ESD.** U15–U18 NUP4202, one per port: channels on `Pn_DP`/`Pn_DM`, VBUS pin → `Pn_VBUS`, GND → `GND2`.

- [ ] **Step 4: ERC + probes.** ERC exit 0. Probe each `Pn_DP` net = {U4, connector, NUP4202}; each `Pn_VBUS` = {TPS2553 OUT, connector, caps, ESD, (+2× 56 kΩ on C ports)}. Analyzer ESD-coverage audit: no uncovered external USB pairs.

- [ ] **Step 5: Commit** — `git commit -am "feat(sch): 4 downstream ports with per-port current limiting"`

---

### Task 9: Indicators, PWR_FLAGs, barrier provisions, ERC zero

**Files:**
- Modify: `isolator.kicad_sch`

- [ ] **Step 1: Indicators.** D3 LED + 1 kΩ from `PGOOD2` → `GND2` (isolator good); D5 LED + 1 kΩ from `DCDC_5V` → `GND2` (bus-power alive). (D4 EXT-active placed in Task 6.)
- [ ] **Step 2: Barrier stitching provision.** C_stitch 1 nF 2 kV rated, `GND1` ↔ `GND2`, marked DNP (`(dnp yes)`, in_bom no). This is the only deliberate GND1↔GND2 element; annotate with a text note "DNP — EMI stitching provision, see spec".
- [ ] **Step 3: PWR_FLAG sweep.** Add `power:PWR_FLAG` to: `VBUS_HOST`, `EXT_5V`, `DCDC_RAW`, `GND1`, `GND2` (and any net ERC still flags as undriven — connector/passive-sourced rails).
- [ ] **Step 4: Final no_connect audit.** Every unused pin on every symbol gets an explicit no_connect; remove all stale ones.
- [ ] **Step 5: ERC must be fully clean** — zero errors AND review every remaining warning; each surviving warning gets a one-line justification in the commit message or gets fixed.
- [ ] **Step 6: Commit** — `git commit -am "feat(sch): indicators, PWR_FLAGs, stitching provision; ERC clean"`

---

### Task 10: Footprint assignment

**Files:**
- Modify: `isolator.kicad_sch`
- Create: `isolator-lib.pretty/` (custom footprints), `fp-lib-table`

**Interfaces:**
- Produces: every component has a Footprint property; custom footprints for T1 and U1.

- [ ] **Step 1: Assign stock footprints:**

| Part | Footprint |
|---|---|
| J1, J5, J6 | `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12` |
| J2 | `Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal` |
| J3, J4 | `Connector_USB:USB_A_Molex_67643_Horizontal` |
| U4 | `Package_DFN_QFN:QFN-36-1EP_6x6mm_P0.5mm_EP3.7x3.7mm` — verify vs USB2514B mech drawing |
| U5, U9–U12 | `Package_TO_SOT_SMD:SOT-23-6` |
| U6 | `Package_TO_SOT_SMD:TO-263-5_TabPin3` — verify tab pin vs MIC29302 datasheet |
| U7 | per TPS2121 package from datasheet (WQFN — pick matching `Package_DFN_QFN` footprint, verify pad map) |
| U8, U13, U14, Q1 | `Package_TO_SOT_SMD:SOT-23-5` / `SOT-23` as appropriate |
| U2, U3, U15–U18 | existing `Package_TO_SOT_SMD:SOT-363_SC-70-6` |
| Y1, Y2 | `Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm` |
| R/C/LED | 0603 (`Resistor_SMD:R_0603_1608Metric` etc.); bulk caps `Capacitor_SMD:C_1206_3216Metric`; C_stitch 1812 |

- [ ] **Step 2: Custom footprints in `isolator-lib.pretty`:**
  - `WE_750313638` — from the Würth datasheet land pattern (Task 2 PDF). Record actual primary-to-secondary pad clearance (7.51 mm per Würth pattern — accepted, see spec).
  - `ADI_SOIC_IC_20_RI-20-1` — from ADuM4165 datasheet Outline Dimensions. Acceptance: pad-row-to-pad-row clearance ≥ 8.3 mm. Register `fp-lib-table` like `sym-lib-table` in Task 1.
- [ ] **Step 3: Verify** — analyzer run: `statistics.missing_footprint`-class findings zero; footprint-filter audit clean. ERC still exit 0.
- [ ] **Step 4: Commit** — `git commit -am "feat(sch): footprint assignment, custom RI-20-1 + WE transformer footprints"`

---

### Task 11: MPNs, BOM, and full design review

**Files:**
- Modify: `isolator.kicad_sch` (MPN properties)
- Create: review report `docs/superpowers/reviews/2026-07-25-schematic-review.md`

- [ ] **Step 1: Populate MPN property on every BOM component** (U1 `ADUM4165BRIZ`, U4 `USB2514B-AEZC`, U5 `SN6505BDBVR`, T1 `750313638`, U6 `MIC29302WU`, U7 `TPS2121RUXR`, U9–12 `TPS2553DBVR`, U13/14 `TLV7041DBVR`, connectors/passives per what the bom skill's distributor search returns in stock — use kicad-happy `bom` + `lcsc`/`digikey` skills to fill and sanity-check availability/pricing).
- [ ] **Step 2: Datasheet sync now that MPNs exist** — run the digikey or lcsc sync script from the kicad skill docs so `datasheets/` coverage is complete (clears DS-00x findings).
- [ ] **Step 3: Full kicad-happy design review** per the kicad skill's Design Review Contract: `analyze_schematic.py` (with `--lifecycle` if network/API keys allow), deep-review pass on U1/U4/U5/U6/U7 against datasheets, SPICE if `which ngspice` hits, and write the report with blockers/verification-basis/skipped sections. No PCB yet → PCB/EMC/thermal analyzers are disclosed as N/A.
- [ ] **Step 4: Fix every `error`-severity and blocker finding; re-run until clean.**
- [ ] **Step 5: Commit** — `git commit -am "feat(sch): MPNs, BOM check, design review clean"`

---

## Self-review notes

- Spec coverage: upstream (T4), barrier+clock (T1/T4), DC-DC (T5), external+mux+CC (T6), hub (T7), ports+ESD+Rp (T8), indicators/stitching (T9), layout-prep items that live in schematic (footprints, creepage-checked custom footprints — T10), verification (T11 + per-task ERC). PCB layout itself is a separate future plan, as scoped.
- Known deliberate deviations from spec text: MIC29302 replaces AP7361C-50; 2× TLV7041 replace TLV7031 (spec amended 2026-07-25).
- Two datasheet-dependent decision points are flagged inline rather than guessed: transformer secondary rectification topology (T5) and comparator polarity / VBUS_DET sensing (T6/T7). The invariants to satisfy are stated in each case.
