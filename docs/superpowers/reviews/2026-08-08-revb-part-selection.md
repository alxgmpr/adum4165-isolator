# Rev B Part Selection — Post-Rectifier Converter, 3.3 V Rail, CC Comparators

**Date:** 2026-08-08 (rev 2 — incorporates Task 2 review)
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
| Hub 3.3 V rail | **Buck** (rule fired: 373 mA < 450 mA) | `TPS62203DBVR` |
| CC comparator output structure | `TLV7041` **is** open-drain — the spec's assumption is correct | `TLV7042DDFR` (dual) |
| Resulting shared port current | **≈ 414 mA** | — |

Three things in this record are corrections the spec did not anticipate:

1. **The converter is a buck-boost.** The spec and the plan both say
   "synchronous buck". §2 shows why a buck cannot be relied on across the legal
   `VBUS_HOST` range.
2. **The CC wire-OR network as written does not work.** The part is right; the
   network around it is not. §4.2 gives the correction.
3. **The spec's DR-06 note prescribes the wrong TPS2121 mechanism.** Its
   *behavioural goal* — "no 3 A ⇒ OUT = IN2 unconditionally; 3 A detected ⇒
   OUT = IN1" — is correct and must be kept. Its *mechanism* ("CP2 must be
   driven by the 3 A-detect net") selects the wrong input. See §4.3.
   **The spec text needs editing, not just the schematic.**

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
| Schottky `V_f` (SS34) | see §2.2 — deliberately swept | SS34 datasheet |

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

**Calibration.** With `R_extra = 0` and `V_f = 0` the model predicts 6.263 V at
rev A's 315 mA operating point; rev A observed ≈ 5.80 V. The rev A data point
therefore pins the **total** post-winding loss at

```
V_f + R_extra × 0.341 A = 0.463 V
```

and nothing more. `V_f` and `R_extra` are **degenerate against a single
calibration point** — one measurement cannot separate a fixed diode drop from a
current-proportional loss. §2.2 handles that by sweeping the split rather than
picking one.

**Baseline split used for all budget arithmetic:** `V_f = 0.30 V` ⇒
`R_extra = 0.479 Ω`. This is the split that puts the most loss into the
current-proportional term, i.e. the most pessimistic for `DCDC_RAW` at high
current — chosen deliberately so the port budget in §3 is a floor, not a
midpoint.

**Results at the baseline split:**

| Case | `V_BUS` | DCRs | `I_o` | `DCDC_RAW` |
|---|---|---|---|---|
| A — nominal | 5.00 V | typ, warm | 615 mA | **5.42 V** |
| B — worst corner | 4.75 V | max, hot (+18 % Cu) | 615 mA | **4.91 V** |
| C — worst corner at rated load | 4.75 V | max, hot | 700 mA | **4.78 V** |
| D — unloaded (external-supply mode) | 5.25 V | — | 0 | **6.68 V** |
| D′ — unloaded, `V_BUS` at Type-C max | 5.50 V | — | 0 | **7.00 V** |

**How firm is the plan's 5.4 V figure?** It is a good *typical*, not a worst
case. Case A lands at 5.42 V. But Type-C `vSafe5V` allows `V_BUS` down to
4.75 V, and copper resistance rises ~18 % at the winding temperature implied by
the transformer's own temp-rise curve. In that corner `DCDC_RAW` falls **below
the 5.0 V output**.

**Volt-second check (does T1 saturate?).** Applied V·µs per half cycle at Case
A = 4.73 V × 1.089 µs = 5.2 V·µs. At the minimum specified 363 kHz it is
6.1 V·µs. Against the 10–11 V·µs rating that is ≥1.6× margin. T1 is not the
limiting element.

**Transformer + rectifier efficiency at the real operating point.** The spec
carried 85 % as an "(estimate)" derived from a 300 mA reference design and
flagged it for re-derivation. At Case A, baseline split:

```
P_host = 5.00 V × 800 mA                     = 4.00 W
P_raw  = 5.42 V × 615 mA                     = 3.33 W
η(T1 + rectifier)                            = 83.3 %
```

**Use 83.3 %, not 85 %.** Across the full `V_f`/`R_extra` sweep (below) it lands
between 83.3 % and 85.7 %; the low end is used throughout §3.

### 2.2 Why the split does not rescue the buck

The obvious objection to §2.1 is that `R_extra` was fitted, so a later reader
could shrink it and conclude a buck is fine. Sweeping the split
self-consistently — holding `V_f + 0.341 × R_extra = 0.463 V` — shows it does
not work, and shows *why*:

| `V_f` | implied `R_extra` | Case A | Case B (615 mA) | Case C (700 mA) |
|---|---|---|---|---|
| 0.30 V (baseline) | 0.479 Ω | 5.42 V | **4.91 V** | **4.78 V** |
| 0.36 V | 0.303 Ω | 5.48 V | 4.97 V | 4.85 V |
| 0.40 V | 0.186 Ω | 5.51 V | 5.01 V | 4.90 V |
| 0.45 V | 0.039 Ω | 5.56 V | 5.06 V | 4.96 V |
| 0.463 V (`R_extra` = 0) | 0 Ω | 5.58 V | **5.07 V** | **4.98 V** |

The last row is the physical limit: `R_extra` cannot go negative, so 5.07 V
(Case B) and 4.98 V (Case C) are the **most favourable values `DCDC_RAW` can
take** under the worst-corner input conditions, for any split consistent with
the rev A measurement.

Now compare against what a buck needs. A synchronous buck in 100 %-duty mode
holds regulation only while

```
V_IN(min) = V_OUT + I_OUT × (R_DS(on),HS + R_L)
```

For a TPS62130-class part (`R_DS(on),HS` 170 mΩ max, inductor DCR ≈ 50 mΩ):

| Load | Required `V_IN` | Best achievable `DCDC_RAW` | Shortfall |
|---|---|---|---|
| 615 mA | 5.135 V | 5.07 V | **−67 mV** |
| 700 mA | 5.154 V | 4.98 V | **−175 mV** |

**The correct statement is not "`R_extra` is non-zero" — it is that the
worst-corner headroom is always smaller than the buck's own dropout, across
every split the calibration permits.** Even handing the buck the entire loss as
a fixed diode drop, it still cannot regulate in the worst corner. That is what
makes the topology decision robust to the calibration.

Where a buck ends up when it drops out, at Case B:

```
DCDC_RAW                                   4.91 V (baseline) … 5.07 V (limit)
− buck at 100 % duty, 613 mA × 220 mΩ      −0.135 V
− TPS2121 IN2→OUT, 613 mA × 90 mΩ max      −0.055 V
− TPS2553 (DBV), 414 mA × 135 mΩ max       −0.056 V
= downstream port                          4.66 V … 4.82 V
```

against a 4.75 V floor for a self-powered hub port — straddling it, with the
SN6505B's 424 kHz ripple riding on top because the buck has stopped regulating.

Two number corrections carried into that chain, both of which Tasks 5 and 7
inherit:

- **`TPS2553`**: rev 1 of this record used 85 mΩ, which is the **25 °C typical**
  for the DBV package. SLVS841F specifies the DBV package (the one this design
  uses, `TPS2553DBVR`) as **85 mΩ typ / 95 mΩ max at 25 °C / 135 mΩ max over
  −40…125 °C**. Use **135 mΩ** for port-drop budgeting. (The 100/115/140/150 mΩ
  figures in the same table belong to the DRV package and do not apply here.)
- **`TPS2121`**: 56 mΩ typ / 70 mΩ max at 25 °C, **90 mΩ max over −40…105 °C**.
  Use 56 mΩ for efficiency, 90 mΩ for worst-case drop.
- Rev 1 also pushed the full 613 mA through a single TPS2553. Only ~414 mA is
  available across all four ports combined, so the port-switch drop is computed
  at 414 mA (one port taking the entire shared budget).

With the buck-boost regulating, `ISO_5V` is 5.00 V and the same worst-case port
lands at **5.00 − 0.414 × 0.135 = 4.94 V**. That difference is the decision.

### 2.3 Topology evaluation

| Topology | Verdict | Reasoning |
|---|---|---|
| **Standard synchronous buck** with 100 %-duty mode | **Rejected** | §2.2: worst-corner headroom is inside the part's own dropout for every split the rev A calibration allows, so `ISO_5V` becomes an unregulated copy of `DCDC_RAW` and a port lands at 4.66–4.82 V against a 4.75 V floor. Additionally, near the dropout boundary the buck hunts between PWM and 100 % mode against a soft source (≈ 0.9 Ω secondary-referred). |
| **Buck-boost** | **Selected** | Regulates 5.00 V across the whole 4.8–7.0 V `DCDC_RAW` range with no mode boundary at `V_in = V_out`. Decouples downstream port voltage from host cable quality. Costs ≈ 3–4 points of efficiency versus a buck in dropout, ≈ 25 mA of port budget. |
| **Raise T1's turns ratio** | **Fallback only** | Electrically sound: output power sets primary current regardless of `n`, so a higher ratio buys headroom for free. But there is no drop-in. Würth's 5 kV, 1 A-class parts with higher ratios (`750316031/32/33`, `750315240`) are 12.32 × 15.41 × 11.05 mm — a different footprint, a different land pattern, a re-run of the routed-slot creepage work, and a re-qualification of the barrier. Reserve for a respin. |

### 2.4 Selected part — `TPS63070RNMR`

| Parameter | Value | Requirement | OK? |
|---|---|---|---|
| Input range | 2.0–16 V (abs max 20 V) | 4.8–7.0 V operating | ✓ |
| Output range | 2.5–9 V, `V_FB` = 800 mV | 5.0 V | ✓ |
| Output current | 2 A buck and boost | ≥ 700 mA | ✓ |
| High-side switch current limit | 3.6 A | — | ✓ |
| `I_Q` into VIN, **PFM**, no load | 54 µA typ / 103 µA max | matches the PS/SYNC = high configuration below | ✓ |
| Switching frequency | 2.4 MHz | — | — |
| Min duty in buck mode | 30 % (⇒ `V_in/V_out` ≤ 3.33) | 1.40 max | ✓ |
| Package | VQFN-HR-15 (RNM), 3.0 × 2.5 mm | under Shield B | ✓ |

Adjustable version chosen over the fixed-5 V `TPS630701RNMR` purely on stock
depth (26,889 vs 1,740 — see §5).

**Pin table — `TPS63070RNMR`, VQFN-HR-15 (RNM):**

| Pin | Name | I/O | Function | This design |
|---|---|---|---|---|
| 1 | PS/SYNC | I | low = forced PWM; high = PWM/PFM (power save) | tie **high** to `ISO_5V_PRE`; DNP 0 Ω pad to GND2 for forced PWM — see note |
| 2 | PG | O | open-drain power good | 100 kΩ pull-up to `ISO_5V_PRE`, test point |
| 3 | VAUX | O | internal LDO cap; **must not be loaded** | 100 nF 0402 to GND2 |
| 4 | GND | — | control/logic ground | GND2 |
| 5 | FB | I | feedback (0.800 V) | divider from `ISO_5V_PRE` |
| 6 | FB2 | O | voltage-scaling output | 100 kΩ to FB (per TI's BOM) |
| 7, 8 | VOUT | O | converter output | `ISO_5V_PRE` → TPS2121 IN2 |
| 9 | L2 | I | inductor, output side | L to pin 11 |
| 10 | PGND | — | power ground | GND2 |
| 11 | L1 | I | inductor, input side | L to pin 9 |
| 12, 13 | VIN | I | power stage supply | `DCDC_RAW` |
| 14 | EN | I | enable (precise threshold) | tie to `DCDC_RAW` (the enable decision lives on GND1 at `SN6505B.EN`) |
| 15 | VSEL | I | voltage scaling input | tie to GND2 |

**Note on PS/SYNC — changed from rev 1 of this record.** Rev 1 specified forced
PWM (PS/SYNC low) for spectral cleanliness, then cited the datasheet's PFM
`I_Q` as evidence the part idles cheaply. Those are inconsistent: SLVSC58B
§7.5 measures 54 µA/103 µA in PFM, and in forced PWM the device switches at
2.4 MHz unloaded and circulates reverse inductor current, which is orders of
magnitude more. Since the spec explicitly cares about idle draw in
external-supply mode (its unverified 30–50 mA estimate), **PS/SYNC is tied high
(PWM/PFM auto)** so the cited `I_Q` is the number that actually applies. The
converter's own contribution to the idle state is then ≈ 0.1 mA; the spec's
30–50 mA is dominated by the SN6505B plus T1 core and switching loss, which
this choice does not affect either way.

Consequences to check at bring-up: the PFM→PWM transition sits at roughly
650 mA of average inductor current, which is right at the full-load operating
point (~613 mA), so the rail changes mode as the ports load up. DC accuracy is
±1 % in PWM and +3 %/−1 % in PFM — the PFM ceiling of 5.15 V is still inside
USB limits. If mode hunting produces unacceptable `ISO_5V` ripple, fit the DNP
0 Ω to GND2 and accept the idle-draw cost.

**Support components.** TI's validated set (SLVSC58B Table 2) with two
deviations, both recorded with reasons:

| Ref | Value | MPN | Deviation from TI's BOM |
|---|---|---|---|
| L | 1.5 µH | `XFL4020-152MEC` (Coilcraft) | none (TI's part) |
| C_IN | 2 × 10 µF 25 V X5R 0805 | `CL21A106KAYNNNE` (Samsung) | equivalent to TI's Murata `GRM21BC71E106ME11L` (X7S→X5R, same 25 V/0805) |
| C_IN-HF | 1 × 100 nF 25 V-class X7R 0402 | `CL05B104KO5NNNC` (Samsung, 16 V) | **replaces** TI's 10 µF 0603 pin-adjacent cap. TI's requirement is ≥ 4.7 µF at VIN, met by the 2 × 10 µF; the 0402 provides the low-ESL path at the pin. 16 V rating against a 7.0 V worst-case node = 2.3× derating. |
| C_OUT | 3 × 22 µF 16 V X5R 0805 | `CL21A226MOQNNNE` (Samsung) | equivalent to TI's Murata `GRM21BC81C226ME44L` (X6S→X5R) |
| C_OUT-HF | 1 × 100 nF 0402 | `CL05B104KO5NNNC` | **replaces** TI's 10 µF 0603. See C_OUT effective-capacitance check below. |
| C_VAUX | 100 nF 0402 | `CL05B104KO5NNNC` | equivalent to TI's Taiyo Yuden `TMK105B7104MV-FR` |
| R1 (FB top) | 523 kΩ 1 % 0402 | `RC0402FR-07523KL` (Yageo) | — |
| R2 (FB bottom) | 100 kΩ 1 % 0402 | `RC0402FR-07100KL` (Yageo) | — |
| R4 (FB→FB2) | 100 kΩ 1 % 0402 | `RC0402FR-07100KL` | per TI's BOM |
| R_PG | 100 kΩ 1 % 0402 | `RC0402FR-07100KL` | — |

`V_OUT = 0.800 × (1 + 523/100) = 4.98 V`; ±1 % resistors give 4.91–5.05 V.

**Effective-capacitance check.** TI requires the *effective* capacitance at
VOUT to land in 15–470 µF for a 1.5 µH nominal inductor. 3 × 22 µF 16 V X5R
0805 at 5 V DC bias derates to roughly 50–60 % ⇒ ≈ 33–40 µF effective. Inside
the window with margin at both ends. **Verify the chosen lot's bias curve
before layout freeze** — the window's lower bound is what keeps the internal
compensation valid.

Layout note: the FB node's Thevenin impedance is 84 kΩ. Keep the divider
adjacent to pin 5 and route the node away from L1/L2 and the switch loop.

### 2.5 Fit under Shield B (`BMI-S-209-F`, 29.36 × 18.50 × 7.00 mm)

Everything Shield B must cover — rectifier, converter, inductor, switch node,
input and output caps:

| Item | Land area |
|---|---|
| 2 × SS34 (DO-214AC) | ≈ 54 mm² |
| TPS63070 VQFN-HR | ≈ 14 mm² |
| L (XFL4020, 4 × 4) | 16 mm² |
| C_IN (2 × 0805) + C_IN-HF (0402) | ≈ 9 mm² |
| C_OUT (3 × 0805) + C_OUT-HF (0402) | ≈ 13 mm² |
| C_VAUX + 4 × 0402 R | ≈ 5 mm² |
| **Total** | **≈ 111 mm²** |

Usable area inside the frame, allowing 1.5 mm from each wall:
26.4 × 15.5 ≈ **409 mm²**. Component land is 27 % of it — ample for the
switch-node loop, the GND2 pour, and stitching. Tallest part is the SMA
Schottky at ≈ 2.4 mm (inductor 2.1 mm) against a 7.00 mm frame.

**Fits with margin.** The square alternate (`BMI-S-203-F`, 26.21 mm sq,
5.08 mm) also fits.

### 2.6 What this conclusion rests on, and how to falsify it

- **Hard (datasheet maxima, not in dispute):** the winding DCRs, turns ratio,
  `R(ON)`, `t_BBM`, and V·µs rating; the buck-dropout equation and the
  `R_DS(on)`/DCR values it uses; the TPS2121 and TPS2553 on-resistances.
- **Hard (arithmetic over a bounded set):** the §2.2 sweep. The rev A data
  point pins the total post-winding loss; the split between `V_f` and
  `R_extra` is unknown but bounded, and *every* admissible split leaves the
  worst-corner headroom inside the buck's own dropout. **This is the load-
  bearing claim, and it does not depend on the value of `R_extra`.**
- **Soft:** the rev A observation itself, which the spec labels
  "measured/estimated", and the assumption that `V_f` is constant between
  0.34 A and 0.67 A (it is not — it rises with current, which moves loss out
  of `R_extra` and toward the top rows of the sweep, i.e. toward the *limit*
  case already tabulated).
- **Soft:** the 92 % buck-boost efficiency, read from the shape of TI's
  `V_O = 5 V` efficiency family plus a conduction-loss estimate from the
  datasheet `R_DS(on)` figures. §3.2's port number moves ≈ 4.5 mA per point.
- **The falsifying measurement** is already item 3 of the spec's verification
  plan: measure `DCDC_RAW` at 800 mA primary across `V_BUS` = 4.75/5.00/5.25 V,
  hot. If it never drops below ≈ 5.3 V, the buck-boost was insurance rather
  than necessity — ≈ 25 mA of port budget spent. If it dips below 5.15 V, the
  buck-boost is the reason the board meets USB at the port.
- **`I_o` = 700 mA is a part rating, not an operating point.** At the spec's
  800 mA primary budget the chain delivers ≈ 609 mA at `ISO_5V`. Reaching
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

Using the Step 1 converter's numbers at the baseline (pessimistic) split:

```
P_host                = 5.00 V × 800 mA                       = 4.000 W
× η(T1 + rectifier) 83.3 %  (§2.1, derived)                   = 3.333 W  @ DCDC_RAW 5.42 V
× η(TPS63070) 92 %          (buck-boost transition region)    = 3.066 W  @ 5.00 V
− TPS2121 IN2→OUT, 56 mΩ typ × 613 mA → 21 mW                 = 3.045 W
                                                    ISO_5V available = 609 mA
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
| **LDO** (`AP2112K-3.3`) — passes straight through | 155 mA | 609 − 81 − 155 = **373 mA** |
| **Buck** (90 % assumed) — 155 × 3.3 ÷ (5.0 × 0.90) | 114 mA | 609 − 81 − 114 = **414 mA** |

At the optimistic end of the §2.2 sweep (η = 85.7 %) the buck branch reaches
≈ 431 mA. **414 mA is the number to design to.**

### 3.3 Decision

**Rule:** if the port budget is below 450 mA, take the buck.

**373 mA < 450 mA → take the buck.** The rule fires unambiguously; even the
buck branch (414 mA) stays below 450 mA at the design corner, so there was
never a version of this where the LDO's simplicity was affordable.

**Result: shared port current ≈ 414 mA**, versus the spec's 390 mA estimate.
The +41 mA from the buck is partly offset by the more honest 83.3 %
transformer efficiency and by the mux drop the spec omitted.

Worst-case port voltage with the buck-boost regulating and one port taking the
entire shared budget: `5.00 − 0.414 A × 135 mΩ = 4.94 V`, comfortably inside
USB limits.

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
  6 points; the real port figure is likely 3–4 mA better than 414 mA.
- Input abs max 7.0 V. The `ISO_5V` domain is bounded to ≤ 5.5 V by the
  TPS2553 (6.5 V) and the external-input TVS (`T6V0S5A-7`, 6.0 V standoff).

**Pin table — `TPS62203DBVR`, SOT-23-5 (DBV):**

| Pin | Name | I/O | Function | This design |
|---|---|---|---|---|
| 1 | VI | I | supply | `ISO_5V` |
| 2 | GND | — | ground | GND2 |
| 3 | EN | I | enable; **must not float** | tie to `ISO_5V` |
| 4 | FB | I | feedback; connect directly to output on fixed versions | to `HUB_3V3` |
| 5 | SW | I/O | switch node | to L, then `HUB_3V3` |

Inductor: `744043100` (Würth, 10 µH, 1.19 A, 110 mΩ, 4.8 × 4.8 mm).
C_IN 10 µF `CL21A106KAYNNNE`; C_OUT 10 µF `CL21A106KAYNNNE`; 100 nF 0402
`CL05B104KO5NNNC` at the pin.

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

## 4. Step 3 — CC comparator, and the nets it drives

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

### 4.2 GND1 — the wire-OR onto `SN6505B.EN`

The spec says the outputs are "wire-ORed to `SN6505B.EN` **with a pull-down**".
Open-drain outputs can only pull low. Tied together over a pull-down, the net
is low unconditionally and `EN` never asserts.

Correcting it also exposes a polarity trap. Open-drain outputs sharing a
**pull-up** form a wired-AND of their high states — which is an OR only of
their *low-asserted* states. So:

- **Comparator connection must be inverting:** `CC` → `IN−`, `V_REF` → `IN+`.
  Then `CC > V_REF` ⇒ output pulls low.
- **Common pull-up `R_OD` = 100 kΩ** to `VBUS_HOST` on the shared node
  `CC_DET_L`. That node is low if *either* CC line exceeds threshold — the OR
  that is actually wanted. (Sink current 47 µA at 4.75 V, far below the
  3 mA at which `V_OL` is specified as 350 mV max; combined output leakage
  200 pA is negligible against 47 µA.)
- **One inverter** to drive the active-high `SN6505B.EN`: `2N7002`, gate ←
  `CC_DET_L`, source ← GND1, drain → `EN`, with **`R_EN` = 10 kΩ** pull-up to
  `VBUS_HOST`.

**`R_EN` must be sized, not assumed.** SLLSEP9I §6.5 gives `EN` pin leakage
`I_IH` = 10 µA typ / **20 µA max** at `EN = VCC`, and `V_IN(ON)` = 0.7 × VCC.
From a 4.75 V rail the pull-up must satisfy
`V_BUS − I_IH(max) × R_EN ≥ 0.7 × V_BUS`, i.e. `R_EN ≤ 0.3 × 4.75 / 20 µA =
71 kΩ`. **The 100 kΩ used for `CC_DET_L` would put `EN` at ≈ 2.75 V against a
3.33 V threshold — it would not turn the converter on.** At 10 kΩ the leakage
drop is 0.2 mV and the margin to threshold is 1.4 V. Static loss when `EN` is
held low is 2.3 mW.

If a non-inverting connection is wanted instead, the alternative is `TLV7032`
(push-pull dual) with a `BAT54S` diode-OR and a pull-down — same part count,
one diode drop of error added to the threshold. **The open-drain route is
preferred.**

Two further constraints for the implementers:

- **Series protection on the CC inputs.** `V_CM` is `V_EE` to `VCC + 0.1 V`.
  On an e-marked cable one CC line carries VCONN at 5 V, which sits at the top
  of that range; a 10 kΩ series resistor into `IN−` bounds the input current if
  `VBUS_HOST` sags below VCONN during a transient.
- **GND2 pair's supply.** The external-input 3 A detect (Task 6) must be
  powered from **J2's own VBUS**, not from `ISO_5V` — the same
  latch-up-by-construction argument the spec makes for the host side.

### 4.3 GND2 — driving the TPS2121, and the DR-06 correction

**The spec's DR-06 mechanism is wrong.** DR-06 says "CP2 must be driven by the
3 A-detect net, *not* grounded", and rev 1 of this record repeated it. Working
it through SLVSEA3F Table 9-3 shows it selects the opposite input:

| `CP2 ≥ V_REF` | `PR1 ≥ V_REF` | OUT | Mode |
|---|---|---|---|
| 0 | 0 | higher input wins | VCOMP |
| 0 | 1 | **IN1** | VREF |
| 1 | 0 | **IN2** | VREF |
| 1 | 1 | `PR1 > CP2` → IN1, else IN2 | XCOMP |

With `IN1` = external supply and `IN2` = converter, DR-06's arrangement (detect
→ CP2, PR1 grounded) gives: 3 A detected ⇒ CP2 high, PR1 low ⇒ row 3 ⇒ **IN2**
— the converter is selected exactly when the external supply is confirmed good.
And with no detect, CP2 low + PR1 low ⇒ **VCOMP**, higher input wins — which is
precisely the failure mode DR-06 exists to prevent. The note is self-defeating
as written.

**The working assignment is the mirror image:**

| Pin | Connection | Level |
|---|---|---|
| **CP2** (pin 3) | fixed bias from IN1 via a divider — **24 kΩ / 10 kΩ** to GND2 | 1.47 V at IN1 = 5.00 V (1.40 V at 4.75 V; 1.62 V at 5.50 V). Always ≥ `V_REF` (1.10 V max) with ≥ 0.30 V margin, so fast-switchover/XCOMP mode is always armed. |
| **PR1** (pin 6) | driven by the 3 A-detect inverter — **100 kΩ to IN1, 150 kΩ to GND2**, with the `2N7002` drain on the node | 3.00 V at IN1 = 5.00 V when detected (3.30 V at 5.50 V — inside the 5.5 V pin limit); pulled to ≈ 0 V when not |

Truth check against Table 9-3:

- **External supply absent** ⇒ IN1 below UV ⇒ "invalid input" row ⇒ OUT = IN2. ✓
- **External supply present, 3 A not confirmed** ⇒ CP2 = 1 (biased), PR1 = 0
  (FET on) ⇒ row 3 ⇒ **OUT = IN2 unconditionally**. ✓ — and note this is a
  *deterministic* row, not VCOMP, so a weak supply sitting above the converter
  output can never win. That is DR-06's actual intent, now delivered.
- **3 A confirmed** ⇒ CP2 = 1.47 V, PR1 = 3.00 V ⇒ row 4 with `PR1 > CP2` ⇒
  **OUT = IN1**. ✓ Margin 1.53 V against a comparator offset `V_OFST` of
  5–40 mV.

The `2N7002` inverter specified in §4.2 produces exactly the active-high signal
needed; **it lands on PR1, not CP2.** CP2 is never switched — it is a static
bias whose only job is to keep XCOMP mode armed and to set the threshold PR1
must cross.

Pin leakage on both pins is ±0.1 µA max, so the 24 k/10 k and 100 k/150 k
dividers see ≤ 10 mV of leakage error — negligible against the 1.53 V margin.

**Action outside this task:** the spec's DR-06 paragraph
(`docs/superpowers/specs/2026-08-08-isolated-hub-revb-design.md`, "Priority
mux") must be edited. Its behavioural table is right; its mechanism sentence is
not.

### 4.4 Singles versus dual

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

GND2 instance is identical with `V_REF` = 1.23 V, VCC = J2 VBUS, VEE = GND2,
and its `CC_DET_L` node feeding the `2N7002` that drives **PR1**.

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

| Pin | Name | GND1 instance | GND2 instance |
|---|---|---|---|
| 1 | Gate | `CC_DET_L` (host) | `CC_DET_L` (external) |
| 2 | Source | GND1 | GND2 |
| 3 | Drain | `SN6505B.EN`, 10 kΩ pull-up to `VBUS_HOST` | TPS2121 `PR1`, 100 k/150 k divider from IN1 |

---

## 5. Step 4 — Stock survey

Surveyed 2026-08-08. DigiKey API credentials are not configured in this
environment; figures are from distributor product pages. Threshold for a
sourcing flag: < 1000 units.

### Actives

| Part | MPN | Package | Distributor | Stock | Price (1) | Price (100) | Status | Flag |
|---|---|---|---|---|---|---|---|---|
| Buck-boost converter | `TPS63070RNMR` | VQFN-HR-15 | DigiKey | **26,889** | $3.37 | $2.09 | Active | — |
| — fixed-5 V alternate | `TPS630701RNMR` | VQFN-HR-15 | DigiKey | 1,740 | $3.37 | $2.09 | Active | thin |
| 3.3 V buck | `TPS62203DBVR` | SOT-23-5 | DigiKey | 2,205 | $1.62 | $0.954 | Active | — |
| " | `TPS62203DBVR` | SOT-23-5 | LCSC C9051 | 8,180 | $1.41 | $0.821 (1k) | Active | — |
| Comparator (dual) | `TLV7042DDFR` | SOT-23-8 | DigiKey | **1,220** | $1.64 | $0.970 | Active | **thin** |
| Comparator (single, fallback) | `TLV7041DBVR` | SOT-23-5 | DigiKey | 7,726 | $0.88 | $0.500 | Active | — |
| Inverter FET (×2) | `2N7002-7-F` | SOT-23 | DigiKey | 18,679 | $0.18 | — | Active | — |
| 3.3 V LDO (build option) | `AP2112K-3.3TRG1` | SOT-23-5 | DigiKey | **80,565** | $0.23 | — | Active | — |

### Passives

| Part | MPN | Package | Distributor | Stock | Price | Used for |
|---|---|---|---|---|---|---|
| 1.5 µH, 4.6 A Isat, 14.4 mΩ | `XFL4020-152MEC` (Coilcraft) | 4.0 × 4.0 mm | LCSC C3033018 | **20,961** | $3.70 / $2.87 (1k) | TPS63070 |
| 10 µH, 1.19 A, 110 mΩ | `744043100` (Würth) | 4.8 × 4.8 mm | DigiKey | 3,922 | $1.53 / $1.23 (100) | TPS62203; 24 wk lead time |
| 10 µF 25 V X5R | `CL21A106KAYNNNE` (Samsung) | 0805 | LCSC C15850 | **330,660** | $0.106 | C_IN ×2, 3.3 V rail |
| 22 µF 16 V X5R | `CL21A226MOQNNNE` (Samsung) | 0805 | LCSC C98190 | **597,740** | $0.139 / $0.082 (10k) | C_OUT ×3 |
| 100 nF 16 V X7R | `CL05B104KO5NNNC` (Samsung) | 0402 | LCSC C1525 | **1,310,700** | $0.0055 | C_VAUX, pin-adjacent HF caps, comparator decoupling |
| 100 kΩ 1 % | `RC0402FR-07100KL` (Yageo) | 0402 | LCSC C60491 | **3,594,500** | ~$0.0007 | FB bottom, R4, PG pull-up, `CC_DET_L` pull-ups ×2, PR1 divider top |
| 523 kΩ 1 % | `RC0402FR-07523KL` (Yageo) | 0402 | Heisener / DigiKey | 599,928 | ~$0.001 | FB top |
| 150 kΩ, 24 kΩ, 10 kΩ 1 % | `RC0402FR-07150KL`, `-0724KL`, `-0710KL` (Yageo) | 0402 | LCSC / DigiKey | same series as C60491 (>10⁵ each) | ~$0.0007 | PR1 divider bottom; CP2 divider; `R_EN` and CC series ×4 |

**Sourcing risks:**

1. **`TLV7042DDFR` at 1,220 units.** Above the flag threshold but only just,
   and two are needed per board. Mitigation is designed in: the `TLV7041DBVR`
   singles (7,726) implement the identical circuit and need only a footprint
   swap. If a production run is planned, buy the duals ahead of the board.
2. **`744043100` carries a 24-week manufacturer lead time.** 3,922 in stock
   covers prototypes; any 10 µH / ≥ 0.5 A / ≤ 200 mΩ shielded inductor in a
   ≤ 5 × 5 mm body substitutes without change.
3. **`TPS630701RNMR` at 1,740** is why the adjustable `TPS63070RNMR` was
   chosen. Recorded so the fixed version is not "simplified" back in later.
4. `XFL4020-152MEC` no longer appears in DigiKey's own catalogue (it moved to
   DigiKey Marketplace). Source from LCSC or Coilcraft direct.

---

## 6. Handoff

**Task 4 (upstream CC sense, GND1)** — one `TLV7042DDFR`, VCC = `VBUS_HOST`,
`V_REF` = 0.66 V from a `VBUS_HOST` divider, **inverting** connection (CC to
`IN−`), 10 kΩ series into each CC input, outputs wire-ORed over a **100 kΩ**
pull-up to `VBUS_HOST` forming `CC_DET_L`, one `2N7002` inverting that node
onto `SN6505B.EN` with a **10 kΩ** pull-up to `VBUS_HOST` (not 100 kΩ — see
§4.2). Do **not** implement the spec's "pull-down" wording.

**Task 5 (isolated power chain, GND2)** — `TPS63070RNMR` per §2.4, capacitor
and resistor set per §2.4, FB divider 523 k/100 k for 4.98 V, `EN` tied to
`DCDC_RAW`, **`PS/SYNC` tied high** with a DNP 0 Ω pad to GND2, `VSEL` low,
`PG` pulled up with a test point. Output net `ISO_5V_PRE` → TPS2121 `IN2`.
Everything in §2.5 goes inside Shield B. For port-drop budgeting use
**TPS2553 DBV 135 mΩ max** and **TPS2121 90 mΩ max**, not the 25 °C typicals.

**Task 6 (external input, GND2)** — one `TLV7042DDFR`, VCC = **J2 VBUS**,
`V_REF` = 1.23 V, inverting, wire-ORed over a 100 kΩ pull-up, inverted by a
`2N7002` onto TPS2121 **`PR1`** (100 kΩ to IN1 / 150 kΩ to GND2). **`CP2` is a
static bias from IN1 via 24 kΩ / 10 kΩ — it is not driven by the detect.** See
§4.3 for the truth-table derivation and note that the spec's DR-06 wording is
wrong.

**Task 7 (hub rails)** — `TPS62203DBVR` + `744043100` per §3.4, laid out as a
stuff option against `AP2112K-3.3` + 0 Ω per §3.5. Budget the hub at
**155 mA max** at 3.3 V, verified.

**Spec edits required** (`2026-08-08-isolated-hub-revb-design.md`):

1. Power budget table: η(T1+rectifier) **83.3 %** (was 85 % estimate); hub
   3.3 V **155 mA max, verified** (was estimate); add the TPS2121 mux drop;
   shared port current **≈ 414 mA** (was ≈ 390 mA).
2. "Isolated power chain → Regulator": **synchronous buck-boost**, not
   synchronous buck.
3. **DR-06 paragraph: rewrite the mechanism.** Keep the behavioural table;
   replace "CP2 must be driven by the 3 A-detect net" with the CP2-bias /
   PR1-driven arrangement of §4.3.
4. "Upstream CC sensing": replace "wire-ORed to `SN6505B.EN` with a pull-down"
   with the pull-up + inverter arrangement of §4.2.

## 7. Bring-up items this record creates

1. Measure `DCDC_RAW` at 800 mA primary, `V_BUS` = 4.75 / 5.00 / 5.25 V, at
   thermal equilibrium. This is the measurement the whole Step 1 argument is
   waiting on, and it also resolves the `V_f`/`R_extra` degeneracy.
2. Measure the buck-boost's efficiency at the real operating point; §3.2 uses
   92 % and the port figure moves ≈ 4.5 mA per point.
3. Confirm `ISO_5V` stays regulated (not tracking `DCDC_RAW`) at the worst
   `V_BUS`. That is the buck-boost earning its place.
4. Check `ISO_5V` ripple across the PFM↔PWM boundary as the ports load through
   ≈ 613 mA; if it hunts unacceptably, fit the DNP 0 Ω to force PWM and
   re-measure idle draw in external-supply mode.
5. Measure idle draw in external-supply mode against the spec's unverified
   30–50 mA estimate, with the converter unloaded.
6. Verify the C_OUT lot's DC-bias curve keeps effective capacitance inside
   TI's 15–470 µF window at 5 V.
7. Scope `HUB_3V3` ripple and check HS eye / enumeration margin with the buck
   fitted; if degraded, fit the `AP2112K-3.3` + 0 Ω option and re-budget the
   ports at 373 mA.
8. Confirm `SN6505B.EN` polarity end-to-end through the corrected wire-OR and
   the `2N7002` inverter, on a Default, a 1.5 A, and a 3 A advertisement.
9. **Confirm mux selection on the bench in all four states** (external absent /
   present-not-3 A / present-3 A, converter running or not) before trusting
   §4.3. This is the correction with the least field evidence behind it.
10. Check converter start-up against the SN6505B's 1.42 A minimum current clamp
    with all output capacitance present (T1 soft-start 4.25 ms typ).
