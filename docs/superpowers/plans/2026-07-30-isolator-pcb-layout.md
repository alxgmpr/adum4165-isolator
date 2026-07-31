# Isolator PCB Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Place and route the 43-component single-port USB isolator on a 120 × 50 mm 4-layer board for a Hammond 1455C1202, ending DRC-clean with three scripted verification gates passing.

**Architecture:** The board is built programmatically with KiCad 10's `pcbnew` Python API rather than by hand in the GUI, so every placement coordinate, zone boundary and route is reviewable in git and reproducible. Verification is three standalone gate scripts under `tools/gates/`, each of which loads the committed board file and exits non-zero on failure. The gates are written *before* the layout work they police, and each task's cycle is: write the gate, watch it fail, do the work, watch it pass, commit.

**Tech Stack:** KiCad 10.0.5. `pcbnew` via KiCad's bundled Python at `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3` (**not** system python — `pcbnew` is not importable there). `kicad-cli` at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`, not on PATH.

## Global Constraints

Every task implicitly includes these. Values are copied verbatim from the spec and from the schematic's `LAYOUT CONSTRAINTS -- BINDING` text block, which is authoritative.

- **The schematic never changes.** If layout reveals an electrical problem, stop and report it. Do not edit `isolator.kicad_sch`.
- Board is **120 × 50 mm**, origin top-left, x along the 120 mm length, y across the 50 mm width. KiCad's y axis increases downward.
- **Copper band is y ∈ [2, 48].** No copper of any kind — track, via, pad, zone fill — within 1 mm of y = 0 or y = 50, every layer, full length. 2 mm is the target, 1 mm the hard floor.
- **Barrier keepout is x ∈ [55.85, 64.15]**, exactly 8.3 mm, full 50 mm width, all four copper layers. It excludes tracks, vias and zone fill but **permits pads**.
- **U1, T1 and CY1 are the only permitted barrier crossings.** No other copper bridges the barrier on any layer.
- **No DRC rule may demand more than 8.3 mm across the barrier.** U1's pads sit at exactly 8.3000 mm; `barrier-clearance-U1` stays at 8 mm.
- U1 bypass returns to **GND1 via pins 2/10 and GND2 via pins 11/19 only**. Pins 4, 7, 15, 16, 17 are ground-only and unsuitable for bypass current.
- **D1 and D2 side by side, not in series.**
- **J1 and J2 end-launched**, mating faces flush with the outer face of the plastic end panels.
- **U2 and U3 within 5 mm** of the connector pins they protect; array GND pin on its own via straight to plane, never daisy-chained.
- **C7 + C6 at U4 pin 2 / T1 centre-tap. C4 at U1 pin 1. C3 at the J1 entrance.** Do not cluster all four VBUS_HOST caps at U1.
- Differential pairs are `USB_DIFF90`: 0.21 mm width, 0.127 mm gap. Intra-pair skew ≤ 0.15 mm.
- **Do not "fix"** the FAULT LED trip band (R3 = 93.1 kΩ) or the PGOOD push-pull arrangement (R10 populated, R9 DNP). Both are documented decisions carried to bring-up.
- No mounting holes. No fabrication outputs.

## File Structure

| File | Responsibility |
|---|---|
| `isolator.kicad_pcb` | The board. Modified by every task. |
| `isolator.kicad_pro` | Netclass patterns. Modified in Task 2 only. |
| `isolator.kicad_dru` | Custom DRC rules. Rewritten in Task 2 only. |
| `tools/gates/lib_board.py` | Shared helpers: load board, iterate copper items, mm conversion, netclass lookup. Consumed by all three gates. |
| `tools/gates/netclass_coverage.py` | Asserts every copper net is in exactly one of HOST_SIDE / ISO_SIDE, and both diff pairs are USB_DIFF90. |
| `tools/gates/barrier.py` | Gate 1. Minimum HOST_SIDE↔ISO_SIDE separation per layer, creepage-aware on F.Cu. |
| `tools/gates/edge_pullback.py` | Gate 2. No copper within 1 mm of either long edge. |
| `tools/gates/diffpair.py` | Gate 3. Intra-pair skew and 90 Ω against the board's real stackup. |
| `tools/gates/run_all.py` | Runs all gates plus `kicad-cli pcb drc`, single exit code. |
| `tools/skeleton.py` | Board outline, edge keepouts, inner-layer renaming. Task 1. |
| `tools/build_board.py` | Populates the board from the netlist: footprints, nets, pad binding. Task 3. |
| `tools/place.py` | Placement coordinate table, T1 slot, barrier keepout. Task 4. |
| `tools/planes.py` | Split GND1/GND2 pours on both inner layers. Task 5. |

Gates live in their own directory because they are the deliverable that outlives this plan — they get re-run on every future board spin.

---

### Task 1: Board skeleton — stackup, outline, edge keepouts, Gate 2

**Files:**
- Modify: `isolator.kicad_pcb`
- Create: `tools/gates/lib_board.py`
- Create: `tools/gates/edge_pullback.py`

**Interfaces:**
- Produces: `lib_board.load(path)` → `pcbnew.BOARD`; `lib_board.copper_items(board)` → yields `(layer_id, layer_name, kind, net_name, shapely-free bbox tuple (x0,y0,x1,y1) in mm)` for every track, via, pad and filled zone polygon; `lib_board.MM(iu)` and `lib_board.IU(mm)` converters.
- Produces: `edge_pullback.check(board, floor_mm=1.0, target_mm=2.0)` → `(ok: bool, violations: list[dict])`.

- [ ] **Step 1: Write the failing gate**

Create `tools/gates/lib_board.py`:

```python
"""Shared helpers for the board verification gates. Run with KiCad's python."""
import pcbnew

BOARD_LEN_MM = 120.0
BOARD_WID_MM = 50.0
COPPER_LAYERS = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]


def MM(iu):
    return pcbnew.ToMM(iu)


def IU(mm):
    return pcbnew.FromMM(mm)


def load(path):
    return pcbnew.LoadBoard(path)


def _bbox_mm(item):
    b = item.GetBoundingBox()
    return (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))


def copper_items(board):
    """Yield (layer_id, layer_name, kind, net_name, bbox_mm) for all copper."""
    for t in board.GetTracks():
        kind = 'via' if t.GetClass() == 'PCB_VIA' else 'track'
        if kind == 'via':
            for lid in COPPER_LAYERS:
                if t.IsOnLayer(lid):
                    yield (lid, board.GetLayerName(lid), kind, t.GetNetname(), _bbox_mm(t))
        else:
            lid = t.GetLayer()
            yield (lid, board.GetLayerName(lid), kind, t.GetNetname(), _bbox_mm(t))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            for lid in COPPER_LAYERS:
                if pad.IsOnLayer(lid):
                    yield (lid, board.GetLayerName(lid), 'pad:%s.%s' % (fp.GetReference(), pad.GetNumber()),
                           pad.GetNetname(), _bbox_mm(pad))
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for lid in COPPER_LAYERS:
            if not z.IsOnLayer(lid):
                continue
            poly = z.GetFilledPolysList(lid)
            for oi in range(poly.OutlineCount()):
                out = poly.Outline(oi)
                xs = [MM(out.CPoint(i).x) for i in range(out.PointCount())]
                ys = [MM(out.CPoint(i).y) for i in range(out.PointCount())]
                yield (lid, board.GetLayerName(lid), 'zone', z.GetNetname(),
                       (min(xs), min(ys), max(xs), max(ys)))
```

Create `tools/gates/edge_pullback.py`:

```python
"""Gate 2: no copper within 1 mm of either long board edge, any layer.

The 50 mm end edges are deliberately excluded -- J1 and J2 sit flush there
by constraint 6. Only the 120 mm long edges are gripped by the extrusion's
aluminium slots, and those are the ones that can short GND1 to GND2.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_board as L

FLOOR_MM = 1.0
TARGET_MM = 2.0


def check(board, floor_mm=FLOOR_MM, target_mm=TARGET_MM):
    violations, warnings = [], []
    for lid, lname, kind, net, (x0, y0, x1, y1) in L.copper_items(board):
        top_gap = y0 - 0.0
        bot_gap = L.BOARD_WID_MM - y1
        worst = min(top_gap, bot_gap)
        rec = dict(layer=lname, kind=kind, net=net, gap_mm=round(worst, 4),
                   edge='y=0' if top_gap < bot_gap else 'y=%.0f' % L.BOARD_WID_MM)
        if worst < floor_mm:
            violations.append(rec)
        elif worst < target_mm:
            warnings.append(rec)
    return (not violations), violations, warnings


def main():
    board = L.load(sys.argv[1])
    ok, violations, warnings = check(board)
    for w in warnings:
        print("  WARN  %(layer)-8s %(kind)-22s %(net)-14s %(gap_mm)6.3f mm from %(edge)s" % w)
    for v in violations:
        print("  FAIL  %(layer)-8s %(kind)-22s %(net)-14s %(gap_mm)6.3f mm from %(edge)s" % v)
    print("\nGate 2 (edge pullback): %d violations below %.1f mm, %d inside %.1f mm target"
          % (len(violations), FLOOR_MM, len(warnings), TARGET_MM))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the gate to verify it fails informatively on the empty board**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/gates/edge_pullback.py isolator.kicad_pcb
```

Expected: `PASS` with 0 violations — the board has no copper yet. That is the correct result and confirms the gate runs; it becomes meaningful from Task 3 onward. If it errors instead, fix the gate before proceeding.

- [ ] **Step 3: Build the skeleton**

Create `tools/skeleton.py`:

```python
"""Task 1: stackup, board outline, edge-pullback keepouts."""
import sys, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)

# --- inner layer names: retire the inherited GND/PWR, both are split ground ---
b.SetLayerName(pcbnew.In1_Cu, "GND_SPLIT_A")
b.SetLayerName(pcbnew.In2_Cu, "GND_SPLIT_B")

# --- board outline: 120 x 50 rectangle on Edge.Cuts ---
for x1, y1, x2, y2 in [(0, 0, 120, 0), (120, 0, 120, 50), (120, 50, 0, 50), (0, 50, 0, 0)]:
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    s.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    b.Add(s)

# --- edge pullback keepouts: 2 mm strips on both long edges, all copper layers ---
def rule_area(board, x0, y0, x1, y1, allow_pads):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(not allow_pads)
    lset = pcbnew.LSET()
    for lid in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        lset.addLayer(lid)
    z.SetLayerSet(lset)
    pts = pcbnew.VECTOR_VECTOR2I()
    for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
        pts.append(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    z.AddPolygon(pts)
    board.Add(z)
    return z

rule_area(b, 0, 0, 120, 2, allow_pads=False)     # top long edge
rule_area(b, 0, 48, 120, 50, allow_pads=False)   # bottom long edge

pcbnew.SaveBoard(BOARD, b)
print("skeleton written: outline + 2 edge keepouts, inner layers renamed")
```

Run it:

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/skeleton.py isolator.kicad_pcb
```

- [ ] **Step 4: Port the stackup from the archived 4-port board**

The `USB_DIFF90` geometry was tuned against JLCPCB JLC04161H-7628. Copy that `(stackup …)` block verbatim into `isolator.kicad_pcb`'s `(setup …)` section:

```bash
cd /Users/alex/Documents/isolator
git show 4port-archive:isolator.kicad_pcb | sed -n '/(stackup/,/^\t\t)/p' > /tmp/stackup.txt
wc -l /tmp/stackup.txt   # expect ~60 lines, F.SilkS through B.SilkS
```

Insert it inside `(setup …)` in the worktree's `isolator.kicad_pcb`. Verify the four copper thicknesses and two dielectric Er values survived:

```bash
grep -A2 'dielectric\|"In1.Cu"\|"In2.Cu"\|"F.Cu"\|"B.Cu"' isolator.kicad_pcb | grep -E 'thickness|epsilon_r'
```

Expected: `0.035`, `0.2104`/`4.4`, `0.0152`, `1.065`/`4.6`, `0.0152`, `0.2104`/`4.4`, `0.035`.

- [ ] **Step 5: Verify the skeleton**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY - <<'EOF'
import pcbnew
b = pcbnew.LoadBoard('isolator.kicad_pcb')
box = b.GetBoardEdgesBoundingBox()
print("outline mm: %.2f x %.2f" % (pcbnew.ToMM(box.GetWidth()), pcbnew.ToMM(box.GetHeight())))
print("rule areas:", sum(1 for z in b.Zones() if z.GetIsRuleArea()))
print("In1 name:", b.GetLayerName(pcbnew.In1_Cu), "| In2 name:", b.GetLayerName(pcbnew.In2_Cu))
EOF
$KIPY tools/gates/edge_pullback.py isolator.kicad_pcb
```

Expected: `outline mm: 120.10 x 50.10`, `rule areas: 2`, names `GND_SPLIT_A` / `GND_SPLIT_B`, Gate 2 `PASS`.

The bounding box reads 120.10 × 50.10, not 120.00 × 50.00, because it includes the 0.1 mm Edge.Cuts line width — 0.05 mm either side. The board really is 120 × 50 on centreline. Do not "correct" the outline to make this number read 120.00.

- [ ] **Step 6: Commit**

```bash
git add isolator.kicad_pcb tools/skeleton.py tools/gates/lib_board.py tools/gates/edge_pullback.py
git commit -m "feat(pcb): board skeleton -- 120x50 outline, JLC04161H-7628 stackup, edge keepouts, Gate 2"
```

---

### Task 2: Netclass patterns and DRC rules

**Files:**
- Modify: `isolator.kicad_pro` (`net_settings.netclass_patterns`)
- Rewrite: `isolator.kicad_dru`
- Create: `tools/gates/netclass_coverage.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `netclass_coverage.check(pro_path, netlist_path)` → `(ok, unclassified: list[str], both: list[str], diffpair_missing: list[str])`. Task 4's Gate 1 imports and re-runs this, because a net in neither domain is a silent hole in the barrier rule.

- [ ] **Step 1: Write the failing gate**

Create `tools/gates/netclass_coverage.py`:

```python
"""Every copper net must be in exactly one of HOST_SIDE / ISO_SIDE, and both
differential pairs must be USB_DIFF90.

A net in neither domain never triggers the barrier rules in isolator.kicad_dru,
which key off A.hasNetclass('HOST_SIDE') && B.hasNetclass('ISO_SIDE'). That is a
silent hole, not a visible failure, which is why it is gated.
"""
import sys, os, json, re, fnmatch

# Six single-pad nets with no routed copper. Exempt by name, deliberately.
EXEMPT_PREFIX = 'unconnected-('
DIFF_PAIRS = ['/HOST_D+', '/HOST_D-', '/PORT_D+', '/PORT_D-']


def nets_from_netlist(path):
    txt = open(path).read()
    blk = txt[txt.index('(nets'):]
    return sorted(set(re.findall(r'\(name "([^"]*)"\)', blk)))


def classes_for(net, patterns):
    return {c for c, p in patterns if fnmatch.fnmatch(net, p)}


def check(pro_path, netlist_path):
    pro = json.load(open(pro_path))
    pats = [(p['netclass'], p['pattern']) for p in pro['net_settings']['netclass_patterns']]
    side = [(c, p) for c, p in pats if c in ('HOST_SIDE', 'ISO_SIDE')]
    diff = [(c, p) for c, p in pats if c == 'USB_DIFF90']

    unclassified, both = [], []
    for n in nets_from_netlist(netlist_path):
        if n.startswith(EXEMPT_PREFIX):
            continue
        hits = classes_for(n, side)
        if not hits:
            unclassified.append(n)
        elif len(hits) > 1:
            both.append(n)

    diffpair_missing = [n for n in DIFF_PAIRS if not classes_for(n, diff)]
    ok = not unclassified and not both and not diffpair_missing
    return ok, unclassified, both, diffpair_missing


def main():
    ok, unclassified, both, missing = check(sys.argv[1], sys.argv[2])
    for n in unclassified:
        print("  FAIL  %-28s in NEITHER HOST_SIDE nor ISO_SIDE" % n)
    for n in both:
        print("  FAIL  %-28s in BOTH HOST_SIDE and ISO_SIDE" % n)
    for n in missing:
        print("  FAIL  %-28s not matched by any USB_DIFF90 pattern" % n)
    print("\nnetclass coverage: %d unclassified, %d ambiguous, %d diff-pair nets off USB_DIFF90"
          % (len(unclassified), len(both), len(missing)))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run it to verify it fails**

```bash
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KCLI sch export netlist isolator.kicad_sch -o /tmp/net.net
python3 tools/gates/netclass_coverage.py isolator.kicad_pro /tmp/net.net
```

Expected: FAIL — 13 unclassified nets (`/PP_A`, `/PP_B`, `/RECT_A`, `/RECT_B`, `/PORT_VBUS`, `/PORT_D+`, `/PORT_D-`, `/PORT_CC1`, `/PORT_CC2`, `/nFAULT`, `/FAULT_LED_A`, `/PG_LED_A`, `/PG_LED_K`) and 2 diff-pair nets off `USB_DIFF90` (`/PORT_D+`, `/PORT_D-`).

- [ ] **Step 3: Rewrite the netclass patterns**

Replace `net_settings.netclass_patterns` in `isolator.kicad_pro` with exactly this list. The 4-port patterns (`/P1_*`…`/P4_*`, `/EXT_*`, `Net-(T1*`) are dropped: they match nothing here, and `Net-(T1*` was wrong in principle because T1 spans both domains.

```json
[
  {"netclass": "USB_DIFF90", "pattern": "/HOST_D*"},
  {"netclass": "USB_DIFF90", "pattern": "/PORT_D*"},

  {"netclass": "PWR", "pattern": "/VBUS_HOST"},
  {"netclass": "PWR", "pattern": "/DCDC_RAW"},
  {"netclass": "PWR", "pattern": "/ISO_5V"},
  {"netclass": "PWR", "pattern": "/PORT_VBUS"},

  {"netclass": "HOST_SIDE", "pattern": "GND1"},
  {"netclass": "HOST_SIDE", "pattern": "/VBUS_HOST"},
  {"netclass": "HOST_SIDE", "pattern": "/VDD1"},
  {"netclass": "HOST_SIDE", "pattern": "/HOST_*"},
  {"netclass": "HOST_SIDE", "pattern": "/XTAL*"},
  {"netclass": "HOST_SIDE", "pattern": "/PP_*"},
  {"netclass": "HOST_SIDE", "pattern": "Net-(J1*"},

  {"netclass": "ISO_SIDE", "pattern": "GND2"},
  {"netclass": "ISO_SIDE", "pattern": "/VDD2"},
  {"netclass": "ISO_SIDE", "pattern": "/ISO_*"},
  {"netclass": "ISO_SIDE", "pattern": "/DCDC_*"},
  {"netclass": "ISO_SIDE", "pattern": "/RECT_*"},
  {"netclass": "ISO_SIDE", "pattern": "/PORT_*"},
  {"netclass": "ISO_SIDE", "pattern": "/PGOOD*"},
  {"netclass": "ISO_SIDE", "pattern": "/ILIM_SET"},
  {"netclass": "ISO_SIDE", "pattern": "/nFAULT"},
  {"netclass": "ISO_SIDE", "pattern": "/FAULT_LED_*"},
  {"netclass": "ISO_SIDE", "pattern": "/PG_LED_*"}
]
```

- [ ] **Step 4: Rewrite `isolator.kicad_dru`**

Replace the file with exactly this. Three corrections: creepage floor 8 mm → 8.3 mm; the `C49` reasoning replaced with CY1's; `connector-neckdown` reduced from J1–J6 to J1/J2.

```
(version 1)

# Galvanic isolation barrier: enforce creepage between host- and isolated-side
# copper. KiCad's creepage engine follows the board outline, so the routed
# slot under T1 counts toward the path.
(rule "barrier-creepage"
  (condition "(A.Type == 'Track' || A.Type == 'Via' || A.Type == 'Zone') && (B.Type == 'Track' || B.Type == 'Via' || B.Type == 'Zone') && A.hasNetclass('HOST_SIDE') && B.hasNetclass('ISO_SIDE')")
  (constraint creepage (min 8.3mm)))

# U1's land pattern measures exactly 8.3000 mm pad-edge to pad-edge -- it meets
# the requirement with zero margin. This rule stays at 8mm deliberately: setting
# it to 8.3mm puts the threshold on the same value as the geometry it is meant
# to permit, and risks rejecting the part it exists to allow.
(rule "barrier-clearance-U1"
  (condition "(A.memberOfFootprint('U1') || B.memberOfFootprint('U1')) && A.hasNetclass('HOST_SIDE') && B.hasNetclass('ISO_SIDE')")
  (constraint clearance (min 8mm)))

# T1's land pattern measures 7.5100 mm pad-edge to pad-edge -- 0.79 mm under the
# barrier requirement as a straight-line clearance. The routed slot beneath it
# removes substrate so the surface creepage path detours around the slot and
# clears 8.3 mm. This rule permits the clearance; tools/gates/barrier.py is what
# verifies the creepage path actually achieves it.
(rule "barrier-clearance-T1"
  (condition "(A.memberOfFootprint('T1') || B.memberOfFootprint('T1')) && A.hasNetclass('HOST_SIDE') && B.hasNetclass('ISO_SIDE')")
  (constraint clearance (min 7.4mm)))

# CY1 is the barrier stitching capacitor and is POPULATED, not DNP. Its 14 mm
# lead pitch gives 12.0 mm of copper gap, so it needs no relaxation -- it is
# listed here only so a future reader does not mistake its barrier crossing for
# an error.

# Fine-pitch escape: inside either connector courtyard, relax clearance to the
# JLCPCB floor so tracks can escape the 0.5 mm-pitch USB-C pad field. Custom
# rules take precedence over netclass clearances.
(rule "connector-neckdown"
  (condition "A.insideCourtyard('J1') || B.insideCourtyard('J1') || A.insideCourtyard('J2') || B.insideCourtyard('J2')")
  (constraint clearance (min 0.127mm)))
```

- [ ] **Step 5: Run the gate to verify it passes**

```bash
python3 tools/gates/netclass_coverage.py isolator.kicad_pro /tmp/net.net
```

Expected: `0 unclassified, 0 ambiguous, 0 diff-pair nets off USB_DIFF90`, `VERDICT: PASS`.

Also confirm the project file is still valid JSON and the `.dru` still parses:

```bash
python3 -c "import json; json.load(open('isolator.kicad_pro')); print('pro: valid JSON')"
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc isolator.kicad_pcb -o /tmp/drc.rpt --severity-error
```

Expected: `pro: valid JSON`, and DRC runs without a rule-parse error (violation count is irrelevant — the board is empty).

- [ ] **Step 6: Commit**

```bash
git add isolator.kicad_pro isolator.kicad_dru tools/gates/netclass_coverage.py
git commit -m "fix(pcb): netclass patterns and DRC rules for the single-port design

13 live nets matched neither HOST_SIDE nor ISO_SIDE, so the barrier rules never
fired on them -- including all four transformer winding nets, the closest copper
to the barrier on the board. /PORT_D+/- matched no USB_DIFF90 pattern and would
have routed at Default 0.2/0.25 geometry, missing 90 ohm on half the USB path.

Creepage floor raised 8mm -> 8.3mm. barrier-clearance-U1 deliberately left at
8mm: U1's pads are at exactly 8.3000mm. connector-neckdown reduced to J1/J2."
```

---

### Task 3: Populate the board from the netlist

**Files:**
- Create: `tools/build_board.py`
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: `isolator.kicad_sch` via an exported netlist; the corrected `isolator.kicad_pro` from Task 2.
- Produces: a board carrying all 43 footprints with correct references and every pad bound to its net. Task 4 consumes it via `board.FindFootprintByReference(ref)`.

All footprints are parked in a grid outside the board outline at this stage. Placement is Task 4. Splitting them means a parity failure here is unambiguous — it is a netlist problem, not a placement problem.

- [ ] **Step 1: Write the builder**

Create `tools/build_board.py`:

```python
"""Populate the board with every footprint and net from the schematic netlist.

Parks all footprints in a grid at y = 70 mm, clear of the 120x50 outline.
Placement is a separate pass (tools/place.py) so that a schematic-parity
failure here cannot be confused with a placement error.
"""
import sys, os, re, pcbnew

BOARD, NETLIST = sys.argv[1], sys.argv[2]
FPLIB_SYS = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
FPLIB_PRJ = os.path.join(os.path.dirname(os.path.abspath(BOARD)), "isolator-lib.pretty")


def parse(text):
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    stack, cur = [], []
    for t in toks:
        if t == '(':
            n = []; cur.append(n); stack.append(cur); cur = n
        elif t == ')':
            cur = stack.pop()
        elif t.startswith('"'):
            cur.append(t[1:-1])
        else:
            cur.append(t)
    return cur[0]


def find(n, k):
    return [c for c in n if isinstance(c, list) and c and c[0] == k]


def val(n, k, d=None):
    f = find(n, k)
    return f[0][1] if f and len(f[0]) > 1 else d


root = parse(open(NETLIST).read())

comps = {}
for sec in find(root, 'components'):
    for c in find(sec, 'comp'):
        comps[val(c, 'ref')] = val(c, 'footprint')

pad_nets = {}
for sec in find(root, 'nets'):
    for n in find(sec, 'net'):
        name = val(n, 'name')
        for nd in find(n, 'node'):
            pad_nets[(val(nd, 'ref'), val(nd, 'pin'))] = name

b = pcbnew.LoadBoard(BOARD)

# nets first -- a pad cannot be bound to a net the board does not know
for name in sorted(set(pad_nets.values())):
    if b.FindNet(name) is None:
        b.Add(pcbnew.NETINFO_ITEM(b, name))

placed, bound, missing = 0, 0, []
for i, (ref, fpid) in enumerate(sorted(comps.items())):
    nick, name = fpid.split(':', 1)
    lib = FPLIB_PRJ if nick == 'isolator-lib' else os.path.join(FPLIB_SYS, nick + '.pretty')
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        missing.append((ref, fpid)); continue
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(10 + (i % 8) * 14),
                                   pcbnew.FromMM(70 + (i // 8) * 14)))
    b.Add(fp)
    placed += 1
    for pad in fp.Pads():
        net = pad_nets.get((ref, pad.GetNumber()))
        if net:
            pad.SetNet(b.FindNet(net)); bound += 1

print("footprints placed: %d / %d" % (placed, len(comps)))
print("pads bound to nets: %d / %d" % (bound, len(pad_nets)))
for ref, fpid in missing:
    print("  MISSING FOOTPRINT:", ref, fpid)
if missing:
    sys.exit(1)
pcbnew.SaveBoard(BOARD, b)
print("saved")
```

- [ ] **Step 2: Run it**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KCLI sch export netlist isolator.kicad_sch -o /tmp/net.net
$KIPY tools/build_board.py isolator.kicad_pcb /tmp/net.net
```

Expected: `footprints placed: 43 / 43`, `pads bound to nets: 164 / 164`, no missing footprints.

- [ ] **Step 3: Verify against the schematic with an independent tool**

```bash
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KCLI pcb drc isolator.kicad_pcb -o /tmp/drc-parity.rpt --schematic-parity --severity-error
grep -iE "parity|missing|extra" /tmp/drc-parity.rpt | head -20
```

Expected: zero schematic-parity violations. Unconnected-item and clearance violations are expected and fine — nothing is placed or routed yet. **A parity violation here means the board does not match the schematic and must be fixed before Task 4.**

- [ ] **Step 4: Commit**

```bash
git add isolator.kicad_pcb tools/build_board.py
git commit -m "feat(pcb): populate board -- 43 footprints, 34 nets, 164 pads bound, schematic parity clean"
```

---

### Task 4: Placement and the barrier, with Gate 1

**Files:**
- Create: `tools/place.py`
- Create: `tools/gates/barrier.py`
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: the populated board from Task 3; `netclass_coverage.check` from Task 2.
- Produces: `barrier.check(board, pro_path, netlist_path)` → `(ok, per_layer: dict[str, float], failures: list[dict])`. Task 8 re-runs it unchanged.

- [ ] **Step 1: Write Gate 1**

Create `tools/gates/barrier.py`:

```python
"""Gate 1: minimum HOST_SIDE <-> ISO_SIDE copper separation, every layer, >= 8.3 mm.

Creepage-aware on F.Cu. Where the straight line between two copper features
crosses a board cutout (the routed slot under T1), the measured path runs around
the cutout, because that is the surface path a contaminant film follows. This is
what lets T1's 7.5100 mm land pattern pass on the strength of its slot rather
than by exemption.

On In1/In2/B.Cu the assertion is straight-line: T1 has no pads there, and
creepage is a surface phenomenon -- inner layers face solid dielectric.
"""
import sys, os, json, fnmatch, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_board as L
import netclass_coverage as NC
import pcbnew

REQUIRED_MM = 8.3


def _domain_map(pro_path, netlist_path):
    pro = json.load(open(pro_path))
    pats = [(p['netclass'], p['pattern']) for p in pro['net_settings']['netclass_patterns']
            if p['netclass'] in ('HOST_SIDE', 'ISO_SIDE')]
    out = {}
    for net in NC.nets_from_netlist(netlist_path):
        hits = {c for c, p in pats if fnmatch.fnmatch(net, p)}
        if len(hits) == 1:
            out[net] = hits.pop()
    return out


def _slots(board):
    """Bounding boxes (mm) of Edge.Cuts geometry that is not the outer outline."""
    outer = board.GetBoardEdgesBoundingBox()
    ow, oh = pcbnew.ToMM(outer.GetWidth()), pcbnew.ToMM(outer.GetHeight())
    out = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        bb = d.GetBoundingBox()
        w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
        if w > 0.9 * ow and h > 0.9 * oh:
            continue  # this is the outline itself
        out.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                    pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
    return out


def _gap(a, b):
    """Straight-line gap in mm between two axis-aligned bboxes."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(bx0 - ax1, ax0 - bx1, 0.0)
    dy = max(by0 - ay1, ay0 - by1, 0.0)
    return math.hypot(dx, dy)


def _crosses(a, b, slot):
    """True if the x-interval between a and b spans the slot and their y ranges
    overlap the slot -- i.e. a straight path between them passes through it."""
    sx0, sy0, sx1, sy1 = slot
    lo, hi = min(a[2], b[2]), max(a[0], b[0])
    if not (lo <= sx0 and hi >= sx1):
        return False
    ylo, yhi = min(a[1], b[1]), max(a[3], b[3])
    return not (yhi < sy0 or ylo > sy1)


def _creepage(a, b, slots):
    """Straight-line gap, or the detour around a slot when one intervenes."""
    g = _gap(a, b)
    for s in slots:
        if _crosses(a, b, s):
            sx0, sy0, sx1, sy1 = s
            mid_y = (a[1] + a[3] + b[1] + b[3]) / 4.0
            over_top = (mid_y - sy0) if mid_y > sy0 else 0.0
            over_bot = (sy1 - mid_y) if mid_y < sy1 else 0.0
            g = g + 2.0 * min(over_top, over_bot)
    return g


def check(board, pro_path, netlist_path):
    dom = _domain_map(pro_path, netlist_path)
    slots = _slots(board)
    by_layer = {}
    for lid, lname, kind, net, bb in L.copper_items(board):
        if net in dom:
            by_layer.setdefault(lname, {'HOST_SIDE': [], 'ISO_SIDE': []})[dom[net]].append((kind, net, bb))

    per_layer, failures = {}, []
    for lname, sides in sorted(by_layer.items()):
        worst, worst_pair = float('inf'), None
        for hk, hn, hb in sides['HOST_SIDE']:
            for ik, inn, ib in sides['ISO_SIDE']:
                g = _creepage(hb, ib, slots) if lname == 'F.Cu' else _gap(hb, ib)
                if g < worst:
                    worst, worst_pair = g, (hk, hn, ik, inn)
        if worst_pair is None:
            continue
        per_layer[lname] = worst
        if worst < REQUIRED_MM:
            failures.append(dict(layer=lname, gap=round(worst, 4),
                                 host='%s (%s)' % (worst_pair[0], worst_pair[1]),
                                 iso='%s (%s)' % (worst_pair[2], worst_pair[3])))
    return (not failures), per_layer, failures


def main():
    board_path, pro_path, netlist_path = sys.argv[1], sys.argv[2], sys.argv[3]

    cov_ok, unclassified, both, missing = NC.check(pro_path, netlist_path)
    if not cov_ok:
        print("  FAIL  netclass coverage is incomplete -- the barrier rules do not")
        print("        police every net, so this gate cannot be trusted. Fix first:")
        for n in unclassified + both + missing:
            print("          ", n)
        print("VERDICT: FAIL")
        sys.exit(1)

    board = L.load(board_path)
    ok, per_layer, failures = check(board, pro_path, netlist_path)
    for lname, g in per_layer.items():
        mode = 'creepage' if lname == 'F.Cu' else 'clearance'
        print("  %-12s min HOST<->ISO %s: %8.4f mm" % (lname, mode, g))
    for f in failures:
        print("  FAIL  %(layer)s  %(gap).4f mm  between %(host)s and %(iso)s" % f)
    print("\nGate 1 (barrier >= %.1f mm): %d layer(s) failing" % (REQUIRED_MM, len(failures)))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run it to verify it fails**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/gates/barrier.py isolator.kicad_pcb isolator.kicad_pro /tmp/net.net
```

Expected: FAIL. All 43 footprints are still parked in the Task 3 grid at y ≈ 70, interleaved, so host and isolated copper sit millimetres apart.

- [ ] **Step 3: Write the placement pass**

Create `tools/place.py`. The three barrier-crossing parts carry exact coordinates from the spec; the rest are placed by zone. Every part's rotation is chosen so its long axis suits its zone.

```python
"""Task 4: placement. Coordinates in mm, board origin top-left, y increases down."""
import sys, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)

# ref: (x, y, rotation_deg)
PLACEMENT = {
    # --- barrier crossings: exact, from the design spec ---
    'U1':  (60.00, 25.00,   0),   # pads 1-10 at x=55.10, 11-20 at x=64.90
    'T1':  (60.00, 10.16,   0),   # pads at x=55.295/64.705, intrude 0.395 mm/side
    'CY1': (53.00, 38.02,   0),   # origin at pad 1; pads at x=53 and x=67

    # --- zone 1: J1 entrance (host) ---
    'J1':  ( 4.71, 25.00,   0),
    'U2':  (12.50, 25.00,   0),
    'D5':  (16.80, 25.00,   0),
    'C3':  (16.80, 31.00,   0),

    # --- zone 2: ADuM Side 1, crystal, SN6505B (host) ---
    'C4':  (52.00, 18.00,  90),
    'C5':  (52.00, 32.00,  90),
    'Y1':  (34.00, 33.00,   0),
    'C1':  (30.00, 36.50,   0),
    'C2':  (38.00, 36.50,   0),
    'U4':  (34.00, 10.16,   0),
    'C6':  (40.00, 10.16,  90),
    'C7':  (44.00, 10.16,  90),
    'R1':  (10.00, 34.00,  90),
    'R2':  (10.00, 38.00,  90),

    # --- zone 4: rectifier, LDO, current-limit switch (isolated) ---
    'D1':  (70.00,  8.00,   0),   # side by side with D2 -- NOT in series
    'D2':  (70.00, 14.00,   0),
    'C8':  (77.00, 11.00,   0),
    'U5':  (83.00, 11.00,   0),
    'C9':  (88.00,  8.00,   0),
    'C10': (88.00, 14.00,   0),
    'U6':  (94.00, 25.00,   0),
    'R3':  (94.00, 31.00,  90),
    'C11': (89.00, 25.00,  90),
    'C12': (99.00, 25.00,  90),
    'D3':  (86.00, 40.00,   0),
    'D4':  (92.00, 40.00,   0),
    'R4':  (98.00, 40.00,  90),
    'R5':  (92.00, 44.00,  90),
    'R6':  (86.00, 44.00,  90),
    'Q1':  (80.00, 40.00,   0),
    'R9':  (74.00, 40.00,  90),
    'R10': (74.00, 44.00,  90),
    'C13': (70.00, 25.00,  90),
    'C14': (108.00, 31.00,  0),
    'C15': (104.00, 31.00,  0),

    # --- zone 5: J2 exit (isolated) ---
    'D6':  (103.20, 25.00,  0),
    'U3':  (107.50, 25.00,  0),
    'J2':  (115.29, 25.00, 180),

    # --- remaining passives ---
    'R7':  (112.00, 34.00, 90),
    'R8':  (112.00, 38.00, 90),
}

missing = []
for ref, (x, y, rot) in PLACEMENT.items():
    fp = b.FindFootprintByReference(ref)
    if fp is None:
        missing.append(ref); continue
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    fp.SetOrientationDegrees(rot)

unplaced = [f.GetReference() for f in b.GetFootprints() if f.GetReference() not in PLACEMENT]
print("placed: %d" % (len(PLACEMENT) - len(missing)))
if missing:
    print("  REF IN TABLE BUT NOT ON BOARD:", missing)
if unplaced:
    print("  ON BOARD BUT NOT IN TABLE:", unplaced)
if missing or unplaced:
    sys.exit(1)

# --- routed slot under T1: what converts 7.51 mm clearance into >= 8.3 mm creepage ---
# Starting geometry. Gate 1 is the authority -- widen or lengthen until it passes.
SLOT_W, SLOT_Y0, SLOT_Y1 = 2.0, 3.34, 16.98   # 2 mm beyond T1's pad rows each end
for x1, y1, x2, y2 in [(60 - SLOT_W / 2, SLOT_Y0, 60 + SLOT_W / 2, SLOT_Y0),
                       (60 + SLOT_W / 2, SLOT_Y0, 60 + SLOT_W / 2, SLOT_Y1),
                       (60 + SLOT_W / 2, SLOT_Y1, 60 - SLOT_W / 2, SLOT_Y1),
                       (60 - SLOT_W / 2, SLOT_Y1, 60 - SLOT_W / 2, SLOT_Y0)]:
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    s.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    b.Add(s)

# --- barrier keepout: excludes tracks/vias/pour, PERMITS pads ---
# T1's pads intrude 0.395 mm per side and are a permitted crossing, so a
# blanket no-copper rule area would reject the part it exists to accommodate.
z = pcbnew.ZONE(b)
z.SetIsRuleArea(True)
z.SetDoNotAllowTracks(True)
z.SetDoNotAllowVias(True)
z.SetDoNotAllowZoneFills(True)
z.SetDoNotAllowPads(False)
lset = pcbnew.LSET()
for lid in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
    lset.addLayer(lid)
z.SetLayerSet(lset)
pts = pcbnew.VECTOR_VECTOR2I()
for x, y in [(55.85, 0), (64.15, 0), (64.15, 50), (55.85, 50)]:
    pts.append(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
z.AddPolygon(pts)
b.Add(z)

pcbnew.SaveBoard(BOARD, b)
print("placement, T1 slot and barrier keepout written")
```

- [ ] **Step 4: Run placement, then assert the binding constraints**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/place.py isolator.kicad_pcb
$KIPY - <<'EOF'
import pcbnew, itertools, sys
b = pcbnew.LoadBoard('isolator.kicad_pcb')
M = pcbnew.ToMM
fail = []

def crtyd(ref):
    fp = b.FindFootprintByReference(ref)
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    return M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetRight()), M(bb.GetBottom())

# 1. every courtyard inside the copper band and clear of the barrier keepout
for fp in b.GetFootprints():
    r = fp.GetReference()
    x0, y0, x1, y1 = crtyd(r)
    if y0 < 2.0 or y1 > 48.0:
        fail.append("%s courtyard outside copper band y[2,48]: %.2f..%.2f" % (r, y0, y1))
    if r not in ('U1', 'T1', 'CY1') and x1 > 55.85 and x0 < 64.15:
        fail.append("%s intrudes into the barrier keepout and is not a permitted crossing" % r)

# 2. no courtyard overlaps
for a, c in itertools.combinations([f.GetReference() for f in b.GetFootprints()], 2):
    ax0, ay0, ax1, ay1 = crtyd(a); cx0, cy0, cx1, cy1 = crtyd(c)
    if not (ax1 < cx0 or cx1 < ax0 or ay1 < cy0 or cy1 < ay0):
        fail.append("courtyard overlap: %s and %s" % (a, c))

# 3. D1 and D2 side by side, not in series (same x band, different y)
d1, d2 = crtyd('D1'), crtyd('D2')
if not (abs(d1[0] - d2[0]) < 2.0 and (d1[3] < d2[1] or d2[3] < d1[1])):
    fail.append("D1/D2 are not side by side")

# 4. ESD arrays within 5 mm of the connector they protect
for esd, conn in (('U2', 'J1'), ('U3', 'J2')):
    e, c = crtyd(esd), crtyd(conn)
    gap = max(c[0] - e[2], e[0] - c[2], 0.0)
    if gap > 5.0:
        fail.append("%s is %.2f mm from %s, limit 5 mm" % (esd, gap, conn))

for f in fail:
    print("  FAIL ", f)
print("\nplacement assertions: %d failures" % len(fail))
sys.exit(1 if fail else 0)
EOF
```

Expected: `0 failures`. Any failure means the coordinate table needs adjusting — fix `tools/place.py` and re-run.

- [ ] **Step 5: Run Gate 1 to verify it now passes**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/gates/barrier.py isolator.kicad_pcb isolator.kicad_pro /tmp/net.net
```

Expected: `VERDICT: PASS`, with F.Cu reported as `creepage` and the other three as `clearance`, all ≥ 8.3000 mm.

**If F.Cu fails at ~7.51 mm**, the T1 slot is not yet doing its job. Increase `SLOT_Y0`/`SLOT_Y1` span or `SLOT_W` in `tools/place.py` and re-run. Do not exempt T1 from the gate — the slot is the mechanism, and the gate measuring it is the point.

- [ ] **Step 6: Commit**

```bash
git add isolator.kicad_pcb tools/place.py tools/gates/barrier.py
git commit -m "feat(pcb): placement, T1 barrier slot, barrier keepout, Gate 1 passing"
```

---

### Task 5: Split ground planes

**Files:**
- Create: `tools/planes.py`
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: the placed board from Task 4.
- Produces: four filled zones — GND1 and GND2 on In1.Cu and In2.Cu — each clipped by the barrier keepout and the edge strips. Tasks 6 and 7 rely on these for return paths.

- [ ] **Step 1: Write the plane pass**

Create `tools/planes.py`:

```python
"""Task 5: split ground pours. Both inner layers carry GND1 host-side and GND2
isolated-side. A single continuous inner plane would bridge the barrier."""
import sys, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)

# Host side stops before the barrier keepout, isolated side starts after it.
# The keepout itself would clip the fill anyway; stating the bounds explicitly
# means the intent survives even if the keepout is ever edited.
REGIONS = [
    ('GND1', 2.0, 2.0, 55.85, 48.0),
    ('GND2', 64.15, 2.0, 118.0, 48.0),
]

for lid in (pcbnew.In1_Cu, pcbnew.In2_Cu):
    for net_name, x0, y0, x1, y1 in REGIONS:
        net = b.FindNet(net_name)
        if net is None:
            print("  net not found:", net_name); sys.exit(1)
        z = pcbnew.ZONE(b)
        z.SetLayer(lid)
        z.SetNet(net)
        z.SetIsFilled(True)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        pts = pcbnew.VECTOR_VECTOR2I()
        for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            pts.append(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        z.AddPolygon(pts)
        b.Add(z)

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)

for z in b.Zones():
    if not z.GetIsRuleArea():
        print("%-12s %-6s filled %8.2f mm^2" % (b.GetLayerName(z.GetLayer()), z.GetNetname(),
                                                pcbnew.ToMM(pcbnew.ToMM(z.GetFilledArea()))))
```

- [ ] **Step 2: Run it**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/planes.py isolator.kicad_pcb
```

Expected: four filled zones, each with non-zero area. A zone reporting `0.00 mm^2` means the fill was fully clipped — investigate before continuing.

- [ ] **Step 3: Verify no plane bridges the barrier**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/gates/barrier.py isolator.kicad_pcb isolator.kicad_pro /tmp/net.net
$KIPY tools/gates/edge_pullback.py isolator.kicad_pcb
```

Expected: both `PASS`. Gate 1 now has zone copper to measure on In1/In2 — this is the first run where the inner layers carry anything, and it is the run that proves the split actually holds.

- [ ] **Step 4: Commit**

```bash
git add isolator.kicad_pcb tools/planes.py
git commit -m "feat(pcb): split GND1/GND2 pours on both inner layers, barrier intact"
```

---

### Task 6: Route the differential pairs, with Gate 3

**Files:**
- Create: `tools/gates/diffpair.py`
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: the poured board from Task 5.
- Produces: `diffpair.check(board)` → `(ok, results: list[dict])` with per-pair skew and computed differential impedance.

- [ ] **Step 1: Write Gate 3**

Create `tools/gates/diffpair.py`:

```python
"""Gate 3: differential pairs are length-matched and hit 90 ohm against the
stackup actually in the board file -- not a nominal one.

Reading the real stackup is the point of this gate: it is what catches the board
being fabricated on a substrate the trace geometry was never tuned for.
"""
import sys, os, re, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_board as L
import pcbnew

PAIRS = [('/HOST_D+', '/HOST_D-'), ('/PORT_D+', '/PORT_D-')]
SKEW_LIMIT_MM = 0.15
Z_TARGET, Z_TOL = 90.0, 0.10


def stackup_from_file(path):
    """Outer-layer geometry: prepreg thickness and Er between F.Cu and In1.Cu."""
    txt = open(path).read()
    m = re.search(r'\(stackup(.*?)\n\t\t\)', txt, re.S)
    if not m:
        return None
    blk = m.group(1)
    d1 = re.search(r'\(layer "dielectric 1".*?\(thickness ([\d.]+)\).*?\(epsilon_r ([\d.]+)\)', blk, re.S)
    cu = re.search(r'\(layer "F\.Cu".*?\(thickness ([\d.]+)\)', blk, re.S)
    if not (d1 and cu):
        return None
    return dict(h=float(d1.group(1)), er=float(d1.group(2)), t=float(cu.group(1)))


def z_diff_microstrip(w, s, h, er, t):
    """Edge-coupled microstrip. IPC-2141 single-ended Z0, then the standard
    coupling correction for differential pairs."""
    z0 = (87.0 / math.sqrt(er + 1.41)) * math.log(5.98 * h / (0.8 * w + t))
    return 2.0 * z0 * (1.0 - 0.48 * math.exp(-0.96 * s / h))


def net_length(board, net):
    return sum(pcbnew.ToMM(t.GetLength()) for t in board.GetTracks()
               if t.GetNetname() == net and t.GetClass() != 'PCB_VIA')


def pair_geometry(board, net):
    ws = {round(pcbnew.ToMM(t.GetWidth()), 4) for t in board.GetTracks()
          if t.GetNetname() == net and t.GetClass() != 'PCB_VIA'}
    return ws


def check(board, board_path):
    su = stackup_from_file(board_path)
    results, ok = [], True
    if su is None:
        return False, [dict(pair='-', error='no (stackup ...) block in the board file; '
                                            '90 ohm cannot be checked against anything')]
    for a, c in PAIRS:
        la, lc = net_length(board, a), net_length(board, c)
        skew = abs(la - lc)
        widths = pair_geometry(board, a) | pair_geometry(board, c)
        if la == 0 or lc == 0:
            results.append(dict(pair=a + '/' + c, error='unrouted'))
            ok = False
            continue
        if len(widths) != 1:
            results.append(dict(pair=a + '/' + c, error='mixed track widths %s' % sorted(widths)))
            ok = False
            continue
        w = widths.pop()
        s = 0.127   # USB_DIFF90 diff_pair_gap
        z = z_diff_microstrip(w, s, su['h'], su['er'], su['t'])
        pass_skew = skew <= SKEW_LIMIT_MM
        pass_z = abs(z - Z_TARGET) <= Z_TARGET * Z_TOL
        ok = ok and pass_skew and pass_z
        results.append(dict(pair=a + '/' + c, len_a=la, len_b=lc, skew=skew, w=w, s=s,
                            h=su['h'], er=su['er'], z=z,
                            pass_skew=pass_skew, pass_z=pass_z))
    return ok, results


def main():
    path = sys.argv[1]
    board = L.load(path)
    ok, results = check(board, path)
    for r in results:
        if 'error' in r:
            print("  FAIL  %-22s %s" % (r['pair'], r['error']))
            continue
        print("  %-22s len %.3f / %.3f mm  skew %.4f mm  [%s]"
              % (r['pair'], r['len_a'], r['len_b'], r['skew'], 'OK' if r['pass_skew'] else 'FAIL'))
        print("  %-22s w=%.3f s=%.3f h=%.4f er=%.2f -> Zdiff %.2f ohm  [%s]"
              % ('', r['w'], r['s'], r['h'], r['er'], r['z'], 'OK' if r['pass_z'] else 'FAIL'))
    print("\nGate 3 (diff pairs): skew limit %.2f mm, Zdiff %.0f ohm +/-%d%%"
          % (SKEW_LIMIT_MM, Z_TARGET, int(Z_TOL * 100)))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run it to verify it fails**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/gates/diffpair.py isolator.kicad_pcb
```

Expected: FAIL, both pairs `unrouted`.

- [ ] **Step 3: Route the two pairs**

Route on F.Cu, referencing the In1.Cu ground pour. `USB_DIFF90` geometry: 0.21 mm width, 0.127 mm gap.

- `/HOST_D±`: J1 pads A6/B6 and A7/B7 → U2 pins 1/3 → U2 pins 6/4 → U1 pins 8/9. In-line through the array, no stubs (constraint 3).
- `/PORT_D±`: U1 pins 12/13 → U3 pins 1/3 → U3 pins 6/4 → J2 pads A6/B6 and A7/B7.

Neither pair crosses the barrier — U1 crosses it internally.

Route interactively in pcbnew, or scripted with `pcbnew.PCB_TRACK` following the pattern probed in Task 1. Whichever is used, the gate is the arbiter. Keep both nets of a pair on the same layer for their whole run so the skew figure is meaningful.

- [ ] **Step 4: Run Gate 3 to verify it passes**

```bash
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY tools/gates/diffpair.py isolator.kicad_pcb
```

Expected: both pairs report skew ≤ 0.15 mm and Zdiff within 81–99 Ω, `VERDICT: PASS`.

If Zdiff lands outside the band, **do not widen the tolerance.** Either the trace width is wrong for this stackup or the stackup is not the one the geometry was tuned against. Report which.

- [ ] **Step 5: Commit**

```bash
git add isolator.kicad_pcb tools/gates/diffpair.py
git commit -m "feat(pcb): route HOST_D+/- and PORT_D+/- as 90 ohm pairs, Gate 3 passing"
```

---

### Task 7: Route power and remaining signals

**Files:**
- Modify: `isolator.kicad_pcb`

**Interfaces:**
- Consumes: the board from Task 6.
- Produces: a fully-routed board with zero unconnected items.

- [ ] **Step 1: Route the power nets**

`PWR` netclass, 0.5 mm tracks: `VBUS_HOST` (J1 → C3 → U1 pin 1 via C4, and → U4/C6/C7), `DCDC_RAW` (D1/D2 cathodes → C8 → U5), `ISO_5V` (U5 → C9/C10 → U6), `PORT_VBUS` (U6 → C14/C15 → J2).

Honour constraint 9: C7 and C6 stay at U4 pin 2 / T1 centre-tap, C4 at U1 pin 1, C3 at the J1 entrance. Do not route all four back to a single cluster.

- [ ] **Step 2: Route the remaining signals**

`/XTALIN`, `/XTALOUT` (short, direct, Y1 close to U1 Side 1); `/VDD1`, `/VDD2` bypass returns — **GND1 through U1 pins 2/10 and GND2 through pins 11/19 only**, never pins 4/7/15/16/17 (constraint 8); `/PP_A`, `/PP_B` (U4 → T1 primary); `/RECT_A`, `/RECT_B` (T1 secondary → D1/D2); `/ILIM_SET`, `/nFAULT`, `/FAULT_LED_A`, `/PG_LED_A`, `/PG_LED_K`, `/PGOOD2`; `/PORT_CC1`, `/PORT_CC2`, `Net-(J1-CC1)`, `Net-(J1-CC2)`.

Each ESD array's GND pin gets **its own via straight to the plane**, not daisy-chained through a neighbour (constraint 3).

- [ ] **Step 3: Refill zones and check connectivity**

```bash
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KCLI pcb drc isolator.kicad_pcb -o /tmp/drc.rpt --severity-error --refill-zones --save-board --schematic-parity
grep -E "^\*\*|violations|unconnected" /tmp/drc.rpt | head
```

Expected: `Found 0 violations`, `Found 0 unconnected items`, zero schematic-parity issues.

- [ ] **Step 4: Commit**

```bash
git add isolator.kicad_pcb
git commit -m "feat(pcb): route power and remaining signals, DRC clean, zero unconnected"
```

---

### Task 8: Combined gate runner and layout review

**Files:**
- Create: `tools/gates/run_all.py`
- Create: `docs/superpowers/reviews/2026-07-30-pcb-layout-review.md`

**Interfaces:**
- Consumes: all three gates and the routed board.
- Produces: one command that decides whether the board is shippable.

- [ ] **Step 1: Write the runner**

Create `tools/gates/run_all.py`:

```python
"""Run every layout gate plus DRC. Exit 0 only if all pass."""
import subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
KIPY = '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
KCLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
BOARD = os.path.join(PROJ, 'isolator.kicad_pcb')
SCH = os.path.join(PROJ, 'isolator.kicad_sch')
PRO = os.path.join(PROJ, 'isolator.kicad_pro')
NET = '/tmp/net.net'

subprocess.run([KCLI, 'sch', 'export', 'netlist', SCH, '-o', NET], check=True,
               stdout=subprocess.DEVNULL)

steps = [
    ('netclass coverage', ['python3', os.path.join(HERE, 'netclass_coverage.py'), PRO, NET]),
    ('Gate 1 barrier',    [KIPY, os.path.join(HERE, 'barrier.py'), BOARD, PRO, NET]),
    ('Gate 2 edge',       [KIPY, os.path.join(HERE, 'edge_pullback.py'), BOARD]),
    ('Gate 3 diff pairs', [KIPY, os.path.join(HERE, 'diffpair.py'), BOARD]),
    ('DRC + parity',      [KCLI, 'pcb', 'drc', BOARD, '-o', '/tmp/drc.rpt',
                           '--severity-error', '--schematic-parity',
                           '--refill-zones', '--exit-code-violations']),
]

failed = []
for name, cmd in steps:
    print("\n" + "=" * 64 + "\n== " + name + "\n" + "=" * 64)
    if subprocess.run(cmd).returncode != 0:
        failed.append(name)

print("\n" + "=" * 64)
print("FAILED: " + ", ".join(failed) if failed else "ALL GATES PASS")
sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Run it**

```bash
python3 tools/gates/run_all.py
```

Expected: `ALL GATES PASS`, exit 0.

- [ ] **Step 3: Write the layout review**

Create `docs/superpowers/reviews/2026-07-30-pcb-layout-review.md` recording: the achieved minimum barrier separation per layer (real numbers from Gate 1, not the requirement restated); the achieved edge pullback minimum; measured pair lengths, skew and computed Zdiff with the stackup values used; final DRC and unconnected counts; and the T1 slot dimensions actually needed to clear 8.3 mm creepage versus the 2 mm × 13.64 mm starting geometry.

Carry forward, explicitly unresolved by layout: the FAULT LED trip band (R3 = 93.1 kΩ, 252–324 mA against a ~243 mA supply) and PGOOD push-pull with R10 populated / R9 DNP.

- [ ] **Step 4: Commit**

```bash
git add tools/gates/run_all.py docs/superpowers/reviews/2026-07-30-pcb-layout-review.md
git commit -m "feat(pcb): combined gate runner and layout review record"
```

---

## Self-review

**Spec coverage.** Board geometry → Task 1. Stackup → Task 1 Step 4. Netclass and DRU corrections (Findings 2, 3, 5) → Task 2. Board population → Task 3. Barrier geometry, T1 slot, keepout-permits-pads (Finding 1) → Task 4. Split planes → Task 5. Diff pairs → Task 6. Power and remaining signals → Task 7. All three gates → Tasks 1, 4, 6, consolidated in Task 8. Bring-up carry-forwards → Task 8 Step 3.

**Known soft spots, stated rather than hidden:**

- `tools/place.py`'s coordinate table is a first pass. The Task 4 Step 4 assertions (courtyard overlap, copper band, barrier intrusion, D1/D2, ESD proximity) are what make it correct; expect to iterate the table until they pass rather than to get it right first time.
- Gate 1's creepage model uses axis-aligned bounding boxes and a slot-detour approximation, not exact polygon geometry. It is conservative for the barrier's rectangular arrangement, which is what matters here, but it is not a general-purpose creepage solver. It would need real polygon offsetting to be trusted on an arbitrary board.
- `z_diff_microstrip` is the IPC-2141 closed form. It is an estimate, good to roughly ±5 % against a 2-D field solver, which is why the gate uses a ±10 % band. It checks that the geometry and the stackup are consistent with each other — it is not a substitute for the fab's own impedance report.
