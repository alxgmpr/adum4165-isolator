# Rev C progress

## 2026-09-10 — baseline and design audit

- Active goal: complete `hub.kicad_*` on `codex/revc-isousb211`; original
  `isolator.kicad_*` and shared original libraries are preserved.
- Read `REV-C-TI-PLAN.md`, `GOAL-REV-C-TI.md`, the Rev B part-selection record,
  and KiCad schematic/layout/BOM skills. User authorization covers ordinary
  component selection and package choices.
- Baseline XML netlist and ERC exported to `build/revc/baseline/`.
- Baseline has 149 physical components plus nine misreferenced power symbols;
  only T1 has a footprint. Existing board has no routing.
- Mechanical constraints requested; otherwise use a provisional bench board.
- Primary documents retrieved for ISOUSB211, TPS62162, TPS25810, TUSB320,
  TPS2553, TPS2121, SN6505B, and TPS63070.
- Initial findings requiring correction: weak external power can be selected
  when the isolated converter is off; aggregate port overload is not bounded;
  existing buck-boost strap resistors are bypassed by same-net connections;
  downstream Type-C ports lack attach-controlled VBUS; VBUS_DET is permanent.
- In progress: pin-table and mode review; exact parts and power architecture.

## Completion gates — routing handoff

- [x] Electrical architecture and worst-case power/control calculations
- [x] ISOUSB211 symbol, HV footprint, and supply circuit
- [x] USB-C attach, host detection, protection, power modes, and hub configuration
- [x] Complete schematic fields, exact BOM, and project-local libraries
- [x] Clean rendered schematic, zero ERC errors, explained warnings
- [x] Complete synchronized placement, outline, mechanics, stackup, rules
- [x] Isolation, pad-net, inventory, courtyard, and edge verification
- [x] Renders, routing guide, bring-up checklist, hardware/mechanical limitations
- [x] Checkpoint commits, final clean branch, and push

No tracks, vias, autorouter runs, fabrication outputs, main merge, or hardware
orders are authorized. Unrouted connections will be reported separately.

## Checkpoint 2 — electrical capture (2026-09-10)

- Captured Rev C as nine functional child sheets plus an overview: 286 physical parts, 190 named nets. The current export has zero pin/net differences from the electrical source. ERC pass 4: zero errors, zero warnings, no exclusions. This is an electrical checkpoint, **not** a visual or PCB completion claim.
- Replaced the isolator and removed its clock. Verified TI DP0028A-C02 HV lands (8.2 mm nominal clearance). Retained the hub clock and corrected its bypass/filter and configuration circuits.
- Added a 1 A shared 3.3 V buck, GPIO Type-C qualification/attachment controllers, source-aware reset/EEPROM wiring, independent port control, passive and active USB-C discharge, and separate shield-frame symbols.
- The original all-linear host isolator supply could exceed 100 mA on a default-current host. Used TI's documented external 1.8 V buck option on the host core while keeping VBUS1 at 5 V. The isolated side retains internal 1.8 V regulation from 3.3 V. This is a justified departure from the planning default.
- Added a regulated external input to allow for downstream switch drops. Port overload monitors now shed downstream load without shutting off the core supply; the external aggregate switch has a controlled startup ramp. Exact tolerance, compensation and thermal calculations remain to be documented and checked.
- Repaired the shorted configuration-link nets, TVS polarity/part identity, DNP state, missing power declarations, host-converter enable voltage, and mutually exclusive bus/external port paths.
- Started manufacturer/package and indexed availability checks. Exact supporting-part fields and most footprints remain incomplete.
- KiCad was updated by the user's other task; CLI verification now runs on 10.99.0-3770-gd7e34de179. No unrelated open PCB was edited.
- Next: finish BOM/footprints and quantitative power checks, redraw and visually inspect the schematic, synchronize/place every PCB part, then verify geometry and deliver routing/bring-up evidence. PCB remains the original one-transformer placeholder with no tracks or vias.

## Checkpoint 3 — exact BOM and local lands (2026-09-10)

- Assigned all 286 physical schematic components to project-local footprints; 37 local patterns include two future board-only mechanical patterns. Purchase fields contain exact MPN, manufacturer, rating and source. The 17 exposed test pads are documented PCB features, excluded from purchase BOM. Five DNP rework links remain explicit. Cover ordering data lives on SH1/SH2 schematic fields and exports separately.
- Generated the Microchip M2 SQFN36, TI RUX12, TI RYQ21 and Coilcraft XFL4020 lands using official KiCad Library Tools and manufacturer dimensions. Retained the verified TI DP28 HV option. Visually reviewed the nine-pattern dimensional render; no tracks or vias were introduced.
- Checked manufacturer connector and safety-capacitor drawings in the browser. The USB-A choice is an upright right-angle socket requiring approximately 15 mm top-side clearance. Verified the 14 mm capacitor pitch from the exact ordering code. Checked small-shield frame and assembled heights against its drawing.
- Copied models locally. Missing detailed models have labeled dimensional envelopes; these limits and source provenance are documented, not represented as manufacturer assembly models.
- Added reproducible review-only exports and a 974-row symbol/pad/net audit. Physical inventory and all connected pin/net comparisons pass. BOM is exported from schematic fields.
- Enabled previously ignored footprint-filter and four-way-junction ERC checks. Removed duplicate wires caused by stacked connector pins. Fixed a verifier side effect that overwrote the library's power flags. Current ERC: **0 errors, 0 warnings, no exclusions**; only single-use global-label and SPICE checks remain intentionally inapplicable to this capture.
- PCB is still the single-transformer placeholder. Electrical power/compensation calculations, EEPROM content, schematic visual cleanup, PCB placement/geometry and final handoff evidence remain open. This checkpoint is not a placement or final design signoff.

## Checkpoint 4 — synchronized placement and startup correction (2026-09-10)

- Redrew the schematic into functional panels and added the delayed bus-current fault circuit. Current capture: 291 physical parts, 194 named nets, 987 physical pad rows including duplicate lands. U29 now uses TPS2553DBVR constant-current operation: the latch-off version could interrupt charging of the USB-A bulk capacitors. U48 reports sustained bus overload after the charging interval; undervoltage shedding remains independent.
- Set the external regulator to 5.20 V nominal with a zero-ohm R22. The power analysis includes reference, resistor, FB leakage and CDC-current tolerances. Detailed operating-envelope and startup documentation remains in progress.
- Replaced the placeholder PCB with all 291 synchronized footprints plus four mechanical holes on a provisional 136 × 116 mm, four-layer bench board. Placed all bypasses, crystal, connectors and two separate shield frames. Added an all-layer isolation keepout, mounting clearances and domain/differential routing rules. No tracks, vias or filled copper were added.
- Reconciled KiCad's footprint-local pad rotations and corrected STEP model orientation/offset for the HRO connectors and transformer. Cleared courtyard/edge/silkscreen conflicts without altering the verified electrical lands. Primary transformer and shield remain separate.
- Fresh KiCad ERC: **0 errors, 0 warnings**. PCB DRC with explicit `--schematic-parity`: **0 geometry/rule violations, 0 parity issues, 499 expected unrouted connections**. Independent inventory/net audit: no differences. Minimum cross-domain pad copper is 8.200 mm at U1 and 9.410 mm outside U1.
- Remaining final gates: full-page schematic visual signoff, final placement/3D artifacts and mechanical report, fabricator impedance calculation, complete power/startup/descriptor documentation, EEPROM image, routing guide and bring-up checklist. These passing checks are a placement checkpoint, not hardware validation.

## Checkpoint 5 — final design and visual verification (2026-09-10)

- Completed the power/control report and source-load CSV, including component tolerances, voltage drops, thermal estimates, startup, suspend, source switching and faults. Bus design load is 300 mA shared with derating; full 2 A external output is conditional on input voltage, efficiency, temperature and routed loss. Bench-only uncertainty is explicit.
- Set R121 to 68 kΩ and verified the startup-report delay against capacitor/leakage corners. Increased C84 to 22 µF/25 V to retain margin above U28's 4.7 µF effective VCC-capacitance requirement. Updated captured fields, exact BOM and placement together.
- Recorded the live JLC04161H-3313 impedance-calculator result: 90 Ω differential, 0.1356 mm width / 0.1501 mm gap, implemented as 0.136/0.150 mm. Preserved all-layer barrier and mounting keepouts; all routing remains Alex's work.
- Reviewed all eleven schematic pages and dense detail crops. Repaired remaining power-label, field, gate-label and rotated-text collisions. Delivered SVG/PNG pages and an eleven-page PDF.
- Reviewed top/bottom/courtyard placement and top/bottom/isometric 3D renders. Corrected CY1's model height and documented untrimmed lead limits. Moved shield reference labels clear of enclosed parts and displayed mounting circles in the drawing layer. No unresolved courtyard, edge, isolation or placed-body interference was found.
- Final ERC: **0 errors, 0 warnings, no exclusions**. Final DRC: **0 geometry/rule violations, 0 schematic parity issues, 499 expected unrouted connections**. Enabled every PCB DRC check; no ignored checks or exclusions remain. The two inapplicable ERC checks are explained in `docs/revc/VERIFICATION.md`.
- Independent checks pass for all 291 components, 987 pad rows and 42 critical electrical assertions. Board has 295 footprints including four mounting holes, zero tracks, zero vias and zero filled copper. All 37 local footprints and 34 referenced model files resolve. Original single-port files match baseline `741e9b8`.
- Supplied the development EEPROM image/byte map, routing guide, mechanical assumptions, full bring-up checklist, verification reports, final netlist, model/library provenance and artifact hashes. All hardware tests and actual enclosure fit remain pending, as appropriate for this unrouted handoff.
- Handoff starts at `docs/revc/README.md`. Final artifact commit and remote synchronization follow this verification checkpoint; no main merge, hardware order or fabrication output was performed.

## Handoff closed — 2026-09-10

- Completed artifacts are committed as `4f81a98` and pushed to `origin/codex/revc-isousb211`. The working tree was clean after that push; all 186 recorded artifact hashes match. This final log-only checkpoint closes the progress gates.
- The requested schematic/placement deliverables are complete. Alex's routing, all hardware acceptance tests and actual enclosure qualification remain the documented next work. No tracks or vias were added and no fabrication files were released.
