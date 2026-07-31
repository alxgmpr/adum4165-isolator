# Decoupling & Required-Externals Audit vs. Datasheet Typical-Application Circuits

> **Repo note (2026-07-30):** this document describes the **archived 4-port
> design**. That project no longer lives at the repo root — it was archived to
> branch `4port-archive` when the repository collapsed to the single-port
> isolator. Every bare `isolator.kicad_sch` / `isolator.kicad_pcb` /
> `isolator.kicad_pro` path below refers to the **archived** files as they stood
> on that branch, **not** to the files of those names at the root today, which
> are the single-port isolator. Retrieve them with
> `git show 4port-archive:isolator.kicad_sch`.

**Date:** 2026-07-26
**Scope:** every IC in `isolator.kicad_sch` / `isolator.kicad_pcb`, checked against the manufacturer's
"typical application", "application information", "layout guidelines" and "power supply recommendations"
sections. Read-only audit — no project file was modified.

**Inputs**

| Source | Detail |
|---|---|
| Datasheet PDFs | `datasheets/*.pdf`, text-extracted with `pdftotext -layout` |
| AP2112 | **No local PDF.** Retrieved `cdn-shop.adafruit.com/product-files/2471/AP2112.pdf` (BCD Semiconductor Rev 2.0, Mar 2013) — diodes.com returned HTTP 403, LCSC/Mouser mirrors timed out |
| USBLC6-2 | **No local PDF.** Retrieved via `mm.digikey.com/.../USBLC6-2SC6 SOT-23-6L.PDF` (SLKOR second-source, pinout is an image) **and** `kontest.ru` mirror of **ST USBLC6-2 Rev. 2, June 2005** — the ST one has the pinout and the VBUS-cap recommendation in extractable text |
| Netlist | `analyze_schematic.py` → pin-to-net map for all 121 components |
| Placement | Pad-level global coordinates parsed directly from `isolator.kicad_pcb` (125 footprints) |
| Prior record | `docs/superpowers/reviews/2026-07-26-schematic-review.md` (claims spot-verified, see §6) |

**Caveat on placement findings.** The PCB is mid-layout (`HEAD` = "power planes… routing session").
Placement distances below are pad-centre to pad-centre in the *current* board file and are reported so
they can be fixed before routing hardens, not as final defects.

**Known break excluded from scoring:** `U7.OV2` (pin 4) is on an unnamed net — the GUI-buffer wire loss the
user is already fixing. It is scored UNVERIFIABLE, not as a deviation.

---

## 1. Verdict summary

| Verdict | Count |
|---|---|
| COMPLIANT | 42 |
| DEVIATION-JUSTIFIED | 3 |
| DEVIATION-FIX-NEEDED | 9 |
| UNVERIFIABLE | 7 |

Of the 9 fix-needed items, **3 are schematic-level** (U6 output-cap ESR/type, U6 minimum load current,
downstream bulk < USB's 120 µF/hub) and **6 are PCB-placement-level** on the isolated 5 V rail and the
two comparators.

**Headline:** the *schematic* is very close to datasheet-clean. Every mandated external exists with a
correct value. The real problem is that on the isolated side, **the `ISO_5V` decoupling caps have all been
placed on the right-hand third of the board** — `U1.VBUS2`, `U3` (ESD) and `U8` (LDO) sit 37–44 mm from the
nearest cap on their own rail, and the ADuM4165 explicitly caps that distance at **10 mm**.

---

## 2. Per-IC audit tables

### U1 — ADuM4165BRIZ (`adum4165-4166.pdf`, Rev. B)

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| VDD1 bypass | Table 12 p.11 + App Info p.22: **exactly 0.1 µF**, "required capacitor value of 0.1 μF for correct operation of the internal 3.3 V regulator"; ">0.1 μF can disrupt start-up sequencing when using the LDO regulator, while <0.1 μF can result in too much voltage ripple" | C5 `100n` X7R 0603, **3.5 mm** from pin 3 | COMPLIANT |
| VDD2 bypass | same (Table 12 p.11, pin 18) | C36 `0.1u` X7R 0603, **8.2 mm** from pin 18 | COMPLIANT |
| VBUS1 bypass | Table 12 p.11 pin 1: "bypass to GND1 using a 0.1 μF capacitor" | C50 `100n`, **2.9 mm** from pin 1 (C4/C6 also on `VBUS_HOST` but 30 mm away) | COMPLIANT |
| VBUS2 bypass | Table 12 p.11 pin 20: "bypass to GND2 using a 0.1 μF capacitor" | Net-level: `ISO_5V` carries 6 × 0.1 µF. **PCB: nearest cap on `ISO_5V` to pin 20 is C19 at 43.9 mm** | **DEVIATION-FIX-NEEDED** (PCB) |
| Bypass lead length | PCB Layout p.24: "The total lead length between both ends of the capacitor and the power supply pin must not exceed 10 mm", "low ESR type" | C5 3.5 / C50 2.9 / C36 8.2 mm ✔; VBUS2 43.9 mm ✘ | see above |
| Bypass ground return | Table 12 p.11: pins **4, 7** (GND1) and **15, 16, 17** (GND2) "are not suitable for connection of bypass capacitance". Suitable: pins 2, 10 (GND1), 11, 19 (GND2) | Schematic collapses all to `GND1`/`GND2`. PCB: C36 sits 7.3 mm from pin 19 (suitable) — geometry allows the correct return, but the board is not routed yet | UNVERIFIABLE (routing action item) |
| Crystal | p.22: ≤50 ppm tolerance, ≤100 ppm stability, start-up <0.3 ms, "a typical crystal capacitance of 10 pF and capacitive loads <10 pF"; refers to eval-guide BOM. **Eval BOM (`eval-adum4165-4166-ug-2027.pdf` Table 4, line 273): 24 MHz ±50 ppm, 8 pF, 50 Ω 4-SMD (IQD LFXTAL056140REEL) with C1/C2 = 8 pF 0402** | Y1 `SX3B24.000F0810F30` (CL 8 pF, ±10 ppm / ±30 ppm, ESR 30 Ω); C1/C2 = 8 pF C0G at **2.3 / 2.1 mm** from XI1/XO1; Y1 at 4.5 mm | COMPLIANT — an exact copy of ADI's own validated point. (CL_eff ≈ 7 pF with stray, i.e. −12.5 % vs CL, a pull of at most +71 ppm; the eval board has the identical mismatch.) |
| External D± pull-ups | p.22: "External pull-up resistors are not required because these resistors are integrated within the isolator" | none fitted | COMPLIANT |
| Barrier stitching cap | p.22: "important to minimize board capacitive coupling across the isolation barrier" — no component mandated | C49 1 nF 2 kV 2220, **DNP** | COMPLIANT (optional) |

### U4 — USB2514B-AEZC (`USB2514B-AEZC.pdf`, DS00001692E)

> **This datasheet has no Layout section and no decoupling/bypass section at all.** A grep for
> `Layout`, `decoupling`, `bypass capacitor`, `bulk capacit`, `ferrite bead`, `power supply recommend`
> across the whole document returns **zero hits**. Everything below marked *convention* is engineering
> practice / Microchip EVB practice, **not** a datasheet mandate.

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| Per-VDD33/VDDA33 0.1 µF | **silent** (convention: one per supply pin) | 6 supply pins (5, 10, 15, 23, 29, 36) all on `ISO_3V3`; rail carries **9 × 0.1 µF** (C16, C17, C23–C29) + C22 1 µF. PCB: nearest 0.1 µF per pin = 6.6 / 7.7 / 8.0 / 9.0 / 12.1 / 12.9 mm | COMPLIANT-BY-CONVENTION (placement marginal on pins 29/36) |
| Bulk on 3.3 V | **silent** | Only C22 `1u` (which is really the AP2112 COUT). Total `ISO_3V3` = **1.9 µF nominal** | DEVIATION-JUSTIFIED (no datasheet basis) — but 1.9 µF for a 155 mA hi-speed hub is thin; the prior review's open action for a 4.7–10 µF bulk near U4 still stands |
| CRFILT | p.14 Table 3-2: "this pin can have **up to a 0.1 µF** low-ESR capacitor to VSS, or be left unconnected" | C30 `0.1u` (at the ceiling); **11.5 mm** from pin 14 | COMPLIANT (value); placement marginal |
| PLLFILT | p.14 Table 3-2: identical wording | C31 `0.1u`; **15.3 mm** from pin 34 | COMPLIANT (value); placement marginal |
| RBIAS | p.13 Table 3-2: "a **12.0 kΩ (+/- 1%)** resistor is attached from ground to this pin" | R15 `12.0k`, `RC0603FR-0712KL` = ±1 % ✔. PCB: **27.9 mm** from pin 35 | COMPLIANT (value) / **DEVIATION-FIX-NEEDED** (placement) |
| XTAL loading | p.44 Fig 7-2: `C1 = 2 × (CL − C0) − CS1`, C0 → 0; Note 7-2: "Each of these capacitance values is **typically around 18 pF**". Crystal spec p.44: parallel resonant, fundamental, 24 MHz ±350 ppm | Y2 `X322524MOB4SI` CL = 12 pF, ±10 ppm / ±20 ppm; C32/C33 = **18 pF** C0G → 2×12 − CS ≈ 18 pF with CS ≈ 6 pF | COMPLIANT (textbook match). PCB: C32/C33 are 12.3–12.8 mm from XTALIN/XTALOUT — long for a 24 MHz loop |
| RESET_N network | §5.5.1 p.36: "assertion of RESET_N for a **minimum of 1 µs** after all power supplies are within operating range". No RC mandated | R16 10 k pull-up + C34 1 µF → 10 ms; D5 1N4148WS reverse-discharge to `ISO_3V3` | COMPLIANT (RC is convention, 10 000× the minimum) |
| VBUS_DET | p.12: "For self-powered applications with a permanently attached host, this pin must be connected to a **dedicated host control output**, or connected to the 3.3 V domain that powers the host" | `PGOOD2` ← U1 pin 14 PGOOD (a VDD2-referenced 3.3 V output) + R25/R26 100 k bias pair | COMPLIANT — PGOOD is precisely a "host is alive and clocked" control output |
| NON_REM straps | p.14 Table 3-3: 47–100 kΩ for I/O-type strap pins | R23/R24 = 47 k | COMPLIANT |
| CFG_SEL straps | p.14 Table 3-3 / Fig 3-4 | R21/R22 = 10 k to GND2 → CFG_SEL[1:0] = 00 | COMPLIANT |
| TEST pin | p.14: "treat as a no connect pin or connect to ground. No trace or signal should be routed or attached to this pin" | pin 11 unconnected | COMPLIANT |
| OCS_N pull-ups | **silent** (FAULT is open-drain, so needed) | R17–R20 = 100 k to `ISO_3V3` | COMPLIANT-BY-CONVENTION |

### U5 — SN6505BDBVR (`SN6505BDBVR.pdf`, SLLSEP9I)

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| VCC bypass | Table 5-1 p.3: "It should be bypassed with a **4.7 μF or greater, low ESR capacitor**". §11.1 p.34: 1–10 µF X5R/X7R, ≥10 V, closest to VIN/GND pins | C7 `10u` 0805 at **5.9 mm**, C6 `0.1u` at **7.2 mm** from pin 2 | COMPLIANT |
| HF bypass | §9.2.2.4 p.25: "the device requires a bypass capacitor in the range of **10 nF to 100 nF**" | C6 `0.1u` | COMPLIANT |
| Primary centre-tap bulk | §9.2.2.4 p.25 / §11.1 p.34: "**1 μF to 10 μF**", ≥16 V, X5R/X7R, close to the centre-tap | Shared `VBUS_HOST`: C6/C7 at 7.7/8.1 mm from T1 pin 2; C3 `10u` + C4 `0.1u` at the J1 entrance | COMPLIANT |
| Snubbers on D1/D2 | **Not recommended anywhere** — grep for "snubber" across the whole datasheet: 0 hits. §11.1 only asks for short D1/D2-to-primary traces | none fitted | COMPLIANT (no deviation — the absence is correct) |
| EN | Table 5-1 p.3: "If unused this pin should be tied **directly to VCC**" | pin 5 → `VBUS_HOST` (= VCC net) | COMPLIANT |
| CLK | Table 5-1 p.3: "Internally it is pulled down to GND. If valid clock is not detected on this pin, the device shifts automatically to internal clock" | pin 6 → `GND1` → internal oscillator + spread-spectrum active | COMPLIANT |
| Rectifier diodes | §11.1 p.34: "should be Schottky diodes with low forward voltage" | D1/D2 `SS34` (40 V 3 A Schottky, SMA) | COMPLIANT (conservative vs TI's MBR0520L) |
| Rectifier-output bulk | §9.2.2.4 p.25 / §11.1 p.34: "**1 μF to 10 μF**", ≥16 V, X5R/X7R | `DCDC_RAW`: C8 `47u` 1210 + C9 `0.1u`, at 22.0 / 24.9 mm from U6 VIN | **DEVIATION-JUSTIFIED** — 4.7× the recommended ceiling, but §9.3 states soft-start exists specifically to prevent "high inrush current from VCC while charging **large secondary side decoupling capacitors**", and the downstream load is a 1.5 A-class LDO, not TI's 100 mA example. Value is fine; **placement is not** (see fix list) |

### U6 — MIC29302WU (`MIC29302WU.pdf`, DS20005685A — MIC2915X/30X/50X/75X family)

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| **Output cap (stability)** | §4.2 p.25, Table 4-1: MIC2930x minimum **10 µF at full load**. Then verbatim: "This capacitor **need not be an expensive low ESR type**: aluminum electrolytics are adequate. In fact, **extremely low ESR capacitors may contribute to instability**. **Tantalum capacitors are recommended** for systems where fast load transient response is important." Front-page typical app (p.3) and Fig 4-2 (p.26) both show a **tantalum** | C10 `47u` **1210 MLCC** (`TMK325ABJ476MM-P`, X5R-class, ESR of order 2–5 mΩ) + C11 `0.1u` | **DEVIATION-FIX-NEEDED** — this is the one true LDO-stability deviation in the design. A PNP-pass LDO of this family wants ESR in a window; a bare 47 µF MLCC sits far below it |
| Input cap | Front page p.3 typical app: **10 µF tantalum**. §4.2 p.25: "Where the regulator is powered from a source with high AC impedance, a **0.1 µF** capacitor connected between Input and GND is recommended. This capacitor should have good characteristics to above 250 kHz" | C8 `47u` + C9 `0.1u` on `DCDC_RAW` (input is a 400 kHz push-pull rectifier — definitely "high AC impedance") | COMPLIANT (value); placement 22.0 / 24.9 mm — too far |
| ADJ divider | Eq. 4-6 §4.4 p.25: `R1 = R2 × (VOUT/1.240 − 1)`. Adjust-pin bias current 40 nA typ / **120 nA max** (Elec. Char. p.9) | R3 30.1 k / R4 10 k → **1.240 × 4.01 = 4.972 V** ✔. Divider current 124 µA = **1030 × IADJ(max)**; worst-case bias error 3.6 mV | COMPLIANT |
| **Minimum load current** | §4.3 p.25, Table 4-2: MIC2930x = **7 mA**. "If the output current is too small, leakage currents dominate and the output voltage rises." §4.4 adds: "Applications with widely varying load currents may scale the resistors to draw the minimum load current required" | `DCDC_5V` permanent load = R36 1 k + green LED D6 ≈ **2.9 mA**, plus the 124 µA divider ≈ **3.0 mA total**. When `EXT_5V` wins the mux, U7's IN2 draws only ~65 µA quiescent, so 3.0 mA is the whole load | **DEVIATION-FIX-NEEDED** (2.4× under the specified minimum) |
| EN | MIC29xx2 has an enable input | pin 1 → `DCDC_RAW` = VIN → always enabled | COMPLIANT |

### U7 — TPS2121RUXR (`TPS2121RUXR.pdf`, SLVSEA3F)

> §11 Power Supply Recommendations (p.33) is **entirely qualitative** — no capacitor values are given, and
> **none of the four application schematics (Fig 10-1/10-2/10-9/10-13/10-17) show input or output caps at all**.
> The only numeric externals TI gives for §10 are C_SS, R_ILM and the OV/PR divider resistors.

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| IN1 bypass | §11 p.33: "Bypass capacitors on these pins should be placed as close to the device as possible. **Low ESR ceramic capacitors with X5R or X7R dielectric are recommended**." Also: "In the case where there are long cables… a large capacitance can be used near the input" | `EXT_5V`: C12 + C14 `10u`, C13 + C15 `0.1u` — 3.7 / 5.9 / 6.6 mm from pin 7 | COMPLIANT |
| IN2 bypass | same | `DCDC_5V`: C10 `47u` (8.4 mm), C11 `0.1u` (9.2 mm) | COMPLIANT |
| OUT cap | §11 p.33: "To avoid output voltage drop, the capacitance on OUT can be increased" | `ISO_5V`: C18 `47u` (9.7 mm), C21 `1u`, 6 × `0.1u` — 48.6 µF nominal | COMPLIANT |
| ST pull-up | Rec. Operating Conditions p.7: **R_ST = 6 kΩ … 20 kΩ**; V_ST 0–5.5 V (abs max 6 V p.6). Pin Functions p.4: "Connect to GND if not required" | R13 `10k` to `ISO_5V` ✔ in range; V_ST ≤ 5.5 V ✔ | COMPLIANT — *observation only:* R14 1 k + LED D4 hangs off the same node, clamping ST-high to ≈2.3 V and giving the LED only ~0.27 mA. Cosmetic (very dim), not a datasheet violation |
| ILIM resistor | Eq. 2 p.13: `I_LM = 65.2 / R_ILM^0.861`, valid **18 kΩ ≤ R_ILM ≤ 100 kΩ** | R12 `35.7k` → **3.00 A**; in range ✔. PCB: 13.6 mm from pin 10 | COMPLIANT (value); placement long |
| SS cap | Table 9-1 p.12: 100 nF → **780 V/s** at V_IN = 5 V. §10.2.4.3 p.23 worked example uses 100 nF | C20 `0.1u` (8.2 mm) → 780 V/s × 48.6 µF ≈ **38 mA** switchover inrush | COMPLIANT — matches TI's §10 value exactly |
| CP2 | §9.4 p.16: "If CP2 is pulled low, then the TPS2121 ignores this pin… When CP2 is pulled high, this enables fast switchover and is compared to PR1". V_REF = 1.06 V typ; CP2 rated 0–5.5 V | `n3A_DET` (3.3 V logic from the U13/U14 wired-OR) | COMPLIANT |
| PR1 | §9.4 p.16 XREF scheme | R10 100 k / R11 47 k from `EXT_5V` → **1.60 V** (> V_REF), shunted to 0 V by Q1 when `n3A_DET` is high | COMPLIANT — logic resolves correctly in both states |
| OV1 | tie below V_REF to disable OV protection (Table 9-3 p.17) | pin 5 → `GND2` | COMPLIANT |
| **OV2** | same | pin 4 → **unnamed net** (the known GUI wire loss) | **UNVERIFIABLE** — must land on `GND2` when the wire is restored |
| Hotplug TVS | §10.7 p.31–32: recommends a TVS on inputs fed through long cables | `EXT_5V` comes from J2 (a short USB-C cable) with no TVS | DEVIATION-JUSTIFIED (5 V source, 24 V abs max, USB-C cable inductance is small) |

### U8 — AP2112K-3.3 (no local PDF; BCD/Diodes **AP2112 Rev 2.0**, retrieved this session)

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| Pinout (SOT-23-5) | Pin Descriptions p.2: **1 = VIN, 2 = GND, 3 = EN, 4 = ADJ/NC, 5 = VOUT** | exactly that | COMPLIANT (pinout now verified against a manufacturer PDF, closing a prior-review gap) |
| C_IN | Every Electrical Characteristics table header (pp.5–12): "**CIN = 1.0 μF (Ceramic)**". Fig 21 Typical Application p.17, Note 4: "It is recommended to use **X7R or X5R** dielectric capacitor if 1.0 μF ceramic capacitor is selected as input/output capacitors" | C21 `1u` X7R on `ISO_5V`. **PCB: nearest `ISO_5V` cap to pin 1 is 37.4 mm** | Schematic COMPLIANT / **PCB DEVIATION-FIX-NEEDED** |
| C_OUT | same tables: "**COUT = 1.0 μF (Ceramic)**". Features p.1: "**Stable with 1.0 μF Flexible Cap: Ceramic, Tantalum and Aluminum Electrolytic**" — **no ESR window, no minimum-ESR requirement** (CMOS LDO, unlike U6) | C22 `1u` X7R on `ISO_3V3`. **PCB: 15.2 mm from pin 5** (C27 0.1 µF is closer at 5.3 mm, but the 1 µF stability cap is the one that matters) | Schematic COMPLIANT / **PCB DEVIATION-FIX-NEEDED** |
| EN | Elec. Char.: V_EN(H) 1.5 V min, **6.0 V max**; abs max VCC 6.5 V (p.4) | pin 3 → `ISO_5V` (≤5.5 V) | COMPLIANT |
| NC (pin 4) | Pin Descriptions p.2: "No Connection for Fixed Version" | unconnected | COMPLIANT |

### U9–U12 — TPS2553DBVR (`TPS2553DBVR.pdf`, SLVS841F)

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| IN bypass | Pin Functions p.4: "connect a **0.1 µF or greater** ceramic capacitor from IN to GND **as close to the IC as possible**". §10.2.1.2.4 p.20 and §12.1 p.25 repeat it ("place the 100-nF bypass capacitor near the IN and GND pins… low-inductance trace") | `ISO_5V` carries 6 × 0.1 µF. **PCB nearest 0.1 µF per IN pin: U9 5.6 mm ✔, U12 8.5 mm ✔, U11 10.8 mm (marginal), U10 17.0 mm ✘** | Schematic COMPLIANT / **PCB partial DEVIATION-FIX-NEEDED (U10)** |
| OUT cap | §12.1 p.25: "placing a **high-value electrolytic capacitor and a 100-nF bypass capacitor** on the output pin when large transient currents are expected". Front-page Typical Application note: "**USB requirement that downstream facing ports are bypassed with at least 120 µF per hub**" | Per port: `10u` 0805 + `0.1u` (C38/C39, C41/C42, C44/C45, C47/C48) = **40 µF** nominal at the ports, + 47 µF on `ISO_5V` ≈ **88 µF nominal**. After DC-bias derating of 0805/1210 MLCC at 5 V (≈40–55 % loss) the effective figure is roughly **45–60 µF** | **DEVIATION-FIX-NEEDED** vs. the 120 µF/hub figure TI prints on page 1 |
| R_ILIM value | Eq. (1) p.15: `IOS_max = 22980/R^0.94`, `IOS_nom = 23950/R^0.977`, `IOS_min = 25230/R^1.016`; valid **15 kΩ ≤ R_ILIM ≤ 232 kΩ** | R27–R30 `40.2k` → **591 mA min / 648 mA nom / 714 mA max**; comfortably above the 500 mA port class and below a droop-inducing limit | COMPLIANT |
| R_ILIM tolerance | p.15 revision note + §10.2.1.2.2: "the recommended **1 %** resistor range for RILIM is 15 kΩ ≤ RILIM ≤ 232 kΩ **to ensure stability**"; "it is important to account for this tolerance when selecting RILIM" | `RC0603FR-0740K2L` = ±1 % F-grade | COMPLIANT |
| R_ILIM trace | §12.1 p.25: "The traces routing the RILIM resistor to the device must be **as short as possible** to reduce parasitic effects on current limit accuracy" | 2.5 / 8.3 / 10.5 / **14.0 mm** (R27/R28/R29/R30) | **DEVIATION-FIX-NEEDED** (R30, and R29 marginal) |
| FAULT | open-drain, active low (Pin Functions p.4) | R17–R20 100 k to `ISO_3V3`, into hub OCS_N inputs | COMPLIANT |
| EN | logic-high input | driven directly by hub PRTPWR1–4 | COMPLIANT |
| PowerPAD | Pin Functions p.4 — DBV (SOT-23-6) has no pad | n/a | COMPLIANT |

### U13/U14 — TLV7041DBVR (`TLV7041DBVR.pdf`, SLVSE13J)

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| V+ bypass | §7.4.1 Layout Guidelines p.29: "TI recommends a **power-supply bypass capacitor of 100 nF** when supply output impedance is high, supply traces are long, or when excessive noise is expected on the supply lines. Bypass capacitors are also recommended when the comparator output drives a long trace… the system will benefit from a **bypass capacitor directly from the supply pin to ground**" | Net-level `ISO_3V3` has 9 × 0.1 µF, but **all of them are clustered at y ≈ 79–82 near U4/U8**. PCB: nearest 0.1 µF to **U13 pin 5 = 33.9 mm**, to **U14 pin 5 = 31.4 mm** | **DEVIATION-FIX-NEEDED** — this is exactly the "supply traces are long" + "output drives a long trace" case the guideline names (both outputs drive `n3A_DET` across the board to U7 CP2) |
| §7.3 Power Supply Recs | p.29: V_S 1.6–6.5 V; single-ended supply OK | V+ = `ISO_3V3` (3.3 V), V− = `GND2` | COMPLIANT |
| Open-drain output | wired-OR needs a pull-up | R9 100 k `ISO_3V3` → `n3A_DET` | COMPLIANT |

### U2/U3/U15–U18 — USBLC6-2SC6 (**ST USBLC6-2 Rev. 2, June 2005** — retrieved this session)

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| **Pinout** | **Figure 1 "Functional Diagram", p.1** (SOT23-6L), verbatim layout: `I/O1 = 1 … 6 = I/O1`, `GND = 2 … 5 = VBUS`, `I/O2 = 3 … 4 = I/O2` | pin 1 = I/O1, 2 = GND, 3 = I/O2, 4 = I/O2, 5 = VBUS, 6 = I/O1 — on all six devices, with D+ on 1/6 and D− on 3/4 | **COMPLIANT — pinout claim is now double-sourced** (ST Fig. 1 p.1 **+** KiCad `Power_Protection.kicad_sym` base symbol `USBLC6-2P6`, which matches pin-for-pin) |
| VBUS decoupling | **§3 "How to ensure a good ESD protection", p.5**: "the track from the VBUS pin to the power supply +VCC and from the GND pin to GND must be **as short as possible**… **To ensure the same efficiency for positive surges when the connections can't be short enough, we recommend to put close to the USBLC6-2, between VBUS and ground, a capacitance of 100 nF**" (Figure 7; the Figure 8 measurement board shows `C = 100nF`). §2 p.4 quantifies the penalty: 6 nH of track adds **144 V** to the clamp | U2 (host): C4 `100n` at **9.0 mm** ✔<br>U15: C39 `0.1u` at **4.1 mm** ✔<br>U16: C41 `10u` at 3.8 mm / C42 `0.1u` at 6.8 mm ✔<br>U18: C47 `10u` at 10.6 mm (nearest 0.1 µF further) — marginal<br>U17: nearest 0.1 µF **16.7 mm** ✘<br>**U3 (isolated side): nearest `ISO_5V` cap 38.7 mm** ✘ | U2/U15/U16 COMPLIANT; U18 marginal; **U17 and U3 DEVIATION-FIX-NEEDED** |
| I/O routing | §3 p.5: flow-through, short stubs | flow-through pairs (1/6, 3/4) on all six | COMPLIANT |

### T1 — Würth 750313638 + D1/D2 rectifier (`750313638.pdf`)

| Component | Datasheet says | Schematic / PCB has | Verdict |
|---|---|---|---|
| Secondary-side caps | **The Würth datasheet contains no capacitor recommendation of any kind** — it gives Electrical Properties (turns ratio n = 1:1.3, C_WW 4.75 pF, V_T 5000 V rms), the land pattern, two Typical Application property tables and the agency table. Nothing on external components | C8 `47u` + C9 `0.1u` on `DCDC_RAW` | COMPLIANT with Würth (silent). Judged against the driver's guidance instead — see the SN6505 row (DEVIATION-JUSTIFIED, 1–10 µF recommended) |
| Winding usage | **Typical Application (1)**: "Input: N1 / N2, Output 1: N3 / N4", V_in 5 V → V_out1 5 V @ **0.65 A**, f_switch 300–620 kHz | CT1 (pin 2) ← `VBUS_HOST`, N1/N2 (pins 1/3) ← U5 D1/D2; CT2 (pin 5) → `GND2`, N3/N4 (pins 6/4) → D1/D2 (SS34) → `DCDC_RAW`. Correct centre-tapped full-wave configuration, correct winding orientation, and SN6505B's 363–517 kHz sits inside the 300–620 kHz band | COMPLIANT |
| Current headroom | typical application rated 0.65 A out | *Note (outside decoupling scope):* the isolated path can be asked for well over 0.65 A when `EXT_5V` is absent. This is a power-budget matter, already the reason the TPS2121 mux exists | — |

### Y1 / Y2 — load-cap math

| Item | Datasheet says | Schematic has | Verdict |
|---|---|---|---|
| Y1 (ADuM4165) | ADI p.22: crystal cap ~10 pF, **loads < 10 pF**; eval BOM: 8 pF crystal + 8 pF loads | Y1 `SX3B24.000F0810F30`, CL = 8 pF; C1/C2 = 8 pF C0G → CL_eff ≈ **7.0 pF** (analyzer figure), −12.5 % vs CL, pull ≤ +71 ppm | COMPLIANT. **Y1's CL/tolerance came from LCSC's parametric database, not a manufacturer PDF** — confirm CL = 8 pF, ≤50 ppm tol, ≤100 ppm stability on the final MPN |
| Y2 (USB2514B) | Microchip Fig 7-2 p.44 + Note 7-2: `C = 2 × CL − CS`, "typically around 18 pF" | Y2 `X322524MOB4SI`, CL = 12 pF; C32/C33 = **18 pF** → CL_eff ≈ 12.5–13.5 pF, pull ≈ −15 ppm vs the hub's ±350 ppm budget | COMPLIANT. Same caveat: **CL = 12 pF is from the LCSC parametric DB** — confirm on the final MPN. If a CL = 8 pF crystal is ever substituted, C32/C33 must drop to ~10 pF |

---

## 3. Prioritised fix list (DEVIATION-FIX-NEEDED only)

### Schematic-level

**F1 — U6 MIC29302 output capacitor is the wrong dielectric class (LDO stability).** *Highest risk.*
Datasheet §4.2 p.25 warns "extremely low ESR capacitors may contribute to instability" and recommends
tantalum; C10 is a 47 µF 1210 MLCC with single-digit-mΩ ESR.
*Exact change:* keep C11 `0.1u`; either (a) change C10 to a **47 µF / 10 V tantalum** (e.g. AVX/Kemet
T-series D-case, ESR ≈ 0.3–1.5 Ω) — footprint must change from `C_1210_3225Metric` to a
tantalum D case (7343); or (b) keep the MLCC for bulk and **add a parallel 47–100 µF aluminium-polymer
with 30–150 mΩ ESR**; or (c) if the MLCC must stay alone, add a **0.1–0.3 Ω 1206 series resistor in the
feedback-sensed leg** is *not* viable at 3 A — prefer (a) or (b). Whichever is chosen, the cap must sit
within ~5 mm of U6 pin 4 (currently 21.5 mm).

**F2 — U6 minimum load current is 3.0 mA against a specified 7 mA** (Table 4-2, §4.3 p.25).
*Exact change:* R36 `1k` → **330 Ω** (green LED, V_f ≈ 2.1 V → 8.8 mA, 44 mW dissipated in the resistor —
use a 0603 rated ≥1/10 W), **or** add a dedicated bleeder `R_bleed = 680 Ω` from `DCDC_5V` to `GND2`
(7.4 mA, 37 mW) and leave R36 alone.

**F3 — Downstream bulk capacitance is below the USB 120 µF/hub figure** printed on TPS2553 datasheet p.1.
Nominal total is 88 µF (4 × 10 µF at the ports + 47 µF on `ISO_5V`); after 5 V DC-bias derating of the
0805/1210 MLCCs the effective value is roughly 45–60 µF.
*Exact change:* raise each port cap C38/C41/C44/C47 from `10u` 0805 to **`22u` 0805/1206 (≥16 V, X5R)**, or
add a single **100 µF ≥10 V aluminium-polymer on `ISO_5V`** next to C18. Preferred: the polymer bulk — it
also gives the TPS2121 OUT node real low-frequency energy and helps the 3.0 A ILIM behave on hot-plug.

### PCB-placement-level (all on the isolated side — fix before routing hardens)

**F4 — U1 `VBUS2` (pin 20) has no bypass within 43.9 mm; the ADuM4165 mandates ≤10 mm total lead length**
(Table 12 p.11 + PCB Layout p.24). This is the single hardest numeric requirement in the whole design and
it is currently violated by 4×.
*Exact change:* move **C35 `0.1u`** from (143.0, 99.0) to within ~4 mm of U1 pad 20 at (93.4, 65.28) —
e.g. (96.5, 63.5), directly beside C36 — and route its ground return to **U1 pin 19 or pin 11**, never to
pins 15/16/17.

**F5 — U3 (isolated-side USBLC6) `VBUS` has no 100 nF within 38.7 mm.** ST §3 p.5.
*Exact change:* move **C19 `0.1u`** from (138.0, 62.0) to within ~3 mm of U3 pad 5 at (100.14, 73.0).
(C19 currently sits next to U9, which then needs F8's replacement.)

**F6 — U8 AP2112 has neither its 1 µF C_IN (37.4 mm) nor its 1 µF C_OUT (15.2 mm) local.**
*Exact change:* move **C21 `1u`** to within ~3 mm of U8 pad 1 at (99.86, 87.05), and **C22 `1u`** to within
~3 mm of U8 pad 5 at (102.14, 87.05). C22 is currently doing duty as a hub cap at (115, 79) — the hub keeps
nine 0.1 µF parts, so nothing is lost.

**F7 — U13 and U14 (TLV7041) have no local V+ bypass (33.9 mm / 31.4 mm).** TI §7.4.1 p.29.
*Exact change:* re-site **two of the nine `ISO_3V3` 0.1 µF caps** — e.g. C28 to within ~3 mm of U13 pad 5
at (104.14, 116.05) and C29 to within ~3 mm of U14 pad 5. The hub then has 7 × 0.1 µF for 6 supply pins,
which is still one-per-pin.

**F8 — U10 TPS2553 IN pin is 17.0 mm from the nearest 0.1 µF.** Datasheet Pin Functions p.4 says
"as close to the IC as possible"; §12.1 says low-inductance trace.
*Exact change:* after F5 frees the allocation, place one of **C37 / C40 / C46** (all currently bunched at
x ≈ 136–147, y ≈ 111–114) within ~3 mm of U10's IN pad. Re-check U11 (currently 10.8 mm) at the same time.

**F9 — U4 `RBIAS` resistor R15 is 27.9 mm from pin 35; U9–U12 ILIM resistor R30 is 14.0 mm.**
RBIAS sets the whole transceiver bias current; TPS2553 §12.1 p.25 explicitly requires short ILIM traces.
*Exact change:* move **R15** from (143.2, 66.0) to within ~3 mm of U4 pad 35 at (114.5, 67.06); move
**R30** to within ~4 mm of U12's ILIM pad. Also tighten C30 (CRFILT, 11.5 mm) and C31 (PLLFILT, 15.3 mm)
to <5 mm, and Y2's C32/C33 (12.3–12.8 mm) to <5 mm.

---

## 4. Items that remain UNVERIFIABLE (and why)

| Item | Why |
|---|---|
| **U7 `OV2` (pin 4)** | On an unnamed net — the known GUI wire-buffer loss the user is fixing. Once repaired it must land on `GND2` (matching OV1) to keep the "no overvoltage protection" configuration of Table 9-3 p.17. Cannot be scored until then |
| **ADuM4165 bypass-return pin selection** | Table 12 p.11 forbids returning bypass capacitance to GND pins 4/7/15/16/17, but the schematic has one `GND1` and one `GND2` net and the PCB is **not yet routed** in that area. Geometry permits the correct return (C36 is 7.3 mm from pin 19); verification requires the finished copper |
| **Effective (DC-biased) capacitance on `ISO_5V` / port VBUS** | No manufacturer bias curves are present locally for `TMK325ABJ476MM-P` or `CL21A106KAYNNNE`; the 40–55 % derating used in F3 is a class estimate, not a datasheet number. If F3 is to be argued away rather than fixed, pull the real C-vs-V curves first |
| **MIC29302 exact ESR stability window** | DS20005685A gives the qualitative warning and Table 4-1's 10 µF minimum but publishes **no ESR-vs-load stability plot** for the MIC2930x. The "how much ESR is enough" number cannot be sourced from the datasheet — F1 is therefore written as "move into the recommended cap type", not "hit X mΩ" |
| **Y1 CL / tolerance and Y2 CL** | Both came from the LCSC parametric database (per the prior review), not manufacturer PDFs. `SX3B24.000F0810F30` (CL 8 pF, ±10/±30 ppm) and `X322524MOB4SI` (CL 12 pF, ±10/±20 ppm) must be confirmed against SCTF's and YXC's own datasheets before fab |
| **USB2514B decoupling practice** | The datasheet is genuinely silent — no Layout section, no decoupling section. The per-pin 0.1 µF scheme, the 100 k OCS_N pull-ups and the RESET_N RC are all **convention**, correct convention, but they cannot be scored against a datasheet requirement in either direction |
| **Würth 750313638 external components** | The datasheet specifies the transformer only. Any secondary-side capacitor judgement has to borrow the SN6505B's §9.2.2.4 / §11.1 guidance, which is what was done |

---

## 5. Things that were checked and are clean (no action)

- **ADuM4165 VDD1/VDD2 = exactly 0.1 µF.** The datasheet's "**>0.1 µF can disrupt start-up sequencing**"
  trap is respected on both sides, and both caps are within the 10 mm rule (3.5 mm / 8.2 mm). *This value
  must not be "improved" during layout cleanup.*
- **SN6505B has no snubber requirement** — the absence of D1/D2 snubbers is correct, not an omission.
- **SN6505B EN and CLK handling** match Table 5-1 p.3 word for word.
- **TPS2121 R_ST = 10 kΩ** sits inside the rarely-noticed 6–20 kΩ window; R_ILM = 35.7 kΩ inside 18–100 kΩ;
  C_SS = 100 nF is literally TI's §10.2.4.3 worked value.
- **TPS2553 R_ILIM = 40.2 kΩ ±1 %** gives 591–714 mA — correctly above a 500 mA port and correctly below
  a level that would droop the upstream supply, with the ±1 % tolerance the datasheet asks for.
- **USB2514B CRFILT/PLLFILT at the 0.1 µF ceiling, RBIAS 12.0 k ±1 %, Y2 18 pF loads** — all exact matches
  to Microchip's stated values / formula.
- **AP2112 NC pin left open, EN tied to VIN within the 6.0 V ceiling.**
- **USBLC6-2 flow-through I/O routing** (D+ on 1/6, D− on 3/4) on all six devices.
- **T1 winding orientation and switching frequency** match Würth Typical Application (1) exactly.

---

## 6. Spot-checks against the prior review

Three claims from `2026-07-26-schematic-review.md` were re-derived from the PDFs rather than trusted:

| Prior claim | Result |
|---|---|
| DR-07: "`VBUS1` (C4) and `VBUS2` (C35) also carry the specified 0.1 µF" | **Net-level true, but incomplete.** On the PCB the local VBUS1 cap is **C50** (2.9 mm), not C4 (30.6 mm); and C35 is **43.9 mm** from VBUS2. The prior review scored the schematic; the 10 mm lead-length rule was only carried as a layout note. Escalated here to F4 |
| DR-13: "R12 = 35.7 k → 3.002 A", "C20 = 0.1 µF → 780 V/s → ~38 mA" | **Confirmed.** 65.2 / 35.7^0.861 = 3.00 A (Eq. 2 p.13); Table 9-1 p.12 gives 780 V/s for 100 nF at 5 V; 780 × 48.6 µF = 37.9 mA |
| DR-10: "RBIAS = 12.0 k ±1 %… CRFILT and PLLFILT both 0.1 µF at the datasheet's ceiling" | **Confirmed** against p.13/p.14 Table 3-2. Adds: R15's *placement* (27.9 mm) was not covered — now F9 |

The prior review's architecture section still describes the ESD arrays as **NUP4202W1T2G**; the parts are
now **USBLC6-2SC6** (commit `aa4bf66`). That section is stale and should be refreshed on the next full pass.
