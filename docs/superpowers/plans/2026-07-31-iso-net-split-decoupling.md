# Isolated-Side Net Split and Decoupling Ownership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `/ISO_5V`, `/DCDC_RAW` and `/PORT_VBUS` into per-owner branch nets joined by three KiCad net ties, add the two missing decoupling capacitors, and record every capacitor's owning pin as a `Description` property — all in the schematic, leaving the board untouched.

**Architecture:** Connectivity in this schematic is carried entirely by local net labels, so splitting a net means renaming a subset of its labels and inserting a net-tie symbol that rejoins the branches at one defined point. Each task splits exactly one net end-to-end (rename labels, add tie, add any PWR_FLAG the branch now needs) so that ERC is green at every commit. A new gate script asserts net membership node-by-node; it is written first and watched to fail.

**Tech Stack:** KiCad 10.0.5. `kicad-cli` at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` (**not** on PATH). System `python3` is fine for every script here — none of them import `pcbnew`. Schematic edits use the `kicad` MCP server's tools (`mcp__kicad__add_schematic_component`, `add_schematic_wire`, `add_schematic_net_label`, `set_schematic_component_property`) plus one purpose-built label-rename script.

## Global Constraints

Every task implicitly includes these.

- **The board is never edited.** `isolator.kicad_pcb` must be byte-identical at the end of this plan. If a change seems to require a board edit, stop and report it.
- **`pgrep -x kicad` before every edit session.** Alex routes in the GUI between passes. If KiCad is running, stop and ask before touching any project file.
- **Schematic layout rules are acceptance criteria, not cosmetics.** GND symbols point down, rail symbols point up, zero overlap between any symbol, wire, or text, PWR_FLAGs live only in the `POWER FLAGS` box, every subsystem stays inside its graphic box.
- **Symbols sit on the 1.27 mm grid.** Every coordinate in this plan is already a multiple of 1.27.
- **Label text carries no leading `/`.** The label is `ISO_5V`; the netlist name is `/ISO_5V`. Renames edit label text; the gate asserts netlist names.
- **Net ties do not propagate ERC power drive.** KiCad treats net-tie pins as `passive`. A branch net that contains a `power_in` pin and no `power_out` pin needs its own `PWR_FLAG`, even though its sibling branch has one.
- **`Device` and `NetTie` libraries need no registration.** Both resolve through the nested `KiCad` table library in `~/Library/Preferences/kicad/10.0/{sym,fp}-lib-table`. Do not add entries to the project tables.
- **`Device:NetTie_2` and `Device:NetTie_4` already carry `(in_bom no)`**, and `NetTie-*_SMD_Pad0.5mm` footprints already carry `exclude_from_bom exclude_from_pos_files`. Do not set these by hand.
- **Do not "fix"** R3's trip band, the R9-DNP/R10-populated PGOOD arrangement, or the `/VBUS_HOST` topology. All are documented decisions.

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `tools/gates/decoupling_nets.py` | Asserts exact node membership and netclass for the eight nets in the split. Reads the netlist, so it is valid during a board-free pass. | Create |
| `tools/rename_labels.py` | Renames net labels by exact `(name, x, y)` identity, failing loudly on any match count that is not 1. | Create |
| `isolator.kicad_sch` | All schematic changes: label renames, NT1–NT3, C16, C17, two PWR_FLAGs, `Description` properties, constraints text. | Modify |
| `isolator.kicad_pro` | Four new `PWR` netclass patterns. | Modify |
| `tools/gates/run_all.py` | Add `decoupling_nets.py` to the step list. | Modify |

`decoupling_nets.py` lives in `tools/gates/` alongside `netclass_coverage.py` because it is the same kind of check — netlist-level, board-independent — and `run_all.py` already sequences that directory.

---

### Task 1: Membership gate and netclass patterns

**Files:**
- Create: `tools/gates/decoupling_nets.py`
- Modify: `isolator.kicad_pro` (`net_settings.netclass_patterns`)
- Modify: `tools/gates/run_all.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `EXPECT` — a `dict[str, set[tuple[str, str]]]` mapping net name to `{(ref, pin)}`; `CLASSES` — a `dict[str, set[str]]` mapping net name to expected netclass names. Tasks 2–5 are each complete when their slice of `EXPECT` passes.

- [ ] **Step 1: Confirm KiCad is not running**

```bash
pgrep -x kicad && echo "STOP - KiCad is open" || echo "safe to edit"
```

Expected: `safe to edit`. If KiCad is open, stop and ask Alex to close it.

- [ ] **Step 2: Write the membership gate**

Create `tools/gates/decoupling_nets.py`:

```python
"""Gate 4: the isolated-side supply nets have exactly their designed members.

This gate exists because of a specific failure. /ISO_5V used to carry U5's
output, U1's VBUS2 pin and U6's input under one name, so nothing in the design
files said which capacitor served which pin -- and the board put U1's bypass cap
26.46 mm from U1 while U6 borrowed it from 2.01 mm away. The schematic recorded
the intent as drawing position, which no tool reads. Net membership is the
machine-readable form of that intent, so it is asserted here.

Reads the netlist, not the board: this is valid during a schematic-only pass,
when the board still holds the previous netlist and the board gates cannot pass.

Usage: python3 decoupling_nets.py <netlist.net>
"""
import sys, re

# (ref, pin) sets. PWR_FLAG pins are power symbols and never appear as nodes.
EXPECT = {
    '/ISO_5V':        {('U5', '1'), ('U5', '2'), ('C10', '1'), ('C11', '1'), ('NT1', '1')},
    '/ISO_5V_VBUS2':  {('U1', '20'), ('C12', '1'), ('NT1', '2')},
    '/ISO_5V_SW':     {('U6', '1'), ('U6', '3'), ('C16', '1'), ('NT1', '3')},
    '/ISO_5V_IND':    {('R4', '1'), ('R5', '1'), ('R6', '1'), ('NT1', '4')},
    '/DCDC_RECT':     {('D1', '1'), ('D2', '1'), ('C8', '1'), ('NT2', '1')},
    '/DCDC_RAW':      {('U5', '5'), ('U5', '8'), ('C9', '1'), ('NT2', '2')},
    '/PORT_VBUS':     {('U6', '6'), ('C14', '1'), ('C15', '1'), ('NT3', '1')},
    '/PORT_VBUS_J2':  {('J2', 'A4'), ('J2', 'A9'), ('J2', 'B4'), ('J2', 'B9'),
                       ('D6', '1'), ('U3', '5'), ('R7', '1'), ('R8', '1'), ('NT3', '2')},
    '/VBUS_HOST':     {('J1', 'A4'), ('J1', 'A9'), ('J1', 'B4'), ('J1', 'B9'),
                       ('D5', '1'), ('U2', '5'), ('U1', '1'), ('C3', '1'), ('C4', '1'),
                       ('U4', '2'), ('U4', '5'), ('C6', '1'), ('C7', '1'),
                       ('T1', '2'), ('C17', '1')},
}

# /ISO_5V_IND is deliberately NOT in PWR: it carries a few mA and belongs at the
# ISO_SIDE default width, not the 0.5 mm power width.
CLASSES = {
    '/ISO_5V':       {'PWR', 'ISO_SIDE'},
    '/ISO_5V_VBUS2': {'PWR', 'ISO_SIDE'},
    '/ISO_5V_SW':    {'PWR', 'ISO_SIDE'},
    '/ISO_5V_IND':   {'ISO_SIDE'},
    '/DCDC_RECT':    {'PWR', 'ISO_SIDE'},
    '/DCDC_RAW':     {'PWR', 'ISO_SIDE'},
    '/PORT_VBUS':    {'PWR', 'ISO_SIDE'},
    '/PORT_VBUS_J2': {'PWR', 'ISO_SIDE'},
    '/VBUS_HOST':    {'PWR', 'HOST_SIDE'},
}


def parse(path):
    txt = open(path).read()
    blk = txt[txt.index('(nets'):]
    hdr = re.compile(r'\(net\s*\n\s*\(code "\d+"\)\s*\n\s*\(name "([^"]*)"\)'
                     r'\s*\n\s*\(class "([^"]*)"\)')
    out = {}
    marks = list(hdr.finditer(blk))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(blk)
        seg = blk[m.end():end]
        nodes = set(re.findall(r'\(ref "([^"]+)"\)\s*\n\s*\(pin "([^"]+)"\)', seg))
        out[m.group(1)] = (nodes, set(m.group(2).split(',')))
    return out


def main():
    actual = parse(sys.argv[1])
    fails = 0
    for net in sorted(EXPECT):
        want = EXPECT[net]
        if net not in actual:
            print("  FAIL  %-16s net does not exist" % net)
            fails += 1
            continue
        got, cls = actual[net]
        if got != want:
            fails += 1
            print("  FAIL  %-16s membership" % net)
            for r, p in sorted(want - got):
                print("           missing  %s.%s" % (r, p))
            for r, p in sorted(got - want):
                print("           unexpected %s.%s" % (r, p))
        wantc = CLASSES[net]
        if cls != wantc:
            fails += 1
            print("  FAIL  %-16s netclass %s, expected %s"
                  % (net, ','.join(sorted(cls)), ','.join(sorted(wantc))))
        if got == want and cls == wantc:
            print("  ok    %-16s %d nodes, %s" % (net, len(got), ','.join(sorted(cls))))
    print("\ndecoupling nets: %d failures" % fails)
    print("VERDICT:", "PASS" if not fails else "FAIL")
    sys.exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Run the gate against the current schematic and watch it fail**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist isolator.kicad_sch -o /tmp/net.net && python3 tools/gates/decoupling_nets.py /tmp/net.net
```

Expected: `VERDICT: FAIL`, exit 1, and exactly `decoupling nets: 9 failures`:

```
  FAIL  /DCDC_RAW        membership      missing NT2.2; unexpected C8.1, D1.1, D2.1
  FAIL  /DCDC_RECT       net does not exist
  FAIL  /ISO_5V          membership      missing NT1.1; unexpected C12.1, R4.1,
                                         R5.1, R6.1, U1.20, U6.1, U6.3
  FAIL  /ISO_5V_IND      net does not exist
  FAIL  /ISO_5V_SW       net does not exist
  FAIL  /ISO_5V_VBUS2    net does not exist
  FAIL  /PORT_VBUS       membership      missing NT3.1; unexpected D6.1, J2.A4,
                                         J2.A9, J2.B4, J2.B9, R7.1, R8.1, U3.5
  FAIL  /PORT_VBUS_J2    net does not exist
  FAIL  /VBUS_HOST       membership      missing C17.1
```

(The gate prints each missing/unexpected node on its own line; they are folded
here for width.) This is the pre-split state, and it confirms the gate parses
the netlist correctly rather than failing for some unrelated reason.

- [ ] **Step 4: Add the four PWR netclass patterns**

In `isolator.kicad_pro`, inside `net_settings.netclass_patterns`, immediately after the existing `{"netclass": "PWR", "pattern": "/PORT_VBUS"}` entry, insert four entries:

```json
        {
          "netclass": "PWR",
          "pattern": "/ISO_5V_VBUS2"
        },
        {
          "netclass": "PWR",
          "pattern": "/ISO_5V_SW"
        },
        {
          "netclass": "PWR",
          "pattern": "/DCDC_RECT"
        },
        {
          "netclass": "PWR",
          "pattern": "/PORT_VBUS_J2"
        },
```

Match the file's existing two-space-per-level indentation exactly. Do **not** add a pattern for `/ISO_5V_IND`.

- [ ] **Step 5: Verify the JSON still parses and ISO_SIDE needs no change**

```bash
python3 -c "
import json,fnmatch
p=json.load(open('isolator.kicad_pro'))['net_settings']['netclass_patterns']
pats=[(x['netclass'],x['pattern']) for x in p]
for n in ['/ISO_5V','/ISO_5V_VBUS2','/ISO_5V_SW','/ISO_5V_IND','/DCDC_RECT','/DCDC_RAW','/PORT_VBUS','/PORT_VBUS_J2']:
    print(n, sorted({c for c,q in pats if fnmatch.fnmatch(n,q)}))
"
```

Expected: every net shows `ISO_SIDE`, and every one except `/ISO_5V_IND` also shows `PWR`. `/ISO_5V_IND` shows `['ISO_SIDE']` alone.

- [ ] **Step 6: Register the gate in run_all.py**

In `tools/gates/run_all.py`, add one entry to the `steps` list immediately after the `netclass coverage` entry:

```python
    ('decoupling nets',   ['python3', os.path.join(HERE, 'decoupling_nets.py'), NET]),
```

- [ ] **Step 7: Commit**

```bash
git add tools/gates/decoupling_nets.py tools/gates/run_all.py isolator.kicad_pro && git commit -m "test(gates): assert isolated-side net membership, add branch netclass patterns"
```

---

### Task 2: Split /DCDC_RAW at the rectifier

**Files:**
- Create: `tools/rename_labels.py`
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: `decoupling_nets.py` from Task 1.
- Produces: `tools/rename_labels.py` exposing `rename(path, edits)` where `edits` is a list of `(old_name, x_str, y_str, new_name)` and `x_str`/`y_str` are the coordinate tokens **exactly as they appear in the file** (`"203.2"`, not `"203.20"`). Tasks 3 and 4 reuse it unchanged.

`/DCDC_RECT` needs no `PWR_FLAG`: after the split its only nodes are two diode cathodes, C8 and NT2 — all `passive`, no `power_in` pin for ERC to complain about. `/DCDC_RAW` keeps U5 pin 8 (`power_in`) and therefore keeps the existing `#FLG05`.

- [ ] **Step 1: Write the label-rename tool**

Create `tools/rename_labels.py`:

```python
"""Rename schematic net labels by exact (name, x, y) identity.

Connectivity in this schematic is carried by local labels, so renaming a label
IS a net change. Keying on coordinates rather than on the name alone is what
makes a partial rename expressible -- three of eleven ISO_5V labels, say -- and
what makes it reviewable afterwards. Any edit that does not match exactly once
aborts the whole run without writing, because a zero-match or two-match rename
silently produces a netlist nobody designed.

Usage: import and call rename(path, edits).
"""
import re, sys


def rename(path, edits):
    txt = open(path).read()
    for old, x, y, new in edits:
        pat = re.compile(r'(\(label ")' + re.escape(old) +
                         r'("\s*\n\s*\(at ' + re.escape(x) + ' ' + re.escape(y) + ' )')
        txt, n = pat.subn(lambda m: m.group(1) + new + m.group(2), txt, count=1)
        if n != 1:
            sys.exit('ABORT: label %s at (%s, %s) matched %d times, expected 1'
                     % (old, x, y, n))
    open(path, 'w').write(txt)
    for old, x, y, new in edits:
        print('  %-12s (%s, %s)  ->  %s' % (old, x, y, new))
    print('%d labels renamed' % len(edits))
```

- [ ] **Step 2: Rename the three rectifier-side labels**

```bash
python3 -c "
import sys; sys.path.insert(0,'tools')
from rename_labels import rename
rename('isolator.kicad_sch', [
    ('DCDC_RAW', '203.2',  '130.81', 'DCDC_RECT'),   # D1 cathode
    ('DCDC_RAW', '203.2',  '139.7',  'DCDC_RECT'),   # D2 cathode
    ('DCDC_RAW', '222.25', '130.81', 'DCDC_RECT'),   # C8 47uF reservoir
])
"
```

Expected: `3 labels renamed`. The remaining `DCDC_RAW` labels — C9 at (231.14, 130.81), U5 pin 8 at (247.65, 130.81), U5 pin 5 at (247.65, 135.89) and the `#FLG05` stub at (133.35, 255.27) — are untouched.

- [ ] **Step 3: Place NT2**

Verified-clear slot inside the `FULL-WAVE RECTIFIER + TLV76750 5V LDO (GND2)` box, whose bounds are (165.1, 100.33)–(305, 157.86). NT2's full extent including label text is (177.38, 146.79)–(212.78, 150.39).

```
mcp__kicad__add_schematic_component
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  symbol:        Device:NetTie_2
  reference:     NT2
  value:         NetTie_2
  footprint:     NetTie:NetTie-2_SMD_Pad0.5mm
  position:      { x: 195.58, y: 148.59 }
  angle:         0
```

At angle 0 the pin connection points are NT2.1 at (193.04, 148.59) and NT2.2 at (198.12, 148.59).

- [ ] **Step 4: Draw the two stub wires**

```
mcp__kicad__add_schematic_wire
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  waypoints:     [[193.04, 148.59], [187.96, 148.59]]
  snapToPins:    true

mcp__kicad__add_schematic_wire
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  waypoints:     [[198.12, 148.59], [203.20, 148.59]]
  snapToPins:    true
```

- [ ] **Step 5: Label the two branches**

```
mcp__kicad__add_schematic_net_label
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  netName:       DCDC_RECT
  position:      [187.96, 148.59]
  orientation:   180

mcp__kicad__add_schematic_net_label
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  netName:       DCDC_RAW
  position:      [203.20, 148.59]
  orientation:   0
```

- [ ] **Step 6: Run ERC**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc isolator.kicad_sch -o /tmp/erc.rpt --severity-error --exit-code-violations; echo "exit=$?"
```

Expected: `exit=0`. If a `power_pin_not_driven` error names `/DCDC_RECT`, the diode cathode pins are not `passive` as assumed — stop and report rather than adding a flag on a guess.

- [ ] **Step 7: Run the membership gate**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist isolator.kicad_sch -o /tmp/net.net && python3 tools/gates/decoupling_nets.py /tmp/net.net
```

Expected: still `VERDICT: FAIL` overall, but the two lines `ok    /DCDC_RECT       4 nodes, ISO_SIDE,PWR` and `ok    /DCDC_RAW        4 nodes, ISO_SIDE,PWR` now appear. Nothing else may change.

- [ ] **Step 8: Confirm the board was not touched**

```bash
git status --porcelain isolator.kicad_pcb
```

Expected: empty output.

- [ ] **Step 9: Commit**

```bash
git add tools/rename_labels.py isolator.kicad_sch && git commit -m "feat(sch): split /DCDC_RAW into rectifier output and LDO input at NT2"
```

---

### Task 3: Split /PORT_VBUS at U6's output

**Files:**
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: `tools/rename_labels.py` from Task 2.
- Produces: nets `/PORT_VBUS` and `/PORT_VBUS_J2`.

Neither branch needs a `PWR_FLAG`. `/PORT_VBUS` keeps U6 pin 6, which is `power_out` and drives the net. `/PORT_VBUS_J2` has no power pin at all — J2's VBUS pins, U3 pin 5, D6, R7 and R8 are all `passive`.

- [ ] **Step 1: Rename the five connector-side labels**

```bash
python3 -c "
import sys; sys.path.insert(0,'tools')
from rename_labels import rename
rename('isolator.kicad_sch', [
    ('PORT_VBUS', '185.42', '186.69', 'PORT_VBUS_J2'),   # U3 pin 5
    ('PORT_VBUS', '194.31', '190.5',  'PORT_VBUS_J2'),   # D6
    ('PORT_VBUS', '231.14', '182.88', 'PORT_VBUS_J2'),   # J2 VBUS
    ('PORT_VBUS', '247.65', '184.15', 'PORT_VBUS_J2'),   # R7
    ('PORT_VBUS', '262.89', '181.61', 'PORT_VBUS_J2'),   # R8
])
"
```

Expected: `5 labels renamed`. The three surviving `PORT_VBUS` labels are C14 at (325.12, 166.37), C15 at (340.36, 166.37) and U6 pin 6 at (347.98, 146.05).

- [ ] **Step 2: Place NT3**

Verified-clear slot inside the `TPS2553 PORT SWITCH (GND2)` box, bounds (314.96, 100.33)–(400.05, 185.42). NT3's full extent including label text is (347.56, 162.03)–(386.76, 165.63).

```
mcp__kicad__add_schematic_component
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  symbol:        Device:NetTie_2
  reference:     NT3
  value:         NetTie_2
  footprint:     NetTie:NetTie-2_SMD_Pad0.5mm
  position:      { x: 365.76, y: 163.83 }
  angle:         0
```

Pin connection points: NT3.1 at (363.22, 163.83), NT3.2 at (368.30, 163.83).

- [ ] **Step 3: Draw the two stub wires**

```
mcp__kicad__add_schematic_wire
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  waypoints:     [[363.22, 163.83], [358.14, 163.83]]
  snapToPins:    true

mcp__kicad__add_schematic_wire
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  waypoints:     [[368.30, 163.83], [373.38, 163.83]]
  snapToPins:    true
```

- [ ] **Step 4: Label the two branches**

```
mcp__kicad__add_schematic_net_label
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  netName:       PORT_VBUS
  position:      [358.14, 163.83]
  orientation:   180

mcp__kicad__add_schematic_net_label
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  netName:       PORT_VBUS_J2
  position:      [373.38, 163.83]
  orientation:   0
```

- [ ] **Step 5: Run ERC**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc isolator.kicad_sch -o /tmp/erc.rpt --severity-error --exit-code-violations; echo "exit=$?"
```

Expected: `exit=0`.

- [ ] **Step 6: Run the membership gate**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist isolator.kicad_sch -o /tmp/net.net && python3 tools/gates/decoupling_nets.py /tmp/net.net
```

Expected: `ok    /PORT_VBUS       4 nodes, ISO_SIDE,PWR` and `ok    /PORT_VBUS_J2    9 nodes, ISO_SIDE,PWR` join the two `/DCDC_*` lines. Overall still `FAIL`.

- [ ] **Step 7: Confirm the board was not touched**

```bash
git status --porcelain isolator.kicad_pcb
```

Expected: empty output.

- [ ] **Step 8: Commit**

```bash
git add isolator.kicad_sch && git commit -m "feat(sch): split /PORT_VBUS into switch output and connector at NT3"
```

---

### Task 4: Split /ISO_5V four ways

**Files:**
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: `tools/rename_labels.py` from Task 2.
- Produces: nets `/ISO_5V`, `/ISO_5V_VBUS2`, `/ISO_5V_SW`, `/ISO_5V_IND`.

Two branches need a new `PWR_FLAG`. `/ISO_5V_VBUS2` contains U1 pin 20, which is `power_in`; `/ISO_5V_SW` contains U6 pin 1, also `power_in`. Neither has a `power_out` pin any more, and the tie does not carry drive across from `/ISO_5V`. `/ISO_5V` keeps U5 pin 1 (`power_out`) and needs nothing. `/ISO_5V_IND` is all-passive and needs nothing.

C16 does not exist yet, so `/ISO_5V_SW` will have only three of its four nodes until Task 5. That is expected.

- [ ] **Step 1: Rename the seven branch labels**

```bash
python3 -c "
import sys; sys.path.insert(0,'tools')
from rename_labels import rename
rename('isolator.kicad_sch', [
    ('ISO_5V', '317.5',  '44.45',  'ISO_5V_VBUS2'),   # U1 pin 20 VBUS2
    ('ISO_5V', '342.9',  '33.02',  'ISO_5V_VBUS2'),   # C12, drawn beside C13
    ('ISO_5V', '322.58', '146.05', 'ISO_5V_SW'),      # U6 pin 1 IN
    ('ISO_5V', '322.58', '151.13', 'ISO_5V_SW'),      # U6 pin 3 EN
    ('ISO_5V', '365.76', '115.57', 'ISO_5V_IND'),     # R4 nFAULT pull-up
    ('ISO_5V', '375.92', '30.48',  'ISO_5V_IND'),     # R6 PG LED series
    ('ISO_5V', '378.46', '116.84', 'ISO_5V_IND'),     # R5 FAULT LED series
])
"
```

Expected: `7 labels renamed`. The four surviving `ISO_5V` labels are U5 pin 1 at (273.05, 130.81), U5 pin 2 at (273.05, 135.89), C10 at (283.21, 130.81) and C11 at (292.1, 130.81).

- [ ] **Step 2: Place NT1**

Verified-clear slot inside the `FULL-WAVE RECTIFIER + TLV76750 5V LDO (GND2)` box. NT1's full extent including label text is (245.94, 111.23)–(285.18, 117.37), which sits above the `DCDC_*` label band that starts at y = 121.21.

```
mcp__kicad__add_schematic_component
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  symbol:        Device:NetTie_4
  reference:     NT1
  value:         NetTie_4
  footprint:     NetTie:NetTie-4_SMD_Pad0.5mm
  position:      { x: 264.16, y: 113.03 }
  angle:         0
```

`Device:NetTie_4` has pins 1 and 3 on the left and 2 and 4 on the right, the lower pair 2.54 mm below the upper. At angle 0 and position (264.16, 113.03) the connection points are:

| Pin | Sheet coordinate |
|---|---|
| NT1.1 | (261.62, 113.03) |
| NT1.2 | (266.70, 113.03) |
| NT1.3 | (261.62, 115.57) |
| NT1.4 | (266.70, 115.57) |

- [ ] **Step 3: Draw the four stub wires**

```
mcp__kicad__add_schematic_wire
  waypoints: [[261.62, 113.03], [256.54, 113.03]]
  snapToPins: true

mcp__kicad__add_schematic_wire
  waypoints: [[266.70, 113.03], [271.78, 113.03]]
  snapToPins: true

mcp__kicad__add_schematic_wire
  waypoints: [[261.62, 115.57], [256.54, 115.57]]
  snapToPins: true

mcp__kicad__add_schematic_wire
  waypoints: [[266.70, 115.57], [271.78, 115.57]]
  snapToPins: true
```

All four take `schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch`.

- [ ] **Step 4: Label the four branches**

```
mcp__kicad__add_schematic_net_label
  netName: ISO_5V         position: [256.54, 113.03]   orientation: 180
mcp__kicad__add_schematic_net_label
  netName: ISO_5V_VBUS2   position: [271.78, 113.03]   orientation: 0
mcp__kicad__add_schematic_net_label
  netName: ISO_5V_SW      position: [256.54, 115.57]   orientation: 180
mcp__kicad__add_schematic_net_label
  netName: ISO_5V_IND     position: [271.78, 115.57]   orientation: 0
```

All four take `schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch`.

- [ ] **Step 5: Add the two PWR_FLAGs**

Both go in the `POWER FLAGS` box, bounds (15.24, 224.79)–(152.4, 271.78), in the verified-clear gap between the existing `VBUS_HOST` flag at x = 55.88 and the `GND2` flag at x = 106.68. Existing flags sit at y = 247.65 with a wire down to a rot-90 label at y = 255.27; match that pattern exactly.

```
mcp__kicad__add_schematic_component
  symbol: power:PWR_FLAG   reference: #FLG06   value: PWR_FLAG
  position: { x: 73.66, y: 247.65 }   angle: 0

mcp__kicad__add_schematic_wire
  waypoints: [[73.66, 247.65], [73.66, 255.27]]   snapToPins: true

mcp__kicad__add_schematic_net_label
  netName: ISO_5V_VBUS2   position: [73.66, 255.27]   orientation: 90

mcp__kicad__add_schematic_component
  symbol: power:PWR_FLAG   reference: #FLG07   value: PWR_FLAG
  position: { x: 88.90, y: 247.65 }   angle: 0

mcp__kicad__add_schematic_wire
  waypoints: [[88.90, 247.65], [88.90, 255.27]]   snapToPins: true

mcp__kicad__add_schematic_net_label
  netName: ISO_5V_SW   position: [88.90, 255.27]   orientation: 90
```

All take `schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch`.

- [ ] **Step 6: Run ERC**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc isolator.kicad_sch -o /tmp/erc.rpt --severity-error --exit-code-violations; echo "exit=$?"; grep -c . /tmp/erc.rpt
```

Expected: `exit=0`. If `power_pin_not_driven` still fires on `/ISO_5V_VBUS2` or `/ISO_5V_SW`, the flag wire did not land on the label — check the wire endpoint matches the label position to the last decimal.

- [ ] **Step 7: Run the membership gate**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist isolator.kicad_sch -o /tmp/net.net && python3 tools/gates/decoupling_nets.py /tmp/net.net
```

Expected: `/ISO_5V`, `/ISO_5V_VBUS2` and `/ISO_5V_IND` report `ok`. `/ISO_5V_SW` still reports `missing C16.1` — that is Task 5. `/VBUS_HOST` still reports `missing C17.1`. Overall `FAIL` with exactly 2 failures.

- [ ] **Step 8: Confirm the board was not touched**

```bash
git status --porcelain isolator.kicad_pcb
```

Expected: empty output.

- [ ] **Step 9: Commit**

```bash
git add isolator.kicad_sch && git commit -m "feat(sch): split /ISO_5V into LDO, VBUS2, switch and indicator branches at NT1"
```

---

### Task 5: Add C16 and C17

**Files:**
- Modify: `isolator.kicad_sch`

**Interfaces:**
- Consumes: `/ISO_5V_SW` from Task 4.
- Produces: C16 on `/ISO_5V_SW`, C17 on `/VBUS_HOST`. Both complete the `EXPECT` table from Task 1.

C16 is the TPS2553's input bypass, which has never existed — U6's input pin was being served by C12, a capacitor drawn for U1. C17 is the SN6505B's transformer-centre-tap bulk, required separately from the VCC bulk by SLLSEP9I §11.1.

C16 sits on the GND2 side and follows the isolated-side convention: rail label above, `GND2` label below. C17 sits on the GND1 side and follows the host-side convention used by C6 and C7: rail label above, a `power:GND1` symbol below.

- [ ] **Step 1: Place C16**

Verified-clear extent (315.50, 156.56)–(319.50, 180.87), inside the `TPS2553 PORT SWITCH (GND2)` box and clear of U6, C14 and their label bands, which all start at x ≥ 323.32.

```
mcp__kicad__add_schematic_component
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  symbol:        Device:C_Small
  reference:     C16
  value:         100n
  footprint:     Capacitor_SMD:C_0603_1608Metric
  position:      { x: 317.5, y: 173.99 }
  angle:         0
```

`Device:C_Small` pins sit 2.54 mm above and below the symbol origin: C16.1 at (317.5, 171.45), C16.2 at (317.5, 176.53).

- [ ] **Step 2: Wire and label C16**

```
mcp__kicad__add_schematic_wire
  waypoints: [[317.5, 171.45], [317.5, 168.91]]   snapToPins: true
mcp__kicad__add_schematic_net_label
  netName: ISO_5V_SW   position: [317.5, 168.91]   orientation: 90

mcp__kicad__add_schematic_wire
  waypoints: [[317.5, 176.53], [317.5, 179.07]]   snapToPins: true
mcp__kicad__add_schematic_net_label
  netName: GND2   position: [317.5, 179.07]   orientation: 90
```

All take `schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch`.

- [ ] **Step 3: Set C16's sourcing properties**

Match C12's fields so the BOM groups it onto the existing 100 n line rather than creating a new one.

```
mcp__kicad__set_schematic_component_property  reference: C16  name: MPN              value: CC0603KRX7R9BB104
mcp__kicad__set_schematic_component_property  reference: C16  name: Manufacturer     value: YAGEO
mcp__kicad__set_schematic_component_property  reference: C16  name: LCSC             value: C14663
mcp__kicad__set_schematic_component_property  reference: C16  name: Tolerance        value: ±10%
mcp__kicad__set_schematic_component_property  reference: C16  name: KiLib_Generator  value: SMD_2terminal_chip_molded
```

All take `schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch`. These are C12's exact field values.

- [ ] **Step 4: Place C17**

Verified-clear extent (94.50, 103.54)–(99.20, 133.00), inside the `SN6505B PUSH-PULL DRIVER + T1 TRANSFORMER (GND1 PRIMARY)` box, bounds (15.24, 100.33)–(148.59, 157.86), and clear of T1 whose body starts at x = 99.06, y = 135.25.

```
mcp__kicad__add_schematic_component
  schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch
  symbol:        Device:C_Small
  reference:     C17
  value:         4.7uF
  footprint:     Capacitor_SMD:C_0805_2012Metric
  position:      { x: 96.52, y: 121.92 }
  angle:         0
```

Pins: C17.1 at (96.52, 119.38), C17.2 at (96.52, 124.46).

- [ ] **Step 5: Wire and label C17**

```
mcp__kicad__add_schematic_wire
  waypoints: [[96.52, 119.38], [96.52, 116.84]]   snapToPins: true
mcp__kicad__add_schematic_net_label
  netName: VBUS_HOST   position: [96.52, 116.84]   orientation: 90

mcp__kicad__add_schematic_wire
  waypoints: [[96.52, 124.46], [96.52, 127.0]]   snapToPins: true

mcp__kicad__add_schematic_component
  symbol: power:GND1   reference: #PWR020   value: GND1
  position: { x: 96.52, y: 127.0 }   angle: 0
```

`#PWR020` is the next free power designator — the schematic currently holds
`#PWR01`–`#PWR15` and `#PWR016`–`#PWR019`.

The `power:GND1` symbol body must hang below its pin — angle 0 is correct and any other angle violates the standing layout rule. All calls take `schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch`.

- [ ] **Step 6: Set C17's sourcing properties**

These are C7's exact field values — same MPN, so the BOM's `4.7uF` line just
gains quantity. C7 carries no `Tolerance` field; do not invent one.

```
mcp__kicad__set_schematic_component_property  reference: C17  name: MPN              value: GRM21BR71E475KA73L
mcp__kicad__set_schematic_component_property  reference: C17  name: Manufacturer     value: Murata
mcp__kicad__set_schematic_component_property  reference: C17  name: LCSC             value: C162427
mcp__kicad__set_schematic_component_property  reference: C17  name: KiLib_Generator  value: SMD_2terminal_chip_molded
```

All take `schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch`.

- [ ] **Step 6b: Verify the net-tie footprint strings resolve**

The three tie footprints are not on the board yet, so the only thing checkable
now is that the `Footprint` property names a real footprint carrying
`net_tie_pad_groups`. Without that attribute the board DRC will later flag the
deliberate short as an error.

```bash
FP=/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/NetTie.pretty
python3 -c "
import re
t=open('isolator.kicad_sch').read()
want=dict(re.findall(r'\"(NT[123])\"[\s\S]{0,900}?\(property \"Footprint\" \"([^\"]*)\"',t))
print('schematic says:',want)
" 
for f in NetTie-4_SMD_Pad0.5mm NetTie-2_SMD_Pad0.5mm; do
  printf '%s: ' "$f"; grep -o 'net_tie_pad_groups "[^"]*"' "$FP/$f.kicad_mod" || echo MISSING
done
```

Expected: NT1 maps to `NetTie:NetTie-4_SMD_Pad0.5mm`, NT2 and NT3 to
`NetTie:NetTie-2_SMD_Pad0.5mm`, and both footprints report a
`net_tie_pad_groups` line (`"1, 2, 3, 4"` and `"1, 2"`).

- [ ] **Step 7: Run ERC**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc isolator.kicad_sch -o /tmp/erc.rpt --severity-error --exit-code-violations; echo "exit=$?"
```

Expected: `exit=0`.

- [ ] **Step 8: Run the membership gate — this is where it turns green**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist isolator.kicad_sch -o /tmp/net.net && python3 tools/gates/decoupling_nets.py /tmp/net.net
```

Expected: nine `ok` lines and `VERDICT: PASS`.

- [ ] **Step 9: Run netclass coverage**

```bash
python3 tools/gates/netclass_coverage.py isolator.kicad_pro /tmp/net.net
```

Expected: `VERDICT: PASS` — every new net lands in exactly one of `HOST_SIDE`/`ISO_SIDE`.

- [ ] **Step 10: Regenerate the BOM and confirm no new line items**

This exact invocation reproduces the committed `isolator-bom.csv` byte-for-byte
on the pre-change schematic, so any difference beyond the expected ones is a
real difference:

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export bom isolator.kicad_sch \
  -o /tmp/bom.csv \
  --fields 'Reference,Value,Footprint,MPN' \
  --labels 'Reference,Value,Footprint,MPN' \
  --group-by 'Value,Footprint,MPN' \
&& diff /tmp/bom.csv isolator-bom.csv
```

Expected differences, and only these:

1. The `100n` line's references become `C4-C6,C9,C11-C13,C15-C16`.
2. The `4.7uF` line's references become `C3,C7,C17`.
3. J2's `Value` reads `ISO_PORT`, not `PORT`. **This one is pre-existing** —
   J2 was renamed after `isolator-bom.csv` was last committed, so the stale
   line is being corrected here as a side effect. Do not treat it as a
   regression and do not revert it.

NT1–NT3 must not appear at all; `Device:NetTie_*` carries `(in_bom no)`. If a
new `Value`/`Footprint`/`MPN` triple appears, C16 or C17 has a mismatched
property — fix the property rather than editing the BOM.

- [ ] **Step 11: Update the committed BOM**

```bash
cp /tmp/bom.csv isolator-bom.csv && git diff --stat isolator-bom.csv
```

- [ ] **Step 12: Confirm the board was not touched**

```bash
git status --porcelain isolator.kicad_pcb
```

Expected: empty output.

- [ ] **Step 13: Commit**

```bash
git add isolator.kicad_sch isolator-bom.csv && git commit -m "feat(sch): add C16 TPS2553 input bypass and C17 T1 centre-tap bulk"
```

---

### Task 6: Ownership documentation and visual verification

**Files:**
- Modify: `isolator.kicad_sch` (`Description` properties and the `LAYOUT CONSTRAINTS -- BINDING` text block)

**Interfaces:**
- Consumes: the finished netlist from Task 5.
- Produces: nothing downstream. This task is the half of the change that survives if a net tie is ever removed.

Nine capacitors currently carry the stock library string `Unpolarized capacitor, small symbol`. C3, C4, C6 and C7 carry hand-written ownership text, and those are the four that landed correctly on the board. That correlation is the reason this task exists.

- [ ] **Step 1: Write the ownership descriptions**

Each call is `mcp__kicad__set_schematic_component_property` with `schematicPath: /Users/alex/Documents/isolator/isolator.kicad_sch`, `name: Description`, and `hide: true`.

| reference | value |
|---|---|
| C8 | `Rectifier reservoir on DCDC_RECT, 47uF. Layout: place at the D1/D2 cathodes, NOT at U5 -- the pulsed rectifier current is what this cap smooths. C9 is the LDO input cap; do not swap them.` |
| C9 | `TLV76750 U5 input bypass on DCDC_RAW, 100n. Layout: place close to U5 pin 8 / GND. Reaches U5 only through NT2; do not feed it from the rectifier side.` |
| C10 | `TLV76750 U5 output bulk on ISO_5V, 47uF. Layout: place close to U5 pins 1/2, outboard of C11.` |
| C11 | `TLV76750 U5 output HF bypass on ISO_5V, 100n. Layout: place closer to U5 pins 1/2 than C10.` |
| C12 | `ADuM4165 U1 VBUS2 bypass on ISO_5V_VBUS2, 100n (datasheet Rev. B, Table 12, pin 20). Layout: MUST sit within U1's 10 mm bypass-lead budget at U1 pin 20, returning to GND2 via pins 11/19 only. This cap was placed at U6 on the first board revision -- it does not belong there.` |
| C13 | `ADuM4165 U1 VDD2 bypass on VDD2, 100n (datasheet Rev. B, Table 12, pin 18). Layout: within the 10 mm bypass-lead budget at U1 pin 18, returning to GND2 via pins 11/19 only.` |
| C14 | `TPS2553 U6 output bulk on PORT_VBUS, 22uF (SLVS841F Sec 12.1). Layout: place at U6 pin 6, outboard of C15 -- NOT down at J2.` |
| C15 | `TPS2553 U6 output HF bypass on PORT_VBUS, 100n (SLVS841F Sec 12.1). Layout: place closer to U6 pin 6 than C14 -- NOT down at J2.` |
| C16 | `TPS2553 U6 input bypass on ISO_5V_SW, 100n (SLVS841F Sec 10.2.1.2.4, "0.1uF or greater as close to the device as possible"). Layout: place at U6 pins 1/3. Reaches the LDO only through NT1.` |
| C17 | `SN6505B transformer centre-tap bulk on VBUS_HOST, 4.7uF (SLLSEP9I Sec 11.1, separate from the VCC bulk). Layout: place at T1 pin 2, NOT at U4 -- C7 is the VCC bulk.` |
| C1 | `24 MHz crystal load cap on XTALIN, 8p. Layout: place at Y1, minimising the Y1-to-U1 pin 5 trace.` |
| C2 | `24 MHz crystal load cap on XTALOUT, 8p. Layout: place at Y1, minimising the Y1-to-U1 pin 6 trace.` |

- [ ] **Step 2: Narrow C6's description**

C6's current text says it clusters at "U4 pin 2 / T1 center-tap". C17 now owns the centre tap, so that wording is wrong.

```
mcp__kicad__set_schematic_component_property
  reference: C6   name: Description   hide: true
  value: SN6505B U4 VCC close-to-pin bypass, 0.1uF (datasheet Sec 10, Power Supply Recommendations). Layout: place immediately at U4 pin 2, inboard of C7. C17 now covers the T1 centre-tap -- do not cluster C6 there.
```

- [ ] **Step 3: Verify no capacitor carries the stock description**

```bash
python3 -c "
import re
t=open('isolator.kicad_sch').read()
i=0; bad=[]
while True:
    j=t.find('\n\t(symbol\n',i)
    if j<0: break
    k=j+1; d=0
    while True:
        c=t[k]
        if c=='\"':
            k+=1
            while t[k]!='\"' or t[k-1]=='\\\\': k+=1
        elif c=='(': d+=1
        elif c==')':
            d-=1
            if d==0: break
        k+=1
    b=t[j:k+1]
    r=re.search(r'\(property \"Reference\" \"(C\d+)\"',b)
    dsc=re.search(r'\(property \"Description\" \"([^\"]*)\"',b)
    if r and dsc and 'Unpolarized capacitor' in dsc.group(1): bad.append(r.group(1))
    i=k
print('stock description still on:', sorted(bad) or 'none')
"
```

Expected: `none`.

- [ ] **Step 4: Update the LAYOUT CONSTRAINTS text block**

The block lives in a single `(text "...")` s-expression with `\n` escapes, anchored at (335.5, 196.34). Edit three things:

Item 5, replace:
```
5. ADuM4165 bypass caps within 10 mm total lead length.
```
with:
```
5. ADuM4165 bypass caps within 10 mm total lead length: C4 at VBUS1 (pin 1),\n    C5 at VDD1 (pin 3), C12 at VBUS2 (pin 20), C13 at VDD2 (pin 18). All four\n    are named because pin names alone did not stop C12 landing at U6.
```

Item 9, replace the whole item with:
```
9. VBUS_HOST's 5 caps serve 3 pins -- see each cap's Description property\n    before placing. C6 alone at U4 pin 2, inboard of C7 (SN6505B's mandatory\n    >=4.7 uF VCC bypass, Table 5-1). C17 at T1's center-tap (SLLSEP9I Sec 11.1,\n    a separate requirement from the VCC bulk). C4 clusters at U1 pin 1 -- NOT\n    with C3. C3 is J1-entrance bulk/inrush capacitance and stays near J1.
```

Append a new item 10:
```
10. THREE NET TIES DEFINE THREE STAR POINTS. NT1 splits ISO_5V into ISO_5V\n    (U5 out, C10+C11), ISO_5V_VBUS2 (U1 pin 20, C12), ISO_5V_SW (U6 in, C16)\n    and ISO_5V_IND (R4/R5/R6). NT2 splits DCDC_RECT (D1/D2, C8) from DCDC_RAW\n    (U5 in, C9). NT3 splits PORT_VBUS (U6 out, C14+C15) from PORT_VBUS_J2 (J2,\n    D6, U3, R7/R8). A branch may be fed ONLY through its tie -- never bridge\n    two branches with copper anywhere else. The ties exist because these pins\n    shared a net name and the board satisfied the wrong ones.
```

- [ ] **Step 5: Run ERC and the gate one final time**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc isolator.kicad_sch -o /tmp/erc.rpt --severity-error --exit-code-violations && echo "ERC ok" && /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist isolator.kicad_sch -o /tmp/net.net && python3 tools/gates/decoupling_nets.py /tmp/net.net && python3 tools/gates/netclass_coverage.py isolator.kicad_pro /tmp/net.net
```

Expected: `ERC ok`, then both gates `VERDICT: PASS`. Descriptions are metadata and must not have changed connectivity — if membership moved, something other than a `Description` was edited.

- [ ] **Step 6: Render and check for overlaps**

```bash
SC=/tmp/schcheck && mkdir -p $SC && /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export svg --exclude-drawing-sheet -o $SC isolator.kicad_sch && rsvg-convert -z 8 -b white $SC/isolator.svg -o $SC/full.png && magick $SC/full.png -crop 3175x2570+8921+454 +repage -resize 1500x $SC/adum.png && magick $SC/full.png -crop 2873x2722+9374+3024 +repage -resize 1400x $SC/tps.png && magick $SC/full.png -crop 4536x1965+4838+2873 +repage -resize 1600x $SC/ldo.png && magick $SC/full.png -crop 4386x1965+302+2873 +repage -resize 1600x $SC/sn6505.png && magick $SC/full.png -crop 4300x1500+430+6740 +repage -resize 1500x $SC/flags.png && ls $SC/*.png
```

Then **read all five PNGs** and confirm, region by region:

1. `adum.png` — C12's label reads `ISO_5V_VBUS2`, C13's still reads `VDD2`, U1 pin 20's stub reads `ISO_5V_VBUS2`, R6's reads `ISO_5V_IND`. No text overlaps.
2. `tps.png` — U6 pins 1 and 3 read `ISO_5V_SW`; C14/C15 still read `PORT_VBUS`; C16 is present below-left of U6 with `ISO_5V_SW` above and `GND2` below; NT3 sits clear with `PORT_VBUS` and `PORT_VBUS_J2` stubs; R4/R5 read `ISO_5V_IND`.
3. `ldo.png` — D1/D2/C8 read `DCDC_RECT`, C9 and U5 pins 5/8 read `DCDC_RAW`, NT1 sits above the diode row with four labelled stubs, NT2 sits below with two.
4. `sn6505.png` — C17 is present left of T1 with `VBUS_HOST` above and a GND1 symbol pointing **down** below it. C6 and C7 unchanged.
5. `flags.png` — six flags in one row, the two new ones labelled `ISO_5V_VBUS2` and `ISO_5V_SW`, none overlapping their neighbours' `PWR_FLAG` value text.

Any overlap is a failure. Nudge the offending item by ±1.27 mm and re-render; do not accept "close enough".

- [ ] **Step 7: Confirm the board is still untouched across the whole plan**

```bash
git diff --quiet e9c8dc7 HEAD -- isolator.kicad_pcb && echo "board untouched" || echo "BOARD CHANGED - investigate"
```

Expected: `board untouched`. `e9c8dc7` is the commit that captured Alex's in-progress board edits, immediately before this plan's first commit. `git diff --quiet` is what makes the exit status meaningful here — plain `git diff --stat` returns 0 whether or not there is a diff.

- [ ] **Step 8: Commit**

```bash
git add isolator.kicad_sch && git commit -m "docs(sch): record each cap's owning pin and the three star points"
```

---

## Follow-on, explicitly not in this plan

The board still carries the pre-split netlist. A separate plan must place C16, C17 and NT1–NT3, relocate C6, C8, C12, C14 and C15, rip up and reroute `/ISO_5V*`, `/PORT_VBUS*` and `/DCDC_*`, and bring `tools/gates/run_all.py` back to green including DRC with `--schematic-parity`. Until that runs, `run_all.py` will fail on Gates 1–3 and on parity, and that failure is expected rather than a regression.
