# Archived 4-port design finding — CC lines drive comparator inputs with no ESD clamp

> **Repo note (2026-07-30):** the design this document calls "v1" is now simply
> **the isolator** — the single, shipping project at the repo root
> (`isolator.kicad_sch` / `.kicad_pcb` / `.kicad_pro`). It is no longer a
> sub-project under `v1/`, and paths below have been updated accordingly. What
> this document calls "v2" is the **archived 4-port design**, now on branch
> `4port-archive`. Past-tense passages comparing the two are kept as written —
> they record why decisions were made and only make sense in that tense.

**Date:** 2026-07-28
**Applies to:** the archived 4-port design (`4port-archive:isolator.kicad_sch`), not the isolator
**Severity:** medium — exposed IC pin on an external connector
**Found during:** ESD review for the isolator's design spec
(`docs/superpowers/specs/2026-07-28-usb-isolator-v1-design.md`)

## Finding

On the external-power USB-C receptacle J2, both CC lines run from the
connector pin, through a 5.1 kΩ Rd, directly into a TLV7041 comparator input
with no ESD protection anywhere on the net.

From the exported netlist:

```
/EXT_CC1: J2.A5 (USB_C_Receptacle_PowerOnly_6P) → R5.1 (5.1k) → U13.4 (TLV7041DBV)
/EXT_CC2: J2.B5 (USB_C_Receptacle_PowerOnly_6P) → R6.1 (5.1k) → U14.4 (TLV7041DBV)
```

These are the most exposed IC pins on the board: a user-accessible connector
contact with a semiconductor input behind it and nothing in between but a
series resistor.

Every other CC net in the 4-port design is fine — `/P3_CC1`, `/P3_CC2`, `/P4_CC1`,
`/P4_CC2`, `Net-(J1-CC1)`, and `Net-(J1-CC2)` all terminate on resistors
only, with no IC pin behind them.

## Why it matters

TI SLVAF82B §7.2 calls for ESD protection on CC pins with V_RWM ≥ 5 V, and
§8.3 documents the short-to-VBUS case: withdrawing a plug at an angle can
short the VBUS pin to a CC pin. On the 4-port design's external port that event, or a plain
contact discharge, reaches the TLV7041 input.

The 5.1 kΩ series resistor helps but is not a clamp — it limits steady-state
current, not the peak voltage presented to the input during a nanosecond-scale
transient.

## Recommended fix

Add an ESD441-class part (V_RWM 5.5 V, ~1 pF, DFN0603) from each of
`/EXT_CC1` and `/EXT_CC2` to GND2, placed **connector-side of R5/R6** so the
clamp sees the strike before the resistor. Two parts.

While in that area, apply the same layout rules the isolator's design spec makes binding:
clamp within 5 mm of the connector pin, ground pin on its own via straight to
plane.

## Explicitly not applicable to the isolator

The isolator has no external power input, no CC comparators, and no PD. Its CC nets
reach only a 5.1 kΩ Rd upstream and a 56 kΩ Rp downstream, with no IC pin
behind either. The short-to-VBUS case there pushes about 1 mA through a
resistor. The isolator deliberately ships without CC protection; see the ESD section of
The isolator's design spec.
