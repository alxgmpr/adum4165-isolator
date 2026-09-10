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

## Completion gates (open)

- [ ] Electrical architecture and worst-case power/control calculations
- [ ] ISOUSB211 symbol, HV footprint, and supply circuit
- [ ] USB-C attach, host detection, protection, power modes, and hub configuration
- [ ] Complete schematic fields, exact BOM, and project-local libraries
- [ ] Clean rendered schematic, zero ERC errors, explained warnings
- [ ] Complete synchronized placement, outline, mechanics, stackup, rules
- [ ] Isolation, pad-net, inventory, courtyard, and edge verification
- [ ] Renders, routing guide, bring-up checklist, hardware/mechanical limitations
- [ ] Checkpoint commits, final clean branch, and push

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
