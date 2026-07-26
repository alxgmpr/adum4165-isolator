#!/usr/bin/env python3
"""Task-11 deep-review computations for isolator.kicad_sch.

Every number quoted in docs/superpowers/reviews/2026-07-26-schematic-review.md
that is not a direct datasheet quote is produced here. Run:

    python3 analysis/helpers/verify_limits.py
"""
from __future__ import annotations
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def latest_schematic_json() -> dict:
    runs = sorted(glob.glob(os.path.join(ROOT, "analysis", "20*")))
    for r in reversed(runs):
        p = os.path.join(r, "schematic.json")
        if os.path.isfile(p):
            print(f"# analyzer run: {os.path.basename(r)}")
            return json.load(open(p))
    raise SystemExit("no analyzer run found")


def hdr(t: str) -> None:
    print(f"\n=== {t}")


def main() -> None:
    d = latest_schematic_json()
    nets = d["nets"]
    comps = {c["reference"]: c for c in d["components"]}

    # ---- 1. TPS2121 (U7) mux current limit -------------------------------
    # DS SLVSEA3F Eq.2 (p.13): ILM[A] = 65.2 / RILIM[kohm]**0.861, 18k..100k
    hdr("U7 TPS2121 active current limit (R12 on ILIM_SET)")
    r_ilim_k = float(comps["R12"]["value"].rstrip("k"))
    ilm = 65.2 / (r_ilim_k ** 0.861)
    print(f"R12 = {r_ilim_k} kohm  -> ILM = {ilm:.3f} A "
          f"(range check 18k<= {r_ilim_k} <=100k : "
          f"{'OK' if 18 <= r_ilim_k <= 100 else 'OUT OF RANGE'})")
    print(f"OCP trip (2.4x ILM, DS 9.3.2) = {2.4 * ilm:.2f} A")

    # ---- 2. TPS2553 (U9..U12) per-port limit -----------------------------
    # DS SLVS841F Eq.1 (p.16), RILIM in kohm, IOS in mA, 15k..232k
    hdr("U9-U12 TPS2553 per-port current limit (R27-R30)")
    r_port_k = float(comps["R27"]["value"].rstrip("k"))
    ios_max = 22980 / (r_port_k ** 0.94)
    ios_nom = 23950 / (r_port_k ** 0.977)
    ios_min = 25230 / (r_port_k ** 1.016)
    print(f"RILIM = {r_port_k} kohm -> IOS min/nom/max = "
          f"{ios_min:.0f} / {ios_nom:.0f} / {ios_max:.0f} mA "
          f"(range check 15k<= {r_port_k} <=232k : "
          f"{'OK' if 15 <= r_port_k <= 232 else 'OUT OF RANGE'})")
    print("USB 2.0 high-power port needs >=500 mA: "
          f"{'OK' if ios_min >= 500 else 'MARGINAL'} (worst case {ios_min:.0f} mA)")

    # ---- 3. MIC29302 (U6) output voltage ---------------------------------
    # DS DS20005685A Table: VREF = 1.240 V typ (1.228 .. 1.252 V)
    hdr("U6 MIC29302WU adjustable output (R3 top / R4 bottom)")
    r_top = 30.1
    r_bot = 10.0
    for vref, tag in ((1.240, "typ"), (1.228, "min"), (1.252, "max")):
        print(f"  VREF={vref} V ({tag:3s}) -> VOUT = "
              f"{vref * (1 + r_top / r_bot):.3f} V")
    tol = 0.01
    vmin = 1.228 * (1 + (r_top * (1 - tol)) / (r_bot * (1 + tol)))
    vmax = 1.252 * (1 + (r_top * (1 + tol)) / (r_bot * (1 - tol)))
    print(f"  with +-1% divider resistors: VOUT = {vmin:.3f} .. {vmax:.3f} V")
    print(f"  USB port window 4.75..5.25 V at the connector: "
          f"{'headroom OK' if vmin > 4.75 else 'CHECK'}")

    # ---- 4. LDO dissipation ----------------------------------------------
    hdr("LDO dissipation")
    # U6: VIN = rectified secondary, VOUT = 4.972 V
    for vin, iout in ((6.0, 0.10), (6.0, 0.40), (6.5, 0.40)):
        print(f"  U6 MIC29302WU TO-263: VIN={vin} V IOUT={iout*1000:.0f} mA "
              f"-> Pd = {(vin - 4.972) * iout * 1000:.0f} mW")
    for iout in (0.10, 0.15, 0.20):
        print(f"  U8 AP2112K-3.3 SOT-23-5: VIN=5.0 V IOUT={iout*1000:.0f} mA "
              f"-> Pd = {(5.0 - 3.3) * iout * 1000:.0f} mW "
              f"(Tj rise @250 C/W = {(5.0-3.3)*iout*250:.0f} C)")

    # ---- 5. Crystal load capacitance -------------------------------------
    hdr("Crystal load capacitance")
    # Y1 / ADuM4165: caps C1=C2=8 pF. ADI gives no XI1/XO1 pin capacitance;
    # sweep a plausible pin+trace stray.
    for cs in (2.0, 4.0, 6.0, 8.0):
        print(f"  Y1 (C1=C2=8 pF, Cstray/side={cs} pF) -> "
              f"CL_eff = {(8.0 + cs) / 2:.1f} pF   [chosen crystal CL = 8 pF]")
    # Y2 / USB2514B: Microchip Fig 7-2 C1 = 2*(CL - C0) - CS1, CXTAL = 6 pF max
    for cb in (1.0, 2.0, 3.0):
        cs = 6.0 + cb
        print(f"  Y2 (C1=C2=18 pF, CXTAL=6 pF + CB={cb} pF) -> "
              f"CL_eff = {(18.0 + cs) / 2:.1f} pF   [chosen crystal CL = 12 pF; "
              f"Microchip-ideal C1 = {2*(12.0) - cs:.0f} pF]")
    # pulling error for a CL mismatch, Cm = 7 fF, C0 = 3 pF (typical 24 MHz AT)
    cm, c0 = 0.007, 3.0
    for cl_spec, cl_eff, tag in ((8.0, 6.0, "Y1 worst"), (8.0, 8.0, "Y1 nominal"),
                                 (12.0, 13.0, "Y2 typical")):
        ppm = cm / 2 * (1 / (c0 + cl_eff) - 1 / (c0 + cl_spec)) * 1e6
        print(f"  pull error {tag}: CL_spec={cl_spec} CL_eff={cl_eff} "
              f"-> {ppm:+.0f} ppm")

    # ---- 6. Downstream bulk capacitance vs USB 2.0 -----------------------
    hdr("Downstream bulk capacitance (USB 2.0 / TPS2553 DS: >=120 uF per hub)")
    total = 0.0
    for net in ("ISO_5V", "P1_VBUS", "P2_VBUS", "P3_VBUS", "P4_VBUS"):
        sub = 0.0
        for p in nets[net]["pins"]:
            c = comps.get(p["component"])
            if c and c.get("type") == "capacitor":
                v = c["value"].replace("u", "e-6").replace("n", "e-9").replace("p", "e-12")
                try:
                    sub += float(v) * 1e6
                except ValueError:
                    pass
        print(f"  {net:9s} {sub:7.2f} uF")
        total += sub
    print(f"  TOTAL nominal {total:.1f} uF  "
          f"({'MEETS' if total >= 120 else 'BELOW'} the 120 uF guidance, "
          f"before MLCC DC-bias derating)")

    # ---- 7. Isolated-side supply budget ----------------------------------
    hdr("Isolated-side supply headroom (bus-powered path)")
    print("  TI SLLSEP9I Table 9-3: SN6505B + Wurth 750313638, 1:1.3, "
          "5 V -> 5 V, 100 mA, LDO required -- an APPLICATION column entry, not a rating")
    print("  Wurth 750313638 datasheet typical-application table: IOut1 = 0.65 A")
    print("  Binding constraint is the host port's 500 mA obligation, not the magnetics:")
    print("  TI SLLSEP9I Fig 6-21/6-22 (p.10) 'SN6505B + Wurth 760390014, VCC = 5 V' "
          "- the electrically identical 1:1.3 5V->5V '100 mA' entry - sweeps load current to 200 mA")
    print("  Wurth 750313638 p.3 temperature-rise curve: push-pull output current axis "
          "runs to 1.2 A (~40 K at 0.65 A)")
    host_w = 0.500 * 5.0
    u1_side1_w = 0.070 * 5.0
    conv_w = (host_w - u1_side1_w) * 0.90
    for vraw in (5.8, 6.15, 6.2):
        i_raw = conv_w / vraw
        print(f"  host {host_w:.2f} W - U1 {u1_side1_w:.2f} W = "
              f"{host_w - u1_side1_w:.2f} W; x0.90 = {conv_w:.2f} W; "
              f"at DCDC_RAW {vraw} V -> {i_raw*1000:.0f} mA -> "
              f"ISO_5V ceiling ~{i_raw*1000 - 7:.0f} mA -> "
              f"{i_raw*1000 - 7 - 235:.0f} mA for four ports")

    # ---- 8. Transformer DCR headroom and PR1 cold-start level ------------
    hdr("T1 DCR headroom (Wurth p.1: RDC1 0.35 ohm, RDC2 0.33 ohm; SN6505B RON 0.25 ohm)")
    rdc1, rdc2, ron, n = 0.35, 0.33, 0.25, 1.3
    for iout, vf in ((0.315, 0.40), (0.635, 0.44)):
        ipri = n * iout
        vpri = 5.0 - ipri * (ron + rdc1 / 2)
        vraw = n * vpri - iout * (rdc2 / 2) - vf
        print(f"  IOUT={iout*1000:.0f} mA (Vf={vf} V): Ipri={ipri:.3f} A, "
              f"Vpri={vpri:.3f} V, DCDC_RAW={vraw:.2f} V "
              f"({'above' if vraw > 5.2 else 'BELOW'} the LDO's 5 V + dropout)")

    hdr("Q1 / PR1 lockout levels (TPS2121 VREF 1.06 V rising, 1.04 V falling)")
    r_top, r_bot = 100.0, 47.0          # R10 / R11, divider off EXT_5V
    v_pr1 = 5.0 * r_bot / (r_top + r_bot)
    print(f"  PR1 divider R10={r_top}k / R11={r_bot}k off EXT_5V -> {v_pr1:.3f} V "
          f"({'above' if v_pr1 > 1.06 else 'BELOW'} VREF) - fed from EXT_5V, "
          f"so it is independent of the mux output during cold start")
    print(f"  divider current = {5.0/((r_top+r_bot)*1e3)*1e6:.0f} uA -> Q1 must sink that "
          f"from a 3.3 V gate drive (2N7002 VGS(th) <= 2.5 V worst case)")
    print(f"  CP2 pull-up R9 100k with +-0.1 uA control-pin leakage -> "
          f"{0.1e-6*100e3*1000:.0f} mV drop; n3A_DET high = ~3.29 V >> 1.06 V")


if __name__ == "__main__":
    main()
