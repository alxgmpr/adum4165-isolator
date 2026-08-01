# Isolated-Side Board Resync and Re-place Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `isolator.kicad_pcb` to the split netlist, re-place and re-route the entire isolated side around the three net-tie star points, and end with all six gates and a schematic-parity DRC passing.

**Architecture:** The board is manipulated programmatically through KiCad's bundled `pcbnew` Python, following the pattern already in `tools/` — every coordinate reviewable in git and reproducible. Verification is scripted gates under `tools/gates/`, and the new one (`decoupling.py`) is written before the placement it polices, watched to fail, exactly as `decoupling_nets.py` was in the schematic pass.

**Tech Stack:** KiCad 10.0.5. `pcbnew` via KiCad's bundled interpreter at `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3` — **`pcbnew` is not importable from system python3**. `kicad-cli` at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, not on PATH. Gates that read only the netlist or the board file as text run fine under system `python3`.

## Global Constraints

Every task implicitly includes these. Values are copied from the spec and from the schematic's `LAYOUT CONSTRAINTS -- BINDING` block, which is authoritative.

- **The schematic never changes.** `isolator.kicad_sch` must be byte-identical to `2c1167d` at every commit. If layout reveals an electrical problem, stop and report it.
- **Coordinate frames.** `tools/place.py` uses **board-local** mm, origin at the outline's top-left. **Absolute = local + (86.88, 76.70).** The file's `aux_axis_origin` is (86.875, 126.7034), bottom-left, and is *not* that origin. Every coordinate you write or read must be labelled with its frame — mixing them moves parts by 50 mm silently.
- **Board is 120 × 50 mm**, absolute x 86.88–206.88, y 76.70–126.70. KiCad's y increases downward.
- **Barrier keepout: absolute x 142.72–151.03**, full height, all four copper layers. Excludes tracks, vias and zone fill; permits pads. **U1, T1 and CY1 are the only permitted crossings.**
- **Copper band: absolute y 78.70–124.70.** No copper of any kind within 1 mm of the long edges, any layer, full length.
- **Frozen parts:** J1, J2, U1, T1, CY1, H1–H4, FID1–3, and the entire host side except C6 and C17.
- **Free parts:** U5, U6, U3, D1, D2, D6, C8–C16, NT1–NT3, R3–R10, Q1, D3, D4.
- **U3 within 5 mm** of the J2 pins it protects; its array GND pin on its own via straight to plane, never daisy-chained.
- **Differential pairs are `USB_DIFF90`:** 0.21 mm width, 0.127 mm gap, intra-pair skew ≤ 0.15 mm.
- **Each branch net is fed only through its net tie.** Never bridge two branches with copper anywhere else, and never feed a tie pad from a pour — route both pads explicitly.
- **`PWR` routes at 0.5 mm.** `/ISO_5V_IND` stays at the `ISO_SIDE` default 0.2 mm.
- **Do not "fix"** R3's trip band or the R9-DNP/R10-populated PGOOD arrangement.
- **Run `pcbnew` scripts as files** with `python3 -u`, not inline heredocs (heredocs lose stdout). End each with `sys.stdout.flush(); os._exit(0)` to suppress harmless teardown segfaults that spawn macOS crash dialogs.
- **Zone fills are stored in the file.** `kicad-cli pcb drc` judges the stored fill — refill before believing a wave of clearance or dangling errors.
- **`pcbnew` prints a harmless assert on stderr** at import: `stdpbase.cpp(59): assert "traits" failed in Get(): create wxApp before calling this`. It appears on every headless run and means nothing. Do not chase it, and do not suppress stderr wholesale to hide it — you will hide real errors with it.
- **These `pcbnew` calls are verified working on this install** (KiCad 10.0.5, checked against the real board before this plan was written): `board.FindFootprintByReference(ref)`, `footprint.GetPath().AsString()`, `pcbnew.KIID_PATH("/<uuid>")`, `pad.GetNumber()`, `pad.GetPosition()` returning nanometres, and `pcbnew.NETINFO_ITEM(board, name)`. Positions divide by 1e6 for millimetres — `U1` pad 1 reads 141.975, 95.9884.
- **Before editing, check `pgrep -x kicad`** — but confirm it is *this* project before stopping: `lsof -p <pid> | grep kicad_` and look for `~*.lck` in the project directory. Alex usually has a different project open, and a bare "KiCad is running" stop is a false positive most of the time.

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `tools/gates/decoupling.py` | Asserts each capacitor's owning pin, max distance, and the three ordering rules, against the board. | Create |
| `tools/resync_board.py` | Adds C16, C17, NT1–NT3 to the board and applies the renamed nets from the netlist. | Create |
| `tools/ripup_iso_side.py` | Rips all routing east of the barrier plus the two host-side rails that C6/C17 disturb. | Create |
| `tools/place_iso.py` | The isolated-side placement table, board-local coordinates. | Create |
| `tools/route_iso.py` | Routes the eight branch nets and the star points. | Create |
| `isolator.kicad_pcb` | All board changes. | Modify |
| `tools/gates/run_all.py` | Add `decoupling.py` to the step list. | Modify |

`decoupling.py` joins `tools/gates/` because it is the same kind of check as its siblings and `run_all.py` already sequences that directory. Placement and routing are separate files because a placement failure and a routing failure need to be distinguishable — the same reason `build_board.py` and `place.py` were split in the original layout pass.

---

### Task 1: The decoupling gate

**Files:**
- Create: `tools/gates/decoupling.py`
- Modify: `tools/gates/run_all.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `OWNS` — a list of `(cap, [owner_pins], budget_mm)`; `ORDER` — a list of `(inner_cap, outer_cap, shared_pin)`. Tasks 4 and 5 are complete when this gate passes.

- [ ] **Step 1: Write the gate**

Create `tools/gates/decoupling.py`:

```python
"""Gate 5: every decoupling capacitor sits within budget of the pin it serves.

This gate exists because of a specific failure. /ISO_5V once carried U5's
output, U1's VBUS2 pin and U6's input under one name, and the board satisfied
C12 -- drawn on the sheet as U1's bypass -- at U6 instead, 26.46 mm from the pin
it belonged to. The schematic pass fixed the netlist so that can no longer
happen by accident. This gate covers what the netlist still cannot say: a
capacitor on the correct net, placed too far from its own pin.

Distances are pad-centre to pad-centre with footprint rotation applied. The
ordering rules matter as much as the distances -- a bulk cap inboard of the
ceramic it is meant to back up is a defect even when both are within budget.

Usage: <kicad python3> decoupling.py <board.kicad_pcb>
"""
import sys, os, math, pcbnew

# (cap, [owner pins, nearest wins], budget mm)
OWNS = [
    ('C12', [('U1', '20')], 3.0),
    ('C13', [('U1', '18')], 3.0),
    ('C16', [('U6', '1')],  3.0),
    ('C15', [('U6', '6')],  3.0),
    ('C14', [('U6', '6')],  6.0),
    ('C11', [('U5', '1')],  3.0),
    ('C10', [('U5', '1')],  4.0),
    ('C9',  [('U5', '8')],  3.5),
    ('C8',  [('D1', '1'), ('D2', '1')], 4.0),
    ('C6',  [('U4', '2')],  2.5),
    ('C7',  [('U4', '2')],  3.5),
    ('C17', [('T1', '2')],  4.0),
    ('C4',  [('U1', '1')],  3.5),
    ('C5',  [('U1', '3')],  4.0),
]

# (inner, outer, shared owner pin) -- inner must be strictly nearer than outer.
# C6 inboard of C7 follows SN6505B Sec 10 ("0.1 uF as close as possible to the
# VCC pin"); Sec 11.1's competing "bulk closest to VIN" is satisfied by C17 at
# the centre tap, which is why C17 exists. Do not invert this to match Sec 11.1.
ORDER = [
    ('C11', 'C10', ('U5', '1')),
    ('C15', 'C14', ('U6', '6')),
    ('C6',  'C7',  ('U4', '2')),
]


def pad_xy(board, ref, pad_name):
    fp = board.FindFootprintByReference(ref)
    if fp is None:
        return None
    for p in fp.Pads():
        if p.GetNumber() == pad_name:
            v = p.GetPosition()
            return (v.x / 1e6, v.y / 1e6)
    return None


def nearest(board, cap, owners):
    c = pad_xy(board, cap, '1')
    if c is None:
        return None, None
    best, who = None, None
    for ref, pin in owners:
        t = pad_xy(board, ref, pin)
        if t is None:
            continue
        d = math.hypot(c[0] - t[0], c[1] - t[1])
        if best is None or d < best:
            best, who = d, '%s.%s' % (ref, pin)
    return best, who


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    fails = 0
    for cap, owners, budget in OWNS:
        d, who = nearest(board, cap, owners)
        if d is None:
            print('  FAIL  %-5s footprint or pad missing from the board' % cap)
            fails += 1
            continue
        verdict = 'ok  ' if d <= budget else 'FAIL'
        if d > budget:
            fails += 1
        print('  %s  %-5s %6.2f mm to %-6s (budget %4.1f)' % (verdict, cap, d, who, budget))
    for inner, outer, pin in ORDER:
        di, _ = nearest(board, inner, [pin])
        do, _ = nearest(board, outer, [pin])
        if di is None or do is None:
            print('  FAIL  order %s/%s: a footprint is missing' % (inner, outer))
            fails += 1
            continue
        if di < do:
            print('  ok    %-5s (%.2f) is inboard of %-5s (%.2f) at %s.%s'
                  % (inner, di, outer, do, pin[0], pin[1]))
        else:
            print('  FAIL  %-5s (%.2f) must be INBOARD of %-5s (%.2f) at %s.%s'
                  % (inner, di, outer, do, pin[0], pin[1]))
            fails += 1
    print('\ndecoupling placement: %d failures' % fails)
    print('VERDICT:', 'PASS' if not fails else 'FAIL')
    sys.stdout.flush()
    os._exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run it against the current board and watch it fail**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/gates/decoupling.py isolator.kicad_pcb; echo "exit=$?"
```

Expected: `VERDICT: FAIL`, exit 1. Specifically — C16, C17 and the ordering rules that reference them report *footprint missing* (they exist only in the schematic so far); C12 reports ≈26.46 mm against a 3.0 budget; C15 ≈12.49 against 3.0; C14 ≈10.87 against 6.0; C8 ≈8.08 against 4.0; C6 ≈4.23 against 2.5; and the C6/C7 ordering rule fails because C7 is currently nearer. C13, C11, C10, C9, C7, C4 and C5 should already read `ok`. Record the actual output — later tasks are measured against it.

- [ ] **Step 3: Register the gate in run_all.py**

In `tools/gates/run_all.py`, add one entry to `steps`, after the `Gate 3 diff pairs` entry:

```python
    ('Gate 5 decoupling', [KIPY, os.path.join(HERE, 'decoupling.py'), BOARD]),
```

- [ ] **Step 4: Commit**

```bash
git add tools/gates/decoupling.py tools/gates/run_all.py && git commit -m "test(gates): assert decoupling capacitor ownership and ordering on the board"
```

---

### Task 2: Resync the board to the split netlist

**Files:**
- Create: `tools/resync_board.py`
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: `tools/gates/decoupling.py` from Task 1.
- Produces: a board carrying C16, C17, NT1, NT2 and NT3 as footprints, and the eight branch net names on every pad. Every later task assumes these exist.

There is no `kicad-cli` command for "update PCB from schematic" — it is a GUI action. `tools/build_board.py` already implements the equivalent through `pcbnew`, parking new footprints off-board so a parity failure cannot be mistaken for a placement error. Read it before writing `resync_board.py` and follow its structure; do not re-invent its netlist parser.

- [ ] **Step 1: Export the reference netlist**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist isolator.kicad_sch -o /tmp/net.net
grep -c '(net' /tmp/net.net
```

- [ ] **Step 2: Write the resync script**

Create `tools/resync_board.py`. Reuse `build_board.py`'s `parse`/`find`/`val` s-expression helpers verbatim by importing them — do not write a second netlist parser.

Note one thing `build_board.py` does **not** do, which this script must: set each new footprint's schematic path. Without it, KiCad's GUI Update-from-Schematic creates a duplicate and orphans the footprint. The netlist carries the UUID as `(tstamps "...")` inside each `(comp ...)`, and the board wants it as `/<uuid>` — C16's, for example, is `03860154-d792-4dfe-992b-227dff463e68`, stored as `(path "/03860154-…")`.

```python
"""Bring the board up to the schematic's netlist without disturbing placement.

Unlike build_board.py, which populates an empty board, this runs against a board
that is already placed and routed: it adds only the footprints that are missing,
parks them below the outline, and rebinds every pad to whatever net the netlist
now says. The eight branch nets from the schematic split arrive here.
"""
import sys, os, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_board import parse, find, val, FPLIB_SYS, FPLIB_PRJ

BOARD, NETLIST = sys.argv[1], sys.argv[2]
PARK_X, PARK_Y, PARK_DX = 96.88, 136.70, 5.0     # absolute mm, below the outline

root = parse(open(NETLIST).read())

comps, paths = {}, {}
for sec in find(root, 'components'):
    for c in find(sec, 'comp'):
        ref = val(c, 'ref')
        comps[ref] = val(c, 'footprint')
        ts = val(c, 'tstamps')
        if ts:
            paths[ref] = '/' + ts

pad_nets = {}
for sec in find(root, 'nets'):
    for n in find(sec, 'net'):
        name = val(n, 'name')
        for nd in find(n, 'node'):
            pad_nets[(val(nd, 'ref'), val(nd, 'pin'))] = name

b = pcbnew.LoadBoard(BOARD)

created = []
for name in sorted(set(pad_nets.values())):
    if b.FindNet(name) is None:
        b.Add(pcbnew.NETINFO_ITEM(b, name))
        created.append(name)

added, missing = [], []
have = {fp.GetReference() for fp in b.GetFootprints()}
for i, ref in enumerate(sorted(set(comps) - have)):
    nick, name = comps[ref].split(':', 1)
    lib = FPLIB_PRJ if nick == 'isolator-lib' else os.path.join(FPLIB_SYS, nick + '.pretty')
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        missing.append((ref, comps[ref]))
        continue
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(PARK_X + i * PARK_DX),
                                   pcbnew.FromMM(PARK_Y)))
    if ref in paths:
        fp.SetPath(pcbnew.KIID_PATH(paths[ref]))
    b.Add(fp)
    added.append(ref)

rebound = 0
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        want = pad_nets.get((ref, pad.GetNumber()))
        if want and pad.GetNetname() != want:
            pad.SetNet(b.FindNet(want))
            rebound += 1

print('nets created:      %s' % (', '.join(created) or 'none'))
print('footprints added:  %s' % (', '.join(added) or 'none'))
print('pads rebound:      %d' % rebound)
for ref, fpid in missing:
    print('  MISSING FOOTPRINT:', ref, fpid)
if missing:
    sys.stdout.flush()
    os._exit(1)
pcbnew.SaveBoard(BOARD, b)
print('saved')
sys.stdout.flush()
os._exit(0)
```

If `build_board.py`'s helpers are not importable as written (it executes work at module scope), copy the four helper functions into the new file rather than refactoring `build_board.py` — that file is a record of how the board was originally built and should not change.

- [ ] **Step 3: Run it**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/resync_board.py isolator.kicad_pcb /tmp/net.net
```

Expected: 5 footprints added, 5 nets created, and pad reassignments on C8, C12, C14, C15, D1, D2, D6, J2, R7, R8, U3, U6.

- [ ] **Step 4: Verify parity**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc isolator.kicad_pcb -o /tmp/drc.rpt --severity-error --schematic-parity --exit-code-violations; echo "exit=$?"
grep -ciE 'missing_footprint|net_conflict' /tmp/drc.rpt
```

Expected: parity errors are now **zero** — `missing_footprint` and `net_conflict` were promoted to errors at the end of the schematic pass specifically so this step is meaningful. DRC will still fail overall on unrouted nets and on clearance from the parked footprints; that is expected at this stage. What must be zero is the parity class.

- [ ] **Step 5: Confirm the schematic did not move**

```bash
git diff --quiet 2c1167d HEAD -- isolator.kicad_sch && echo "schematic frozen" || echo "SCHEMATIC CHANGED - stop"
```

- [ ] **Step 6: Commit**

```bash
git add tools/resync_board.py isolator.kicad_pcb && git commit -m "feat(pcb): resync board to the split netlist, park C16/C17/NT1-3"
```

---

### Task 3: Rip up the isolated side

**Files:**
- Create: `tools/ripup_iso_side.py`
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: the resynced board from Task 2.
- Produces: a board with no routing east of the barrier, host-side routing intact except the two rails C6/C17 disturb.

`tools/ripup_iso.py` already exists and rips by net-name allowlist. It is the wrong shape here — this task rips by **geometry**, because the whole isolated side goes, including nets that also have host-side copper. Write a new script rather than bending the old one; leave `ripup_iso.py` in place.

- [ ] **Step 1: Record the pre-rip baseline**

```bash
cat > /tmp/count.py <<'EOF'
import sys, os, pcbnew
from collections import Counter
b = pcbnew.LoadBoard(sys.argv[1])
c = Counter()
for t in b.GetTracks():
    c[type(t).__name__] += 1
print(dict(c))
sys.stdout.flush(); os._exit(0)
EOF
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u /tmp/count.py isolator.kicad_pcb
```

Record the counts. The board held 297 segments and 61 vias before this plan began.

- [ ] **Step 2: Write the rip-up script**

Create `tools/ripup_iso_side.py`:

```python
"""Rip every track east of the barrier, plus the whole VBUS_HOST rail.

ripup_iso.py rips by net-name allowlist, which is the wrong shape here: this
pass clears the isolated side by GEOMETRY, including nets that also carry
host-side copper. VBUS_HOST goes too, despite being host-side, because C6 moves
inboard of C7 and C17 is new at T1's centre tap -- the rail has to be re-routed
to serve the new arrangement either way.

Zones are deliberately untouched. Planes and their stitching are re-done in the
final task, after placement settles.
"""
import sys, os, pcbnew
from collections import Counter

BARRIER_W, BARRIER_E = 142.72, 151.03      # absolute mm
ALWAYS_RIP = {'/VBUS_HOST'}
NEVER_RIP = {'/HOST_D+', '/HOST_D-'}       # host-side, Gate 3 already passes

b = pcbnew.LoadBoard(sys.argv[1])
doomed, straddling = [], []

for t in b.GetTracks():
    net = t.GetNetname()
    if net in NEVER_RIP:
        continue
    xs = [t.GetStart().x / 1e6, t.GetEnd().x / 1e6]
    if min(xs) < BARRIER_W and max(xs) > BARRIER_E:
        straddling.append((net, xs))
        continue
    if net in ALWAYS_RIP or min(xs) >= BARRIER_E:
        doomed.append(t)

if straddling:
    print('STOP: %d track(s) cross the barrier keepout -- Gate 1 should have caught this:'
          % len(straddling))
    for net, xs in straddling[:10]:
        print('   %-16s x %.3f .. %.3f' % (net, min(xs), max(xs)))
    sys.stdout.flush()
    os._exit(1)

c = Counter(t.GetNetname() for t in doomed)
for t in doomed:
    b.Remove(t)
for n, k in sorted(c.items()):
    print('  ripped %-18s %d items' % (n, k))
print('total ripped: %d' % len(doomed))
pcbnew.SaveBoard(sys.argv[1], b)
sys.stdout.flush()
os._exit(0)
```

Two things the geometry test relies on. A track lying wholly west of the barrier on a net other than `/VBUS_HOST` is kept, which is what preserves the host side. A track that *straddles* the barrier aborts the run rather than being deleted — that would be a pre-existing isolation violation, and silently removing the evidence is the worst possible response to finding one.

**`GetTracks()` returns vias as well as segments** — `PCB_VIA` is a `PCB_TRACK` subclass — so every GND2 stitching via east of the barrier is ripped along with the copper. That is intended: Task 7 re-stitches from scratch, and stitching computed against the old placement would be wrong anyway. What survives untouched are the **zones**, which are not tracks: both ground planes keep their outlines and their stored fills until Task 7 refills them.

- [ ] **Step 3: Run it and check the damage matches expectation**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/ripup_iso_side.py isolator.kicad_pcb
```

Expected: roughly 150–170 segments removed across `/ISO_5V*`, `/DCDC_*`, `/PORT_*`, `/VBUS_HOST`, `/nFAULT`, `/PGOOD2`, `/ILIM_SET`, `/PG_LED_*`, `/FAULT_LED_A`, `/RECT_A`, `/RECT_B`, `/PP_A`, `/PP_B` and GND2, and no report of a barrier-crossing track. `/HOST_D±` must show **zero** removals.

- [ ] **Step 4: Confirm Gate 3 still passes on the host pair**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/gates/diffpair.py isolator.kicad_pcb 2>&1 | tail -20
```

Expected: `/HOST_D±` still reports its matched length and impedance. `/PORT_D±` will now fail — it was ripped, and Task 6 re-routes it.

- [ ] **Step 5: Commit**

```bash
git add tools/ripup_iso_side.py isolator.kicad_pcb && git commit -m "feat(pcb): rip up all isolated-side routing and the VBUS_HOST rail"
```

---

### Task 4: Place the isolated side

**Files:**
- Create: `tools/place_iso.py`
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: the ripped board from Task 3, and `OWNS`/`ORDER` from Task 1's gate.
- Produces: a fully placed isolated side. Task 5 routes it.

This is the task the gate from Task 1 exists to judge. Work in **board-local** mm — absolute = local + (86.88, 76.70) — matching `tools/place.py`, and say so in a comment at the top of the file.

- [ ] **Step 1: Read the existing placement for context**

Read `tools/place.py`. It carries the original placement with its reasoning in comments, including why J1 sits 0.42 mm inboard of flush and why D1/D2 must be side by side rather than in series. Preserve every such decision that this task does not deliberately overturn.

- [ ] **Step 2: Place the three star points first**

Their positions are topology decisions, so they anchor everything else:

- **NT2** between D1 and D2, near their common cathode node. The gap between the two diode courtyards is the natural home; C8 then sits immediately east of it.
- **NT1** at U5's output, east of U5 and clear of C10/C11 which must stay within 3.0/4.0 mm of U5.1.
- **NT3** at U6's output, between U6 and the C14/C15 pair.

Each tie is a `NetTie-*_SMD_Pad0.5mm`, a 1.5 × 1.5 mm copper square. Both pads of every tie must be reachable by track from opposite sides — check that before committing to a position, because a tie boxed in on one side cannot be routed without a via, and a via on a net tie defeats the point.

- [ ] **Step 3: Place everything else against the budget**

Write the `PLACEMENT` dict. Satisfy every row of the spec's ownership budget, then place the rest for routability:

- C12 within 3.0 mm of U1.20 (absolute 151.78, 95.99 — note this is 0.75 mm east of the barrier keepout, so C12 has very little room west and must go east).
- C16 within 3.0 mm of U6.1; C15 within 3.0 and C14 within 6.0 of U6.6, C15 nearer.
- C11 within 3.0 and C10 within 4.0 of U5.1, C11 nearer; C9 within 3.5 of U5.8.
- C8 within 4.0 mm of the nearer of D1.1/D2.1.
- C13 stays within 3.0 mm of U1.18 — it is already at 2.45; do not regress it.
- U3 within 5 mm of the J2 pins it protects.
- D1 and D2 side by side, **not in series** — in series the rectifier+LDO+switch zone overruns its 20 mm budget by 3.36 mm.
- The indicator cluster (R4, R5, R6, D3, D4, Q1, R9, R10) stays roughly where it is in the southern strip.

- [ ] **Step 4: Run the placement**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/place_iso.py isolator.kicad_pcb
```

- [ ] **Step 5: Check courtyard overlaps with real courtyards**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/check_placement.py isolator.kicad_pcb 2>&1 | tail -30
```

Read `tools/check_placement.py` first to see what it reports. Judge overlaps with **real** courtyards (`GetCourtyard`), never inflated bounding boxes — inflated checks "fix" deliberate tight placements and drag pads off their pins.

- [ ] **Step 6: Run the decoupling gate — this is the acceptance test for this task**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/gates/decoupling.py isolator.kicad_pcb; echo "exit=$?"
```

Expected: `VERDICT: PASS`, exit 0. All fourteen distance rows `ok` and all three ordering rows `ok`. If any row fails, move the part — do not widen the budget. The budgets came from datasheets, not from convenience.

- [ ] **Step 7: Run the two geometry gates**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/gates/edge_pullback.py isolator.kicad_pcb 2>&1 | tail -5
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/gates/barrier.py isolator.kicad_pcb isolator.kicad_pro /tmp/net.net 2>&1 | tail -8
```

Expected: both PASS. Gate 1 is creepage-aware and measures around the routed slot under T1 — a part drifting west toward the barrier can fail it in ways a straight-line intuition will not predict. If it fails, move the part east; do not touch the barrier rules in `isolator.kicad_dru`.

- [ ] **Step 8: Confirm nothing frozen moved**

```bash
cat > /tmp/frozen.py <<'EOF'
import sys, os, pcbnew
FROZEN = ['J1','J2','U1','T1','CY1','H1','H2','H3','H4','FID1','FID2','FID3',
          'U2','U4','Y1','C1','C2','C3','C4','C5','C7','D5','R1','R2']
b = pcbnew.LoadBoard(sys.argv[1])
for r in FROZEN:
    fp = b.FindFootprintByReference(r)
    p = fp.GetPosition()
    print('%-5s %9.4f %9.4f %7.1f' % (r, p.x/1e6, p.y/1e6, fp.GetOrientationDegrees()))
sys.stdout.flush(); os._exit(0)
EOF
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u /tmp/frozen.py isolator.kicad_pcb > /tmp/frozen_after.txt
git stash && /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u /tmp/frozen.py isolator.kicad_pcb > /tmp/frozen_before.txt && git stash pop
diff /tmp/frozen_before.txt /tmp/frozen_after.txt && echo "frozen parts unmoved"
```

Expected: no diff. C6 is deliberately absent from the frozen list — it moves in this task.

- [ ] **Step 9: Commit**

```bash
git add tools/place_iso.py isolator.kicad_pcb && git commit -m "feat(pcb): place the isolated side around the three star points"
```

---

### Task 5: Route the power rails

**Files:**
- Create: `tools/route_iso.py`
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: the placed board from Task 4.
- Produces: all eight branch nets plus `/VBUS_HOST` routed. Task 6 routes the signals.

- [ ] **Step 1: Read the existing routing helpers**

Read `tools/route_remaining.py` and `tools/route_port_pair.py` for this repo's track-creation idiom — layer selection, width from netclass, via placement. Reuse it rather than writing a third style.

- [ ] **Step 2: Route the star points first**

Both pads of every net tie, explicitly, on F.Cu:

- **NT2:** pad 1 → D1.1 and D2.1 and C8.1 (`/DCDC_RECT`); pad 2 → C9.1 and U5.5/U5.8 (`/DCDC_RAW`).
- **NT1:** pad 1 → U5.1/U5.2, C10.1, C11.1 (`/ISO_5V`); pad 2 → C12.1 → U1.20 (`/ISO_5V_VBUS2`); pad 3 → C16.1 → U6.1/U6.3 (`/ISO_5V_SW`); pad 4 → the southern indicator strip (`/ISO_5V_IND`).
- **NT3:** pad 1 → U6.6, C15.1, C14.1 (`/PORT_VBUS`); pad 2 → J2 VBUS pads, D6.1, U3.5, R7.1, R8.1 (`/PORT_VBUS_J2`).

**Never feed a tie pad from a pour**, and never place a via on a tie pad. A branch fed by a pour on one side looks routed to DRC while defeating the star point entirely.

- [ ] **Step 3: Route at the right widths**

`PWR` members — `/ISO_5V`, `/ISO_5V_VBUS2`, `/ISO_5V_SW`, `/DCDC_RECT`, `/DCDC_RAW`, `/PORT_VBUS`, `/PORT_VBUS_J2`, `/VBUS_HOST` — at 0.5 mm. `/ISO_5V_IND` at the `ISO_SIDE` default 0.2 mm; it carries single-digit milliamps over a ~30 mm run and its length is deliberately not optimised.

- [ ] **Step 4: Route `/VBUS_HOST` on the host side**

It was ripped in Task 3 because C6 moved and C17 is new. It must now serve: the J1 entrance and C3, U2.5, D5.1, U1.1 and C4, U4 pins 2 and 5 with C6 inboard and C7 outboard, and T1.2 with C17.

- [ ] **Step 5: Verify every branch is connected**

```bash
cat > /tmp/ratsnest.py <<'EOF'
import sys, os, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
b.BuildConnectivity()
c = b.GetConnectivity()
c.RecalculateRatsnest()
print('unconnected items:', c.GetUnconnectedCount())
sys.stdout.flush(); os._exit(0)
EOF
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u /tmp/ratsnest.py isolator.kicad_pcb
```

Expected: the count covers only the signal nets Task 6 has yet to route. Every net named in Step 2 must contribute zero.

- [ ] **Step 6: Confirm no track crosses the barrier**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/gates/barrier.py isolator.kicad_pcb isolator.kicad_pro /tmp/net.net 2>&1 | tail -8
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/route_iso.py isolator.kicad_pcb && git commit -m "feat(pcb): route the eight branch nets through their star points"
```

---

### Task 6: Route the differential pair and remaining signals

**Files:**
- Modify: `isolator.kicad_pcb`, `tools/route_iso.py`

**Interfaces:**
- Consumes: the power-routed board from Task 5.
- Produces: a fully routed board. Task 7 pours and verifies.

`/PORT_D±` is the exposure this whole plan carries. Gate 3 passed before the re-place on tuned length matching, and Task 3 ripped it. It must come back at 0.21 mm width, 0.127 mm gap, intra-pair skew ≤ 0.15 mm, 90 Ω against the stackup actually in the board file.

- [ ] **Step 1: Read how the pair was routed the first time**

Read `tools/route_port_pair.py`. It carries the original approach and the reasoning about the USB-C receptacle's A/B tie — the connector ties A6 to B6 for the same signal, so the matched length is driver → the *nearer* connector pad, and the remaining hop cannot be made symmetric because the pads interleave at 0.5 mm pitch. Gate 3 measures it that way; route it that way.

- [ ] **Step 2: Route `/PORT_D+` and `/PORT_D-`**

U1.12/U1.13 → J2.A6/B6 and J2.A7/B7, in-line through U3 pins 1/3 → 6/4 with no stubs. U3's array GND pin gets its own via straight to the plane, never daisy-chained.

- [ ] **Step 3: Verify the pair before routing anything else**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/gates/diffpair.py isolator.kicad_pcb 2>&1 | tail -20
```

Expected: PASS on both pairs, skew ≤ 0.15 mm. Fix the pair now — routing the rest of the board first only makes it harder to adjust.

- [ ] **Step 4: Route the remaining signals**

`/nFAULT`, `/PGOOD2`, `/ILIM_SET`, `/PG_LED_A`, `/PG_LED_K`, `/FAULT_LED_A`, `/PORT_CC1`, `/PORT_CC2`, `/RECT_A`, `/RECT_B`. `/ILIM_SET` wants the shortest possible run from R3 to U6.5 — SLVS841F warns that parasitics there degrade current-limit accuracy.

- [ ] **Step 5: Confirm the board is fully routed**

```bash
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u /tmp/ratsnest.py isolator.kicad_pcb
```

Expected: `unconnected items: 0`.

- [ ] **Step 6: Commit**

```bash
git add tools/route_iso.py isolator.kicad_pcb && git commit -m "feat(pcb): route PORT_D+/- and the remaining isolated-side signals"
```

---

### Task 7: Pours, stitching and full verification

**Files:**
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: the routed board from Task 6.
- Produces: the finished board. Nothing consumes this.

- [ ] **Step 1: Re-stitch GND2**

Read `tools/stitch_ground.py` and re-run it — the re-place invalidated the old stitching pattern. Keep every stitching via clear of the barrier keepout and the copper band.

- [ ] **Step 2: Refill all zones**

```bash
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc isolator.kicad_pcb -o /tmp/drc.rpt --severity-error --schematic-parity --refill-zones --exit-code-violations; echo "exit=$?"
```

`--refill-zones` matters: DRC otherwise judges the *stored* fill, and a wave of clearance or dangling errors after moving parts usually means nothing worse than a stale fill.

- [ ] **Step 3: Fix any DRC errors**

Read `/tmp/drc.rpt`. `tools/fix_drc_violations.py` exists from the original layout pass — read it before writing anything new; it may already handle the class you are seeing. Do not relax `isolator.kicad_dru`; the barrier rules in particular are load-bearing for the isolation argument.

- [ ] **Step 4: Run the whole gate suite**

```bash
python3 tools/gates/run_all.py
```

Expected: `ALL GATES PASS`. That is six gates plus DRC with schematic parity:
netclass coverage · decoupling nets · Gate 1 barrier · Gate 2 edge · Gate 3 diff pairs · Gate 5 decoupling · DRC + parity.

This is the first time in either plan that `run_all.py` is expected to be fully green. If any gate fails, fix the board — the gates encode datasheet and safety requirements, not preferences.

- [ ] **Step 5: Confirm the schematic never moved**

```bash
git diff --quiet 2c1167d HEAD -- isolator.kicad_sch && echo "schematic frozen throughout" || echo "SCHEMATIC CHANGED - investigate"
```

- [ ] **Step 6: Render the board and look at it**

```bash
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KC pcb export svg isolator.kicad_pcb -o /tmp/board.svg --layers F.Cu,F.SilkS,Edge.Cuts --exclude-drawing-sheet
rsvg-convert -z 6 -b white /tmp/board.svg -o /tmp/board.png
```

Read the PNG. Confirm by eye: the three net ties are visible as small squares with copper entering both sides; C12 sits beside U1's east edge; C14/C15 sit under U6 with C15 nearer; C8 sits at the rectifier; no silkscreen collides with a pad. Every gate in this suite is blind to things a rendering shows in a second — that lesson cost two fix rounds in the schematic pass.

- [ ] **Step 7: Commit**

```bash
git add isolator.kicad_pcb && git commit -m "feat(pcb): re-stitch GND2, refill zones, all gates green"
```

---

## What this plan does not do

Fabrication outputs — Gerbers, drill, CPL, stencil — are a separate step, and the `bom` and `jlcpcb` skills cover them. The board being gate-green is not the same as the board being ordered, and nothing here checks panelisation, solder-mask slivers, or assembly clearances.
