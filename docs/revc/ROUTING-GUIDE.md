# Rev C routing handoff

Open `hub.kicad_pro` and route `hub.kicad_pcb`. All 291 physical schematic parts
and four mechanical holes are placed. **There are no tracks, vias or filled
copper zones.** The five unfilled rule areas are the isolation barrier and four
mounting clearances. Alex owns every routed connection, including thermal vias.

## Stackup and differential pairs

The reference stack is JLC04161H-3313, nominal 1.6 mm, 1 oz outside/0.5 oz inside:
F.Cu 0.035 / prepreg 0.0994 / In1.Cu 0.0152 / core 1.265 / In2.Cu 0.0152 /
prepreg 0.0994 / B.Cu 0.035 mm. Prepreg εr=4.1; current calculator-guide core
εr=4.43. Use In1 as continuous GND1/GND2 reference regions separated only at the
isolation barrier. In2 can carry domain-local power and ground. Keep a continuous
local return plane beneath every USB segment.

The live fabricator calculator gives **0.1356 mm width at 0.1501 mm gap** for a
90 Ω, masked, non-coplanar differential pair on L1 over L2. KiCad uses
**0.136/0.150 mm**. `reports/impedance-calculator.json` records inputs, result,
mask assumptions and the distinction between calculator and process tolerance.
Do not substitute the common 7628 stack without recalculating. Keep surrounding
same-layer copper at least 0.5 mm from the pair so it remains approximately
non-coplanar; nearer guard copper requires recalculation.
[Fabricator calculator](https://jlcpcb.com/pcb-impedance-calculator),
[stackup](https://jlcpcb.com/impedance).

| Pair prefix | Route endpoints and priority |
|---|---|
| HOST_D+/D− | J1 → U2 ESD → U1.8/.7; GND1 throughout |
| HUB_UP_D+/D− | U1.21/.22 → U11 upstream; GND2 throughout |
| PORT1_D+/D− | U11 → U16 → J3, right upper USB-A |
| PORT2_D+/D− | U11 → U17 → J4, right lower USB-A |
| PORT3_D+/D− | U11 → U18 → J5, right upper USB-C |
| PORT4_D+/D− | U11 → U19 → J6, right lower USB-C |

Route these six pairs first, with short pin escapes and flow-through ESD pads.
Use the **actual pad-net report** for exact hub pin numbers, rather than guessing
from package orientation. The two equivalent D+/D− contacts of each USB-C
receptacle join locally. Keep ESD stubs and exposed-pad test stubs off the pairs.
Default rules set 0.25 mm intrapair skew, 5 mm total uncoupled length and 80 mm
maximum segment length. These are layout targets, not measured eye margins.
The longest port-1 connection needs a deliberate corridor from the hub's lower
edge around the left of the port-power region. Shorten it where practical; do
not add large meanders simply to consume the skew allowance. No polarity swap
is configured in EEPROM.

Keep USB on top where possible. If a layer transition becomes necessary, use
matched transitions with adjacent same-domain return vias and recalculate the
new layer geometry. Never cross a split or route under a switching node, inductor,
crystal or isolation barrier. Do not stitch GND1 to GND2.

## Bypass and switching loops

`reports/bypass-placement.csv` lists each capacitor's owning pin or purpose and
placement. U1's four local supply/return groups take priority over convenience:
C65/C66/C67 serve pins 4/3, C68/C69/C70 pins 11/12, C71/C72/C73 pins 25/26,
and C74/C75/C76 pins 18/17. The 10 nF parts are nearest the package, then 100 nF,
then bulk. Route each supply-pin-to-capacitor-to-ground-pin loop on top with no
intervening via. Connect each domain's two 1.8 V groups after the local loops;
those links must not cut or displace the USB reference plane. U1's host external
1.8 V source is U45; never join it to the secondary internal 1.8 V rail.

Route U11's six 100 nF supply caps to their assigned supply pins, and return
CRFILT/PLLFILT capacitors directly to GND2. Y2/C32/C33 must remain local to the
hub clock pins with no USB/power routes underneath; its case pins and hub EP37
are grounded. The 27 pF values assume the stated IC/PCB stray loading and require
frequency verification.

| Power stage | Critical physical loop |
|---|---|
| U45 host 1.8 V | C113–U45 VIN/GND; U45 SW–L4–C114; feedback from quiet C114 output |
| U5/T1 primary | C10/C11/C12–T1 center tap–U5 D1/D2–GND1; short symmetric legs; keep driver EN on its 5 V supply |
| T1/D3/D4/U6 | Each secondary half-winding–Schottky–input reservoir–center tap; short U6/L1/input/output-cap loops inside SH2 |
| U28 external | Input bank to VIN/PGND, SW1–L3–SW2, output bank to VOUT/PGND; C82/C83 local boot loops; C84 local VCC–ground return |
| U10 3.3 V | C30–VIN/PGND, SW–L2–C31, separate quiet VOS sense; AGND/PGND/EP join locally |

Minimize exposed switching copper and avoid routing beneath control/feedback
nodes. Connect R110 and R116 sense traces as Kelvin pairs from the resistor
lands, inside the power-current takeoff. Route INA300 sense/control away from
SW1/SW2 and transformer drive. Route feedback, compensation and supervisor
dividers to quiet ground; do not share their returns with diode or USB-port
current pulses. Thermal lands and vias must follow the exact package drawings.
The current board deliberately contains none of those vias.

## Power routing constraints

The 1.0 mm Power netclass is a starting width, not a 3 A rating. Prefer pours
for the J2–R110–U27–U28 path and regulator–mux–U30–R116 distribution path.
The input routed resistance allowance is 10 mΩ; the regulator-to-worst-port
additional voltage-drop allowance is **15 mV total** at 2 A shared/500 mA per port.
For scale, 1 oz copper has roughly 0.49 mΩ/square at 20°C before temperature and
process allowances. Count squares and include return-path loss, connectors,
neckdowns and vias; verify the actual drop under load. Revisit the load rating
if the routing cannot meet the budget. Keep U8 junction ≤85°C for the full-load
voltage calculation.

Separate source/switch/port nets exactly as captured. Never bypass R110/R116,
U29/U30, or individual port switches with pours. R22 is a populated zero-ohm
feedback return link. R112 is populated for normal overload protection. The five
DNP EQ/mode links are rework options, not accidental missing BOM entries.

## Barrier and mechanics

The rule area spans all four copper layers. Maintain 8.30 mm primary-to-secondary
clearance/creepage except between U1's opposing manufacturer HV lands, which are
8.20 mm nominal. The local exception only applies to U1-to-U1 lands; it is not a
general waiver. T1's nearest cross-domain copper is 9.41 mm. CY1 is the only
intentional inter-ground capacitor. No arbitrary ground net ties, shield joins,
metal standoffs or mounting plates may defeat the barrier.

SH1 is GND1, SH2 is GND2. Their removable covers are separate purchase items.
Keep switching circuits within their assigned frames; avoid traces under the
frame solder lands and leave cover access. USB connector shell lands return to
their own domain. Preserve the NPTH/hardware keepouts and the provisional connector
mating datums in `MECHANICAL.md`.

After routing: rerun ERC, full DRC with schematic parity, isolation checks and
field-solver/impedance review; inspect planes, hot loops, every bypass return and
3D geometry again. Unrouted connections must then reach zero. Fabrication output
review, electrical testing and enclosure qualification are subsequent work.
