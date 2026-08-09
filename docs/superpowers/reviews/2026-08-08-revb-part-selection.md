# Rev B Part Selection — Post-Rectifier Converter, 3.3 V Rail, CC Comparators

**Date:** 2026-08-08
**Task:** Task 2 of `2026-08-08-revb-hub-schematic`
**Scope:** closes the spec's two Open Decisions and verifies one part the spec
assumed. No KiCad files touched.
**Consumed by:** Task 4 (upstream CC sense), Task 5 (isolated power chain),
Task 6 (external input), Task 7 (hub rails).

---

## 1. Decisions at a glance

| Decision | Outcome | MPN |
|---|---|---|
| Post-rectifier converter topology | **Buck-boost**, not a plain buck | `TPS63070RNMR` |
| Hub 3.3 V rail | **Buck** (rule fired: 375 mA < 450 mA) | `TPS62203DBVR` |
| CC comparator output structure | `TLV7041` **is** open-drain — the spec's assumption is correct | `TLV7042DDFR` (dual) |
| Resulting shared port current | **≈ 416 mA** | — |

Two things in this record are changes the spec did not anticipate:

1. **The converter is a buck-boost.** The spec and the plan both say
   "synchronous buck". Section 2 shows why a buck cannot be relied on across
   the legal `VBUS_HOST` range.
2. **The comparator wire-OR as written does not work.** The part is right;
   the network around it is not. Section 4.2 gives the correction. Tasks 4
   and 6 must implement the corrected form.

---

## 2. Step 1 — Post-rectifier converter topology

### 2.1 What `DCDC_RAW` actually is

The plan states `DCDC_RAW` "may sag to ~5.4 V at 625 mA". That number was an
extrapolation from rev A's ~5.8 V at 315 mA and had never been checked against
the transformer's own spec. It has now been derived from first principles and
calibrated against the rev A data point.

**Inputs (all from datasheets, not estimated):**

| Parameter | Value | Source |
|---|---|---|
| T1 turns ratio (N1+N2 : N3+N4) | 1 : 1.3 ±2% | 750313638 datasheet p.1 |
| T1 `R_DC1` (N1+N2, 20 °C) | 0.35 Ω max | 750313638 p.1 |
| T1 `R_DC2` (N3+N4, 20 °C) | 0.33 Ω max | 750313638 p.1 |
| T1 volt-µsecond rating | 10 V·µs (TI lists 11) | 750313638 p.1 / SLLSEP9I Table 9-3 |
| T1 temp rise at 0.65 A push-pull out | ≈ +25 K | 750313638 p.3 curve |
| SN6505B `R(ON)` @ 4.5 V, 1 A | 0.16 Ω typ / **0.25 Ω max** | SLLSEP9I §6.5 |
| SN6505B `F_SW` | 363 / 424 / 517 kHz | SLLSEP9I §6.5 |
| SN6505B `t_BBM` (break-before-make) | 90 ns | SLLSEP9I §6.6 |
| SN6505B `I_LIM` | 1.42 A min | SLLSEP9I §6.5 |
| Schottky `V_f` (SS34) at 0.7 A | ≈ 0.30–0.36 V | SS34 datasheet |

Because the primary is centre-tapped, each half winding carries half the
specified series DCR: `R_pri_half = 0.175 Ω max`, `R_sec_half = 0.165 Ω max`.

**Conduction duty.** At 424 kHz the period is 2.358 µs, so each half-cycle is
1.179 µs. Break-before-make removes 90 ns of it, leaving a conduction fraction
of `(1.179 − 0.090)/1.179 = 0.924`. Winding current during conduction is
therefore `I / 0.924`, not `I`.

**Model.**

```
I_sec(cond) = I_o / 0.924
I_pri(cond) = 1.3 × I_sec(cond)

V_pri_half  = V_BUS − I_pri(cond) × (R_ON + R_pri_half)
V_sec_half  = 1.3 × V_pri_half − I_sec(cond) × R_sec_half
DCDC_RAW    = V_sec_half − R_extra × I_sec(cond) − V_f
```

**Calibration of `R_extra`.** With `R_extra = 0` the model predicts 5.95 V at
rev A's 315 mA operating point; rev A observed ≈ 5.8 V. The 0.15 V residual —
leakage-inductance commutation, core loss, and the non-flat conduction pulse —
divided by the 0.341 A conduction current gives an effective
**`R_extra` = 0.44 Ω referred to the secondary**. That single calibration
constant is carried into every case below.

**Results.**

| Case | `V_BUS` | DCRs | `I_o` | `DCDC_RAW` |
|---|---|---|---|---|
| A — nominal | 5.00 V | typ, warm | 615 mA | **5.44 V** |
| B — worst corner | 4.75 V | max, hot (+18 % Cu) | 615 mA | **4.94 V** |
| C — worst corner at rated load | 4.75 V | max, hot | 700 mA | **4.81 V** |
| D — unloaded (external-supply mode) | 5.25 V | — | 0 | **6.68 V** |
| D′ — unloaded, `V_BUS` at Type-C max | 5.50 V | — | 0 | **7.00 V** |

**How firm is the plan's 5.4 V figure?** It is a good *typical*, not a worst
case. Case A lands at 5.44 V — the plan's number is essentially right for a
5.0 V host and typical windings. But Type-C `vSafe5V` allows `V_BUS` down to
4.75 V, and copper resistance rises ~18 % at the winding temperature implied by
the transformer's own temp-rise curve. In that corner `DCDC_RAW` falls **below
the 5.0 V output**, which is the whole ballgame.

The confidence split: the resistive terms are datasheet-hard; the 0.44 Ω
`R_extra` is a one-point calibration against a rev A number that is itself
"measured/estimated". If `R_extra` is optimistic, cases B and C get worse, not
better. **No part of this conclusion depends on `R_extra` being small — it
depends on it being non-zero, which the rev A data point establishes.**

**Volt-second check (does T1 saturate?).** Applied V·µs per half cycle at Case
A = 4.73 V × 1.089 µs = 5.2 V·µs. At the minimum specified 363 kHz it is
6.1 V·µs. Against the 10–11 V·µs rating that is ≥1.6× margin. T1 is not the
limiting element.

**Transformer + rectifier efficiency at the real operating point.** The spec
carried 85 % as an "(estimate)" derived from a 300 mA reference design and
flagged it for re-derivation. At Case A:

```
P_host = 5.00 V × 800 mA                     = 4.00 W
P_raw  = 5.44 V × 615 mA                     = 3.34 W
η(T1 + rectifier)                            = 83.6 %
```

**Use 83.6 %, not 85 %.** The spec's figure was 1.4 points optimistic.

### 2.2 Topology evaluation

| Topology | Verdict | Reasoning |
|---|---|---|
| **Standard synchronous buck** with 100 %-duty mode | **Rejected** | Works in Case A. In Cases B/C the input is *below* the output, so the part sits in 100 % duty and `ISO_5V` becomes an unregulated copy of `DCDC_RAW` — ≈ 4.85 V at the mux, ≈ 4.76 V at a port after the TPS2121 (56 mΩ) and TPS2553 (85 mΩ) drops. That is 10 mV from the USB self-powered-hub floor, with the SN6505B's 424 kHz ripple riding on it unattenuated. Also: near the dropout boundary the buck hunts between PWM and 100 % mode against a soft source (≈ 0.9 Ω secondary-referred), which is a limit cycle waiting to happen. |
| **Buck-boost** | **Selected** | Regulates 5.00 V across the whole 4.8–7.0 V `DCDC_RAW` range with no mode boundary at `V_in = V_out`. Decouples downstream port voltage from host cable quality. Costs ≈ 3–4 points of efficiency versus a buck in dropout, which is ≈ 25 mA of port budget — see §3 for why that is affordable. |
| **Raise T1's turns ratio** | **Fallback only** | Electrically sound: output power sets primary current regardless of `n`, so a higher ratio buys headroom for free. But there is no drop-in. Würth's 5 kV, 1 A-class parts with higher ratios (`750316031/32/33`, `750315240`) are 12.32 × 15.41 × 11.05 mm — a different footprint, a different land pattern, a re-run of the routed-slot creepage work, and a re-qualification of the barrier. Reserve for a respin if bring-up shows the buck-boost is not enough. |

**Chosen: buck-boost.** If bring-up measures `DCDC_RAW` comfortably above
5.4 V at 615 mA across every host, a buck would have been adequate and cheaper
— but that is not knowable before boards exist, and the buck's failure mode is
an out-of-spec port rail that still enumerates.

### 2.3 Selected part — `TPS63070RNMR`

| Parameter | Value | Requirement | OK? |
|---|---|---|---|
| Input range | 2.0–16 V (abs max 20 V) | 4.8–7.0 V operating | ✓ |
| Output range | 2.5–9 V, `V_FB` = 800 mV | 5.0 V | ✓ |
| Output current | 2 A buck and boost | ≥ 700 mA | ✓ |
| Switch current limit | 3.6 A | — | ✓ |
| `I_Q` (into VIN, PFM, no load) | 54 µA typ / 103 µA max | idles in external-supply mode | ✓ |
| Switching frequency | 2.4 MHz | — | — |
| Min duty in buck mode | 30 % (⇒ `V_in/V_out` ≤ 3.33) | 1.40 max | ✓ |
| Package | VQFN-HR-15 (RNM), 3.0 × 2.5 mm | under Shield B | ✓ |

Adjustable version chosen over the fixed-5 V `TPS630701RNMR` purely on stock
depth (26,889 vs 1,740 — see §5). Cost is two 1 % divider resistors:
`R1/R2` for `V_FB` = 800 mV, e.g. R1 = 523 kΩ, R2 = 100 kΩ → 4.984 V.
`R4` = 100 kΩ from FB to FB2 is per TI's BOM; `VSEL` is tied low (voltage
scaling unused).

**Pin table — `TPS63070RNMR`, VQFN-HR-15 (RNM):**

| Pin | Name | I/O | Function | This design |
|---|---|---|---|---|
| 1 | PS/SYNC | I | low = forced PWM; high = PWM/PFM | tie **low** (forced PWM) — see note |
| 2 | PG | O | open-drain power good | pull-up to `ISO_5V_PRE`, optional LED / test point |
| 3 | VAUX | O | internal LDO cap; **must not be loaded** | 100 nF 0402 to GND |
| 4 | GND | — | control/logic ground | GND2 |
| 5 | FB | I | feedback (0.800 V) | divider from `ISO_5V_PRE` |
| 6 | FB2 | O | voltage-scaling output | 100 kΩ to FB (per TI BOM) |
| 7, 8 | VOUT | O | converter output | `ISO_5V_PRE` → TPS2121 IN2 |
| 9 | L2 | I | inductor, output side | L to pin 11 |
| 10 | PGND | — | power ground | GND2 |
| 11 | L1 | I | inductor, input side | L to pin 9 |
| 12, 13 | VIN | I | power stage supply | `DCDC_RAW` |
| 14 | EN | I | enable (precise threshold) | tie to `DCDC_RAW` (always on; the enable decision lives on GND1 at SN6505B.EN) |
| 15 | VSEL | I | voltage scaling input | tie to GND2 |

Note on PS/SYNC: the device enters PFM below roughly 650 mA of average
inductor current, so this rail *would* run in PFM whenever the ports are idle.
Forced PWM is chosen deliberately: it keeps the switching spectrum fixed at
2.4 MHz, avoids PFM bursts modulating `ISO_5V`, and makes the Shield B
emissions story a single tone rather than a load-dependent burst pattern. The
cost is light-load efficiency, which shows up as host draw in external-supply
mode (where the converter idles anyway). Revisit at bring-up if that idle draw
matters more than the ripple.

**Support components (TI's validated BOM, SLVSC58B Table 2):**

| Ref | Value | Part | Note |
|---|---|---|---|
| L | 1.5 µH | `XFL4020-152MEC` (Coilcraft) | 4.0 × 4.0 × 2.1 mm, DCR 14.4 mΩ, Isat 4.6 A. Effective inductance must stay in 0.7–2.8 µH. |
| C_IN | 2 × 10 µF 0805 25 V X7S + 1 × 10 µF 0603 | — | ≥ 4.7 µF required at VIN |
| C_OUT | 3 × 22 µF 0805 16 V X6S + 1 × 10 µF 0603 | — | total *effective* capacitance must land in 15–470 µF after DC bias derating |
| C_VAUX | 100 nF 0402 25 V X7R | — | required, do not load VAUX |
| R1, R2, R4 | 523 k / 100 k / 100 k, 1 % | — | FB divider + FB2 |

### 2.4 Fit under Shield B (`BMI-S-209-F`, 29.36 × 18.50 × 7.00 mm)

Everything Shield B must cover — rectifier, converter, inductor, switch node,
input and output caps:

| Item | Land area |
|---|---|
| 2 × SS34 (DO-214AC) | ≈ 54 mm² |
| TPS63070 VQFN-HR | ≈ 14 mm² |
| L (XFL4020, 4 × 4) | 16 mm² |
| C_IN (2×0805 + 0603) | ≈ 12 mm² |
| C_OUT (3×0805 + 0603) | ≈ 14 mm² |
| C_VAUX + 3 × 0402 R | ≈ 4 mm² |
| **Total** | **≈ 114 mm²** |

Usable area inside the frame, allowing 1.5 mm from each wall:
26.4 × 15.5 ≈ **409 mm²**. Component land is 28 % of it — ample for the
switch-node loop, the GND2 pour, and stitching. Tallest part is the SMA
Schottky at ≈ 2.4 mm (inductor 2.1 mm) against a 7.00 mm frame.

**Fits with margin.** The square alternate (`BMI-S-203-F`, 26.21 mm sq,
5.08 mm) also fits and remains available if the section lays out squarer.

### 2.5 What this conclusion rests on, and how to falsify it

- **Hard:** the winding DCRs, turns ratio, `R(ON)`, `t_BBM`, and V·µs rating.
  These are datasheet maxima and are not in dispute.
- **Soft:** the 0.44 Ω `R_extra`, calibrated from a single rev A data point
  that the spec itself labels "measured/estimated". Everything about Cases B
  and C moves with it.
- **The falsifying measurement** is already item 3 of the spec's verification
  plan: measure `DCDC_RAW` at 800 mA primary across `V_BUS` = 4.75/5.00/5.25 V,
  hot. If it never drops below ≈ 5.3 V, the buck-boost was insurance rather
  than necessity — no harm done, ≈ 25 mA of port budget spent. If it dips
  below 5.0 V, the buck-boost is the reason the board works.
- **`I_o` = 700 mA is a part rating, not an operating point.** At the spec's
  800 mA primary budget the chain delivers ≈ 611 mA at `ISO_5V`. Reaching
  700 mA needs ≈ 910 mA primary, i.e. the spec's "SN6505B at 900 mA" lever,
  still inside the 1 A device rating and the 1.42 A min current clamp.

---

## 3. Step 2 — Hub 3.3 V rail

### 3.1 USB2514B current — verified, not estimated

The spec carried "155 mA **(estimate)**". From the USB251xB/xBi datasheet
(rev 2.2, Tables 6.4 and 6.6):

| Condition | Typ | Max |
|---|---|---|
| Configured, Hi-Speed host, base (1 downstream port) | 70 mA | 80 mA |
| Each additional downstream port | +25 mA | +25 mA |
| **4 ports = base + 3 × 25 mA** | **145 mA** | **155 mA** |
| Suspend (all supplies combined) | 550 µA | 1200 µA |

The 155 mA figure is the **datasheet maximum** and is correct. The USB2514B
has no external supply other than 3.3 V (the 1.8 V core is internally
regulated via CRFILT), so all of it lands on the 3.3 V rail. Budget at max.

### 3.2 Port budget arithmetic

Using the Step 1 converter's real numbers:

```
P_host                = 5.00 V × 800 mA                       = 4.000 W
× η(T1 + rectifier) 83.6 %  (§2.1, derived)                   = 3.343 W  @ DCDC_RAW 5.44 V
× η(TPS63070) 92 %          (buck-boost transition region)    = 3.076 W  @ 5.00 V
− TPS2121 IN2→OUT, 56 mΩ × 615 mA = 34 mV                     = 3.055 W
                                                    ISO_5V available = 611 mA
```

Fixed loads on `ISO_5V`:

| Load | Current | Source |
|---|---|---|
| ADuM4165 `IDD2(H)` max | 70 mA | ADuM4165 datasheet (59 typ / 70 max) |
| Status indicators | 10 mA | spec |
| TPS2553 ×4 + TPS2121 + TPS63070 quiescent | ≈ 1 mA | datasheets |
| **Subtotal** | **81 mA** | |

Two branches:

| Branch | 3.3 V rail draws from `ISO_5V` | Ports get |
|---|---|---|
| **LDO** (`AP2112K-3.3`) — passes straight through | 155 mA | 611 − 81 − 155 = **375 mA** |
| **Buck** (90 % assumed) — 155 × 3.3 ÷ (5.0 × 0.90) | 114 mA | 611 − 81 − 114 = **416 mA** |

### 3.3 Decision

**Rule:** if the port budget is below 450 mA, take the buck.

**375 mA < 450 mA → take the buck.** The rule fires unambiguously; even the
buck branch (416 mA) stays below 450 mA, so there was never a version of this
where the LDO's simplicity was affordable.

**Result: shared port current ≈ 416 mA**, versus the spec's 390 mA estimate.
The improvement comes from the buck (+41 mA) partly offset by the more honest
83.6 % transformer efficiency and the buck-boost's 92 % versus the spec's 92 %
buck assumption (a wash) plus the mux drop the spec omitted.

### 3.4 Selected part — `TPS62203DBVR`

| Parameter | Value |
|---|---|
| Input range | 2.5–6.0 V rec., **7.0 V abs max** |
| Output | 3.3 V fixed, ±3 %, 300 mA |
| Switching frequency | 650 / 1000 / 1500 kHz |
| `I_Q` | 15 µA typ (not switching) |
| P-ch `R_DS(on)` | 530 mΩ typ @ 3.6 V |
| P-ch current limit | 380 mA min / 480 typ |
| Package | SOT-23-5 (DBV) |
| Inductor | 4.7–10 µH (10 µH nominal) |
| C_IN / C_OUT | 4.7 µF / 10 µF |

Headroom checks:
- Load 155 mA max against 300 mA rating — 1.9× margin.
- Peak inductor current = 155 mA + ΔI/2 = 155 + 56 = 211 mA against a 380 mA
  **minimum** current limit. Clear.
- Efficiency from the loss budget: P-ch conduction 8.4 mW + N-ch 3.5 mW +
  inductor DCR (110 mΩ) 2.6 mW + switching ≈ 5 mW + `I_Q` 0.08 mW ≈ 20 mW on
  512 mW delivered ⇒ **≈ 96 %**. The 90 % used in §3.2 is conservative by
  6 points; the real port figure is likely 3–4 mA better than 416 mA.
- Input abs max 7.0 V. The `ISO_5V` domain is already bounded to ≤ 5.5 V by the
  TPS2553 (6.5 V) and the external-input TVS (`T6V0S5A-7`, 6.0 V standoff).

**Pin table — `TPS62203DBVR`, SOT-23-5 (DBV):**

| Pin | Name | I/O | Function | This design |
|---|---|---|---|---|
| 1 | VI | I | supply | `ISO_5V` |
| 2 | GND | — | ground | GND2 |
| 3 | EN | I | enable; **must not float** | tie to `ISO_5V` |
| 4 | FB | I | feedback; connect directly to output on fixed versions | to `HUB_3V3` |
| 5 | SW | I/O | switch node | to L, then `HUB_3V3` |

Inductor: `744043100` (Würth, 10 µH, 1.19 A Isat, 110 mΩ, 4.8 × 4.8 mm).

### 3.5 Build option — LDO fallback with no respin

`AP2112K-3.3` (SOT-23-5) and `TPS62203DBVR` (SOT-23-5) share pins 1/2/3
exactly:

| Pin | AP2112K-3.3 | TPS62203DBVR |
|---|---|---|
| 1 | VIN | VI |
| 2 | GND | GND |
| 3 | EN | EN |
| 4 | NC | FB |
| 5 | VOUT | SW |

**Lay the 3.3 V section out so the LDO is a stuff option:** route pin 4 to
`HUB_3V3` (harmless on the AP2112K, where it is NC) and put the 10 µH inductor
in a footprint that also accepts an 0805 0 Ω link. Fitting `AP2112K-3.3` +
0 Ω instead of `TPS62203` + inductor reverts to the LDO. That matters because
the buck puts a 1 MHz switcher on the hub's own supply rail, outside Shield B
— if bring-up finds it degrades HS eye quality or enumeration margin, the
fallback costs a BOM line, not a board spin.

Layout constraint to record on the parts: keep the 3.3 V switch node and
inductor away from the USB2514B's 24 MHz crystal and its 12 kΩ RBIAS, and put
a local LC/ferrite between `HUB_3V3` and the hub's analog `VDD33` pins.

---

## 4. Step 3 — CC comparator

### 4.1 Output structure — the assumption is correct

**`TLV7041` is open-drain.** From SLVSE13J:

- Features, p.1: "Push-pull output (**TLV703x**)" / "Open-drain output
  (**TLV704x**)".
- §6.3: "The TLV704x has an open-drain output stage".
- §7.1: "When level shifting or **wire-ORing of the comparator outputs** is
  needed, the TLV704x with open-drain [output is used]".
- §5.7: `V_OH` is specified "for TLV7031 only"; `I_LKG` "Open-drain output
  leakage current (**TLV7041 only**)" = 100 pA.

The mnemonic runs the *opposite* way to the direction the plan feared: **7031
is the push-pull part, 7041 is the open-drain part.** The spec and the archive
both name `TLV7041`, and both are right. No part change on that basis.

### 4.2 …but the wire-OR network as specified does not work

The spec says the outputs are "wire-ORed to `SN6505B.EN` **with a pull-down**".
Open-drain outputs can only pull low. Tied together over a pull-down, the net
is low unconditionally and `EN` never asserts.

Correcting it also exposes a polarity trap. Open-drain outputs sharing a
**pull-up** form a wired-AND of their high states — which is an OR only of
their *low-asserted* states. So:

- **Comparator connection must be inverting:** `CC` → `IN−`, `V_REF` → `IN+`.
  Then `CC > V_REF` ⇒ output pulls low.
- **Common pull-up** (e.g. 100 kΩ) to `VBUS_HOST` on the shared node
  `CC_DET_L`. That node is low if *either* CC line exceeds threshold — the
  OR that is actually wanted.
- **One inverter** to drive the active-high `SN6505B.EN`: `2N7002`, gate ←
  `CC_DET_L`, source ← GND1, drain → `EN` with a pull-up to `VBUS_HOST`.
  (`SN6505B` `V_IN(ON)` = 0.7 × VCC, and the pull-up rail *is* VCC, so levels
  are correct by construction.)

If a non-inverting connection is wanted instead, the alternative is `TLV7032`
(push-pull dual) with a `BAT54S` diode-OR and a pull-down — same part count,
one diode drop of error added to the threshold. **The open-drain route is
preferred.**

Two further constraints for the implementers:

- **Series protection on the CC inputs.** `V_CM` is `V_EE` to `VCC + 0.1 V`.
  On an e-marked cable one CC line carries VCONN at 5 V, which sits right at
  the top of that range; a ~10 kΩ series resistor into `IN−` bounds the input
  current if `VBUS_HOST` sags below VCONN during a transient.
- **GND2 pair's supply.** The external-input 3 A detect (Task 6) must be
  powered from **J2's own VBUS**, not from `ISO_5V`. Same latch-up-by-
  construction argument the spec makes for the host side: the comparison has to
  be valid before the mux prefers the external supply. Its output drives
  TPS2121 `CP2`, which must be **high** (≥ `V_REF` = 1.06 V rising / 1.04 V
  falling) when 3 A is detected, so the same inversion applies there.

### 4.3 Singles versus dual

Four comparators are needed, split across two ground domains: two on GND1
(upstream CC1/CC2, Task 4) and two on GND2 (external CC1/CC2, Task 6). A dual
cannot span the barrier, but each same-domain pair fits one dual.

| Option | Package | Bodies | Body area | Bypass caps |
|---|---|---|---|---|
| 4 × `TLV7041DBVR` | SOT-23-5, 2.90 × 1.60 mm | 4 | 18.6 mm² | 4 |
| **2 × `TLV7042DDFR`** | SOT-23-8 (DDF), 2.90 × 1.60 mm | 2 | **9.3 mm²** | **2** |

**Selected: `TLV7042DDFR`** — half the area, half the part count, half the
decoupling, and each pair already shares one reference divider. Electrically
identical (`V_IO` ±8 mV max, `V_HYS` 10 mV typ vs 7 mV on the single,
`V_OL` 350 mV max at 3 mA, `I_CC` 315 nA/channel).

Stock on the dual is thinner than on the single (§5), so the singles are the
sanctioned fallback — footprint change only, no circuit change.

**Pin table — `TLV7042DDFR`, SOT-23-8 (DDF):**

| Pin | Name | I/O | This design (GND1 instance) |
|---|---|---|---|
| 1 | OUTA | O | open-drain → `CC_DET_L` |
| 2 | INA− | I | `CC1` via 10 kΩ series |
| 3 | INA+ | I | `V_REF` = 0.66 V from the `VBUS_HOST` divider |
| 4 | VEE | — | GND1 |
| 5 | INB+ | I | `V_REF` = 0.66 V (same divider) |
| 6 | INB− | I | `CC2` via 10 kΩ series |
| 7 | OUTB | O | open-drain → `CC_DET_L` |
| 8 | VCC | — | `VBUS_HOST` |

GND2 instance is identical with `V_REF` = 1.23 V, VCC = J2 VBUS, VEE = GND2.

**Pin table — `TLV7041DBVR`, SOT-23-5 (DBV), "North West" pinout — fallback:**

| Pin | Name | I/O |
|---|---|---|
| 1 | OUT | O (open-drain) |
| 2 | V− (VEE) | — |
| 3 | IN+ | I |
| 4 | IN− | I |
| 5 | V+ (VCC) | — |

Note: TI also sells `TLV7041S` (South-East pinout) and `TLV7041L` (legacy
LMC72xx pinout) in the same SOT-23-5 body. **Order the plain `TLV7041DBVR`** —
the three variants are not interchangeable on the board.

**Pin table — `2N7002` (inverter), SOT-23:**

| Pin | Name | This design |
|---|---|---|
| 1 | Gate | `CC_DET_L` |
| 2 | Source | GND1 |
| 3 | Drain | `SN6505B.EN`, with pull-up to `VBUS_HOST` |

---

## 5. Step 4 — Stock survey

Surveyed 2026-08-08. DigiKey API credentials are not configured in this
environment; figures are from distributor product pages. Threshold for a
sourcing flag: < 1000 units.

| Part | MPN | Package | Distributor | Stock | Price (1) | Price (100) | Status | Flag |
|---|---|---|---|---|---|---|---|---|
| Buck-boost converter | `TPS63070RNMR` | VQFN-HR-15 | DigiKey | **26,889** | $3.37 | $2.09 | Active | — |
| — fixed-5 V alternate | `TPS630701RNMR` | VQFN-HR-15 | DigiKey | 1,740 | $3.37 | $2.09 | Active | thin |
| Converter inductor | `XFL4020-152MEC` | 4.0 × 4.0 mm | LCSC C3033018 | **20,961** | $3.70 | $2.87 (1k) | Active | — |
| 3.3 V buck | `TPS62203DBVR` | SOT-23-5 | DigiKey | 2,205 | $1.62 | $0.954 | Active | — |
| " | `TPS62203DBVR` | SOT-23-5 | LCSC C9051 | 8,180 | $1.41 | $0.821 (1k) | Active | — |
| 3.3 V inductor | `744043100` | 4.8 × 4.8 mm | DigiKey | 3,922 | $1.53 | $1.23 | Active | 24 wk lead |
| Comparator (dual) | `TLV7042DDFR` | SOT-23-8 | DigiKey | **1,220** | $1.64 | $0.970 | Active | **thin — see below** |
| Comparator (single, fallback) | `TLV7041DBVR` | SOT-23-5 | DigiKey | 7,726 | $0.88 | $0.500 | Active | — |
| Inverter FET | `2N7002-7-F` | SOT-23 | DigiKey | 18,679 | $0.18 | — | Active | — |
| 3.3 V LDO (build option) | `AP2112K-3.3TRG1` | SOT-23-5 | DigiKey / LCSC C51118 | deep | $0.23 | — | Active | — |

**Sourcing risks:**

1. **`TLV7042DDFR` at 1,220 units.** Above the flag threshold but only just,
   and two are needed per board. Mitigation is already designed in: the
   `TLV7041DBVR` singles (7,726 in stock) implement the identical circuit and
   need only a footprint swap. If a production run is planned, buy the duals
   ahead of the board.
2. **`744043100` carries a 24-week manufacturer lead time.** 3,922 in stock
   covers prototypes; any second source of a 10 µH / ≥ 0.5 A / ≤ 200 mΩ
   shielded inductor in a ≤ 5 × 5 mm body substitutes without change.
3. **`TPS630701RNMR` at 1,740** is why the adjustable `TPS63070RNMR` was
   chosen. Recorded so the fixed version is not "simplified" back in later.
4. `XFL4020-152MEC` no longer appears in DigiKey's own catalogue (it moved to
   DigiKey Marketplace). Source from LCSC or Coilcraft direct.

---

## 6. Handoff

**Task 4 (upstream CC sense, GND1)** — one `TLV7042DDFR`, VCC = `VBUS_HOST`,
`V_REF` = 0.66 V from a `VBUS_HOST` divider, **inverting** connection (CC to
`IN−`), outputs wire-ORed over a pull-up to `VBUS_HOST`, one `2N7002` inverting
that node onto `SN6505B.EN`. 10 kΩ series into each CC input. Do **not**
implement the spec's "pull-down" wording.

**Task 5 (isolated power chain, GND2)** — `TPS63070RNMR` per §2.3, TI's
capacitor set per §2.3, FB divider for 5.00 V, `EN` tied to `DCDC_RAW`,
`PS/SYNC` low, `VSEL` low, `PG` pulled up with a test point. Output net
`ISO_5V_PRE` → TPS2121 `IN2`. Everything in §2.4 goes inside Shield B.

**Task 6 (external input, GND2)** — one `TLV7042DDFR`, VCC = **J2 VBUS**,
`V_REF` = 1.23 V, inverting, wire-ORed over a pull-up, inverted to drive
TPS2121 `CP2` **high** on 3 A detect (`V_REF(CP2)` = 1.06 V rising).

**Task 7 (hub rails)** — `TPS62203DBVR` + `744043100` per §3.4, laid out as a
stuff option against `AP2112K-3.3` + 0 Ω per §3.5. Budget the hub at
**155 mA max** at 3.3 V, verified.

**Update the spec's Power budget table** with: η(T1+rectifier) **83.6 %**
(was 85 % estimate), hub 3.3 V **155 mA max verified** (was estimate), mux
drop included, shared port current **≈ 416 mA** (was ≈ 390 mA).

## 7. Bring-up items this record creates

1. Measure `DCDC_RAW` at 800 mA primary, `V_BUS` = 4.75 / 5.00 / 5.25 V, at
   thermal equilibrium. This is the measurement the entire Step 1 argument is
   waiting on.
2. Measure the buck-boost's efficiency at the real operating point; §3.2 uses
   92 % and the port figure moves ~4.5 mA per point.
3. Confirm `ISO_5V` stays regulated (not tracking `DCDC_RAW`) at the worst
   `V_BUS`. That is the buck-boost earning its place.
4. Scope `HUB_3V3` ripple and check HS eye / enumeration margin with the buck
   fitted; if degraded, fit the `AP2112K-3.3` + 0 Ω option and re-budget the
   ports at 375 mA.
5. Confirm `SN6505B.EN` polarity end-to-end through the corrected wire-OR and
   the `2N7002` inverter, on a Default, a 1.5 A, and a 3 A advertisement.
6. Check converter start-up against the SN6505B's 1.42 A minimum current clamp
   with all output capacitance present (T1 soft-start 4.25 ms typ).
