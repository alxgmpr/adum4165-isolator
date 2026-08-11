# Continuation prompt — rev B isolated 4-port USB hub

Paste everything below the line into a new chat.

---

I'm building **rev B of an isolated USB hub** in KiCad at `/Users/alex/Documents/isolator` (branch `main`, everything committed and pushed). Tasks 1–7 of a 12-task plan are done. I want to finish **Task 8** (four downstream port switches + connectors + ESD) and **Task 9** (barrier stitching cap, PWR_FLAGs, ERC to zero), then stop. Tasks 10–12 are deferred.

## Read these first, in this order

1. `docs/superpowers/specs/2026-08-08-isolated-hub-revb-design.md` — the design spec
2. `docs/superpowers/reviews/2026-08-08-revb-part-selection.md` — **the authoritative decision record.** Where it disagrees with the spec or the plan, it wins. It has every part, value, pin table and net name, with datasheet citations.
3. `docs/superpowers/plans/2026-08-08-revb-hub-schematic.md` — the task plan (Tasks 8 and 9 are what remain)
4. `.superpowers/sdd/2026-08-08-revb-hub-schematic/progress.md` — the full execution ledger: every finding, ruling, and trap from Tasks 1–7

## What the board is

USB-C host → ADuM4165 (5.7 kV isolator) → USB2514B 4-port hub → 2× USB-A + 2× USB-C. Isolated power is an SN6505B push-pull converter across a 750313638 transformer, rectified, then a **TPS630701RNMR fixed-5 V buck-boost** (not a buck — the adjustable version's feedback divider put the worst-case port 9 mV under the USB floor). A TPS2121 muxes that against an external USB-C supply. New versus both predecessor boards: comparators on the **host** port's CC lines detect the 1.5 A advertisement and gate `SN6505B.EN`, so the board can legally draw ~870 mA instead of 500 mA. Bus-powered ports share ≈414 mA.

## State: `hub.kicad_sch`, 105 components, 91 nets

Captured and verified: upstream host section, CC sensing, isolated converter, external input + mux, ADuM Side 2, USB2514B hub, 3.3 V rail. `PRTPWR1..4` and `OCS1..4` exist as single-pin nets waiting for Task 8.

## Three known defects to fix

1. **Y2's crystal case is floating** — `Net-(Y2-G-Pad2)` holds only `Y2.2`/`Y2.4`, not tied to `GND2`. (Y1 on the ADuM side is correct.)
2. **Y2 load caps are 18 pF**; the archived design used 12 pF. Check against the USB2514B datasheet's CL spec.
3. **102 Reference/Value field pairs are closer than 2.54 mm**, so text collides. Caused by an eeschema save (see traps).

## Task 8 constraints that matter

- **56 kΩ Rp per USB-C CC pin, dedicated, never shared.** Do NOT fit 22 kΩ — bus-powered ports share ~414 mA and over-advertising is what caused rev A's brown-out behaviour.
- **ILIM: compute from all three of SLVS841F's min/typ/max equations**, not by scaling the nominal. Rev A set 93.1 kΩ and ended up with a guaranteed-minimum trip point *above* what its supply could deliver, so the FAULT LED could never light. Target 500 mA per port in external-supply mode. Note the part is **TPS2553DBV** — 85/95 mΩ at 25 °C, **135 mΩ max over temperature**; the 100/115/140 figures are the DRV package.
- Per-port `EN` from hub `PRTPWR`, `~FAULT` to hub `OCS`.
- USBLC6-2SC6 per port, flow-through (in on 1/3, out on 6/4), `VBUS` pin 5 to that port's switched rail.
- Build **one** port completely and verify it before replicating. Four structurally identical port blocks are the intended design, not a DRY defect — that ruling is already recorded.

## Task 9

CY1 (1 nF **Y1-rated**, populated not DNP) is the only intentional GND1↔GND2 connection. PWR_FLAGs in a dedicated corner area, not inline. Drive ERC to zero at `--severity-all`. Also place the no-connect flag on `U6.FB2` and clear the pre-existing `R16`/`#PWR090` symbol overlap.

## Tooling reality — read this before doing anything

`kicad-cli` is at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` (not on PATH).

**MCP-driven schematic capture took ~78 minutes per circuit block.** I drew Task 7 by hand in eeschema much faster. Strongly consider drawing Task 8 by hand and having the agent do verification, which is fast and is where the real bugs were caught.

Traps, all of which cost real time:

- **An eeschema save rewrites every symbol's field offsets** and undoes MCP layout work. Do any layout polish ONCE, last, in whichever tool edits last.
- **Konnect MCP disconnects often.** When it does, no capture is possible. The kicad-happy MCP (`mcp__kicad__*`) is a separate server and often survives — it has `autoplace_schematic_fields`, `batch_set_schematic_property_positions`, `lint_schematic_cosmetic`.
- **A subagent's tool list is snapshotted at dispatch.** Konnect's `load_toolset` called *inside* a subagent registers server-side but never becomes callable there. The controller must pre-load toolsets before dispatching.
- **Wires routed through an unrelated pin silently short nets.** Neither the parse gate nor the overlap checker sees it — only a netlist diff does. Task 6 created three such shorts.
- **`move_region` / `move_connected` snap to a 1.27 mm grid** and detach pins that connect by sitting on another pin. They broke the netlist twice.
- **`add_schematic_text` with embedded newlines** yields a file KiCad's parser rejects while SVG rendering still works. One single-line text node per line; re-export a netlist after every text batch.
- **`autoplace_schematic_fields` leaves 1.27 mm between Reference and Value** — one line pitch, zero clearance. Widen to ≥ 2.54 mm afterwards. It also ignores power symbols entirely.
- Konnect's `check_schematic_overlaps` returns 0 on files with real overlaps. Useless.

## Verification gates — run all of these

```bash
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KCLI sch export netlist --format kicadxml -o /tmp/n.xml hub.kicad_sch   # parse gate
python3 tools/check_isolation.py /tmp/n.xml                              # only U1, T1, CY1 may bridge domains
python3 tools/check_sch_text_overlap.py hub.kicad_sch                     # text overlaps AND off-page items
$KCLI sch erc hub.kicad_sch --output /tmp/erc.rpt --severity-all --exit-code-violations
```

Plus a short check — no pin may appear on more than one net — and **render the sheet and actually look at it**; no automated gate on this project detects symbol-vs-symbol overlap or judges density.

One off-page item remains: a `GND2` net label at y≈293.4, needs a label-move tool.

## How I want you to work

Follow the decision record over the spec and plan where they conflict. Verify mechanically rather than dispatching review subagents — that's what I asked for and it works. Tell me plainly when something is blocked rather than working around it.
