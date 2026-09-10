# Rev C verification record

Design handoff: 2026-09-10, branch `codex/revc-isousb211`. Verified with KiCad
CLI **10.99.0-3770-gd7e34de179** and the project-local Python review scripts.
These results apply to the captured schematic and **unrouted placement**.

| Gate | Final result | Evidence |
|---|---|---|
| ERC | **0 errors, 0 warnings, no exclusions** | [erc-final.txt](reports/erc-final.txt) |
| PCB geometry/rule checks | **0 violations**, including courtyard, edge, copper clearance and creepage | [drc-final.json](reports/drc-final.json) |
| Schematic/PCB parity | **0 issues**, explicit CLI `--schematic-parity` | Same DRC report |
| Expected unrouted connections | **499**, reported separately; check remains enabled as error | `unconnected_items` in DRC report |
| Routed geometry | **0 tracks, 0 vias, 0 filled copper zones** | [Inventory and isolation](reports/pcb-inventory-and-isolation.json) |
| Component synchronization | 291 schematic parts; 295 PCB footprints including H1–H4; zero missing/extra electrical parts | Same inventory report |
| Pad/net inventory | 987 physical pad rows including duplicate lands; no connected-pin differences | [Symbol/pad audit](symbol-pad-net-audit.json), [PCB pad map](reports/pcb-pad-net-map.csv) |
| Critical pin/control assertions | 42 component checks pass; USB polarity, power mux, host reset, Type-C attach/discharge, aggregate fault and programming pads | [Electrical invariants](reports/electrical-invariants.json) |
| Domain separation | Only U1, T1 and CY1 span domains; no mixed-domain conductive net | [Net domains](reports/net-domains.json), electrical invariants |
| Physical barrier | 8.200 mm at TI HV lands; 9.410 mm minimum outside U1; all four copper layers have barrier keepout | Inventory/isolation report |
| Mechanical placement | 136 × 116 mm outline, R3 corners, four 3.2 mm NPTH holes; no courtyard collisions | [Mechanical report](reports/mechanical.json), [assumptions](MECHANICAL.md) |
| Shields | Separate GND1/GND2 frames; 16.37 mm outer-envelope gap; calculated lid margins 0.99/4.10 mm | Mechanical report; [covers BOM](BOM-covers.csv) |
| Libraries/BOM | Every physical symbol has a local footprint; exact MPN/manufacturer/datasheet; no missing local model files | [BOM](BOM.csv), [land review](footprint-verification.md), [artifact manifest](reports/artifact-manifest.json) |
| Power/control | DC corner calculations, source/load derating, fault and discharge timing; 432-corner ideal loop screen | [Power report](POWER-AND-CONTROL.md), [numeric results](reports/power-calculations.json) |
| EEPROM | 256-byte development image, annotated bytes and SHA-256 | [Programming instructions](EEPROM.md), [manifest](eeprom/manifest.json) |

The 499 unconnected findings are the expected airwires of a completely
unrouted board. They are not suppressed, waived or counted as placement defects.
After Alex routes the board, all of them must be resolved and the full checks
repeated. There are five unfilled rule areas: isolation plus four mounting
clearances; these are not conductive plane fills.

## Checker configuration and scope

PCB DRC has **no ignored checks and no exclusions**. Inherited ignored checks
for missing courtyards, footprint filters/types and track/tuning geometry were
enabled before the final passing run. Unconnected pads retain error severity.

ERC has no item exclusions. Two non-electrical checks remain intentionally
ignored: `single_global_label`, because named one-use observation/configuration
nets are intentional and exported pin/net auditing checks their identity; and
`simulation_model_issue`, because this is a hardware schematic without a complete
SPICE model assignment. Electrical conflicts, missing power drivers, library
mismatches, footprint filters, dangling wires and four-way junctions remain
checked. Power flags identify actual qualified power origins, and pass-switch
terminals use passive pin types to describe their conductive function.

The source-to-netlist check and physical pad comparison are complemented by
independent critical pin assertions. These are not substitutes for the cited
manufacturer package review or for physical testing. DRC evaluates placed
geometry; it cannot establish future copper continuity, impedance, thermal
performance or a certified insulation rating.

## Visual review

Reviewed all eleven schematic pages as high-resolution SVG/PNG, including
close views of the isolator supply/EQ groups, mux supply fanout, hub pin groups
and Type-C logic. Repaired overlapping labels/fields, power-arrow collisions,
rotated inductor/capacitor text and crowded fault fanout. The final layout has
one overview and ten functional sheets, with no unresolved off-frame content
or symbol/text collisions. The [PDF](renders/schematic.pdf) contains all 11 pages.

Reviewed [top placement](renders/placement-top.png), bottom and courtyard plots,
and top/bottom/isometric 3D renders. Reference labels are on F.Fab for assembly
inspection; a small board overview cannot make every 0402 reference readable,
so use the SVG at full zoom. Mounting holes and the barrier are shown in the
drawing layer. Corrected connector/transformer model orientation and CY1's
vertical datum. CY1's displayed untrimmed leads are an assembly assumption,
with the required trim clearance stated in [MECHANICAL.md](MECHANICAL.md).
Open shield frames and USB-A/body envelopes have the documented model limits;
no detailed enclosure/cover solid-contact certification is claimed.

## Reproduce review without overwriting placement

From the repository, using the installed KiCad CLI and the prepared
`.venv-revc/bin/python`:

```sh
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
"$KCLI" sch erc hub.kicad_sch --output docs/revc/reports/erc-final.txt --severity-all --exit-code-violations
"$KCLI" sch export netlist --format kicadxml --output build/revc/hub.xml hub.kicad_sch
"$KCLI" pcb drc hub.kicad_pcb --output docs/revc/reports/drc-final.json --format json --severity-all --schematic-parity
.venv-revc/bin/python tools/revc/verify_footprints.py
.venv-revc/bin/python tools/revc/verify_board.py
.venv-revc/bin/python tools/revc/verify_electrical.py
.venv-revc/bin/python tools/revc/mechanical.py
.venv-revc/bin/python tools/revc/power.py
.venv-revc/bin/python tools/revc/eeprom.py
```

Inspect DRC's three result arrays separately; an exit code of zero without
`--exit-code-violations` is not a clean-routing claim. `verify_board.py` is a
handoff checker that intentionally rejects tracks/vias; after routing, retain
its inventory/domain checks but use the normal routed-board acceptance criteria.
The review scripts write reports, not routed geometry. `capture.py`, `board.py`,
`rules.py` and `refine_placement.py` are design generators and must not be run
over subsequent manual edits. `board.py` refuses an already routed board.

Renders can be regenerated with `tools/revc/render.py schematic` or `pcb`;
on this Mac, Cairo uses `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.
No review command exports Gerbers, drills or assembly-position files.

## Pending hardware and mechanical evidence

All items in [BRING-UP.md](BRING-UP.md) remain untested. Principal uncertainties
are effective capacitance, conversion efficiency, real startup/fault timing,
distributed-loop stability, intended-host descriptor allocation, narrow default
host suspend-current margin, USB eye/ESD performance, and temperatures under
fitted covers. The 2 A external target is conditional on the detailed input,
routing and thermal budget; the bus target is shared and derated at low input.

Enclosure selection, connector plug clearance, formed shield/lid dimensions,
lead trimming and mounting hardware fit are provisional. These are explicit
bench/enclosure handoff items, not unresolved component-placement collisions.
The original single-port files and library were compared with baseline
`741e9b8` and are unchanged. No main merge, hardware order or fabrication release
was performed.
