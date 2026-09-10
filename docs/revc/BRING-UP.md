# Rev C bring-up checklist — all hardware tests pending

No hardware was ordered or energized for this handoff. Complete routing and
independent fabrication/assembly review before performing these tests. Record
board revision, actual component lots, cable, source, ambient temperature,
instruments and scope captures for each result.

## Before first power

- Rerun ERC and PCB DRC with schematic parity; resolve all remaining unrouted
  connections after routing. Inspect planes, differential paths, Kelvin sense,
  thermal lands/vias and all four U1 bypass returns. Preserve the barrier.
- Verify exact U1 DP28 HV package, U11 M2/EP37, U6 RNM15 and U28 RYQ21 pin maps.
  Check diode/TVS polarity, polarized capacitor orientation, USB pin numbering,
  populated zero-ohm links and five deliberate DNP positions.
- Check GND1/GND2 DC isolation and absence of accidental shell/hardware bridges.
  Account for CY1 charging when measuring resistance. Do not select a hipot
  voltage from U1's headline rating alone.
- Check input-to-ground shorts and each regulated rail. Inspect fine-pitch
  soldering, exposed pads and shield lands under magnification.
- Confirm capacitance at working bias: 22 µF bulk groups, ≥4.7 µF C84 VCC,
  ≥0.47 µF LDO outputs, and ≥12.79 µF C116 for the timer calculation. Check
  transformer and inductor identities. Verify connector and lid fit separately.

## Controlled power and configuration

1. Use a current-limited bench source and a correct Type-C advertisement fixture.
   Start externally powered with no host/peripherals, ramp voltage slowly and
   observe EXT_3A_OK, U27 output, U28 output, ISO_5V and ISO_3V3. Confirm weak
   default/1.5 A external sources are rejected in both orientations.
2. Check 5.20 V nominal external regulation, 3.3 V core, and host 1.8 V when a
   host fixture is present. Verify U28/inductor/diode switching waveform limits,
   startup, no unexpected backfeed and no abnormal heating.
3. Program/read back the 256-byte EEPROM using `EEPROM.md`: TP13 reset,
   TP14 SDA, TP15 SCL, TP16 GND2; board already powered. Verify the manifest hash.
4. Connect a default-current host with external power. Check V1OK/HOST_PRESENT,
   VBUS_DET, reset timing and enumeration at **480 Mbps**. Read all descriptors:
   four ports, correct high/full-speed behavior, dynamic power status, individual
   switching/OC, no charging, 500 ms port-power interval.
5. Repeat host-first, external-first, simultaneous and slow/bouncing supplies.
   Remove the host while external power remains; hub must disconnect/reset and
   ports lose permission. Reconnect without cycling external power.

## Source and load matrix

- Host alone: test unattached, default, 1.5 A and 3 A advertisements in both
  orientations. Default host must not enable isolated converter. Qualified
  operation must remain below the 1.5 A allowance; predicted maximum steady
  draw is 1.064 A. Verify advertisement changes while attached and fallback.
- Bus mode: increase total downstream load through 0, 100, 200, 300 mA, then
  overload. Test simultaneous USB-A reservoir charging and four attached
  devices at cold start. Measure the actual U29 limit (approximately 312–393 mA),
  startup before the 500 ms descriptor interval, and delayed OCS behavior.
  Confirm logic/link recovery after overload; reduce the published bus budget
  if low-input or thermal corners cannot sustain it.
- External mode: test 0–2 A aggregate and 0–500 mA per port. For initial 2 A
  acceptance require **≥5.0 V at J2 under load**, U28 efficiency ≥90%, U8 junction
  ≤85°C, and the stated routed voltage-drop/ripple budget. At 4.75 V or poorer
  efficiency, characterize derating instead of silently accepting low VBUS.
- At full external load, measure every receptacle VBUS: **≥4.75 V and ≤5.5 V**,
  including ripple/transients. Measure regulator-to-port routed loss separately;
  the current DC budget allocates only 15 mV beyond listed component drops.
- Sweep J2 input-current trip and external output-current trip: expected audited
  ranges are 2.772–2.971 A and 2.027–2.277 A respectively. Apply single-port and
  aggregate shorts with a controlled fixture. Verify OCS fanout, core survival,
  thermal behavior and recovery after all PRTPWR permissions are cleared.
- Remove/restore external power at idle and load. Expect disconnect and
  re-enumeration. Check mux reverse current and connector backfeed in every
  source combination. Confirm weak external power never becomes a sole source.

## Type-C, data, suspend and thermal tests

- For J5/J6, verify default Rp on either orientation and VBUS absent before
  valid sink attachment. Require attachment AND hub permission. Check detach,
  fault, host reset and total board-power-loss discharge to <0.8 V, including
  device-side capacitance and backfeed. Calculated board-only times are 2.53 ms
  active and 253 ms passive at the conservative 13 µF load.
- Check USB-A fault isolation and USB-C per-port fault indication. Force a
  persistent bus short long enough to observe delayed fault reporting and
  possible limiter thermal cycling; ensure recovery does not leave ports stuck.
- Exercise high-speed bulk transfers on each port and all four together; mix
  low/full-speed devices to exercise multi-TT operation. Check both C-port
  orientations, hot plug and marginal cables. Perform USB2 eye, jitter, reset,
  chirp, ESD and immunity tests with suitable fixtures before any compliance claim.
- Check hub crystal frequency/load/drive. Start with the captured 27 pF caps;
  adjust only from measured frequency and known probe loading. EQ straps remain
  at zero initially; change them only after link-loss/eye measurements.
- With default host plus external power, measure upstream suspend draw ≤2.5 mA
  and resume/remote wake. The calculated 2.463 mA estimate has little margin and
  depends on actual light-load behavior. Qualified 1.5/3 A Type-C source power
  allowances apply during suspend; verify current fallback when advertisement
  changes. Test descriptor acceptance on intended OSes, including bus-mode
  child-device power allocation. Legacy bus-host interoperability is not assured.
- Measure U28 loop response and line/load steps over Ceff/ESR/cable/load corners,
  including PFM and source switching. Initial goals: ≥45° phase margin, ≥10 dB
  gain margin, no sustained oscillation, and port/logic rails within limits.
- Soak at the intended maximum ambient with both covers fitted; measure U8,
  U28, U5/U6, transformer, rectifiers, inductors and shunts. Verify the ≤85°C U8
  full-load constraint, component derating and enclosure temperatures. Repeat
  cold start and hot restart, including a rapid restart after a latched fault.

## Mechanical and release work still pending

Verify received connector mating datums, plug insertion/strain clearance,
through-hole lead protrusion, shield cover engagement and removal, and all
standoff heights. Select a real plastic enclosure and check its full dimensions.
After routing, confirm the chosen impedance stack with the fabricator and review
manufacturing outputs separately. This task neither generated nor released those
outputs and assigned no certified insulation or USB compliance rating.
