# Rev C mechanical and isolation handoff

The provisional bench board is **136 × 116 mm**, nominal 1.6 mm thick, with
3 mm corner radii. All components are on top. Four 3.2 mm NPTH holes are at
(5,5), (131,5), (5,111), (131,111) mm from the upper-left outline datum.
A 3.2 mm radius around each center is reserved for M3 hardware. Use nylon
hardware and a plastic enclosure; no common metal mounting plate is assumed.
No specific enclosure or panel cutout has been qualified.

| Connector | Center/rotation in PCB | Mating direction |
|---|---|---|
| J1 host USB-C | (3.15,76), 270° | Left |
| J2 external-power USB-C | (92,3.15), 180° | Top |
| J3 USB-A port 1 | (124.17,20), 180° | Right |
| J4 USB-A port 2 | (124.17,46), 180° | Right |
| J5 USB-C port 3 | (132.85,77), 90° | Right |
| J6 USB-C port 4 | (132.85,102), 90° | Right |

Connector mating faces project nominally 0.5 mm beyond the outline. The USB-A
maximum body envelope can extend about 0.65 mm. These are placement datums,
not completed panel cutouts. The selected USB-A sockets are upright right-angle
parts; reserve **15 mm above PCB**. Start with **5 mm below PCB** for soldered
through-hole leads and standoff clearance, then verify actual assembled lead
protrusion and plug envelopes. Cable strain relief and the enclosure wall need
an independent fit check.

SH1 BMI-S-201-F is centered at (27.5,28), grounded only to GND1. Its conservative
outer envelope is 12.8 × 13.76 mm. SH2 BMI-S-209-F is at (65,28), grounded only
to GND2, envelope 29.46 × 18.6 mm. Their edge-to-edge separation is **16.37 mm**.
Order BMI-S-201-C and BMI-S-209-C separately as recorded in `BOM-covers.csv`.
The 3D render shows open frames; the covers are not modeled as installed solids.
`reports/mechanical.json` lists enclosed parts and height margins against
conservative lid underside assumptions of 2.44 mm and 6.80 mm respectively.
Verify received lid/formed-tab dimensions before final enclosure design.

T1 is centered at (42,28), outside both frames. Its 7.62 mm maximum height
would not fit under SH1. The selected 1210 capacitors reserve 2.7 mm maximum
height and fit under SH2. No body/frame interference is found in the placed
courtyard check and reviewed top/isometric views. Generic models are explicitly
identified in `footprint-verification.md` and `body-envelopes.json`; dimensions
and the manufacturer land drawings take precedence over cosmetic models.

The HRO and T1 STEP origins were translated and rotated into the footprint
datums. Their original geometry used a vertical axis different from the PCB
coordinate system. These alignment corrections do not alter lands, drills or
manufacturer dimensions. The USB-A body is a dimensioned envelope, not a detailed
assembly STEP. All model references resolve locally.

## Complete barrier

The primary region is left of x=37.85 mm, the secondary right of x=46.15 mm.
The all-layer keepout is 8.30 mm wide, locally reduced to 8.20 mm at U1's exact
manufacturer HV land gap. U1 is centered at (42,76). The independent physical
pad audit measures **8.200 mm** across U1 and **9.410 mm** at T1, the next-smallest
cross-domain pad gap. CY1 uses 14 mm formed leads with a 12 mm pad-edge gap;
it is the only intentional GND1–GND2 capacitance. Do not substitute its 10 mm
lead variant. No slot is needed to manufacture a larger claim than the verified
T1 pad gap; no slots are included.

TI specifies greater than 8.15 mm package clearance/creepage for U1. The nominal
PCB land gap has fabrication and solder tolerances. Shield shells, connector
metal, hardware, T1 insulation, CY1 approvals, board contamination, altitude,
material group and final enclosure all constrain the complete insulation system.
This deliverable assigns **no certified board working-voltage or withstand
rating**. It is a low-voltage prototype routing handoff; any future insulation
qualification requires a defined application and separate test plan.

Sources and exact mechanical drawings are linked in
[footprint-verification.md](footprint-verification.md).

CY1's supplied STEP has its disc centered at Z=0 and untrimmed leads. The local
model is raised 4 mm so the 7 mm disc sits 0.5 mm above the board, with its top
at 7.5 mm. Its raw lead ends extend below the PCB; trim formed leads to no more
than 3 mm below the assembled board for the provisional 5 mm underside space.
Lead bending/soldering must preserve the selected 14 mm pitch and barrier gap.
