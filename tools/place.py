"""Task 4: placement. Coordinates in mm, board origin top-left, y increases down."""
import sys, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)

# ref: (x, y, rotation_deg)
PLACEMENT = {
    # --- barrier crossings: exact, from the design spec ---
    'U1':  (60.00, 25.00,   0),   # pads 1-10 at x=55.10, 11-20 at x=64.90
    'T1':  (60.00, 10.16,   0),   # pads at x=55.295/64.705, intrude 0.395 mm/side
    # Origin is pad 1, which carries GND2 -- so it must land on the ISOLATED side.
    # At rot 180 pad 1 sits at the origin and pad 2 (GND1) at origin-14.
    'CY1': (67.00, 38.02, 180),   # pad1 GND2 @ x=67, pad2 GND1 @ x=53

    # --- zone 1: J1 entrance (host) ---
    # Shifted 0.42 mm inboard from a flush 4.71: the shield pads otherwise reach
    # x=-0.110, i.e. 0.11 mm past the routed board edge. Mating face moves inboard
    # by the same 0.42 mm -- see the layout review note on constraint 6.
    'J1':  ( 5.13, 25.00,   0),
    'U2':  (12.50, 25.00,   0),
    'D5':  (16.80, 25.00,   0),
    'C3':  (16.80, 31.00,   0),

    # --- zone 2: ADuM Side 1, crystal, SN6505B (host) ---
    'C4':  (52.00, 18.00,  90),
    'C5':  (52.00, 32.00,  90),
    'Y1':  (34.00, 33.00,   0),
    'C1':  (30.00, 36.50,   0),
    'C2':  (38.00, 36.50,   0),
    'U4':  (34.00, 10.16,   0),
    'C6':  (40.00, 10.16,  90),
    'C7':  (44.00, 10.16,  90),
    'R1':  (10.00, 34.00,  90),
    'R2':  (10.00, 38.00,  90),

    # --- zone 4: rectifier, LDO, current-limit switch (isolated) ---
    'D1':  (72.00,  8.00,   0),   # side by side with D2 -- NOT in series
    'D2':  (72.00, 14.00,   0),
    'C8':  (80.00, 11.00,   0),
    'U5':  (87.00, 11.00,   0),
    'C9':  (94.00,  8.00,   0),
    'C10': (95.00, 14.00,   0),
    'U6':  (94.00, 25.00,   0),
    'R3':  (94.00, 31.00,  90),
    'C11': (89.00, 25.00,  90),
    'C12': (99.00, 25.00,  90),
    'D3':  (86.00, 40.00,   0),
    'D4':  (92.00, 40.00,   0),
    'R4':  (98.00, 40.00,  90),
    'R5':  (92.00, 44.00,  90),
    'R6':  (86.00, 44.00,  90),
    'Q1':  (80.00, 40.00,   0),
    'R9':  (74.00, 40.00,  90),
    'R10': (74.00, 44.00,  90),
    'C13': (70.00, 25.00,  90),
    'C14': (108.00, 33.00,  0),   # clear of J2's courtyard after its 0.42 mm inboard shift
    'C15': (104.00, 31.00,  0),

    # --- zone 5: J2 exit (isolated) ---
    'D6':  (103.20, 25.00,  0),
    'U3':  (107.50, 25.00,  0),
    'J2':  (114.87, 25.00, 180),   # same 0.42 mm inboard shift as J1

    # --- remaining passives ---
    'R7':  (112.00, 34.00, 90),
    'R8':  (112.00, 38.00, 90),
}

missing = []
for ref, (x, y, rot) in PLACEMENT.items():
    fp = b.FindFootprintByReference(ref)
    if fp is None:
        missing.append(ref)
        continue
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    fp.SetOrientationDegrees(rot)

unplaced = [f.GetReference() for f in b.GetFootprints() if f.GetReference() not in PLACEMENT]
print("placed: %d" % (len(PLACEMENT) - len(missing)))
if missing:
    print("  REF IN TABLE BUT NOT ON BOARD:", missing)
if unplaced:
    print("  ON BOARD BUT NOT IN TABLE:", unplaced)
if missing or unplaced:
    sys.exit(1)

# --- routed slot under T1: what converts 7.51 mm clearance into >= 8.3 mm creepage ---
# Starting geometry. Gate 1 is the authority -- widen or lengthen until it passes.
SLOT_W, SLOT_Y0, SLOT_Y1 = 2.0, 3.34, 16.98   # 2 mm beyond T1's pad rows each end
for x1, y1, x2, y2 in [(60 - SLOT_W / 2, SLOT_Y0, 60 + SLOT_W / 2, SLOT_Y0),
                       (60 + SLOT_W / 2, SLOT_Y0, 60 + SLOT_W / 2, SLOT_Y1),
                       (60 + SLOT_W / 2, SLOT_Y1, 60 - SLOT_W / 2, SLOT_Y1),
                       (60 - SLOT_W / 2, SLOT_Y1, 60 - SLOT_W / 2, SLOT_Y0)]:
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    s.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    b.Add(s)

# --- barrier keepout: excludes tracks/vias/pour, PERMITS pads ---
# T1's pads intrude 0.395 mm per side and are a permitted crossing, so a
# blanket no-copper rule area would reject the part it exists to accommodate.
z = pcbnew.ZONE(b)
z.SetIsRuleArea(True)
z.SetDoNotAllowTracks(True)
z.SetDoNotAllowVias(True)
z.SetDoNotAllowZoneFills(True)
z.SetDoNotAllowPads(False)
lset = pcbnew.LSET()
for lid in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
    lset.addLayer(lid)
z.SetLayerSet(lset)
pts = pcbnew.VECTOR_VECTOR2I()
for x, y in [(55.85, 0), (64.15, 0), (64.15, 50), (55.85, 50)]:
    pts.append(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
z.AddPolygon(pts)
b.Add(z)

pcbnew.SaveBoard(BOARD, b)
print("placement, T1 slot and barrier keepout written")
