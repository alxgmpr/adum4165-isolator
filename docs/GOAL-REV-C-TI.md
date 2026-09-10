# Paste into a new session

```text
/goal Build Rev C of the isolated four-port USB hub in /Users/alex/Documents/isolator through a fully verified schematic and a completely placed, unrouted KiCad PCB that I can take over for routing.

Work on codex/revc-isousb211. The ADI baseline is checkpoint 741e9b8 on origin/main. Read docs/REV-C-TI-PLAN.md first; it supersedes conflicting Rev B instructions. Inspect the actual hub.kicad_sch, hub.kicad_pro, and hub.kicad_pcb, then use the historical Rev B decision record for context. Preserve the original single-port isolator.kicad_* design.

Use TI ISOUSB211DPR in its verified DP 28-pin HV/isolation footprint. Preserve USB 2.0 low/full/high speed, the USB2514B hub, two USB-A and two USB-C downstream ports, host-power operation, and the separate 5 V USB-C power input. Remove the ADI isolator clock circuit but retain the hub crystal. Use the plan's 5 V host-side / 3.3 V isolated-side supply strategy with a suitably rated 3.3 V buck; resolve its exact part and supporting components from primary datasheets. Recompute the complete power and thermal budget rather than trusting the historical shared-current estimate.

Finish the deferred power audit, footprint assignment, exact BOM fields, and two separate shield frames. Correct the downstream USB-C attachment/VBUS control, host-power detection, and any demonstrated circuit defects identified in the plan. Validate USB-C current detection, source-mux truth table, startup/inrush, suspend, aggregate overload, and per-port fault behavior. Use standalone hardware where practical. Follow manufacturer pin tables and reference drawings; validate netlists after circuit edits and inspect rendered schematics throughout.

Complete the PCB outline, mounting provisions, four-layer stack/rules, verified isolation geometry, connector and component placement, and routing annotations. Ask for mechanical constraints early while progressing on the schematic; if none are supplied, make a practical bench-board outline and document enclosure fit as provisional. Use project-local verified symbols and footprints. Select ordinary supporting parts and reasonable package sizes autonomously, retaining existing conventions where sound.

I will handle ALL routing: do not add tracks, vias, run an autorouter, or release fabrication files. Leave expected unrouted connections visible. Do not claim a certified isolation rating or carry the ADI 8.3 mm assumption over the TI package without reconciling the actual geometry.

Done means a readable, visually reviewed schematic; zero ERC errors and no unexplained warnings; complete usable BOM and libraries; a PCB with every physical component correctly synchronized and placed; no unresolved placement, courtyard, edge, or isolation defects; and no tracks or vias. Supply schematic/placement renders, netlist and check reports, power-budget calculations, routing priorities, and a bench bring-up checklist. Clearly distinguish verified design checks from pending routing, enclosure-fit, and hardware tests.

Work in checkpoints and maintain docs/REV-C-PROGRESS.md. Commit and push completed work to codex/revc-isousb211; do not merge main or order hardware. Continue until the stated deliverables are complete, resolving routine engineering choices without repeated confirmation. If a genuine blocker remains, preserve completed work and report the specific missing evidence or input; never mark partial work complete.
```
