# Rev C: TI ISOUSB211 isolated four-port hub

Planning handoff, 2026-09-10. This document takes precedence over the Rev B
specification, decision record, and continuation prompt for this revision.
It records a proposed implementation, not a completed or bench-verified design.

## Baseline and scope

- ADI revision checkpoint: `741e9b8`, pushed to `origin/main`.
- New revision branch: `codex/revc-isousb211`.
- Target: `hub.kicad_sch`, `hub.kicad_pro`, and `hub.kicad_pcb`.
- The four-port target and ISOUSB211DPR package were proposed during planning;
  no answer to those optional questions had arrived when this handoff was written.
  These are the defaults for the accompanying goal prompt, not recorded approvals.
- Preserve the original single-port `isolator.kicad_*` files and their history.
- End state: complete schematic, sourced BOM, reproducible libraries, and a
  synchronized PCB with outline, mechanical features, rules, and component placement.
  **Alex will route the board.** No tracks, routing vias, autorouter runs, or
  fabrication release are part of the next session.

The electrical architecture remains USB-C host -> isolated USB link -> USB2514B
-> two USB-A and two USB-C downstream ports. Retain 5 V operation, bus power
as the primary mode, and a separate USB-C power input for heavy loads. Keep
the SN6505B / 750313638 transformer / SS34 / TPS630701RNMR fixed-5 V chain
and TPS2121 power mux unless verification reveals a concrete defect.

Preserve the intended power behavior: host advertisement of at least 1.5 A
enables the isolated converter; external power is preferred only when its
3 A capability is established. A default-current host without external power
does not power the isolated hub. Full 500 mA per downstream port requires the
external source. No PD, SuperSpeed, or higher-current downstream advertising.
Those behaviors need validation; the previous text is not proof of compliance.

## What is actually in the saved files

KiCad CLI `10.99.0` successfully exported both the checkpoint and preceding
commit. Their component reference/value/footprint/description fields and all
102 nets were identical. The checkpoint contains KiCad serialization/project
updates and a transformer placed on the otherwise empty hub PCB.

- Netlist contains 149 physical symbols and nine incorrectly numbered power
  symbols (`1` through `9`). Correct the latter's references/exclusion flags.
- Only T1 has a footprint assignment; 148 physical symbols still need one.
- The PCB has one footprint, no tracks, no vias, and no finished outline.
- ERC: **0 errors, 64 warnings**: 59 library mismatches, one missing ADUM4165
  library symbol, three mixed local/global names, and one dangling wire at
  approximately (261.62, 24.13) mm.
- The existing two-terminal isolation checker passed. It does not check
  arbitrary multi-pin internal paths, creepage, mechanics, or copper geometry.
- Render review found substantial text/symbol overlap, content outside the
  frame, and excessive blank space on A0. The text checker reported 12
  off-frame items. Do not preserve this schematic presentation.
- Y2 case pins 2/4 are already grounded. Its current load capacitors are
  18 pF; recalculate them for the exact selected crystal. Old continuation
  claims that the case is floating and Tasks 8/9 are unfinished are stale.
- The deferred power audit, footprint/BOM completion, and shield frames are
  still outstanding. Finish these in Rev C.

Baseline checks were read-only. No electrical or placement changes were made
while preparing this plan.

## TI migration decisions

Use **ISOUSB211DPR**, TI DP 28-pin wide-body SSOP. PCBParts identified LCSC
`C5772877` with 2,369 units in its indexed inventory on 2026-09-10; refresh
availability when resolving the BOM. This is not a stock reservation or live quote.
ISOUSB111 is unsuitable for retaining 480 Mbps operation.

Replace U1, remove its Y1 clock and C5/C6 load capacitors, and rebuild the
isolator support circuit. Keep the hub's separate Y2 crystal.

Proposed connections (verify against the current TI pin table before capture):

| Function | Side 1 | Side 2 |
|---|---|---|
| USB data | UD+ 8, UD- 7 to host pair | DD+ 21, DD- 22 to hub upstream pair |
| Ground | 3, 12 to GND1 | 17, 26 to GND2 |
| Main input | VBUS1 1 and VCC1 5 to VBUS_HOST | VBUS2 28, V3P3V2 27, VCC2 24 to ISO_3V3 |
| Local regulator output | V3P3V1 2; V1P8V1 4/11 | V1P8V2 18/25 |
| Charging advertisement | CDPENZ1 13 high to local 3.3 V | CDPENZ2 16 high to local 3.3 V |
| Initial equalization | EQ10/11 9/10 low | EQ20/21 20/19 low |
| Remote power indication | V2OK 6, optional test point | V1OK 23, host-present indication |
| Unused | NC 14 | NC 15 |

Use local bypass groups at each supply/ground pair, following TI's drawings;
do not reuse ADI ground-pin or decoupling assumptions. Keep the two domains'
internal rails distinct. Leave unused outputs/NC pins explicitly accounted for.
Provide compact strap rework options for equalization if practical; do not
increase equalization without a trace-loss rationale or subsequent measurement.

Reference: [TI ISOUSB211 datasheet, SLLSFC5D](https://www.ti.com/lit/ds/symlink/isousb211.pdf),
sections 4, 7.3, 8.2-8.4; compare the schematic visually with
[TI EVM guide, SBOU261](https://www.ti.com/lit/pdf/sbou261).
Use current datasheet ratings over older EVM prose. Confirm apparent datasheet
typos against the figures: side-2 bypass returns belong to GND2, and the second
side-2 1.8 V bypass group belongs at pins 18/17.

## Supply choice and budget

Default: host side from 5 V, isolated side from the shared 3.3 V buck, using
the TI internal 1.8 V regulators. Upgrade U10 to a suitable **at least 500 mA
3.3 V buck** with startup/thermal margin; select its exact MPN and passives
before capture. This avoids adding a third regulated rail while leaving margin
for the isolator and Type-C controllers. Do not assume pin compatibility with
the existing TPS62203.

The hub maximum is 80 + 3 x 25 = 155 mA. ISOUSB211's zero-EQ HS maximum is
13.5 + 96 = 109.5 mA per side. Together that is 264.5 mA on ISO_3V3 before
other loads or startup. The present 300 mA regulator is not necessarily
overloaded at steady state, but its approximately 35.5 mA remaining margin
is a poor default for the expanded design.

These estimates reuse Rev B's **unmeasured** 609 mA available at ISO_5V,
90% secondary-buck efficiency, and 11 mA indicator/control allowance:

| Isolator side-2 supply strategy | Estimated shared downstream current |
|---|---:|
| All isolator supplies from 5 V | 375 mA |
| Shared 3.3 V buck, internal 1.8 V regulation (default) | 404 mA |
| 3.3 V logic plus a separate efficient 1.8 V buck | 436 mA |

For the default: `609 - 11 - (155 + 109.5) * 3.3 / (5 * 0.90) = 404 mA`.
New controllers, actual regulator efficiency, tolerances, and protection losses
will change this. These figures compare choices; they are not guaranteed output
ratings. Host steady-state draw starts near 800 + 109.5 = 909.5 mA before
host-side control loads. A 1.8 V buck is a fallback if the final budget or
thermal calculation requires it, not a prerequisite for this plan.

Rebuild the full budget from the completed netlist, including worst-case port
voltage, per-port fault thresholds, aggregate overload, startup, attach,
pre-enumeration, suspend, and external-source switchover. A 500 mA port current
limit does not enforce a roughly 400 mA total converter budget. An SN6505B
switch-current rating also does not establish a precise aggregate output limit.
Resolve how overload is bounded without link brownouts before claiming readiness.

References: [Microchip USB251xB data sheet, DS00001692E, table 6-4](https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf),
[TI TPS6220x data sheet](https://www.ti.com/lit/ds/symlink/tps62203.pdf),
and the TI isolator data sheet above. The old calculation is in
`docs/superpowers/reviews/2026-08-08-revb-part-selection.md`, section 3.

## Existing issues to resolve while completing the schematic

1. **Downstream Type-C attach control.** J5/J6 presently have 56 kR pull-ups
   to their switched VBUS rails, with TPS2553 enables driven directly by
   PRTPWR3/4. Select a source-port Type-C controller per port, or a suitable
   integrated controller/switch. Require both hub power permission and valid
   sink attachment before enabling VBUS; provide detach/discharge behavior,
   correct default-current advertising, and fault reporting. Keep the two
   USB-A port switches. Do not duplicate discrete Rp around an IC that
   supplies it internally. No MCU/firmware is needed unless a demonstrated
   requirement cannot be met with standalone hardware.
2. **Host removal with external power.** U11.27 VBUS_DET is currently tied
   permanently to ISO_3V3. Prefer ISOUSB211 V1OK as a GND2-local host-power
   indication, after verifying output levels, power-up/down state, and hub
   input requirements. Retain a valid hub reset circuit; test the proposed
   state sequence for host absent, host power cycling, and either supply order.
   Rework the ADI-specific PGOOD2/Q4/R31/D7 indicator meaning explicitly.
3. **Power behavior and descriptors.** Keep strap-only operation where sound,
   but verify self/bus-powered declarations, charging straps, port power
   timing, and the real behavior with a default-current host. Record inherited
   limitations; do not silently describe this as USB-IF certified. EEPROM
   configuration is an available remedy if justified, not an automatic addition.
4. **CC detection and mux.** Recheck both cable orientations, thresholds
   across VBUS/tolerance corners, attach/detach behavior, and the existing
   comparator/inverter polarities. In particular, do not repeat the old claim
   that an unused CC pin seeing VCONN proves a high-current source. Verify
   the actual receptacle/cable behavior against current Type-C references.
   Test the complete TPS2121 source truth table, including weak external power
   with the converter off. Preserve valid existing corrections to PR1/CP2.
5. **Capacitance/inrush and protection.** VBUS_HOST already has 9.9 uF nominal
   directly connected capacitance. Check tolerances and total attach inrush
   when changing bypassing. Validate downstream bulk capacitance, USB-C
   discharge, ESD part capacitance, and differential polarity/flow-through.

The Type-C and host-detect recommendations follow
[Microchip USB2514B hardware checklist, DS00004541A, sections 5 and 8](https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DesignChecklist/USB2514B-Hardware-Design-Checklist-DS00004541.pdf).
Treat primary documents as evidence, not infallible prose: cross-check tables
and diagrams where their wording is inconsistent.

## Isolation, mechanics, and placement

Use a verified project-local TI DP0028A-C02 **HV/isolation** footprint, not a
generic SSOP land pattern. TI shows 8.2 mm nominal pad clearance for this
option versus 7.3 mm for its standard pattern; the package specifies greater
than 8.15 mm clearance/creepage. The old blanket 8.3 mm claim cannot be carried
over unchanged. Retain at least 8.3 mm separation elsewhere where practical,
document the TI footprint's actual limits and fabrication tolerances, and
reconcile the whole barrier requirement before freezing placement. Do not
shorten pads arbitrarily or suppress the resulting DRC without justification.

Review T1, CY1, slots, exposed connector metal, mounting hardware, and both
shield fences as a complete barrier. The old transformer-slot rationale may
be stale: the current custom footprint states a 9.41 mm pad gap. Recompute
the real shortest paths rather than inheriting a slot blindly. The system
rating is limited by all barrier components and geometry, not U1's headline
test rating. This plan makes no certified board-level insulation claim.

Keep the plastic enclosure concept and two separate removable shield cans:
BMI-S-201-F/C on GND1 and BMI-S-209-F/C on GND2, subject to verified fit and
availability. Include frame symbols/footprints/BOM entries and cover ordering
notes. Shields and hardware must not join the two grounds. The 1 nF Y1-rated
CY1 remains the only intentional inter-ground capacitive connection.

Four-layer placement target: short USB segments on top, adjacent reference
planes split only at the isolation barrier. There are **six** differential
segments: host-to-isolator, isolator-to-hub, and four hub-to-port segments.
Set a 90 R differential target using an actual fabricator stackup; do not
invent width/gap numbers from impedance alone. Annotate routing priorities,
each bypass capacitor's owning pin/return, and switching-current loops.

Place every footprint, including pin-adjacent bypass capacitors, hub crystal,
ESD parts, shields, and mechanicals. Ensure space exists to route the supply
pin/return bypass loops on top without intervening vias, per TI. Keep the
1.8 V pin-to-pin links from cutting USB reference planes. Define barrier
keepouts on all copper layers and preserve routing room around connectors.
No tracks or vias should be added by the agent; zones may be defined as
unfilled routing guides, with the limitation documented.

No exact enclosure or PCB dimensions are selected in the current hub project.
Ask for mechanical constraints early in the build session while completing
independent schematic work. If none are supplied, size a practical bench-board
outline from verified footprints and clearances, and label enclosure fit
provisional. Do not copy the single-port extrusion dimensions or claim a
commercial enclosure fits without a dimensional check.

## Execution sequence and completion evidence

1. Recheck branch/baseline and read this document, then the current schematic
   and historical decision record. Load relevant KiCad skills. Audit old helper
   scripts before running them: many mutate the original single-port project
   or assume ADI pins, footprint positions, and net names.
2. Resolve the isolator symbol/footprint, 3.3 V buck, Type-C source controllers,
   connector MPNs, shield footprints, and safety capacitor. Use existing package
   conventions (0402 signal passives, larger effective bulk capacitors) where
   electrically and mechanically sound. Check pin maps and exposed pads against
   manufacturer drawings; record exact MPN, Manufacturer, LCSC when available.
3. Implement the TI circuit and necessary corrections. Export a netlist after
   each functional block and compare expected pin/net changes. Keep ordinary
   reference/field changes separate from connectivity changes in the audit.
4. Finish the power budget, all modes, component ratings, and BOM. Generate BOM
   from schematic fields; never fix electrical data only in an exported CSV.
5. Redraw the schematic cleanly in coherent blocks, preferably a compact A2
   sheet if it fits. Render high-resolution SVG/PNG and inspect block crops and
   the complete sheet. Repair overlap, off-page text, wrong rotations, and
   confusing labels. Preserve verified pin numbering during symbol cleanup.
6. Synchronize the PCB, establish outline/rules/mechanicals/barrier, and complete
   placement. Inspect top/bottom renders and 3D geometry where models exist.
   Verify all physical schematic symbols have matching footprints and pad nets.
7. Deliver verification reports, updated design notes, a routing guide and
   bring-up checklist, with a clean committed branch. Push the revision branch
   when the new session's prompt authorizes it. Never merge it into main or
   order boards as part of this work.

Completion requires: zero ERC errors and no unexplained warnings; no missing
physical footprints/MPNs except explicitly justified commodity or mechanical
cases; correct USB polarity and control nets; independently checked isolation
domains; no placement/courtyard/edge/barrier DRC defects; no routed tracks or
vias; a complete netlist/PCB inventory match; and readable, visually reviewed
schematic and placement artifacts. Unconnected-pad DRC findings are expected
on an unrouted board and must be reported separately, not globally disabled.
Bench-only tests and enclosure assumptions must be listed as unverified.

Tooling at planning time:

```sh
KCLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KCLI sch export netlist --format kicadxml -o /tmp/hub.xml hub.kicad_sch
$KCLI sch erc hub.kicad_sch --output /tmp/hub-erc.rpt --severity-all --exit-code-violations
python3 tools/check_isolation.py /tmp/hub.xml
python3 tools/check_sch_text_overlap.py hub.kicad_sch
```

These checks are necessary aids, not substitutes for datasheet, geometry, and
image review. Adapt only checks whose assumptions no longer match Rev C.
Do not weaken tests to manufacture a clean report.
