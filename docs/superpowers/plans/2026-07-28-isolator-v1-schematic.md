# Isolator v1 — Schematic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the KiCad schematic for the single-port inline isolator per `docs/superpowers/specs/2026-07-28-usb-isolator-v1-design.md`, ending with an ERC-clean, footprint-assigned, MPN-populated schematic in a new `v1/` project that passes a kicad-happy design review, plus a proven mechanical fit against a Hammond 1455C802.

**Architecture:** USB-C upstream → ADuM4165 (5.7 kV isolation) → USB-C downstream. No hub, no external power, no CC sensing. Isolated power from an SN6505B push-pull DC-DC through a center-tapped 5 kV transformer, full-wave rectified, regulated to 5.0 V by a fixed low-dropout regulator, delivered through one TPS2553 current-limit switch.

**Tech Stack:** KiCad 10 (`kicad-cli` at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, not on PATH), kicad-happy plugin analyzers, stock KiCad symbol/footprint libraries plus the existing project library `isolator-lib` shared from the repo root.

**Scope:** This plan ends at a reviewed schematic and a validated board outline. PCB layout and routing are a follow-on plan.

## Global Constraints

Copied from the spec — every task implicitly includes these:

- Two ground domains only: `GND1` (host side), `GND2` (isolated side). No net, wire, or component other than U1 (ADuM4165), T1 (transformer), and CY1 (stitching capacitor) may touch both domains.
- ADuM4165 bypass: **exactly 0.1 µF** at `VDD1` and `VDD2` — larger disrupts start-up sequencing per the data sheet. 0.1 µF at `VBUS1`/`VBUS2`. Place-close note ≤10 mm total lead length.
- Crystal Y1: 24 MHz, ≤50 ppm total tolerance, ≤100 ppm stability, CL ≈ 10 pF, start-up within 0.3 ms, 8 pF load caps, on **Side 1** (XI1/XO1 — the '4165 has no Side-2 clock input).
- Downstream USB-C advertises Default USB Power: **56 kΩ Rp** from each of CC1 and CC2 to `PORT_VBUS`. Dedicated resistor per CC pin, never shared.
- Upstream USB-C is a UFP: **5.1 kΩ Rd** from each of CC1 and CC2 to `GND1`. Dedicated resistor per CC pin, never shared.
- Downstream current limit **≈250 mA** via the TPS2553 ILIM resistor.
- Both USB data pairs get a USBLC6-2SC6 with its `VBUS` pin (5) tied to that connector's local VBUS rail.
- Each connector's VBUS gets a dedicated unidirectional TVS, V_RWM ≥ 5.5 V.
- The barrier-stitching capacitor CY1 is **populated**, not DNP.
- Upstream `VBUS_HOST` bulk capacitance stays under the USB 2.0 §7.2.4.1 bus-powered limit of 10 µF / 50 µC at hot-plug.
- All new symbols placed with `(in_bom yes)`, unique reference designators, and Value/Footprint/MPN properties filled by the end of the plan.

## Working conventions (read once before any task)

**Paths.** Repo root is `/Users/alex/Documents/isolator/.claude/worktrees/isolator-v1-simplified-909ae9`. All paths below are relative to it unless absolute.

```bash
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
KH=/Users/alex/.claude/plugins/cache/kicad-happy/kicad-happy/2.0.0/skills
SCH=v1/isolator-v1.kicad_sch
```

**How edits are made.** The schematic is a single flat sheet in KiCad 10 s-expression format. Place symbols by (a) copying the full library symbol definition into the file's `lib_symbols` section, once per `lib_id`, and (b) adding a `(symbol (lib_id ...) (at x y rot) ...)` instance with Reference/Value/Footprint properties and a UUID. Grid is 1.27 mm (50 mil) — every pin endpoint must land on grid. Prefer net labels over long wires: place a short wire stub from each pin and label it; connectivity is by label name. See kicad-happy `references/file-formats.md` for field-by-field details.

**Copy from v2, do not retype.** `isolator.kicad_sch` at the repo root already contains working, reviewed instances of U1 (ADuM4165), the USBLC6-2SC6, SN6505BDBV, TPS2553DBV, 750313638, the USB-C receptacle, and the crystal network. Lift the `lib_symbols` blocks and the symbol instances from there. This is the single biggest source of errors avoided.

**Verification tools (used in every task):**

```bash
# ERC — also validates the file still parses; must exit 0 at the end of every task
$KCLI sch erc "$SCH" --output /tmp/erc-v1.rpt --severity-error --exit-code-violations; echo "exit=$?"; cat /tmp/erc-v1.rpt

# Netlist — the ground truth for probes
$KCLI sch export netlist --format kicadxml -o /tmp/v1-net.xml "$SCH"

# Analyzer
python3 $KH/kicad/scripts/analyze_schematic.py "$SCH" --analysis-dir analysis-v1/
```

**Probe pattern** (fill in the net name per task):

```bash
python3 - <<'EOF'
import xml.etree.ElementTree as ET
r = ET.parse('/tmp/v1-net.xml').getroot()
TARGET = 'ISO_5V'
for n in r.iter('net'):
    if n.get('name').lstrip('/') == TARGET:
        for nd in n.iter('node'):
            print(f"{nd.get('ref')}.{nd.get('pin')} ({nd.get('pinfunction')})")
EOF
```

**Isolation check** — run this at the end of every task from Task 4 onward. It must print nothing:

```bash
python3 - <<'EOF'
import xml.etree.ElementTree as ET
r = ET.parse('/tmp/v1-net.xml').getroot()
ALLOWED = {'U1', 'T1', 'CY1'}   # the only parts permitted to bridge domains

nets = {n.get('name').lstrip('/'): {nd.get('ref') for nd in n.iter('node')}
        for n in r.iter('net')}
d1, d2 = nets.get('GND1', set()), nets.get('GND2', set())

# A part in both domain sets is a bridge. Only ALLOWED may be one.
for ref in sorted((d1 & d2) - ALLOWED):
    print("BRIDGE (part on both grounds):", ref)

# A signal net carrying parts from both domains is a bridge, unless every
# such part is an allowed barrier-crossing device.
for name, refs in nets.items():
    if name in ('GND1', 'GND2'):
        continue
    a, b = refs & d1, refs & d2
    if a and b and not (a | b) <= ALLOWED:
        print("BRIDGE (net spans domains):", name, sorted(refs))
EOF
```

A clean run prints nothing. Note the second check flags a net only when a
non-allowed part sits on each side — U1, T1, and CY1 legitimately appear on
nets that touch both domains.

**ERC policy.** The schematic is ERC-clean at the end of every task *for the circuitry placed so far*. Pins whose wiring belongs to a later task get explicit `(no_connect)` markers, removed in that later task. Exit code 0 with `--severity-error` is the gate. Warnings are triaged; two-domain designs legitimately warn until PWR_FLAGs land in Task 6.

**Reference designator allocation (fixed for the whole plan):**

| Ref | Part |
|---|---|
| U1 | ADuM4165 (`Isolator:ADUM4165`) |
| U2 | USBLC6-2SC6, upstream ESD |
| U3 | USBLC6-2SC6, downstream ESD |
| U4 | SN6505BDBV |
| U5 | Fixed 5.0 V LDO (selected in Task 2) |
| U6 | TPS2553DBV |
| T1 | Würth 750313638 |
| Y1 | 24 MHz crystal |
| J1 | Upstream USB-C receptacle (UFP) |
| J2 | Downstream USB-C receptacle (DFP) |
| D1, D2 | Rectifier Schottky (SS34) |
| D3 | PGOOD LED |
| D4 | FAULT LED |
| D5 | VBUS TVS, upstream |
| D6 | VBUS TVS, downstream |
| Q1 | PGOOD level-shift FET (2N7002), **only if Task 5 Step 1 shows it is needed** |
| CY1 | Barrier-stitching capacitor |
| C*/R* | Number sequentially from C1/R1 |

**Net names (fixed):**

- GND1 domain: `VBUS_HOST`, `HOST_D+`, `HOST_D-`, `VDD1`, `XTALIN`, `XTALOUT`, `GND1`
- GND2 domain: `DCDC_RAW`, `ISO_5V`, `VDD2`, `PGOOD2`, `PORT_D+`, `PORT_D-`, `PORT_VBUS`, `PORT_CC1`, `PORT_CC2`, `nFAULT`, `ILIM_SET`, `GND2`

Note there is no separate `ISO_D+`/`PORT_D+` split: with no hub, the ADuM4165's `DD+` pin, the USBLC6 array, and the connector are all one net. Same for `D-`.

**Pin numbers verified from the v2 netlist** — use these, do not infer:

| Part | Pins |
|---|---|
| U1 ADuM4165 | 1 VBUS1 · 2/4/7/10 GND1 · 3 VDD1 · 5 XI1 · 6 XO1 · 8 UD+ · 9 UD− · 11/15/16/17/19 GND2 · 12 DD+ · 13 DD− · 14 PGOOD · 18 VDD2 · 20 VBUS2 |
| U2/U3 USBLC6-2SC6 | 1 I/O1 · 2 GND · 3 I/O2 · 4 I/O2 · 5 VBUS · 6 I/O1 |
| U4 SN6505BDBV | 1 D1 · 2 VCC · 3 D2 · 4 GND · 5 EN · 6 CLK |
| U6 TPS2553DBV | 1 IN · 2 GND · 3 EN · 4 ~FAULT · 5 ILIM · 6 OUT |
| T1 750313638 | Primary: 1 N1 · 2 CT1 · 3 N2 — Secondary: 4 N4 · 5 CT2 · 6 N3 |
| J1/J2 USB_C_Receptacle_USB2.0_16P | A1/A12/B1/B12 GND · SH SHIELD · A4/A9/B4/B9 VBUS · A5 CC1 · B5 CC2 · A6/B6 D+ · A7/B7 D− · A8/B8 SBU (leave unconnected) |
| Y1 | 1, 3 crystal · 2, 4 GND |

---

### Task 1: v1 project skeleton and mechanical feasibility gate

**Files:**
- Create: `v1/isolator-v1.kicad_pro`, `v1/isolator-v1.kicad_sch`, `v1/isolator-v1.kicad_pcb`, `v1/sym-lib-table`, `v1/fp-lib-table`
- Create: `docs/superpowers/reviews/2026-07-28-v1-mechanical-feasibility.md`

**Interfaces:**
- Produces: an empty but openable KiCad project at `v1/isolator-v1.kicad_pro` with the shared `isolator-lib` registered; a written go/no-go on the 80 × 50 mm board target.

- [ ] **Step 1: Create the project directory and copy settings from v2**

```bash
mkdir -p v1
cp isolator.kicad_pro v1/isolator-v1.kicad_pro
cp isolator.kicad_dru v1/isolator-v1.kicad_dru
```

Copying v2's `.kicad_pro` carries over the ERC/DRC severity settings and net classes that were already tuned for this design — do not start from a default project.

- [ ] **Step 2: Create the empty schematic and PCB**

`v1/isolator-v1.kicad_sch`:

```
(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0")
  (uuid "00000000-0000-0000-0000-000000000001")
  (paper "A3")
  (lib_symbols)
  (sheet_instances (path "/" (page "1")))
)
```

`v1/isolator-v1.kicad_pcb`:

```
(kicad_pcb (version 20241229) (generator "pcbnew") (generator_version "9.0")
  (general (thickness 1.6) (legacy_teardrops no))
  (paper "A4")
  (layers
    (0 "F.Cu" signal) (1 "In1.Cu" signal) (2 "In2.Cu" signal) (31 "B.Cu" signal)
    (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user) (39 "F.Mask" user)
    (44 "Edge.Cuts" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard")
  )
)
```

- [ ] **Step 3: Register the shared libraries**

`v1/sym-lib-table`:

```
(sym_lib_table
  (version 7)
  (lib (name "isolator-lib")(type "KiCad")(uri "${KIPRJMOD}/../isolator-lib.kicad_sym")(options "")(descr "Shared project symbols"))
)
```

`v1/fp-lib-table`:

```
(fp_lib_table
  (version 7)
  (lib (name "isolator-lib")(type "KiCad")(uri "${KIPRJMOD}/../isolator-lib.pretty")(options "")(descr "Shared project footprints"))
)
```

- [ ] **Step 4: Verify the project opens and the libraries resolve**

Run:
```bash
$KCLI sch erc v1/isolator-v1.kicad_sch --output /tmp/erc-v1.rpt --severity-error --exit-code-violations; echo "exit=$?"
```
Expected: exit 0, empty schematic, no parse error. If `kicad-cli` rejects the file version strings, open the project once in the KiCad GUI to let it migrate, then re-run.

- [ ] **Step 5: Run the mechanical feasibility gate**

Compute the total component courtyard area and the longest dimension chain against the 1455C802 envelope. Usable area is 80 × 50 mm minus a 2 mm copper pullback on each long edge, i.e. **80 × 46 = 3680 mm²**.

```bash
python3 - <<'EOF'
# Courtyard footprints (mm) for every v1 part. ADuM4165 and T1 measured from
# isolator-lib.pretty; the rest are standard package sizes.
parts = {
    'J1 USB-C':        (9.0, 7.5),   'J2 USB-C':        (9.0, 7.5),
    'U1 ADuM4165':     (11.8, 16.04),'T1 750313638':    (13.2, 9.64),
    'U2 USBLC6':       (3.0, 3.0),   'U3 USBLC6':       (3.0, 3.0),
    'U4 SN6505':       (3.0, 3.0),   'U5 LDO':          (3.0, 3.0),
    'U6 TPS2553':      (3.0, 3.0),   'Y1 crystal':      (3.2, 2.5),
    'D1 SMA':          (5.0, 3.0),   'D2 SMA':          (5.0, 3.0),
    'C bulk in':       (2.0, 1.25),  'C raw 47u':       (7.3, 4.3),
    'C iso 47u':       (7.3, 4.3),   'CY1 Y2 disc':     (10.0, 6.0),
    'D3/D4 LEDs':      (3.2, 1.6),   'D5/D6 TVS':       (2.0, 1.2),
}
area = sum(w*h for w, h in parts.values())
passives = 25 * (1.6 * 0.8)   # ~25 0603 R/C
total = area + passives
usable = 80 * 46
print(f"component area   {total:7.1f} mm^2")
print(f"usable area      {usable:7.1f} mm^2")
print(f"utilization      {100*total/usable:6.1f} %   (target < 45%)")

# Length chain along the 80 mm axis. Parts not listed sit beside these, not in line.
chain = [('J1 + ESD + bulk', 16), ('ADuM4165 barrier zone', 16),
         ('rectifier + LDO + TPS2553', 18), ('ESD + J2', 12)]
spacing = 2.0 * (len(chain) + 1)
length = sum(v for _, v in chain) + spacing
print(f"\nlength chain     {length:6.1f} mm  (available 80.0 mm)")
for n, v in chain: print(f"    {n:<32} {v:5.1f}")
EOF
```

Expected: utilization comfortably under 45 %, length chain under 80 mm with margin.

- [ ] **Step 6: Write the feasibility record**

Create `docs/superpowers/reviews/2026-07-28-v1-mechanical-feasibility.md` containing the script output, the verdict, and one explicit sentence on the fallback: if either number fails, the design moves to **1455C1202** (120 mm, same 1455C profile, same 50 mm board width) by editing only the board outline — no schematic or architecture change.

- [ ] **Step 7: Commit**

```bash
git add v1 docs/superpowers/reviews/2026-07-28-v1-mechanical-feasibility.md
git commit -m "feat(v1): project skeleton, shared lib tables, mechanical feasibility gate"
```

---

### Task 2: Part selection — 5.0 V LDO, VBUS TVS, stitching capacitor

**Files:**
- Modify: `isolator-lib.kicad_sym` (only if the LDO has no stock symbol)
- Create: `datasheets/extracted/<LDO-MPN>-pins.md`
- Create: `docs/superpowers/reviews/2026-07-28-v1-part-selection.md`

**Interfaces:**
- Produces: a chosen LDO MPN with a verified pin table and a symbol resolvable by `lib_id`; a chosen VBUS TVS MPN; a chosen CY1 MPN with a footprint that clears the barrier.

- [ ] **Step 1: Select and verify the 5.0 V LDO**

Requirements, all of which must be checked against the actual data sheet — do not select from memory:

| Requirement | Value |
|---|---|
| Output | Fixed 5.0 V |
| Output current | ≥ 400 mA (the load ceiling is 315 mA) |
| Dropout at 315 mA | ≤ 0.6 V, giving margin against a `DCDC_RAW` that sags to ~5.8 V under load |
| Input range | must include 5.5–6.5 V |
| Package | SOT-23-5 or SOT-223, hand-solderable |

First candidate: **TLV76750** (TI, 1 A, fixed 5.0 V, SOT-23-5). Download the data sheet, confirm the fixed-5.0 V option and the exact orderable part number exist, and read the dropout-vs-current curve at 315 mA.

**Documented fallback:** if the first candidate fails any row, or its 5.0 V variant is not orderable, use **MIC29302WU** — the v2 part, already validated, already has a working symbol and the `TO-263-5_TabPin3` footprint in the schematic, wired adjustable with R 30.1 kΩ / 10 kΩ for ≈4.97 V. It is physically larger and oversized for the current, which is the only reason v1 tried to replace it. Record which path was taken.

- [ ] **Step 2: Write the LDO pin table**

Create `datasheets/extracted/<MPN>-pins.md` with a pin-number → name → function table read from the data sheet. This is the ground truth for Task 4 — do not wire from memory.

- [ ] **Step 3: Resolve the LDO symbol**

Check for a stock symbol first:

```bash
grep -rl "TLV767\|TLV76750" /Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/ | head
```

If a stock symbol exists, note its `lib_id`. If not, add a symbol to `isolator-lib.kicad_sym` built from the Step 2 pin table, following the style of the existing `TPS2553` and `TPS2121` entries in that file.

- [ ] **Step 4: Select the VBUS TVS (D5, D6)**

Unidirectional TVS, V_RWM ≥ 5.5 V, capacitance is unconstrained on a power rail. Candidates: **ESD441** (TI, DFN0603 — very small, check assembly method) or **PESD5V0S1BA** (Nexperia, SOD-523 — easier to hand-place). Pick one, confirm stock, and use the stock KiCad symbol `Device:D_TVS`.

- [ ] **Step 5: Select the barrier-stitching capacitor CY1 — this is where v2's part is wrong**

v2 carries `C49` as a **1 nF 2 kV part in a 2220 (5.7 × 5.0 mm) SMD package, DNP**. That package spans only 5.7 mm. Populating it as-is would **reduce the barrier from 8.3 mm to 5.7 mm**, making the capacitor the weakest point in the isolation — exactly what the spec forbids.

Select instead a **through-hole Y2-rated safety capacitor**, 470 pF–1 nF, with a lead spacing of at least 10 mm so its body and pads clear the barrier gap. Y2 parts carry agency-rated creepage and clearance by construction. Confirm the chosen part's own creepage rating equals or exceeds 8.3 mm.

Symbol: `Device:C`. Footprint: a through-hole disc footprint with ≥10 mm pad pitch — check `Capacitor_THT:` for a match, and create one in `isolator-lib.pretty` if none fits.

- [ ] **Step 6: Write the selection record**

Create `docs/superpowers/reviews/2026-07-28-v1-part-selection.md` with, for each of the three parts: chosen MPN, the requirement table with measured/data-sheet values filled in, the `lib_id` and footprint, and — for CY1 — the explicit note that v2's C49 footprint must not be reused.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(v1): select 5V LDO, VBUS TVS, and Y2 stitching cap"
```

---

### Task 3: Upstream host section (GND1 domain)

**Files:**
- Modify: `v1/isolator-v1.kicad_sch`

**Interfaces:**
- Consumes: `isolator-lib` from Task 1.
- Produces: nets `VBUS_HOST`, `HOST_D+`, `HOST_D-`, `VDD1`, `XTALIN`, `XTALOUT`, `GND1`; U1 Side-1 pins fully terminated.

- [ ] **Step 1: Copy the symbol definitions from v2**

Lift these `lib_symbols` blocks out of `isolator.kicad_sch` into `v1/isolator-v1.kicad_sch`: `Isolator:ADUM4165`, the USBLC6-2SC6 symbol, `Connector:USB_C_Receptacle_USB2.0_16P`, the crystal, `Device:R`, `Device:C`, and the `power:GND`/`power:PWR_FLAG` symbols.

- [ ] **Step 2: Place and wire the upstream section**

New parts: J1 `Connector:USB_C_Receptacle_USB2.0_16P`, U1 `Isolator:ADUM4165`, U2 USBLC6-2SC6, Y1 24 MHz crystal, D5 TVS, R1/R2 5.1 kΩ, C1/C2 8 pF, C3 4.7 µF, C4 0.1 µF, C5 0.1 µF.

| From | To / net |
|---|---|
| J1 A4, A9, B4, B9 (VBUS) | `VBUS_HOST` |
| J1 A1, A12, B1, B12, SH | `GND1` |
| J1 A5 (CC1) | R1 5.1 kΩ → `GND1` |
| J1 B5 (CC2) | R2 5.1 kΩ → `GND1` |
| J1 A6, B6 | `HOST_D+` |
| J1 A7, B7 | `HOST_D-` |
| J1 A8, B8 (SBU) | leave unconnected — add `(no_connect)` markers |
| U2.1, U2.6 | `HOST_D+` |
| U2.3, U2.4 | `HOST_D-` |
| U2.2 | `GND1` |
| U2.5 | `VBUS_HOST` |
| D5 TVS cathode | `VBUS_HOST`; anode → `GND1` |
| U1.1 (VBUS1) | `VBUS_HOST` |
| C3 4.7 µF, C4 0.1 µF | `VBUS_HOST` → `GND1` |
| U1.3 (VDD1) | `VDD1`; C5 **0.1 µF exactly** → `GND1`. VDD1 is an LDO output — no other load. |
| U1.5 (XI1) | `XTALIN` → Y1.1; C1 8 pF → `GND1` |
| U1.6 (XO1) | `XTALOUT` → Y1.3; C2 8 pF → `GND1` |
| Y1.2, Y1.4 | `GND1` |
| U1.8 (UD+) | `HOST_D+` |
| U1.9 (UD−) | `HOST_D-` |
| U1.2, 4, 7, 10 | `GND1` |
| U1.11–20 | `(no_connect)` for now — removed in Tasks 4 and 5 |

**Bulk capacitance note:** C3 is 4.7 µF, not v2's 10 µF. With no hub and no external-power section, v1's total `VBUS_HOST` capacitance must stay under the USB 2.0 §7.2.4.1 limit of 10 µF / 50 µC. Sum C3 + C4 + U4's input bypass (added in Task 4) and confirm the total is ≤10 µF.

- [ ] **Step 3: Verify**

```bash
$KCLI sch erc "$SCH" --output /tmp/erc-v1.rpt --severity-error --exit-code-violations; echo "exit=$?"
$KCLI sch export netlist --format kicadxml -o /tmp/v1-net.xml "$SCH"
```

Expected: ERC exit 0. Probe `HOST_D+` — must contain `J1.A6`, `J1.B6`, `U1.8`, `U2.1`, `U2.6`. Probe `VBUS_HOST` — must contain `J1.A4/A9/B4/B9`, `U1.1`, `U2.5`, `D5`, C3, C4. Probe `VDD1` — must contain exactly `U1.3` and C5, nothing else.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(v1/sch): upstream USB-C host section, ADuM Side 1, crystal"
```

---

### Task 4: Isolated DC-DC and 5.0 V rail (GND2 domain)

**Files:**
- Modify: `v1/isolator-v1.kicad_sch`

**Interfaces:**
- Consumes: `VBUS_HOST`, `GND1`, the LDO symbol from Task 2.
- Produces: nets `DCDC_RAW`, `ISO_5V`, `GND2`.

- [ ] **Step 1: Copy the symbol definitions from v2**

Lift `Power_Management:SN6505BDBV`, `isolator-lib:750313638`, and `Device:D_Schottky` from `isolator.kicad_sch`. Add the LDO symbol resolved in Task 2.

- [ ] **Step 2: Place and wire the DC-DC**

New parts: U4 SN6505BDBV, T1 750313638, D1/D2 SS34, U5 LDO, C6 0.1 µF, C7 4.7 µF, C8 47 µF, C9 0.1 µF, C10 47 µF, C11 0.1 µF.

This topology is copied verbatim from v2, where it is already reviewed. The secondary **is** center-tapped, so this is a two-diode full-wave rectifier, not a bridge.

| Connection | Notes |
|---|---|
| U4.2 (VCC) ← `VBUS_HOST` | C6 0.1 µF + C7 4.7 µF → `GND1` |
| U4.5 (EN) ← `VBUS_HOST` | always on |
| U4.4 (GND) → `GND1` | |
| U4.6 (CLK) → `GND1` | selects the internal oscillator |
| U4.3 (D2) → T1.1 (N1) | push-pull drive |
| U4.1 (D1) → T1.3 (N2) | push-pull drive |
| T1.2 (CT1) ← `VBUS_HOST` | primary center tap |
| T1.6 (N3) → D1 anode | |
| T1.4 (N4) → D2 anode | |
| D1 cathode, D2 cathode → `DCDC_RAW` | |
| T1.5 (CT2) → `GND2` | secondary center tap is the GND2 reference |
| C8 47 µF + C9 0.1 µF | `DCDC_RAW` → `GND2` |
| U5 VIN ← `DCDC_RAW`, U5 EN ← `DCDC_RAW`, U5 GND → `GND2` | pin numbers from the Task 2 pin table |
| U5 VOUT → `ISO_5V`; C10 47 µF + C11 0.1 µF → `GND2` | |

If Task 2 selected the MIC29302 fallback, U5 is adjustable: add R 30.1 kΩ from `ISO_5V` to ADJ and R 10 kΩ from ADJ to `GND2`, and verify V_ref in the data sheet gives ≈4.97 V.

- [ ] **Step 3: Confirm the upstream capacitance budget**

Sum every capacitor on `VBUS_HOST` — C3, C4 from Task 3 plus C6, C7 here. Confirm ≤10 µF. If over, reduce C7 first; the SN6505B input bypass has more latitude than the ADuM4165's.

- [ ] **Step 4: Verify**

Run ERC, export the netlist, and run the **isolation check** from Working Conventions. Expected: ERC exit 0; isolation check prints nothing; probe `DCDC_RAW` contains `D1.1`, `D2.1`, U5 VIN and EN, C8, C9; probe `GND2` contains `T1.5`, U5 GND, C8, C9, C10, C11.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(v1/sch): SN6505B isolated DC-DC, full-wave rectifier, 5V LDO"
```

---

### Task 5: ADuM Side 2, port switch, and downstream USB-C

**Files:**
- Modify: `v1/isolator-v1.kicad_sch`

**Interfaces:**
- Consumes: `ISO_5V`, `GND2`, U1 from Task 3.
- Produces: nets `VDD2`, `PORT_VBUS`, `PORT_D+`, `PORT_D-`, `PORT_CC1`, `PORT_CC2`, `nFAULT`, `ILIM_SET`, `PGOOD2`.

- [ ] **Step 1: Determine the PGOOD output type before wiring it**

Read the ADuM4165 Rev B data sheet pin description for **PGOOD** (pin 14) — `datasheets/adum4165-4166.pdf`, Pin Configurations and Function Descriptions. Record the output structure and drive current.

- If push-pull and it can source ≥1 mA: wire D3 from `PGOOD2` through a series resistor to `GND2`. With a 3.3 V V_DD2 domain and a ~2.0 V LED, use 1.3 kΩ for ≈1 mA.
- If open-drain: wire D3 anode to `VDD2` through the resistor, cathode to `PGOOD2`.
- If the drive is under 1 mA: add Q1 `2N7002` as v2 does — gate to `PGOOD2`, source to `GND2`, drain to the LED cathode with the LED anode to `ISO_5V` through a resistor.

Record which case applied. Do not guess between them.

- [ ] **Step 2: Compute the TPS2553 ILIM resistor from the data sheet equation**

Read the current-limit equation from `datasheets/extracted/TPS2553DBV-pins.md` and the TPS2553 data sheet. Solve for I_OS = 250 mA and pick the nearest E96 value inside the allowed 15 kΩ ≤ R_ILIM ≤ 232 kΩ range.

Sanity check only, not the method: v2 uses 40.2 kΩ for ≈600 mA, so a linear scaling puts 250 mA near **96.5 kΩ** (E96 neighbours 95.3 kΩ and 97.6 kΩ). If the data-sheet equation lands far from this, trust the equation and note the discrepancy.

- [ ] **Step 3: Place and wire**

New parts: U3 USBLC6-2SC6, U6 TPS2553DBV, J2 `Connector:USB_C_Receptacle_USB2.0_16P`, D4 FAULT LED, D6 TVS, R (ILIM from Step 2), R 100 kΩ (`nFAULT` pull-up), R 330 Ω (FAULT LED), R + LED per Step 1, R 56 kΩ ×2, C12 0.1 µF, C13 0.1 µF, and the port bulk pair **C14 22 µF + C15 0.1 µF** — the same values v2 uses on each of its port outputs (C38/C39), which the TPS2553 data sheet's output-capacitance guidance already covers.

| From | To / net |
|---|---|
| U1.20 (VBUS2) | `ISO_5V`; C12 0.1 µF → `GND2` |
| U1.18 (VDD2) | `VDD2`; C13 **0.1 µF exactly** → `GND2`, no other load |
| U1.11, 15, 16, 17, 19 | `GND2` |
| U1.12 (DD+) | `PORT_D+` |
| U1.13 (DD−) | `PORT_D-` |
| U1.14 (PGOOD) | `PGOOD2`, wired per Step 1 |
| U6.1 (IN) | `ISO_5V` |
| U6.2 (GND) | `GND2` |
| U6.3 (EN) | tie so the switch is permanently enabled — check the TPS2553 polarity in the pin table; the DBV variant's EN is active-high, so tie to `ISO_5V` |
| U6.4 (~FAULT) | `nFAULT`; 100 kΩ pull-up to `ISO_5V`; FAULT LED from `ISO_5V` through 330 Ω to `nFAULT` so it lights when the pin pulls low |
| U6.5 (ILIM) | `ILIM_SET` → R from Step 2 → `GND2` |
| U6.6 (OUT) | `PORT_VBUS`; C14 22 µF + C15 0.1 µF → `GND2` |
| U3.1, U3.6 | `PORT_D+` |
| U3.3, U3.4 | `PORT_D-` |
| U3.2 | `GND2` |
| U3.5 | `PORT_VBUS` |
| D6 TVS cathode | `PORT_VBUS`; anode → `GND2` |
| J2 A4, A9, B4, B9 | `PORT_VBUS` |
| J2 A1, A12, B1, B12, SH | `GND2` |
| J2 A5 (CC1) | `PORT_CC1` → R 56 kΩ → `PORT_VBUS` |
| J2 B5 (CC2) | `PORT_CC2` → R 56 kΩ → `PORT_VBUS` |
| J2 A6, B6 | `PORT_D+` |
| J2 A7, B7 | `PORT_D-` |
| J2 A8, B8 (SBU) | `(no_connect)` |

Remove the `(no_connect)` markers placed on U1.11–20 in Task 3.

- [ ] **Step 4: Verify**

Run ERC, export the netlist, run the isolation check. Expected: ERC exit 0; isolation check prints nothing.

Probe `PORT_D+` — must contain exactly `U1.12`, `U3.1`, `U3.6`, `J2.A6`, `J2.B6`. Five nodes, no hub in between. Probe `PORT_CC1` — must contain exactly `J2.A5` and one 56 kΩ resistor; confirm `PORT_CC2` has its own separate resistor and the two do not share.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(v1/sch): ADuM Side 2, TPS2553 port switch, downstream USB-C"
```

---

### Task 6: Stitching capacitor, PWR_FLAGs, and ERC zero

**Files:**
- Modify: `v1/isolator-v1.kicad_sch`

**Interfaces:**
- Consumes: everything from Tasks 3–5.
- Produces: a schematic with zero ERC errors and zero unexplained warnings.

- [ ] **Step 1: Place CY1, the barrier-stitching capacitor**

Symbol `Device:C`, value from Task 2 (470 pF–1 nF Y2). One terminal to `GND1`, the other to `GND2`. Add a schematic text note beside it:

> CY1 — barrier stitching. POPULATED, not DNP. Gives GND2's ESD current a defined return to GND1 instead of forcing it through the ADuM4165 die. Y2 safety-rated; body creepage must clear the 8.3 mm barrier. Do NOT substitute a 2220 SMD part.

This is the third and last permitted barrier crossing, alongside U1 and T1.

- [ ] **Step 2: Add PWR_FLAGs**

Two-domain designs need one `power:PWR_FLAG` per domain or ERC reports every rail as undriven. Place one on `GND1` and one on `GND2`. Add a third on `VBUS_HOST` — it is fed by a connector, which ERC does not treat as a source.

Per the repo's schematic layout rules, PWR_FLAG symbols go in a sheet corner, not inline with the circuitry.

- [ ] **Step 3: Drive ERC to zero**

```bash
$KCLI sch erc "$SCH" --output /tmp/erc-v1.rpt --severity-error --exit-code-violations; echo "exit=$?"
cat /tmp/erc-v1.rpt
```

Expected: exit 0 and an empty error list. Then re-run without `--severity-error` and triage every remaining warning: either fix it or write a one-line justification into the commit message. Do not leave an unexplained warning.

- [ ] **Step 4: Run the full isolation check one final time**

The check from Working Conventions must print nothing. `ALLOWED` is now `{'U1', 'T1', 'CY1'}` — CY1 is expected to bridge and is the reason it is in the allow-list.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(v1/sch): populated barrier stitching cap, PWR_FLAGs, ERC clean"
```

---

### Task 7: Footprint assignment

**Files:**
- Modify: `v1/isolator-v1.kicad_sch`

**Interfaces:**
- Produces: every symbol carrying a valid, resolvable `Footprint` property.

- [ ] **Step 1: Assign footprints**

Reuse v2's assignments verbatim where the part is the same:

| Ref | Footprint |
|---|---|
| U1 | `isolator-lib:ADI_SOIC_IC_20_RI-20-1` |
| T1 | `isolator-lib:WE_750313638` |
| U2, U3, U4, U6 | `Package_TO_SOT_SMD:SOT-23-6` |
| U5 | per Task 2 — `Package_TO_SOT_SMD:SOT-23-5` or `Package_TO_SOT_SMD:TO-263-5_TabPin3` for the MIC29302 fallback |
| J1, J2 | `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12` |
| D1, D2 | `Diode_SMD:D_SMA` |
| D3, D4 | `LED_SMD:LED_0603_1608Metric` |
| D5, D6 | per Task 2 |
| CY1 | per Task 2 — through-hole, ≥10 mm pad pitch |
| Y1 | copy v2's crystal footprint |
| 47 µF | `Capacitor_SMD:C_1210_3225Metric` |
| 4.7 µF | `Capacitor_SMD:C_0805_2012Metric` |
| 0.1 µF, 8 pF, all R | `Capacitor_SMD:C_0603_1608Metric` / `Resistor_SMD:R_0603_1608Metric` |

- [ ] **Step 2: Record the mechanical constraints as schematic text**

Add a text block to the sheet so the layout plan inherits them without needing the spec open:

> **v1 LAYOUT CONSTRAINTS — binding**
> 1. Board 50 mm wide (Hammond 1455C slot), 80 mm target, 4 layers, 90 Ω differential pairs.
> 2. ALL COPPER PULLED BACK ≥1 mm (target 2 mm) FROM BOTH LONG EDGES, every layer, full length. The extrusion's aluminium slots grip those edges; edge copper lets the enclosure short GND1 to GND2.
> 3. ESD arrays (U2, U3) within 5 mm of the connector pins they protect. Array GND pin on its own via straight to plane, never daisy-chained. Pair routed in-line through pins 1/3 → 6/4, no stubs.
> 4. Barrier: ≥8.3 mm creepage at U1, routed slot under T1, CY1 the only other crossing. No copper bridges the barrier on any layer.
> 5. ADuM4165 bypass caps within 10 mm total lead length.
> 6. J1 and J2 end-launched, mating faces flush with the outer face of the plastic end panels.

- [ ] **Step 3: Verify every footprint resolves**

```bash
$KCLI sch export netlist --format kicadxml -o /tmp/v1-net.xml "$SCH"
python3 - <<'EOF'
import xml.etree.ElementTree as ET
r = ET.parse('/tmp/v1-net.xml').getroot()
missing = [c.get('ref') for c in r.iter('comp') if not (c.findtext('footprint') or '').strip()]
print("MISSING FOOTPRINTS:", missing or "none")
EOF
```

Expected: `none`.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat(v1/sch): footprint assignment and binding layout constraints"
```

---

### Task 8: MPNs, BOM, and design review

**Files:**
- Modify: `v1/isolator-v1.kicad_sch`
- Create: `docs/superpowers/reviews/2026-07-28-v1-schematic-review.md`

**Interfaces:**
- Produces: an MPN on every BOM line, an exported BOM, and a written review against the spec.

- [ ] **Step 1: Populate MPN properties**

Add an `MPN` property to every component. Reuse v2's MPNs where the part is identical — read them out of `isolator.kicad_sch`. New lines are the LDO, the two TVS diodes, and CY1, all chosen in Task 2.

- [ ] **Step 2: Export the BOM**

```bash
$KCLI sch export bom --fields "Reference,Value,Footprint,MPN" --group-by "Value,Footprint,MPN" \
  -o v1/isolator-v1-bom.csv "$SCH"
```

Confirm every grouped line has an MPN.

- [ ] **Step 3: Run the kicad-happy design review**

```bash
python3 $KH/kicad/scripts/analyze_schematic.py "$SCH" --analysis-dir analysis-v1/
```

Then invoke the `kicad-happy:kicad` skill for a full review of `v1/isolator-v1.kicad_sch`.

- [ ] **Step 4: Check the review against the spec, point by point**

Walk the spec's sections and confirm each is implemented. At minimum:

- Power budget — confirm nothing was added to `ISO_5V` beyond U1 VBUS2, U6, and the indicators, so the ~240 mA port budget still holds.
- ESD — U2 and U3 present with pin 5 on the local VBUS rail; D5/D6 present; CC deliberately unprotected.
- CY1 populated, not DNP.
- Exactly 0.1 µF on `VDD1` and `VDD2`.
- Dedicated Rd per upstream CC pin, dedicated Rp per downstream CC pin.
- `VBUS_HOST` total capacitance ≤10 µF.
- Two ground domains, three permitted crossings.

- [ ] **Step 5: Write the review record**

Create `docs/superpowers/reviews/2026-07-28-v1-schematic-review.md`: the analyzer findings, the spec walk-through with each point marked satisfied or deviated, and any deviation justified. Anything unresolved becomes an explicit open item for the layout plan.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(v1/sch): MPNs, BOM export, schematic design review"
```

---

## Follow-on

PCB layout is a separate plan. It inherits the binding constraints recorded in Task 7 Step 2, starts from the board outline validated in Task 1 Step 5, and ends with the enclosure fit confirmed against a 3D-printed 1455C end panel before any machined panel or fab order.
