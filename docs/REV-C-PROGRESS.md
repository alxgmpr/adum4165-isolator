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
