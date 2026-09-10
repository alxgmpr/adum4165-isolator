# Rev C design decisions and evidence

Status: implementation in progress; no completed-board or compliance claim.

## Isolator

U1 is ISOUSB211DPR. The independent pin/net mapping follows TI SLLSFC5D,
Table 4-1. Side 1 uses VBUS_HOST for VBUS1/VCC1; side 2 uses ISO_3V3 for
VBUS2/V3P3V2/VCC2. The four 1.8 V bypass groups remain distinct physical
groups, two per ground domain; the like-named rails within a domain connect
after their local bypass groups. CDP is disabled. Equalization starts at zero.
V1OK supplies the isolated-domain host-present signal; V2OK is a test point.
Y1 and its load capacitors are removed; Y2 remains the hub clock.

The local HV footprint follows TI drawing 4231707/A, DP0028A-C02, p.40:
28 pads, 0.65 mm pitch, 1.65 x 0.45 mm pads, row centers at x = +/-4.925 mm.
The nearest copper edges are +/-4.1 mm: 8.2 mm nominal copper clearance.
This is the manufacturer HV pattern, not an 8.3 mm pattern. Package minimum
clearance/creepage is greater than 8.15 mm. Board fabrication, solder fillets,
other barrier parts, shields, and mechanical geometry constrain the system;
no certified board insulation rating is assigned.

Sources: [ISOUSB211](https://www.ti.com/lit/ds/symlink/isousb211.pdf),
[EVM](https://www.ti.com/lit/pdf/sbou261).

## 3.3 V rail

TPS62162DSGR replaces TPS62203. It supplies a fixed 3.3 V at up to 1 A,
leaving substantial margin above the 264.5 mA hub/isolator maximum before
control loads. It is not pin compatible with TPS62203. PGND, AGND, and EP
join GND2; fixed-version FB is grounded and VOS senses the output.

Source: [TPS6216x](https://www.ti.com/lit/ds/symlink/tps62162.pdf).

## Type-C qualification

Use TUSB320LAIRWBR for each sink input, configured for UFP and GPIO mode.
Use the LAI variant specifically. The old TUSB320 latches its initial current
advertisement; TI support identifies the later LAI as updating it. The LAI
datasheet retains confusing one-time-detection wording, so dynamic current
changes remain an explicit bring-up test. GPIO truth table: HH unattached,
HL default attached, LH 1.5 A, LL 3 A. Host converter permission is NOT OUT1;
external permission is NOR(OUT1, OUT2). Unpowered GPIO pull-ups return only
to their own local supply. No duplicate discrete Rd is fitted.

Sources: [LAI datasheet](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf),
[TI clarification of current tracking](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/735532/tusb320lai-failing-usb-if-td-4-3-4-sink-connect-try-snk-drp-test).

## Power-path defects found in Rev B

- TPS2121 selects the sole valid source irrespective of PR1/CP2 priorities.
  Therefore priority strapping alone cannot reject a weak external source.
  Rev C must gate that source before IN1.
- External VBUS at 4.75 V has no allowance for mux and port-switch drops.
  A regulated external rail is needed to guarantee the downstream voltage
  range over the stated input corners.
- Independent port limits do not protect the isolated converter against the
  sum of loads. Port supply protection must leave the hub/isolator rail alive.
- Existing R10 and R11 are bypassed by same-net wiring; R15's value text says
  DNP but that alone is not an assembly exclusion. Rebuild these straps with
  distinct nets and explicit DNP state.

Source: [TPS2121 truth table](https://www.ti.com/lit/ds/symlink/tps2121.pdf).
