# Isolated 4-Port USB 2.0 Hub — Rev B Design Spec

**Date:** 2026-08-08
**Project:** `isolator` (KiCad)
**Status:** Draft — pending review

> Written in the past tense where it records why a decision was made. Numbers
> marked **(estimate)** have not been verified against a datasheet or a
> measurement and are carried forward from earlier specs; they are the first
> things to confirm at part selection.

## Overview

A galvanically isolated 4-port USB 2.0 hub, built fresh rather than derived
from either existing board. It takes the proven core of the single-port
isolator (`main`, rev A) and the hub architecture of the archived 4-port
design (`4port-archive`), and adds one capability neither had: **detection of
the host's USB-C current advertisement**, so the board can legally draw more
than 500 mA from a capable host.

Relationship to the two predecessors:

| | rev A single-port | 4-port archive | this design |
|---|---|---|---|
| ADuM4165 core + 24 MHz Side-1 crystal | yes | yes | **kept** |
| SN6505B + Würth 750313638 + Schottky | yes | yes | **kept** |
| Post-rectifier regulator | TLV76750 LDO | MIC29302 LDO | **synchronous buck** |
| Upstream CC current sensing | no | no | **new** |
| External supply + priority mux | no | TPS2121 | **kept from archive** |
| Downstream ports | 1 | 4 | 4 |
| Enclosure | Hammond 1455C extrusion | 1455C extrusion | **plastic bench box** |
| Local RF shielding | no | no | **new — 2 cans** |

Primary references:

- ADuM4165/ADuM4166 data sheet Rev. B (`adum4165-4166.pdf`)
- SN6505B data sheet SLLSEP9I (`SN6505BDBVR.pdf`)
- TPS2553 data sheet SLVS841F (`TPS2553DBVR.pdf`)
- USB Type-C Cable and Connector Specification (source current advertisement)

## Requirements

- USB 2.0 low (1.5 Mbps), full (12 Mbps), and high speed (480 Mbps)
  pass-through.
- Galvanic isolation between host and all downstream ports. The power path
  must not undercut the ADuM4165's barrier.
- 4 downstream ports: 2× USB-A, 2× USB-C (USB 2.0 data, 5 V only).
- **Bus-powered is the primary mode.** The board must be useful on host power
  alone, with the external supply reserved for heavy loads.
- Detect the host's Type-C current advertisement and never exceed it.
- Per-port overcurrent protection with fault reporting through the hub.
- Plastic enclosure. No conductive path may exist between GND1 and GND2
  through any mechanical part.

## Architecture

```
 HOST SIDE (GND1)              ║ 5.7 kV ║          ISOLATED SIDE (GND2)
                               ║        ║
 J1 USB-C ──┬── CC sense ──> EN ║        ║   J2 USB-C power-only
 (Rd 5.1k)  │   (>=1.5 A?)   │  ║        ║   (Rd + 3 A CC detect)
            │                v  ║        ║            │
            ├── VBUS ──> SN6505B + 750313638 ══> rect ──> BUCK ──┐
            │            [SHIELD A]     ║        ║   [SHIELD B]  v
            │                           ║        ║      TPS2121 mux ──> ISO_5V
            └──> ADuM4165 VBUS1         ║        ║               │
                 (24 MHz, Side 1)       ║        ║               │
                 D+/D− ─ESD─> UD± ══════║══════> DD± ─> USB2514B <── 3.3 V
                               ║        ║               │
                               ║        ║        4× TPS2553 (PRTPWR / OCS)
                               ║        ║        2× USB-A + 2× USB-C
```

The ADuM4165 (not the '4166) remains correct: its clock input is on Side 1,
and ADI recommends the '4165 with a Side-1 crystal for isolator boxes with no
local controller, since host power is always present there.

## Power state machine

The design's central simplification: **no signal crosses the barrier.** The
CC sense sits on GND1 and drives only `SN6505B.EN`, which is also on GND1.
The external supply reaches `ISO_5V` through the mux independently of the
converter, so disabling the converter never strands the brick path.

| Host advertisement | External supply | Behaviour |
|---|---|---|
| ≥1.5 A | absent | Converter runs. ~390 mA shared across four ports |
| ≥1.5 A | present, 3 A confirmed | Mux selects external. Converter idles unloaded. 500 mA/port |
| Default (500 mA) | present, 3 A confirmed | Converter off. Runs entirely on external supply |
| Default (500 mA) | absent | Converter off, isolated side unpowered. Host not overdrawn |

When the mux selects the external supply the converter is left running but
unloaded, drawing an estimated 30–50 mA of host power in core and quiescent
losses **(estimate)**. Disabling it would require a GND2→GND1 signal and a
second barrier crossing; the idle loss was judged the cheaper trade.

The last row is a silent failure from the host's point of view — no
enumeration, nothing to diagnose. A host-side "insufficient host power" LED
driven from `SN6505B.EN` makes it self-explanatory for two parts, and is
included.

## Power budget

### Bus-powered mode (host advertising ≥1.5 A)

| Term | Value |
|---|---|
| SN6505B primary, 800 mA at 5 V (1 A part, margin kept) | 4.00 W |
| ADuM4165 Side 1 | 0.35 W |
| **Total drawn from host** | **4.35 W ≈ 870 mA** |
| Transformer + rectifier, ~85 % **(estimate)** | 3.40 W at `DCDC_RAW` |
| Buck, ~92 % **(estimate)** | 3.10 W at `ISO_5V` ≈ 625 mA |
| less ADuM4165 Side 2 (`IDD2(H)`) | −70 mA |
| less USB2514B via 3.3 V LDO **(estimate)** | −155 mA |
| less indicators | −10 mA |
| **shared across all four ports** | **≈ 390 mA** |

870 mA sits comfortably inside a 1.5 A advertisement, leaving headroom for
the advertisement to be honoured under transient load.

Two levers raise the port figure if bring-up shows it is not enough:

- **3.3 V buck instead of an LDO for the hub:** an LDO passes the hub's
  155 mA straight through from `ISO_5V`; a 90 % buck draws
  155 mA × 3.3 V ÷ (5 V × 0.90) ≈ 114 mA. **+41 mA to the ports.**
- **SN6505B at 900 mA primary instead of 800 mA:** **+79 mA to the ports**,
  at the cost of margin against the part's 1 A rating.

Taking both would put the port budget near 510 mA. Neither is committed here
— see Open decisions.

The 85 % transformer-plus-rectifier figure is inherited from the rev A spec,
where it was derived from the closest 1 A-class part in the same Würth family
at **300 mA**. This design runs the primary at 800 mA. TI publishes no
efficiency curve for the 750313638 specifically. **Re-derive this number
before trusting the port budget.**

### External-supply mode

A 15 W (5 V / 3 A) source covers 235 mA of logic plus 4 × 500 mA of port
current = 2.235 A ≈ 11.2 W, with margin. Per-port 500 mA is a real number in
this mode.

## Upstream CC sensing (GND1) — new

Two comparators watch J1's CC1 and CC2, outputs wire-ORed to `SN6505B.EN`.
This is the same TLV7041 open-drain arrangement the archived design used on
its *external* input, repointed at the *host* port and at the 1.5 A threshold
rather than 3 A.

> **CORRECTED 2026-08-08.** This paragraph originally specified a **pull-down**
> on the wire-OR node. That cannot work: an open-drain output pulls low when
> asserted and is high-Z otherwise, so a node over a pull-down sits low
> unconditionally and `EN` can never assert. The node needs a **pull-up**, and
> because a pull-up makes it low-when-asserted while `SN6505B.EN` is
> active-high, an inverting stage is required. TLV7041 was separately confirmed
> to be open-drain (TLV703x is push-pull, TLV704x open-drain). Take the
> implemented circuit and its resistor values from
> `docs/superpowers/reviews/2026-08-08-revb-part-selection.md` §4.2, which was
> verified on review — including the `EN` pull-up value, which must clear the
> SN6505B's 20 µA max input leakage against a 0.7 × VCC threshold.

Sink-side detection thresholds, per the Type-C specification:

| Source advertisement | CC voltage across the 5.1 kΩ Rd | Detection threshold |
|---|---|---|
| Default USB power | ≈ 0.40 V | >0.20 V — attached |
| 1.5 A | ≈ 0.92 V | >0.66 V |
| 3.0 A | ≈ 1.68 V | >1.23 V |

Threshold set at 0.66 V. Two implementation constraints:

- **The reference divider must come off `VBUS_HOST`, not off any isolated
  rail.** The comparison has to be valid *before* the converter starts,
  because its result is what starts the converter. A reference derived from
  anything downstream of `SN6505B.EN` is a latch-up by construction.
- **On an e-marked cable one CC line carries VCONN at 5 V**, which reads as a
  false high on that comparator. The wire-OR makes this benign — VCONN only
  appears alongside high-current-capable sources — but it is recorded here so
  it is not rediscovered as a bug.

Both CC lines must be sensed. Only the one mated to the cable's CC wire sees
the source's Rp; the other sees VCONN or nothing, and which is which depends
on plug orientation.

## Isolated power chain (GND2)

- **Converter:** SN6505BDBV push-pull driver (420 kHz, spread spectrum) +
  Würth 750313638 transformer (1:1.3, 5 kVrms) + Schottky full-wave
  rectifier. Unchanged from both predecessors.
- **Regulator:** synchronous buck replacing rev A's TLV76750 LDO. The LDO
  burned the difference between `DCDC_RAW` (~5.8 V loaded) and 5.0 V, which
  at these currents is the single largest recoverable loss in the chain.
  Part not yet selected.
- **External input:** J2, power-only USB-C receptacle, dedicated dual 5.1 kΩ
  Rd. Two TLV7041 open-drain comparators (threshold 1.23 V) confirm a 3 A
  source advertisement before the supply is preferred.
- **Priority mux:** TPS2121. IN1 = external, IN2 = converter output,
  OUT = `ISO_5V`.

  **Required behaviour (archive finding DR-06):** no 3 A ⇒ OUT = IN2
  unconditionally; 3 A detected ⇒ OUT = IN1. Grounding CP2 and relying on PR1
  alone puts the TPS2121 in VCOMP mode, which selects the *higher* input
  rather than IN2 — so a weak supply sitting above the converter output would
  win and be silently overloaded.

  > **CORRECTED 2026-08-08.** This paragraph originally went on to say "CP2
  > must be driven by the 3 A-detect net." **The behavioural goal above is
  > right; that mechanism is wrong** and delivers its opposite. Per SLVSEA3F
  > Table 9-3, `CP2` high with `PR1` low selects **IN2** — so driving CP2 from
  > the detect makes the mux ignore the external supply exactly when it has
  > been confirmed good, and fall into VCOMP mode when it has not. The working
  > arrangement biases CP2 to a fixed level above V_REF and drives **PR1** from
  > the detect. Take the divider values, the bias source, and the resulting
  > switchback threshold from
  > `docs/superpowers/reviews/2026-08-08-revb-part-selection.md` §4.2.

- **Rails from `ISO_5V`:** ADuM4165 `VBUS2`, the four port switches, and a
  3.3 V rail for the hub.

## Hub and downstream ports (GND2)

- **Hub:** USB2514B (QFN-36). 3.3 V supply, internal 1.8 V core regulator
  (CRFILT), own 24 MHz crystal, 12 kΩ RBIAS, strap configuration, no
  SMBus/EEPROM. Upstream port from ADuM4165 `DD+`/`DD−`.
- **Port switches:** one TPS2553 per port, EN from hub PRTPWR, FAULT to hub
  OCS, so an overcurrent is reported upstream and the other three ports
  survive.
- **ILIM:** set per port so `I_OS(min)` clears the intended per-port current.
  Compute from all three of SLVS841F's min/typ/max equations, not by scaling
  the nominal — rev A set 93.1 kΩ for a nominal 286 mA and ended up with a
  guaranteed minimum trip point *above* what its supply could deliver, so the
  FAULT LED could never light on a real overload.
- **Connectors:** 2× USB-A, 2× USB-C. Each USB-C CC pin pulls up through
  56 kΩ (Default USB power). **Do not advertise 1.5 A downstream** — in
  bus-powered mode the ports share ~390 mA, and advertising more than can be
  delivered is what produced rev A's brown-out behaviour.
- **Protection:** USBLC6-2SC6 per downstream port on D+/D−, flow-through
  orientation (in on pins 1/3, out on 6/4) so each pair enters one edge and
  leaves the opposite edge at constant spacing.

## Enclosure and shielding

**Plastic bench box.** Chosen over metal specifically to eliminate a failure
mode: in a metal enclosure a downstream connector shell contacting the panel
bonds GND2 to a GND1-referenced chassis and destroys the barrier, while the
board continues to enumerate and pass data with nothing visibly wrong. Every
mitigation for that (sub-panels, insulating bushings, clearance apertures)
depends on assembly care, which is the wrong class of defence for a safety
barrier.

Shielding is instead local, and proactive:

| | Frame | Cover | Footprint | Height | Cost |
|---|---|---|---|---|---|
| **Shield A** — GND1: SN6505B, bypass caps, primary loop | `BMI-S-201-F` | `BMI-S-201-C` | 13.66 × 12.70 mm | 2.54 mm | $1.25 |
| **Shield B** — GND2: rectifier, buck, inductor, switch node | `BMI-S-209-F` | `BMI-S-209-C` | 29.36 × 18.50 mm | 7.00 mm | $2.59 |

Alternate for Shield B if the buck section lays out squarer:
`BMI-S-203-F` / `-203-C`, 26.21 mm square, 5.08 mm. **Do not use
`BMI-S-205-F`** — 243 in stock at survey time.

Hard rules:

1. **Two shields, never one.** A single can spanning T1 would land walls on
   both GND1 and GND2 copper — the metal-enclosure failure mode reintroduced
   in miniature and soldered down.
2. **T1 itself is not shielded, and cannot be.** Its leakage field is the
   dominant radiator; the cans address the two switchers only. Control of the
   transformer's field is loop area, the stitching grid, and CY1.
3. **Each can's fence carries the full ≥8.3 mm creepage obligation** to the
   opposite domain, because the fence is live copper on its own ground. The
   cans must sit back from the barrier, not against it. Budget this at
   placement — it costs area in the most congested part of the board.
4. **Two-piece, not one-piece.** The frame solders at assembly; the cover
   snaps on after bring-up. Scoping the switch node on a first board is not
   optional.
5. Frames go on the board and the BOM; covers are optional stock. A soldered
   frame with no cover costs ~$2 and adding the cover later is a snap-fit,
   not a respin.

Both frames need custom footprints built from Laird's published pad patterns.

## Barrier and layout rules

Carried over from rev A unchanged unless noted:

- ADuM4165 in 20-lead wide-body SOIC, **≥8.3 mm creepage/clearance**.
- Routed slot under T1 (the recommended land pattern yields 7.51 mm; the slot
  restores margin).
- **CY1 is the only intentional barrier crossing** — Y1-rated, giving GND2's
  ESD current a defined return path instead of forcing it through the
  ADuM4165 die. No copper bridges the barrier on any layer.
- 90 Ω differential pairs, length-matched, for every USB segment: J1→ADuM,
  ADuM→hub, hub→each port.
- 4 layers, ground pour on both outer layers, via stitching on a 4 mm grid,
  fences around every USB pair.
- ADuM4165 bypass within 10 mm total lead length. **Pins 4, 7 (GND1) and 15,
  16, 17 (GND2) are ground-only and are not valid bypass returns** (data
  sheet Table 12) — Side-1 bypass returns via pins 2/10 only, Side-2 via
  11/19 only.
- Rectifier diodes placed **side by side, not in series**.
- Each cap's owning pin and placement constraint recorded in its `Description`
  property. Rev A demonstrated that pin names alone do not stop a bypass cap
  landing at the wrong device.
- Star-point discipline for shared rails: where one net name feeds several
  devices with different placement needs, split it explicitly rather than
  letting the router satisfy whichever pin it reaches first.
- **Edge copper:** the rev A ≥1 mm pullback existed only for the extrusion's
  aluminium slots and no longer applies as written. Retain a pullback sized
  to the plastic box's standoffs and internal features.

## Open decisions

Deliberately unresolved. Both are implementation choices, and both should be
settled with the port budget in hand.

1. **Buck part selection.** Needs ≥700 mA output at 5.0 V from a ~5.8–6.15 V
   input — a low dropout ratio, which constrains the choice more than the
   current does. Must fit under Shield B with its inductor.
2. **Hub 3.3 V rail: LDO or second buck.** Worth ~41 mA of port budget, which
   is over 10 % of what the ports get in bus-powered mode. An LDO is one part
   and no magnetics; a buck is the difference between a usable and a marginal
   bus-powered mode.

## Known limitations (accepted)

- **Bus-powered ports share ~390 mA.** Any one port can take most of it; four
  cannot run hot simultaneously. This matches how bus-powered hubs behave in
  practice and is why the downstream ports advertise Default USB power rather
  than 1.5 A.
- **Full 500 mA per port requires the external supply.**
- **A Default-advertising host with no external supply leaves the isolated
  side unpowered.** Deliberate — the alternative is overdrawing a port that
  offered 500 mA. Signalled by the host-side LED.
- **Legacy USB-A-to-C cables always read as Default**, since the adapter
  presents a fixed Rp. On a legacy host this board needs the external supply.
- The isolator adds hub-tier delay; with the USB2514B this consumes ~3 of
  USB's 5 tiers. Deeply cascaded hubs downstream may fail.
- Downstream USB-C ports are USB 2.0 data, 5 V only. No PD, no SuperSpeed
  pairs.
- The hub declares self-powered regardless of actual source (strap-only
  configuration cannot switch descriptors dynamically). In bus-powered mode
  this is a descriptor-honesty deviation; the per-port TPS2553 limits and the
  converter's own ceiling bound the actual draw.
- L1 sleep is not supported by the ADuM4165 (L2 suspend is).
- T1's leakage field is unshielded by necessity.

## Verification plan

1. **Host side alone:** VDD1 present, 24 MHz oscillation.
2. **CC sensing:** confirm `SN6505B.EN` asserts on a 1.5 A and a 3 A
   advertisement and stays low on Default. Test on the target MacBook, a
   legacy USB-A-to-C cable, and a bus-powered hub. Measure the actual CC
   voltage in each case rather than inferring it.
3. **Converter efficiency at the real operating point** — 800 mA primary, not
   300 mA. This validates or invalidates the port budget; do it before
   trusting any of the numbers in Power budget.
4. **Isolated rails:** buck output voltage and ripple, 3.3 V rail, mux
   switchover under load.
5. **Hub enumerates through the isolator at high speed** (`lsusb -t`).
6. **Each port with real LS/FS/HS devices** — mouse, serial adapter, flash
   drive.
7. **Per-port overcurrent:** shorted load ⇒ hub reports fault, other ports
   unaffected. Confirm the FAULT path actually asserts, which rev A's ILIM
   choice prevented.
8. **Port budget under load:** four devices drawing simultaneously,
   bus-powered, confirm the shared ceiling behaves as specified rather than
   browning out the link.
9. **Radiated emissions with covers off and on**, to decide whether the
   covers ship populated.
10. **Barrier continuity check:** confirm no DC path GND1↔GND2 on an
    assembled unit, including through both shield cans.
