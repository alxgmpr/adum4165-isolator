# Rev C routing handoff

**Complete schematic and placed, unrouted PCB**, dated 2026-09-10, on
`codex/revc-isousb211`. Open [hub.kicad_pro](../../hub.kicad_pro),
[schematic](../../hub.kicad_sch) and [PCB](../../hub.kicad_pcb).
The original single-port `isolator.kicad_*` design and libraries are preserved.

TI ISOUSB211DPR isolates the 480 Mbps USB2514B four-port hub, with two USB-A
and two attach-controlled USB-C downstream ports. The isolator clock is
removed; the hub crystal remains. There are 291 schematic components, 295
placed footprints including mounting holes, **zero tracks and zero vias**.
Alex will route every net.

| Deliverable | Files |
|---|---|
| Verification and limitations | [VERIFICATION.md](VERIFICATION.md), [electrical invariants](reports/electrical-invariants.json), [PCB inventory/isolation](reports/pcb-inventory-and-isolation.json), [ERC](reports/erc-final.txt), [DRC](reports/drc-final.json) |
| Readable schematic | [11-page PDF](renders/schematic.pdf), [page SVG/PNG directory](renders/schematic), [exported netlist](reports/hub-netlist.xml) |
| Placement and mechanics | [Top placement](renders/placement-top.svg), [bottom](renders/placement-bottom.svg), [courtyards](renders/placement-courtyards.svg), [mechanical assumptions](MECHANICAL.md) |
| 3D review | [Isometric](renders/pcb-3d-isometric.png), [top](renders/pcb-3d-top.png), [bottom](renders/pcb-3d-bottom.png) |
| Exact components | [BOM](BOM.csv), [separate shield covers](BOM-covers.csv), [land verification](footprint-verification.md), [symbol/pad/net audit](symbol-pad-net-audit.csv) |
| Power and behavior | [Power/control report](POWER-AND-CONTROL.md), [operating envelope](power-operating-envelope.csv), [design decisions](DESIGN-DECISIONS.md) |
| Routing and first hardware | [Routing guide](ROUTING-GUIDE.md), [EEPROM and programming](EEPROM.md), [bring-up checklist](BRING-UP.md) |
| Reproducibility | [Progress/checkpoints](../REV-C-PROGRESS.md), [review scripts](../../tools/revc), [artifact hashes](reports/artifact-manifest.json) |

Qualified host power supports a **300 mA shared downstream design budget**,
derated at low voltage/efficiency. Qualified external power supports **2 A
total, 500 mA per port** under the power report's conditions, including ≥5.0 V
at J2 under load for initial acceptance. A default-current host requires
qualified external power. Program the included development EEPROM before
normal enumeration; intended-host descriptor behavior must be tested.

The provisional bench board is 136 × 116 mm, nominal 1.6 mm, with four M3
mounting provisions and independent shield frames. Actual enclosure, plug,
lid and lead-trim fit remains unqualified. All hardware tests are pending,
including efficiency, loop stability, suspend, faults, USB signal integrity
and thermal performance. No fabrication files, hardware orders or main merge
are part of this handoff.
