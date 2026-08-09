# Rev B Isolated 4-Port Hub — Schematic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the KiCad schematic for the rev B isolated 4-port USB 2.0 hub per `docs/superpowers/specs/2026-08-08-isolated-hub-revb-design.md`, ending with an ERC-clean, footprint-assigned, MPN-populated schematic that passes a design review and whose captured circuit provably matches the spec's power budget.

**Architecture:** USB-C upstream → ADuM4165 (5.7 kV isolation) → USB2514B 4-port hub → 2× USB-A + 2× USB-C. Isolated power from an SN6505B push-pull DC-DC through a center-tapped 5 kV transformer, full-wave rectified, regulated by a switching converter, ORed against an external USB-C supply by a TPS2121 priority mux. New relative to both predecessors: comparators on the host port's CC lines gate `SN6505B.EN` so the board never exceeds the host's advertised current.

**Tech Stack:** KiCad 10, Konnect MCP (all file modifications), `kicad-cli` at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` (not on PATH), kicad-happy analyzers, stock KiCad libraries plus the shared project library `isolator-lib`.

**Scope:** This plan ends at a reviewed schematic. **PCB layout, the two shield footprints' placement, and fabrication are a follow-on plan** — the shield *symbols* and *footprint assignment* are in scope here, their placement and creepage budgeting are not.

## Global Constraints

Copied from the spec — every task implicitly includes these:

- Two ground domains only: `GND1` (host side), `GND2` (isolated side). **No net, wire, or component other than U1 (ADuM4165), T1 (transformer), and CY1 (stitching capacitor) may touch both domains.** This is checked mechanically at the end of every task from Task 5 onward.
- **No signal crosses the barrier.** The CC sense drives `SN6505B.EN`, and both are on GND1. If any task finds itself wanting a GND2→GND1 signal, the design has gone wrong — stop and escalate.
- ADuM4165 bypass: **exactly 0.1 µF** at `VDD1` and `VDD2` — larger disrupts start-up sequencing. 0.1 µF at `VBUS1`/`VBUS2`. Place-close note ≤10 mm total lead length.
- ADuM4165 pins **4, 7 (GND1) and 15, 16, 17 (GND2) are ground-only and are not valid bypass returns** (data sheet Table 12). Side-1 bypass returns via pins 2/10 only; Side-2 via 11/19 only.
- Crystal Y1: 24 MHz, ≤50 ppm total tolerance, ≤100 ppm stability, CL ≈ 10 pF, 8 pF load caps, on **Side 1** (XI1/XO1 — the '4165 has no Side-2 clock input).
- Upstream J1 is a UFP: **5.1 kΩ Rd** from each of CC1 and CC2 to `GND1`. Dedicated resistor per CC pin, never shared.
- External input J2 is a UFP: **5.1 kΩ Rd** per CC pin to `GND2`. Never shared.
- All four downstream USB-C ports advertise **Default USB Power: 56 kΩ Rp** per CC pin to that port's switched VBUS. Dedicated resistor per CC pin. **Do not advertise 1.5 A downstream.**
- Every USB data pair gets a USBLC6-2SC6 in flow-through orientation (in on pins 1/3, out on 6/4), `VBUS` pin 5 tied to that connector's local VBUS rail.
- Each connector's VBUS gets a dedicated unidirectional TVS, V_RWM ≥ 5.5 V.
- CY1 is **populated**, not DNP, and is Y1-rated.
- Upstream `VBUS_HOST` bulk capacitance stays under the USB 2.0 §7.2.4.1 bus-powered limit of 10 µF / 50 µC at hot-plug.
- All symbols placed with `(in_bom yes)`, unique reference designators, and Value/Footprint/MPN properties filled by the end of the plan.

## Working conventions (read once before any task)

**Project location.** This is a fresh design and must not disturb rev A. Work on branch `revb-hub`. The new project lives at the repo root as `hub.kicad_pro` / `hub.kicad_sch` / `hub.kicad_pcb`, sharing `isolator-lib.kicad_sym`, `isolator-lib.pretty`, `sym-lib-table`, and `fp-lib-table` with the rev A project. Rev A's `isolator.*` files are not touched by any task in this plan.

```bash
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
KH=/Users/alex/.claude/plugins/cache/kicad-happy/kicad-happy/2.0.0/skills
SCH=hub.kicad_sch
```

**How edits are made.** **All modifications go through Konnect MCP tools.** KiCad files are serialized object graphs with UUIDs and cross-references; text edits break them. Call `list_toolboxes` first to confirm the server is connected — if it is not, **stop and tell the user**; do not fall back to file editing. Typical sequence: `load_toolset("sch_components")` → `add_schematic_component` / `batch_add_components` → `load_toolset("sch_wiring")` → `batch_connect` / `add_schematic_net_label`.

> **Known issue at plan time:** the Konnect MCP server was disconnected when this plan was written. Reconnect it before Task 1.

**Where to copy parts from, rather than retyping.** Both predecessors contain working, reviewed instances. Lift `lib_symbols` blocks and symbol instances instead of authoring new ones — this is the single largest source of avoided errors.

| Part | Source |
|---|---|
| ADuM4165, USBLC6-2SC6, SN6505BDBV, TPS2553DBV, 750313638, USB-C 16P receptacle, crystal network | either predecessor |
| USB2514B, TPS2121, AP2112K-3.3, TLV7041DBV, USB-A receptacle, power-only USB-C 6P | `4port-archive:hub` — retrieve with `git show 4port-archive:isolator.kicad_sch` |
| TLV76750DGNR | `main:isolator.kicad_sch` |

**Verified pin numbering** (from the rev A netlist — trust these, do not re-derive):

| Part | Pins |
|---|---|
| SN6505BDBV | 1=D1, 2=VCC, 3=D2, 4=GND, 5=EN, 6=CLK |
| TPS2553DBV | 1=IN, 2=GND, 3=EN, 4=~FAULT, 5=ILIM, 6=OUT |
| ADuM4165 | 1=VBUS1, 2=GND1, 3=VDD1, 4=GND1, 5=XI1, 6=XO1, 7=GND1, 8=UD+, 9=UD−, 10=GND1, 11=GND2, 12=DD+, 13=DD−, 14=PGOOD, 15/16/17=GND2, 18=VDD2, 19=GND2, 20=VBUS2 |
| 750313638 | 1=N1, 2=CT1, 3=N2, 4=N4, 5=CT2, 6=N3 |
| USBLC6-2SC6 | 1=I/O1, 2=GND, 3=I/O2, 4=I/O2, 5=VBUS, 6=I/O1 |

For USB2514B, TPS2121, AP2112K, TLV7041, and the buck selected in Task 2, **take pin numbers from the archive symbol or the datasheet** — they are not verified here.

**Verification tools (used in every task):**

```bash
# ERC — also validates the file still parses; must exit 0 at the end of every task
$KCLI sch erc "$SCH" --output /tmp/erc.rpt --severity-error --exit-code-violations; echo "exit=$?"; cat /tmp/erc.rpt

# Netlist — the ground truth for probes
$KCLI sch export netlist --format kicadxml -o /tmp/net.xml "$SCH"
```

**Probe pattern** (fill in the net name per task):

```bash
python3 - <<'EOF'
import xml.etree.ElementTree as ET
r = ET.parse('/tmp/net.xml').getroot()
TARGET = 'ISO_5V'
for n in r.iter('net'):
    if n.get('name').lstrip('/') == TARGET:
        for nd in n.iter('node'):
            print(f"{nd.get('ref')}.{nd.get('pin')} ({nd.get('pinfunction')})")
EOF
```

**Isolation check** — run at the end of every task from Task 5 onward. It must print nothing:

```bash
python3 - <<'EOF'
import xml.etree.ElementTree as ET
r = ET.parse('/tmp/net.xml').getroot()
ALLOWED = {'U1', 'T1', 'CY1'}   # the only parts permitted to bridge domains

nets = {n.get('name').lstrip('/'): {nd.get('ref') for nd in n.iter('node')}
        for n in r.iter('net')}
g1 = set(); g2 = set()
for name, refs in nets.items():
    if name == 'GND1': g1 |= refs
    if name == 'GND2': g2 |= refs
# Walk outward: any part sharing a net with a GND1 part is GND1-side, etc.
def domain(seed):
    seen = set(seed)
    changed = True
    while changed:
        changed = False
        for refs in nets.values():
            if refs & seen and not refs <= seen:
                seen |= refs; changed = True
    return seen
d1 = domain(g1) - ALLOWED
d2 = domain(g2) - ALLOWED
for ref in sorted(d1 & d2):
    print(f"BARRIER VIOLATION: {ref} touches both domains")
EOF
```

**Commit after every task.** Small commits, conventional-commit prefixes, matching the repo's existing style (`feat(revb/sch):`, `fix(revb/sch):`, `docs(revb):`).

---

### Task 1: Project skeleton and library seeding

**Files:**
- Create: `hub.kicad_pro`, `hub.kicad_sch`, `hub.kicad_pcb`
- Modify: `sym-lib-table`, `fp-lib-table` (only if the shared library is not already registered for the new project)

**Interfaces:**
- Produces: an empty, ERC-clean `hub.kicad_sch` with `isolator-lib` resolvable, and the branch `revb-hub`.

- [ ] **Step 1: Create the branch**

```bash
git checkout -b revb-hub
```

- [ ] **Step 2: Confirm Konnect is connected**

Call `list_toolboxes`. If it errors or returns nothing, **stop and tell the user the MCP server needs reconnecting.** Do not proceed with file editing.

- [ ] **Step 3: Create the project**

Use `load_toolset("project")` then `create_project` with path `hub` at the repo root. Then `create_schematic` for `hub.kicad_sch`.

- [ ] **Step 4: Register the shared libraries**

Confirm `isolator-lib` resolves for the new project. Use `load_toolset("library")` then `list_symbol_libraries` — `isolator-lib` must appear. If not, `register_symbol_library` pointing at `isolator-lib.kicad_sym`, and `register_footprint_library` at `isolator-lib.pretty`.

- [ ] **Step 5: Verify**

```bash
$KCLI sch erc hub.kicad_sch --output /tmp/erc.rpt --severity-error --exit-code-violations; echo "exit=$?"
```

Expected: exit 0 on an empty sheet. Confirm `git status` shows rev A's `isolator.*` files unmodified.

- [ ] **Step 6: Commit**

```bash
git add hub.kicad_pro hub.kicad_sch hub.kicad_pcb sym-lib-table fp-lib-table
git commit -m "feat(revb): project skeleton on shared isolator-lib"
```

---

### Task 2: Part selection — buck topology, 3.3 V rail, comparators

**Files:**
- Create: `docs/superpowers/reviews/2026-08-08-revb-part-selection.md`

**Interfaces:**
- Produces: resolved MPNs and pin tables for the post-rectifier converter, the hub's 3.3 V rail, and the CC comparator. Tasks 4, 5, and 7 consume these.

This task closes the spec's two Open Decisions and resolves one part the spec assumed without verifying. It writes a decision record; it does not touch the schematic.

- [ ] **Step 1: Resolve the post-rectifier converter topology**

This is the hardest part selection on the board and the spec understates it. Work the numbers before shopping:

`DCDC_RAW` comes from a 1:1.3 center-tapped secondary, full-wave rectified through one Schottky drop. Nominal unloaded ≈ 6.15 V. Rev A measured/estimated ≈ 5.8 V at 315 mA. **This design draws 625 mA**, so expect further sag from winding DCR — budget for `DCDC_RAW` as low as **≈5.4 V under full load**.

Against a 5.0 V output that is a duty cycle of 5.0 / 5.4 ≈ **93%**. Most bucks cannot hold that; many are specified to 90–95% max duty and degrade badly near the limit, and dropout at 625 mA is set by the high-side switch R_DS(on).

Evaluate three topologies and record the reasoning:

| Topology | Fits? | Note |
|---|---|---|
| Standard synchronous buck | marginal | Only if the part explicitly supports 100% duty / low-dropout mode. Check the *dropout voltage at 700 mA*, not the duty cycle spec. |
| Buck-boost | yes | Handles `DCDC_RAW` above **and** below 5.0 V, which is the real operating condition. Costs an extra inductor pin count and some efficiency. |
| Raise the turns ratio instead | maybe | A higher-ratio transformer restores buck headroom, but changes T1 — a part already footprinted, sourced, and barrier-qualified. Treat as a fallback, not a first choice. |

Requirements for the chosen part: **≥700 mA continuous at 5.0 V**, input range covering 5.2–6.4 V, and a footprint that fits under Shield B (`BMI-S-209-F`, 29.36 × 18.50 mm internal, 7.00 mm height) together with its inductor and input/output caps.

- [ ] **Step 2: Decide the hub's 3.3 V rail**

The USB2514B draws ~155 mA at 3.3 V **(unverified — confirm against the datasheet in this step)**. An LDO passes that straight through from `ISO_5V`; a 90% buck draws 155 × 3.3 ÷ (5 × 0.90) ≈ 114 mA. The difference is 41 mA of port budget.

**Decision rule:** compute the port budget with the Step 1 converter's actual efficiency figure. If the result is below 450 mA, take the buck. If at or above, take the LDO (`AP2112K-3.3`, already in the archive) and bank the simplicity. Record which branch was taken and the number that decided it.

- [ ] **Step 3: Verify the comparator's output structure**

The spec and the archived design both assume `TLV7041DBV` is **open-drain**, because the design wire-ORs two of them onto one net. Open the datasheet and confirm. If it is push-pull, the wire-OR is a short between two driven outputs and the part must change — `TLV7031` and `TLV7041` differ in exactly this respect and are easy to transpose.

Four comparators are needed in total: two on the upstream CC lines (Task 4) and two on the external input's CC lines (Task 6). Decide singles vs a dual (`TLV7042`-class) on footprint area, and record the pin table for whichever is chosen.

- [ ] **Step 4: Check stock and write the record**

For every part resolved above, capture MPN, distributor, stock, and price. Anything under ~1000 in stock gets flagged in the record as a sourcing risk.

Write `docs/superpowers/reviews/2026-08-08-revb-part-selection.md` containing: the topology decision and its arithmetic, the 3.3 V branch taken and the number that decided it, the comparator output-structure finding, pin tables for every new part, and the stock survey.

- [ ] **Step 5: Verify**

Read the record back. Every part must have an MPN, a pin table, and a stock figure. No entry may say "TBD".

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/reviews/2026-08-08-revb-part-selection.md
git commit -m "docs(revb): part selection — converter topology, 3V3 rail, comparators"
```

---

### Task 3: Upstream host section (GND1 domain)

**Files:**
- Modify: `hub.kicad_sch`

**Interfaces:**
- Consumes: nothing.
- Produces: nets `VBUS_HOST`, `GND1`, `HOST_D+`, `HOST_D−`, `VDD1`, `CC1_HOST`, `CC2_HOST`; components J1, U1, U2, Y1, R1, R2.

- [ ] **Step 1: Copy the symbol definitions**

Lift `Connector:USB_C_Receptacle_USB2.0_16P`, `Isolator:ADUM4165`, `Power_Protection:USBLC6-2SC6`, and `Device:Crystal` from `main:isolator.kicad_sch`.

- [ ] **Step 2: Place and wire**

New parts: J1 (USB-C 16P, HOST), U1 (ADuM4165), U2 (USBLC6-2SC6), Y1 (24 MHz), R1/R2 (5.1 kΩ), C1 (0.1 µF), C2 (4.7 µF), C3 (0.1 µF VBUS1), C4 (0.1 µF VDD1), C5/C6 (8 pF), D1 (TVS).

| Connection | Notes |
|---|---|
| J1.A4/A9/B4/B9 (VBUS) → `VBUS_HOST` | |
| J1.A1/A12/B1/B12/SH → `GND1` | |
| J1.A5 (CC1) → `CC1_HOST`; R1 5.1 kΩ → `GND1` | **dedicated resistor** |
| J1.B5 (CC2) → `CC2_HOST`; R2 5.1 kΩ → `GND1` | **dedicated resistor** |
| J1.A6/B6 (D+) → U2.3, U2.4 | flow-through in |
| J1.A7/B7 (D−) → U2.1, U2.6 | flow-through in |
| U2.5 (VBUS) → `VBUS_HOST`; U2.2 → `GND1` | |
| U2 out → `HOST_D+` → U1.8; `HOST_D−` → U1.9 | |
| U1.1 (VBUS1) ← `VBUS_HOST`; C3 0.1 µF → `GND1` | return via pins 2/10 **only** |
| U1.3 (VDD1) → `VDD1`; C4 **exactly** 0.1 µF → `GND1` | return via pins 2/10 **only** |
| U1.2, U1.10 → `GND1` | bypass returns |
| U1.4, U1.7 → `GND1` | ground-only, **no bypass here** |
| U1.5 (XI1) ↔ Y1.1; U1.6 (XO1) ↔ Y1.3; C5/C6 8 pF → `GND1`; Y1.2/Y1.4 → `GND1` | |
| D1 TVS on `VBUS_HOST` → `GND1`; C1 0.1 µF, C2 4.7 µF → `GND1` | |

`CC1_HOST` and `CC2_HOST` are given explicit net labels because Task 4 taps them. Rev A left them as auto-named `Net-(J1-CC1)`, which is harder to probe and easier to mis-wire.

- [ ] **Step 3: Confirm the upstream capacitance budget**

Sum every capacitor on `VBUS_HOST`. At this point: C1 (0.1 µF) + C2 (4.7 µF) + C3 (0.1 µF). Confirm ≤10 µF, and note the running total — Task 5 adds the SN6505B's bypass to the same net and must not breach it.

- [ ] **Step 4: Verify**

Run ERC and export the netlist. Expected: ERC exit 0. Probe `VBUS_HOST` contains J1's four VBUS pins, U1.1, U2.5, C1, C2, C3, D1. Probe `VDD1` contains U1.3 and C4 and **nothing else**. Probe `CC1_HOST` contains exactly J1.A5 and R1.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(revb/sch): upstream USB-C, ESD, ADuM4165 Side 1, crystal"
```

---

### Task 4: Upstream CC current sensing (GND1 domain) — new circuit

**Files:**
- Modify: `hub.kicad_sch`

**Interfaces:**
- Consumes: `CC1_HOST`, `CC2_HOST`, `VBUS_HOST`, `GND1` from Task 3; the comparator resolved in Task 2.
- Produces: net `HOST_PWR_OK`, consumed by Task 5 as `SN6505B.EN`.

This circuit exists in neither predecessor. It is the reason the board can draw more than 500 mA.

- [ ] **Step 1: Place the reference divider**

R3 / R4 divide `VBUS_HOST` down to **0.66 V** — the Type-C sink threshold for a 1.5 A source advertisement. With a 5 V rail: R3 = 66.5 kΩ (top), R4 = 10.2 kΩ (bottom) gives 0.664 V. Both **1%**.

**The reference must come off `VBUS_HOST`, not off any isolated rail or anything downstream of `HOST_PWR_OK`.** The comparison result is what starts the converter; a reference derived from the converter's output is a latch-up by construction. This is the single most important constraint in the task.

Add C7 (0.1 µF) across R4 to keep the reference quiet.

- [ ] **Step 2: Place the two comparators**

U3 and U4 (or one dual, per Task 2). Non-inverting input ← `CC1_HOST` / `CC2_HOST` respectively. Inverting input ← the 0.66 V reference node. Supply ← `VBUS_HOST`, with a 0.1 µF bypass each (C8, C9) to `GND1`.

Both CC lines must be sensed. Only the one mated to the cable's CC wire sees the source's Rp; the other sees VCONN or nothing, and which is which depends on plug orientation.

- [ ] **Step 3: Wire-OR the outputs**

Tie both outputs to `HOST_PWR_OK` with R5 (100 kΩ) pulling **up** to `VBUS_HOST`.

Note the polarity carefully: open-drain outputs pull **low** when their input exceeds the threshold, so a naive wire-OR gives an active-low "≥1.5 A detected". `SN6505B.EN` is active-**high**. Choose one:

- Swap the comparator inputs (invert at the comparator) so the output floats high on detection and the pull-up asserts `HOST_PWR_OK` — **preferred**, costs nothing.
- Or add an inverting NMOS stage — costs two parts.

Record which was taken in a schematic text note beside the circuit. Getting this backwards produces a board that runs the converter **only** on hosts that cannot feed it.

- [ ] **Step 4: Add the host-side status LED**

D2 (LED) + R6 (series, ~1 mA off 5 V ⇒ 3.3 kΩ for a 1.7 V-Vf part) indicating **insufficient host power**, driven from `HOST_PWR_OK`. Its whole purpose is to explain the otherwise-silent "Default host, no external supply" state, so it must light when `HOST_PWR_OK` is **de**asserted. If that needs a second inverting stage, add it — the diagnostic is worth two parts.

- [ ] **Step 5: Add the design notes as schematic text**

Place a text block beside the circuit recording:
- the 0.66 V threshold and why (Type-C 1.5 A detection point),
- that the reference must stay on `VBUS_HOST`,
- that on an e-marked cable one CC line carries VCONN at 5 V and reads as a false high — benign under the wire-OR because VCONN only appears alongside high-current-capable sources,
- the polarity choice from Step 3.

Rev A demonstrated that constraints not written into the schematic get violated at layout.

- [ ] **Step 6: Verify**

Run ERC and export the netlist. Expected: ERC exit 0. Probe `HOST_PWR_OK` contains both comparator outputs, R5, and nothing on GND2. Probe `CC1_HOST` now contains J1.A5, R1, and one comparator input — **three nodes, no more**. Confirm by inspection that no node of this circuit touches `GND2` or any isolated net.

- [ ] **Step 7: Commit**

```bash
git commit -am "feat(revb/sch): upstream CC current-advertisement sensing"
```

---

### Task 5: Isolated converter and 5 V rail (GND2 domain)

**Files:**
- Modify: `hub.kicad_sch`

**Interfaces:**
- Consumes: `VBUS_HOST`, `GND1`, `HOST_PWR_OK` from Tasks 3–4; the converter resolved in Task 2.
- Produces: nets `DCDC_RAW`, `DCDC_5V`, `GND2`.

- [ ] **Step 1: Place and wire the push-pull DC-DC**

New parts: U5 (SN6505BDBV), T1 (750313638), D3/D4 (SS34), C10 (0.1 µF), C11 (4.7 µF), C12 (4.7 µF centre-tap), C13 (47 µF), C14 (0.1 µF).

| Connection | Notes |
|---|---|
| U5.2 (VCC) ← `VBUS_HOST`; C10 0.1 µF + C11 4.7 µF → `GND1` | C11 is the datasheet's mandatory ≥4.7 µF low-ESR VCC bulk |
| **U5.5 (EN) ← `HOST_PWR_OK`** | **the change from both predecessors, which tied EN to VBUS** |
| U5.4 (GND) → `GND1`; U5.6 (CLK) → `GND1` | CLK low selects the internal oscillator |
| U5.3 (D2) → T1.1 (N1); U5.1 (D1) → T1.3 (N2) | push-pull drive |
| T1.2 (CT1) ← `VBUS_HOST`; C12 4.7 µF → `GND1` | primary centre tap — a **separate** requirement from the VCC bulk |
| T1.6 (N3) → D3 anode; T1.4 (N4) → D4 anode | |
| D3 cathode, D4 cathode → `DCDC_RAW` | **side by side, not in series** |
| T1.5 (CT2) → `GND2` | secondary centre tap is the GND2 reference |
| C13 47 µF + C14 0.1 µF | `DCDC_RAW` → `GND2` |

- [ ] **Step 2: Place the converter from Task 2**

U6, wired `DCDC_RAW` → `DCDC_5V`, ground `GND2`, with the input/output capacitors and inductor its datasheet requires. Pin numbers come from the Task 2 record.

Output net is **`DCDC_5V`, not `ISO_5V`** — the mux in Task 6 produces `ISO_5V`. Conflating them is the mistake that makes the mux a no-op.

- [ ] **Step 3: Re-confirm the upstream capacitance budget**

`VBUS_HOST` now carries Task 3's C1+C2+C3 plus C10, C11, C12. Sum them. Must stay ≤10 µF. If over, reduce C12 first — the centre-tap bulk has more latitude than the SN6505B's VCC bypass or the ADuM4165's.

- [ ] **Step 4: Verify**

Run ERC, export the netlist, and run the **isolation check**. Expected: ERC exit 0; isolation check prints nothing; probe `DCDC_RAW` contains D3, D4 cathodes, C13, C14, and the converter input; probe `GND2` contains T1.5, C13, C14, and the converter ground. Probe `HOST_PWR_OK` now additionally contains U5.5.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(revb/sch): SN6505B isolated DC-DC gated by host CC sense"
```

---

### Task 6: External supply input and priority mux (GND2 domain)

**Files:**
- Modify: `hub.kicad_sch`

**Interfaces:**
- Consumes: `DCDC_5V`, `GND2` from Task 5; the comparator from Task 2.
- Produces: net `ISO_5V` — the rail every remaining task draws from.

- [ ] **Step 1: Place the external input**

J2 (power-only USB-C 6P), R7/R8 (5.1 kΩ Rd, one per CC pin, to `GND2`), D5 (TVS on `EXT_5V` → `GND2`), C15 (bulk). Net `EXT_5V`.

- [ ] **Step 2: Place the 3 A detect comparators**

U7, U8 (per Task 2), threshold **1.23 V** — the Type-C 3.0 A detection point, distinct from Task 4's 1.5 A threshold. Divider R9/R10 off `EXT_5V`. Outputs wire-ORed to `EXT_3A_DET` with a 100 kΩ pull-up.

- [ ] **Step 3: Place the TPS2121 mux — wire CP2 and PR1 per the Task 2 record**

U9 (TPS2121). IN1 ← `EXT_5V`, IN2 ← `DCDC_5V`, OUT → `ISO_5V`.

**CORRECTED 2026-08-08 (human ruling: datasheet governs).** An earlier version of
this step said "CP2 must be driven by `EXT_3A_DET`, not grounded." **That was
wrong** and would have produced the opposite of the intended behaviour. Per
SLVSEA3F Table 9-3, `CP2` high with `PR1` low selects **IN2** — the converter — so
driving CP2 from the detect makes the board ignore an external supply exactly when
it has been confirmed good, and fall into VCOMP mode when it has not.

The behavioural goal is unchanged and still correct: **no 3 A ⇒ OUT = IN2; 3 A
detected ⇒ OUT = IN1.**

**Take the actual CP2/PR1 arrangement, divider values, and pin numbers from the
Task 2 decision record** (`docs/superpowers/reviews/2026-08-08-revb-part-selection.md`,
§4.2 and the §6 handoff), which was verified against SLVSEA3F on review. In outline:
CP2 is biased to a fixed level above V_REF and the 3 A detect drives PR1 above that
bias, so no detect gives Table 9-3's deterministic IN2 row rather than VCOMP. The
2N7002 inverter still produces the right active-high sense; it lands on PR1.

Do not re-derive this from the archive symbol — the archive is where the original
error came from. The record also states the switchback threshold; carry it into a
schematic text note so bring-up can measure it.

- [ ] **Step 4: Add the source-indication LED**

D6 + R11 off the TPS2121 `ST` status pin, indicating external-supply-selected. Because selection implies the 3 A detect passed, "external present but locked out" reads as this LED off.

- [ ] **Step 5: Add a schematic text note**

Record the CP2 rule and *why* — this is a bug that was already found once, in a different project, and the reasoning does not survive in the netlist.

- [ ] **Step 6: Verify**

Run ERC, export the netlist, run the **isolation check**. Expected: ERC exit 0; isolation check prints nothing; probe `ISO_5V` contains the TPS2121 output and nothing else yet; probe `DCDC_5V` contains the converter output and the TPS2121 IN2 pin **only** — if it contains any load, the mux has been bypassed.

- [ ] **Step 7: Commit**

```bash
git commit -am "feat(revb/sch): external USB-C input, 3A detect, TPS2121 priority mux"
```

---

### Task 7: ADuM Side 2, hub, and the 3.3 V rail (GND2 domain)

**Files:**
- Modify: `hub.kicad_sch`

**Interfaces:**
- Consumes: `ISO_5V`, `GND2` from Task 6; the 3.3 V part from Task 2.
- Produces: nets `VDD2`, `ISO_3V3`, `PORT_D+`/`PORT_D−` (hub upstream), `PRTPWR1..4`, `OCS1..4`.

- [ ] **Step 1: Wire ADuM4165 Side 2**

| Connection | Notes |
|---|---|
| U1.20 (VBUS2) ← `ISO_5V`; C16 0.1 µF → `GND2` | return via pins 11/19 **only** |
| U1.18 (VDD2) → `VDD2`; C17 **exactly** 0.1 µF → `GND2` | return via pins 11/19 **only** |
| U1.11, U1.19 → `GND2` | bypass returns |
| U1.15, U1.16, U1.17 → `GND2` | ground-only, **no bypass here** |
| U1.12 (DD+) → `PORT_D+`; U1.13 (DD−) → `PORT_D−` | to the hub's upstream port |
| U1.14 (PGOOD) → `PGOOD2` | drives the indicator in Step 2 |

- [ ] **Step 2: Place the PGOOD indicator**

`PGOOD2` must not be left dangling. Drive D11 (LED) + R19 (series, ~1 mA off 5 V) from it through Q2 (2N7002) as a level-shift buffer to `ISO_5V`, with R20 (100 kΩ) gate pull-down so Q2 parks off if the PGOOD output structure turns out to be open-drain.

This is lifted verbatim from rev A, where the pull-down was added precisely because the ADuM4165 datasheet does not specify PGOOD's output structure.

- [ ] **Step 3: Place the 3.3 V rail**

U10, per the Task 2 decision — either `AP2112K-3.3` or the buck. Input `ISO_5V`, output `ISO_3V3`, ground `GND2`, with the input/output capacitors its datasheet requires.

- [ ] **Step 4: Place the hub**

U11 (USB2514B, QFN-36). Lift the symbol from the archive.

- 3.3 V supply from `ISO_3V3`, decoupled per datasheet.
- Internal 1.8 V core regulator: CRFILT capacitor to `GND2`.
- Own 24 MHz crystal Y2 with its load caps (the archive used 12 pF — confirm against the USB2514B datasheet, which specifies a different CL from the ADuM4165's crystal).
- RBIAS 12 kΩ to `GND2`, **1%**.
- Strap configuration, no SMBus/EEPROM. Take the strap pin states from the archive.
- Upstream port ← `PORT_D+` / `PORT_D−`.
- `PRTPWR1..4` and `OCS1..4` brought out as labelled nets for Task 8.

- [ ] **Step 5: Verify**

Run ERC, export the netlist, run the **isolation check**. Expected: ERC exit 0; isolation check prints nothing; probe `VDD2` contains U1.18 and C17 and **nothing else**; probe `ISO_3V3` contains U10's output and the hub's supply pins; probe `PORT_D+` contains exactly U1.12 and the hub's upstream D+ pin.

- [ ] **Step 6: Commit**

```bash
git commit -am "feat(revb/sch): ADuM4165 Side 2, USB2514B hub, 3V3 rail"
```

---

### Task 8: Four port switches, connectors, and per-port ESD (GND2 domain)

**Files:**
- Modify: `hub.kicad_sch`

**Interfaces:**
- Consumes: `ISO_5V`, `ISO_3V3`, `GND2`, `PRTPWR1..4`, `OCS1..4` from Task 7.
- Produces: nets `PORT1_VBUS`..`PORT4_VBUS`, and the four downstream data pairs.

This task is four near-identical blocks. Build **one** completely, verify it, then replicate — do not build all four and then debug.

- [ ] **Step 1: Compute the ILIM resistor**

Per port, from **all three** of SLVS841F's min/typ/max equations — not by scaling the nominal.

Rev A set 93.1 kΩ for a 286 mA nominal and ended up with a guaranteed *minimum* trip point (252 mA) **above** what its supply could deliver (~240 mA), so the FAULT path could never assert on a real overload. Do not repeat that: choose R_ILIM so `I_OS(min)` sits **above** the intended per-port current and `I_OS(max)` sits **below** what the external supply can deliver.

Target per-port current is 500 mA (external-supply mode). Record the three computed values in a schematic text note next to the switches.

- [ ] **Step 2: Build port 1 completely**

U12 (TPS2553DBV), R12 (ILIM), J3 (USB-A), U16 (USBLC6-2SC6), D7 (TVS), C18 (0.1 µF in), C19 (22 µF out), C20 (0.1 µF out).

| Connection | Notes |
|---|---|
| U12.1 (IN) ← `ISO_5V`; C18 0.1 µF → `GND2` | |
| U12.3 (EN) ← `PRTPWR1` | hub-controlled, **not** tied high |
| U12.5 (ILIM) → R12 → `GND2` | value from Step 1 |
| U12.4 (~FAULT) → `OCS1` | reported to the hub |
| U12.6 (OUT) → `PORT1_VBUS`; C19 22 µF + C20 0.1 µF → `GND2` | |
| U16 flow-through on the pair; U16.5 ← `PORT1_VBUS`; U16.2 → `GND2` | |
| D7 TVS on `PORT1_VBUS` → `GND2` | |
| J3 VBUS ← `PORT1_VBUS`; J3 GND/shell → `GND2` | USB-A has no CC pins |

- [ ] **Step 3: Verify port 1 before replicating**

Run ERC and probe `PORT1_VBUS` — it must contain U12.6, C19, C20, D7, U16.5, and J3's VBUS pin. Probe `OCS1` — exactly U12.4 and the hub pin. Only once this is clean, continue.

- [ ] **Step 4: Replicate for ports 2, 3, 4**

Port 2 is the second USB-A (J4) and is identical to port 1. Ports 3 and 4 are USB-C (J5, J6) and add **two 56 kΩ Rp resistors each** — one per CC pin, to that port's switched VBUS, never shared:

| Port 3 (J5) | Port 4 (J6) |
|---|---|
| J5.A5 (CC1) → R15 56 kΩ → `PORT3_VBUS` | J6.A5 (CC1) → R17 56 kΩ → `PORT4_VBUS` |
| J5.B5 (CC2) → R16 56 kΩ → `PORT3_VBUS` | J6.B5 (CC2) → R18 56 kΩ → `PORT4_VBUS` |

Reference designators across the four blocks: switches U12–U15, ESD arrays U16–U19, ILIM resistors R12–R14 continuing from port 1's R12, Rp resistors R15–R18, TVS D7–D10, capacitors continuing from C21.

**56 kΩ = Default USB Power.** Do not fit 22 kΩ — advertising 1.5 A downstream when bus-powered ports share ~390 mA is exactly the mismatch that produced rev A's brown-out behaviour.

- [ ] **Step 5: Verify**

Run ERC, export the netlist, run the **isolation check**. Expected: ERC exit 0; isolation check prints nothing. Probe each of `PORT1_VBUS`..`PORT4_VBUS` and confirm the same node pattern. Confirm each `OCS1..4` and `PRTPWR1..4` has exactly two nodes.

- [ ] **Step 6: Commit**

```bash
git commit -am "feat(revb/sch): four TPS2553 port switches, 2x USB-A + 2x USB-C, per-port ESD"
```

---

### Task 9: Stitching capacitor, PWR_FLAGs, and ERC zero

**Files:**
- Modify: `hub.kicad_sch`

**Interfaces:**
- Consumes: everything.
- Produces: an ERC-clean schematic with zero warnings.

- [ ] **Step 1: Place CY1**

CY1, 1 nF **Y1-rated**, 400 VAC, between `GND1` and `GND2`. Populated, not DNP.

This is the only intentional connection between the two grounds and gives GND2's ESD current a defined return path instead of forcing it through the ADuM4165 die. It is **not** a decoupling capacitor and must not be substituted with a non-safety-rated part — record that in its `Description` property.

- [ ] **Step 2: Add PWR_FLAGs**

One per independently-driven power net that ERC cannot otherwise resolve: `VBUS_HOST`, `EXT_5V`, `GND1`, `GND2`. Per the repo's schematic-layout convention, PWR_FLAGs go in a corner block, not scattered.

- [ ] **Step 3: Drive ERC to zero**

Run ERC and resolve **every** warning, not just errors. Genuine no-connects get explicit no-connect flags (`batch_add_no_connects`) rather than being suppressed.

- [ ] **Step 4: Verify**

```bash
$KCLI sch erc "$SCH" --output /tmp/erc.rpt --severity-all --exit-code-violations; echo "exit=$?"; cat /tmp/erc.rpt
```

Expected: exit 0 with `--severity-all`, not just `--severity-error`. Run the isolation check — must print nothing, and CY1 must be the only new part in the allowed set.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(revb/sch): barrier stitching cap, PWR_FLAGs, ERC zero"
```

---

### Task 10: Power budget audit against the captured schematic

**Files:**
- Create: `docs/superpowers/reviews/2026-08-08-revb-power-budget.md`

**Interfaces:**
- Consumes: the complete schematic and the Task 2 record.

The spec's budget was written before any part was chosen. This task checks the *captured* design against it — the point where an optimistic assumption becomes a discoverable error rather than a bring-up surprise.

- [ ] **Step 1: Rebuild the budget from actual parts**

Recompute the bus-powered chain using the Task 2 converter's real efficiency curve at **625 mA output**, the real quiescent currents of every isolated-side part now in the netlist, and the 3.3 V branch actually taken:

```
SN6505B primary (800 mA @ 5 V)                = 4.00 W
ADuM4165 Side 1                               = 0.35 W
  → drawn from host                           = 4.35 W ≈ 870 mA
transformer + rectifier (× η_xfmr)            = ? W at DCDC_RAW
converter (× η_conv from the real datasheet)  = ? W at ISO_5V
  less ADuM4165 Side 2                        = −70 mA
  less USB2514B (via the chosen 3V3 path)     = −? mA
  less indicators (count them in the netlist) = −? mA
  = shared across four ports                  = ? mA
```

- [ ] **Step 2: Compare against the spec and act on the gap**

The spec claims ≈390 mA shared, on an 85% transformer figure **inherited from a 300 mA operating point** while this design runs the primary at 800 mA. If the recomputed figure lands materially below 390 mA, do not silently accept it. Apply the spec's documented levers in order:

1. 3.3 V buck instead of LDO, if Task 2 took the LDO (+41 mA)
2. SN6505B at 900 mA primary instead of 800 mA (+79 mA), spending margin against the 1 A rating

If both levers still leave the figure short, **stop and escalate** — the port count or the converter topology needs revisiting, and that is a spec change, not an implementation choice.

- [ ] **Step 3: Confirm the upstream draw against the advertisement**

Total host-side draw must sit comfortably inside 1.5 A, with headroom for transient load. If it exceeds ~1.2 A, the CC threshold in Task 4 should move to the 3 A detection point (1.23 V) instead of 1.5 A (0.66 V) — which changes which hosts the board works on and must be recorded.

- [ ] **Step 4: Verify**

The record must state a single number for shared port current, the efficiency figures it rests on, whether each came from a datasheet or remains an estimate, and which levers were applied.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/reviews/2026-08-08-revb-power-budget.md
git commit -m "docs(revb): power budget audit against the captured schematic"
```

---

### Task 11: Footprint assignment, including the two shield frames

**Files:**
- Modify: `hub.kicad_sch`
- Create: `isolator-lib.pretty/BMI-S-201-F.kicad_mod`, `isolator-lib.pretty/BMI-S-209-F.kicad_mod`

**Interfaces:**
- Produces: every symbol with a resolvable `Footprint` property.

- [ ] **Step 1: Assign footprints to everything reusable**

Lift assignments from the two predecessors wherever the part is shared — ADuM4165 (`isolator-lib:ADI_SOIC_IC_20_RI-20-1`), 750313638 (`isolator-lib:WE_750313638`), CY1 (`isolator-lib:C_Disc_D7.0mm_W5.5mm_P14.00mm`), the USB-C receptacles, USBLC6, SN6505B, TPS2553.

- [ ] **Step 2: Build the two shield frame footprints**

Create `BMI-S-201-F` (13.66 × 12.70 mm) and `BMI-S-209-F` (29.36 × 18.50 mm) from **Laird's published pad patterns** — do not estimate the fence geometry from the overall dimensions.

Both are frames for a two-piece shield: the frame solders at assembly, the cover snaps on after bring-up. Give each a `Description` recording:
- which domain its fence sits on (**A on GND1, B on GND2**),
- that the fence is live copper carrying the full **≥8.3 mm creepage obligation** to the opposite domain,
- that the two shields must never be merged into one part spanning T1.

The covers (`BMI-S-201-C`, `BMI-S-209-C`) are optional stock and get no footprint — they snap onto the frames.

- [ ] **Step 3: Add the shield symbols to the schematic**

Two mechanical symbols so the frames appear in the BOM and the netlist. Each gets its fence net tied to its own ground — Shield A to `GND1`, Shield B to `GND2`. **Never both.**

- [ ] **Step 4: Verify**

```bash
$KCLI sch export netlist --format kicadxml -o /tmp/net.xml "$SCH"
python3 - <<'EOF'
import xml.etree.ElementTree as ET
r = ET.parse('/tmp/net.xml').getroot()
missing = [c.get('ref') for c in r.iter('comp')
           if not (c.findtext('footprint') or '').strip()]
print("missing footprints:", missing or "none")
EOF
```

Expected: `none`. Then run the **isolation check** — the two shield symbols must not appear as violations, which they will if either was tied to both grounds.

- [ ] **Step 5: Commit**

```bash
git add isolator-lib.pretty/BMI-S-201-F.kicad_mod isolator-lib.pretty/BMI-S-209-F.kicad_mod hub.kicad_sch
git commit -m "feat(revb): footprint assignment and two-piece RF shield frames"
```

---

### Task 12: MPNs, BOM, and design review

**Files:**
- Modify: `hub.kicad_sch`
- Create: `hub-bom.csv`, `docs/superpowers/reviews/2026-08-08-revb-schematic-review.md`

- [ ] **Step 1: Populate MPN properties**

Every `in_bom` symbol gets an MPN. Carry the rev A sourcing pass forward where parts are shared, and take the new parts from the Task 2 record.

Flag as hand-solder / excluded from JLC assembly anything not in the JLC library — rev A found the ADuM4165 and T1 both fall in this category, and the ADuM4165 was the long-lead part that gated the whole build. **Check ADuM4165 lead time early**; it was backordered at Mouser and zero-stock at DigiKey during rev A.

- [ ] **Step 2: Export the BOM**

```bash
$KCLI sch export bom --output hub-bom.csv "$SCH"
```

- [ ] **Step 3: Run the design review**

```bash
python3 $KH/kicad/scripts/analyze_schematic.py "$SCH" --analysis-dir analysis/
```

Resolve every finding or record why it is accepted.

- [ ] **Step 4: Review against the spec by hand**

Walk the spec section by section and confirm each requirement appears in the schematic. Pay particular attention to the constraints that exist because something already went wrong once:

- ADuM4165 pins 4/7/15/16/17 carry no bypass capacitance
- TPS2121 CP2 is **driven**, not grounded
- `SN6505B.EN` comes from `HOST_PWR_OK`, and the polarity is right
- the CC reference divider sits on `VBUS_HOST`
- all four downstream ports advertise 56 kΩ, not 22 kΩ
- `DCDC_5V` feeds only the mux, never a load directly
- exactly 0.1 µF at `VDD1` and `VDD2`
- CY1 is the only part besides U1 and T1 touching both domains

- [ ] **Step 5: Write the review record**

`docs/superpowers/reviews/2026-08-08-revb-schematic-review.md`: findings, resolutions, accepted deviations, the sourcing risk list, and any spec requirement deliberately not implemented.

- [ ] **Step 6: Verify**

ERC exit 0 at `--severity-all`. Isolation check prints nothing. No symbol missing MPN or footprint. Design review has no unresolved findings.

- [ ] **Step 7: Commit**

```bash
git add hub.kicad_sch hub-bom.csv docs/superpowers/reviews/2026-08-08-revb-schematic-review.md
git commit -m "feat(revb/sch): MPNs, BOM export, schematic design review"
```

---

## Follow-on

Not in this plan, in dependency order:

1. **PCB layout** — its own plan. Board outline and enclosure selection, barrier geometry (≥8.3 mm creepage, routed slot under T1), the two shield frames' placement **and their fence creepage budget**, 90 Ω length-matched pairs for five USB segments, 4-layer stack with pours on both outer layers and 4 mm via stitching, edge-copper rules sized to the plastic box's standoffs.
2. **Enclosure selection** — deferred deliberately; nothing electrical depends on it. Needs the board outline first.
3. **Fabrication** — Gerbers, CPL, JLC assembly with the hand-solder exclusions from Task 12.
4. **Bring-up** — the spec's 10-step verification plan, which is bench work and has no schematic-phase equivalent. Two of its steps are gates rather than checks and should be scheduled first: **step 2** (measure the actual CC voltage on the target MacBook, a legacy USB-A-to-C cable, and a bus-powered hub — do not infer it) and **step 3** (converter efficiency at 800 mA primary, not 300 mA). Step 3 validates or invalidates the entire power budget; if it comes in materially below 85%, Task 10's levers get spent for real and the port figure moves.

Two spec items are deliberately carried into layout rather than resolved here:

- **Shield fence creepage** is the item most likely to cause grief. Each can's fence is live copper on its own domain carrying the full ≥8.3 mm obligation, so the cans must sit back from the barrier in the most congested part of the board. If it does not fit, Shield A shrinks before the barrier moves.
- **T1's leakage field is unshielded by necessity** and no layout choice changes that. Loop area, the stitching grid, and CY1 are the controls.
