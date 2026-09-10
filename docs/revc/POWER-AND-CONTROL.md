# Rev C power and control verification

This is a calculated design envelope for the placed, unrouted prototype. It is
not a measured output rating. Run `tools/revc/power.py` to regenerate the numeric
report, 432-corner averaged-loop screen and source/load envelope CSV. Values below
refer to the captured BOM; changing parts, EQ, stackup or routing requires review.

## Operating envelope

| Source condition | Intended behavior |
|---|---|
| Host absent; external absent or below 3 A advertisement | Off |
| Default-current host; no qualified external source | Host-side circuitry only; isolated hub cannot enumerate |
| Host advertises 1.5 A or 3 A; no qualified external source | Bus operation; **300 mA shared across all four downstream ports**, derated for low connector voltage/efficiency |
| External input advertises 3 A | External source preferred; **2 A total, 500 mA/port** design target, subject to the voltage/thermal conditions below |
| External powered, host absent | Secondary logic can run; host-presence reset prevents hub attachment |
| Either source changes | Hub dynamically disconnects, removes port power and re-enumerates; no seamless data-transfer claim |

The 3.3 V design load is **290 mA**: 155 mA USB2514B, 109.5 mA ISOUSB211
side 2 at zero EQ, and 25.5 mA for controllers, gates, monitors, EEPROM,
pullups and indicators. U10 is a 1 A TPS62162. At 85% assumed efficiency,
this is 0.247 A from a 4.75 V core rail, including a further 10 mA allowance.
The allowances deliberately exceed the ordinary control load; they are not
measured consumption. [Hub data](https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf),
[isolator data](https://www.ti.com/lit/ds/symlink/isousb211.pdf),
[3.3 V buck](https://www.ti.com/lit/ds/symlink/tps62162.pdf).

**Bus power.** U26's 28.7 kΩ setting bounds the converter branch to approximately
825–990 mA across its specified limit/resistor corners. The host core uses U45's
external 1.8 V buck; the all-linear alternative exceeded the default host budget.
At 4 V and 75% assumed buck efficiency, the host-side active estimate is 74.1 mA,
including 3 mA controls. Qualified-host maximum steady draw is about 1.064 A,
below the required 1.5 A advertisement. Do not confuse the branch's 990 mA upper
limit with available isolated output power.

The host envelope deducts U26's 135 mΩ maximum plus 10 mΩ routed input path,
then applies a **70–80% end-to-end isolated conversion efficiency assumption**.
At 4.75 V and 70%, the calculation permits 299.6 mA, slightly below the
300 mA target; use at least 4.80 V at that efficiency for the full target. At 4.25 V,
derate to approximately 240 mA. The hardware sheds port load if this estimate is
optimistic. The transformer is not a precision output current limiter.

**External power.** U46's input-current threshold is calculated as 2.772–2.971 A
(2.87 A nominal), including resistor/shunt tolerance, temperature excursion,
monitor current-source limits, offset and PSRR. U47's fast output threshold is
2.027–2.277 A (2.15 A nominal). Input protection remains below 3 A at the audited
corners; output protection admits 2 A before its minimum threshold.

The external envelope includes **61.29 mΩ** between connector and converter:
31 mΩ U27, 20.29 mΩ shunt and 10 mΩ routed path. With high output-setpoint and
worst-case core load simultaneously, full 2 A needs **at least 4.917 V at J2**
if U28 is 90% efficient. Use **5.0 V measured at J2 under load** as the initial
2 A bench acceptance condition. A source advertised as “5 V / 3 A” does not
establish the voltage at the board after cable loss. At 4.75 V, derate according
to the CSV unless measured efficiency establishes adequate margin. This is an
explicit limitation, not an unconditional 2 A rating at 4.75 V.

## Port voltage and power dissipation

U28 regulates **5.20 V nominal** (R20=10 kΩ, R21=3 kΩ, R22=0 Ω). The calculated
DC range is 5.1343–5.2690 V, including ±1% reference, precision resistor tolerance
and drift, ±100 nA FB leakage and up to 300 nA CDC current. R22 must be populated.
A 20 mV ripple allowance makes the upper bound 5.289 V. USB-IF's required 2014
VBUS ECN permits 5.5 V maximum; the design is not constrained to the obsolete
5.25 V maximum. [USB-IF ECN](https://compliance.usb.org/index.asp?UpdateFile=Electrical).

At 2 A shared and 500 mA on the evaluated port:

`Vport(min) = 5.1343 - 2.2470×0.085 - 2×0.031 - 2×0.010145 - 0.5×0.135 - 0.015 - 0.020 = 4.7585 V`.

This requires U8 junction temperature **≤85°C**, its input ≥5 V, and no more than
**15 mV total additional routed voltage drop** from regulator sense point to the
worst receptacle. The margin to 4.75 V is only 8.5 mV at this combined corner.
Use wide pours and a short common power path; if ripple, routing resistance or
junction temperature exceed those bounds, reduce the load rating. U8's higher
hot-resistance limits do not support this same full-load voltage claim.
[TPS2121](https://www.ti.com/lit/ds/symlink/tps2121.pdf),
[TPS22975](https://www.ti.com/lit/ds/symlink/tps22975.pdf),
[TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf).

| Dissipation at stated design load | Estimate |
|---|---:|
| U8 power mux | 0.429 W |
| U30 external port switch | 0.124 W |
| R116 10 mΩ, rated 1 W | 0.0406 W |
| Each downstream switch | 0.0338 W |
| R110 20 mΩ at 3 A, rated 1 W | 0.183 W |
| Complete U28 conversion stage at 90% | about 1.28 W |
| Complete U10 stage at 85% | about 0.169 W |

At 70% isolated-conversion efficiency, a roughly 2.68 W core-plus-port output
implies approximately 1.15 W lost across U5, T1, rectifiers and U6. Allow roughly
0.55 A secondary current and check both diode and transformer temperatures with
the shield covers fitted. The transformer primary half-winding flux estimate at
5.5 V / 363 kHz is 7.58 Vµs, below its 10 Vµs specification. Its 0.65 A application
example is typical, not a guaranteed thermal rating. Full-winding DCR maxima are
0.35/0.33 Ω; do not use the full-primary 340 µH value as a half-winding inductance.
[Transformer](https://www.we-online.com/components/products/datasheet/750313638.pdf),
[SN6505B](https://www.ti.com/lit/ds/symlink/sn6505b.pdf).

A conservative 1.28 W entirely assigned to U28 and its standard 43.4°C/W board
metric implies about 56°C rise; TI's much larger EVM gives a different result.
At 40°C ambient that suggests about 96°C, subject to the actual copper layout.
U8 needs a measured rise below 45°C at 40°C ambient to preserve its ≤85°C voltage
budget. Its older datasheet thermal table names an RNW package and must not be
represented as a verified RUX thermal characterization. Final copper, thermal
vias, shields and enclosure airflow govern temperatures. Alex must add the
required copper/thermal vias during routing and verify temperatures on hardware.
[TPS552892](https://www.ti.com/lit/ds/symlink/tps552892.pdf).

## Source qualification, mux and host detection

TUSB320LAI input controllers operate in UFP/GPIO mode with their internal Rd.
OUT1/OUT2 are HH unattached, HL default, LH 1.5 A, LL 3 A. U24 inverts OUT1
for host converter permission. U25 NORs both outputs for external permission,
then U27 gates the external converter input. VCONN on the unused cable contact
is not a current-qualification signal. Both cable orientations must pass.
Dynamic current-advertisement tracking is a hardware acceptance test because
TI's LAI support clarification and legacy datasheet wording differ.
[LAI data](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf),
[TI clarification](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/735532/tusb320lai-failing-usb-if-td-4-3-4-sink-connect-try-snk-drp-test).

| Qualified external IN1 | Isolated IN2 | Expected mux result |
|---|---|---|
| Absent | Absent | Off |
| Absent | Valid | IN2, ST low, bus port path enabled when requested |
| Valid | Absent | IN1, ST high through local pullup |
| Valid | Valid | IN1 priority: PR1≈1.87 V exceeds CP2≈1.50 V |

At the DC corners PR1 remains above CP2. OV pins are grounded. The mux alone
would select a weak sole source, which is why external qualification acts before
IN1. ST is pulled up to the output-derived 3.3 V, so it is only interpreted while
logic power is valid. U32/U42/U43 select mutually exclusive port paths. Brief gate
propagation overlap during switching is not claimed impossible; both paths join
the same source/output nodes, and hardware transients remain an acceptance test.

U1 V1OK becomes GND2-local HOST_PRESENT and drives U11 VBUS_DET and U33 MR.
U33 holds reset for undervoltage/host absence and provides its restart delay.
Host removal with external power therefore disconnects the data link and holds
the hub in reset. Check V1OK's rise/fall behavior in both supply orders, including
a slow host ramp; pin/net verification does not establish analog timing.

## Startup, overload and discharge

Direct host VBUS capacitance is **6.9 µF nominal, 7.59 µF at +10%**. The host
1.8 V output bank and isolated converter input reservoir are behind their active
stages. Check input charge and peak current on a real cable; summing nominal
capacitors alone does not certify attach inrush. External input bulk similarly
sits behind U27, whose 10 nF/50 V CT gives about 21.6 ms calculated rise at 5 V.
Its datasheet table gives a different typical value; neither is a guaranteed
minimum. U30's 22 nF/50 V CT gives about 49.3 ms at 5.2 V. The 50 V CT parts
satisfy TI's recommendation for more than 30 V rating at that pin.

U29 is **TPS2553DBVR constant-current**, with R62=75 kΩ. Its approximate
312–393 mA range admits the 300 mA shared target. The latch-off `-1` part must
not be substituted: charging the two 220 µF USB-A reservoirs can exceed its
minimum fault-deglitch interval. C44/C47 each retain at least 176 µF from nominal
tolerance, above the USB-A 120 µF design requirement.

U48/R121=68 kΩ/R122=1 kΩ/C116=22 µF report sustained bus overload after an RC
interval. C116 returns to ISO_3V3 so a fresh supply ramp begins with a healthy
input. With stated capacitor-retention and leakage assumptions, reporting delay
is **0.320–4.16 s**. A conservative 600 µF at 5.5 V, with 300 mA already drawn
and 312 mA available, charges in 275 ms. EEPROM power-on time is 500 ms.
A persistent short can cause U29 thermal cycling before the delayed fault;
current limiting remains immediate and U31 independently sheds loads on core
undervoltage. The delay is only fault reporting. Do not call it a precise timer.
On power removal R122 bounds input-clamp current; a rapid restart after a fault
can require seconds to clear. Verify minimum effective C116 and worst startup
with all four attached devices. [Schmitt buffer](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf).

U47 uses the 10 µs INA300 setting for external aggregate overload, U46 the
100 µs setting for input overload. Both pull PORT_RAIL_OK low and latch while
PORT_ANY_ON is high. U31 also pulls this net low near 4.455 V ISO_5V, with a
restart delay, preserving logic power ahead of loss of U10 regulation. Diode
fanout pulls all four OCS inputs low. The host must remove **all** port power
permissions to clear the aggregate latch. Per-port faults remain independent;
each TPS2553 reports through its own OCS net. Observe actual threshold/timing
and latch recovery; a single port short may first trip the faster aggregate
monitor. [INA300](https://www.ti.com/lit/ds/symlink/ina300.pdf),
[supervisor](https://www.ti.com/lit/ds/symlink/tps3808.pdf).

For J5/J6, controller ID is active low on valid sink attachment. The inverter
and AND gate require both attachment and hub PRTPWR permission before VBUS.
Default Rp is always provided by the controller; no external Rp or VCONN supply
is fitted. The complementary gate drives 100 Ω discharge through Q5/Q6 after
detach. With 13 µF and 5.5→0.8 V, calculated active discharge is 2.53 ms and
10 kΩ passive fallback is 253 ms. These estimates omit an attached device's
extra capacitance and backfeed; test the connector voltage directly. Peak
resistor energy is about 0.20 mJ at 5.5 V, not continuous 5.5 V loading.

## Capacitance and loop stability

Selected 25 V bulk MLCCs provide voltage headroom, but nameplate capacitance is
not effective capacitance. The screening assumption for 22 µF X7R is
`22 × 0.9 tolerance × 0.85 temperature × 0.95 ageing × 0.80 bias = 12.79 µF`.
Three capacitors provide 38.37 µF; U28's four provide 51.16 µF. For 10 µF X5R,
use at least 50% bias retention plus tolerance/temperature/ageing: about 3.63 µF.
C84 is increased to 22 µF/25 V, giving 7.99 µF even with only 50% bias
retention, above its 4.7 µF minimum. The 1 µF LDO output capacitors
must retain ≥0.47 µF. Verify all these values against the purchased part's
manufacturer bias data or measured lots before assembly acceptance; the Murata
SimSurfing EULA was not accepted on the user's behalf.

U28 uses 4.7 µH, 400 kHz, RC=2.7 kΩ, CC=220 nF, CP=100 pF. The reproducible
averaged boost-plant screen spans input, load, Ceff, ESR and assumed error-amp
output resistance. It finds minimum 56.5° phase margin, 16.6 dB gain margin and
maximum crossover 11.77 kHz; no screened corner exceeds the selected crossover
limit. Ro is not guaranteed in the datasheet, and lumped ESR/capacitance does not
model distributed USB reservoirs or PFM transitions. Thus this is a component
selection screen, **not loop-stability signoff**. Verify Bode response and line,
load, startup and cable transients on the routed board; retain the reworkable
compensation parts.

## Suspend and descriptor limits

The default-current host with external power has a calculated L2 estimate of
2.463 mA at 4 V, assuming 60% U45 light-load efficiency and 0.50 mA combined
controls. This narrow budget requires measurement; controller typical currents
are not guaranteed maxima. Test suspend/resume and remote wake across both
supply orders. With a qualified 1.5/3 A Type-C host, Type-C current allowances
continue during suspend; the isolated converter need not be disabled solely
because USB data suspended. [USB-IF sink suspend test](https://www.usb.org/sites/default/files/USB%20Type%20C%20Functional%20Test%20Specification%202024%2003%2003.pdf).

The EEPROM declares dynamic self/bus power honestly, with 100 mA upstream
controller allowance externally powered and 500 mA bus-powered. This four-port
bus mode does **not** guarantee four simultaneous 100 mA unit loads: the shared
300 mA power budget and host software's legacy hub accounting are limitations.
Use qualified Type-C hosts and validate descriptor acceptance; external power
is required for four 500 mA loads and is the interoperability fallback. There is
no USB-IF certification, proprietary charging, PD, or unconditional legacy-host
bus-power claim. See `EEPROM.md` and the explicit bring-up tests.
