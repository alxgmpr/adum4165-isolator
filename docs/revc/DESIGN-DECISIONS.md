# Rev C final design decisions

The schematic and unrouted placement are complete. This record supersedes the
planning defaults where the completed audit demonstrated a required change.
Hardware performance, enclosure fit and compliance testing remain pending.
Start with [the handoff index](README.md) for the verification evidence.

## Isolation and supply migration

U1 is **ISOUSB211DPR**, using TI's DP0028A-C02 HV land pattern. VBUS1 pin 1
uses the host 5 V rail. **VCC1 pin 5 and V1P8V1 pins 4/11 use U45's external
1.8 V buck output**, not 5 V. This documented TI supply option reduces host
current for the default-current-host/external-power mode. The original
all-linear planning option had inadequate upstream current margin. Side 2
uses ISO_3V3 on pins 24/27/28 and its internal 1.8 V regulator on pins 18/25.
Each of the four 1.8 V supply/ground pairs has its own local bypass group.
The two domains' 1.8 V rails remain separate.

CDP is disabled; EQ starts at zero with explicit DNP rework links. V1OK drives
isolated HOST_PRESENT, the hub VBUS detector and reset supervisor MR. V2OK is
available at TP3. The isolator's Y1/C5/C6 clock circuit is removed; the hub's
24 MHz Y2 remains, with 27 pF loads calculated for the selected 18 pF crystal.
[TI ISOUSB211 supply options and pin table](https://www.ti.com/lit/ds/symlink/isousb211.pdf).

U10 is TPS62162DSGR, a fixed 3.3 V, 1 A buck. The final 3.3 V allowance is
290 mA, including hub, isolator and controls. Its pin map and feedback/ground
connections replace the obsolete TPS62203 arrangement.
[TI TPS6216x](https://www.ti.com/lit/ds/symlink/tps62162.pdf).

U1's manufacturer lands have **8.20 mm nominal** opposing copper clearance;
the remaining domain rules require 8.30 mm. Measured placed pad clearance
outside U1 is at least 9.41 mm. The blanket historical 8.3 mm claim is retired.
T1 remains outside both shield frames; no transformer slot is needed for the
verified land geometry. SH1 and SH2 are separately grounded, with separate
cover purchase entries. CY1 is the sole intentional inter-ground capacitor.
No certified board insulation rating is assigned. See [mechanics](MECHANICAL.md).

## Source qualification, regulation and protection

TUSB320LAIRWBR controllers replace ambiguous discrete CC interpretation.
GPIO OUT1/OUT2 truth table is HH unattached, HL default, LH 1.5 A, LL 3 A.
NOT OUT1 permits host converter operation; NOR of both outputs qualifies the
external 3 A source. U27 physically gates the external input, because TPS2121
priority dividers alone cannot reject a weak sole source. Dynamic current
advertisement changes remain an explicit hardware test.
[TUSB320LAI](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf),
[TI current-tracking clarification](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/735532/tusb320lai-failing-usb-if-td-4-3-4-sink-connect-try-snk-drp-test).

The SN6505B/750313638/SS34/TPS630701 fixed-5 V isolated chain remains. U26
bounds its input draw. U28 TPS552892 adds external buck-boost regulation to
5.20 V, allowing for mux, shunt and port-switch losses. INA300 monitors bound
external input and aggregate output load; faults shed the ports while leaving
the core supply connected. Undervoltage shedding is independent.

U29 is **TPS2553DBVR constant-current**, not the latch-off `-1` variant. The
latter could shut off while charging the USB-A bulk capacitors. A Schmitt/RC
stage delays the bus overcurrent report while current limiting and core
undervoltage protection remain immediate. U30 supplies the separately selected
external port path. Logic makes the two paths mutually exclusive. Rebuilt
configuration links have distinct nets and genuine DNP assembly state.

The resulting downstream design budgets are **300 mA shared on qualified bus
power**, with low-voltage/efficiency derating, and **2 A total / 500 mA per port
on qualified external power**, subject to the specified input voltage, thermal,
efficiency and routed-loss conditions. The old 404/609 mA estimates are retired.
See [complete calculations and control tables](POWER-AND-CONTROL.md).

## Ports, reset and descriptors

Each downstream Type-C port uses a TUSB320LAI in DFP/default-Rp mode. VBUS
requires valid sink attachment AND hub permission. Active discharge operates
when disabled, with passive discharge retained for total board power loss.
All four ports retain individual current limiting and OC reporting; aggregate
faults fan out to the four OC inputs. No duplicate discrete Rp/Rd is fitted.

HOST_PRESENT now controls U11 VBUS_DET and the reset supervisor; external
power cannot falsely imply that a host is present. A 24LC02B EEPROM configures
dynamic power status, individual switching/OC, multi-TT high-speed operation,
four removable ports and the startup interval. Source changes cause
re-enumeration. See [EEPROM.md](EEPROM.md) for the development image and
programming instructions. Legacy bus-powered hub allocation and narrow upstream
suspend margin are documented limitations requiring intended-host testing.

## Placement and routing ownership

The provisional 136 × 116 mm board has four layers, four mounting holes,
all-layer isolation and hardware keepouts, every component placed, and separate
shield frames. The fabricator's live JLC04161H-3313 calculator supplies the
90 Ω differential starting dimensions, 0.136 mm width / 0.150 mm gap.
The six USB pairs, bypass returns, hot loops and power-loss limits are in the
[routing guide](ROUTING-GUIDE.md). Alex owns all routing; no tracks, vias,
filled copper or fabrication outputs were created.
