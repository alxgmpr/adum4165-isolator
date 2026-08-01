"""Task 4: place the isolated side (plus the two host-side caps C6/C17).

COORDINATE FRAME
----------------
The table below is in **board-local mm**, origin at the outline's top-left,
y increasing down -- the same frame `tools/place.py` used. The board file
stores **absolute** coordinates; absolute = local + (86.88, 76.70). The
conversion happens once, in `place()`. Do not mix the two: the file's
`aux_axis_origin` (86.875, 126.7034) is the BOTTOM-left and is not this origin.

Reference landmarks, local mm:
    board outline      x 0..120, y 0..50
    copper band        y 2..48        (absolute 78.70..124.70)
    barrier keepout    x 55.84..64.15 (absolute 142.72..151.03), pads only
    U1 iso pad column  x 64.895       U1.20 local (64.895, 19.288)
    T1 iso pad column  x 64.700
    J2 pad column      x 110.820      J2 courtyard starts x 109.550

WHAT THIS TASK OVERTURNS FROM tools/place.py
--------------------------------------------
Nothing structural. J1/J2's 0.42 mm inboard shift, U1/T1/CY1 as the only
barrier crossings, and D1/D2 side-by-side rather than in series are all
preserved. What changes is that every decoupling capacitor now sits at the
pin it serves rather than on the right net somewhere, and the three net ties
that replaced the shared rails get real positions.

One ordering decision is deliberately overturned: place.py put C7 inboard of
C6 at U4's VCC pin. The schematic says the opposite and so does SN6505B Sec
10. C6 and C7 swap; see the note on them in the table below.

PLACEMENT REASONING
-------------------
Star points first -- their positions are topology decisions, everything else
hangs off a pin.

  NT2 (/DCDC_RECT -> /DCDC_RAW) sits east of C8 on the straight run between
      the reservoir cap and U5's input pins 5/8. The brief's first choice --
      the gap between the D1/D2 courtyards -- is not available here: D1 and
      D2 had to be pulled to 4.20 mm cathode pitch so C8 could meet its
      farther-of budget, which leaves 0.61 mm between their courtyards, less
      than the tie's 1.5 mm body. West pad faces C8, east pad faces U5.5.

  NT1 (/ISO_5V -> VBUS2 / SW / IND) sits south-east of U5, clear of C10 and
      C11 by 1.4 mm on every side. It is the only three-way split on the
      board and each branch leaves on a different side: pad 1 (in) north-west
      toward U5.1/C11, pad 2 (VBUS2) north-east then west down the empty
      y~92 corridor to C12/U1.20, pad 3 (SW) south to C16/U6.1, pad 4 (IND)
      south-east to the indicator strip.

  NT3 (/PORT_VBUS -> /PORT_VBUS_J2) sits in line east of C15, between U6's
      output and U3/J2, with 0.73 mm west and 2.03 mm east. The brief asked
      for it between U6 and the C14/C15 pair; that would push C15 to roughly
      3.7 mm from U6.6 against a 3.0 mm budget, so C15 keeps the pin and the
      tie moves outboard of it. C14 moves north instead of east, which keeps
      it inside its 6.0 mm budget and out of the tie's way.

Everything else is placed at a pin:

  C12 east of U1.20. U1.20 is 0.745 mm east of the barrier keepout, so there
      is no room west; C12's courtyard clears U1's by 0.41 mm to the east.
  C16 north of U6.1 with its hot pad facing the pin.
  C15/C14 east and north-east of U6.6, C15 nearer.
  C11 east of U5.1, C10 south of it and outboard.
  C9  directly south of U5.8. It read 3.48 mm against a 3.5 mm budget on the
      old board -- effectively zero margin. It now reads 1.85 mm.
  C8  east of the diode pair on the cathode centreline, so the farther-of
      distance is symmetric rather than hugging one diode.

The /PORT_D+- corridor is deliberately widened, not narrowed: C14 and C15
used to sit at y 103.6..107.1, directly in the run between U1.12/13 and J2's
A6/B6 A7/B7. Both move north of U6's row, leaving the band y 103.5..111 empty
from x 153 to 190 for Task 6 to length-match in.

The indicator cluster (R4-R6, D3, D4, Q1, R9, R10) and U3/D6/R7/R8 are left
exactly where they were.

COPPER THIS FILE TOUCHES BESIDES FOOTPRINTS
-------------------------------------------
Moving a footprint does not move the copper that was drawn around it, and this
board carries 261 zones including four GND1/GND2 plane pours and several small
F.Cu power pours. Two things therefore need cleaning up after the moves, and
both are done here rather than left for a later task to trip over:

  strip_vbus_host()     -- three track/via items orphaned by moving C6
  strip_stranded_pours() -- two F.Cu power pours left ringing the wrong pads

Of the 32 entries in PLACEMENT, 18 actually change position; the other 14
re-assert coordinates the board already had. Re-asserting them is deliberate --
it makes this file a complete record of where the isolated side sits, rather
than a diff against a state nobody has written down.

Usage:  <kicad python3> -u tools/place_iso.py isolator.kicad_pcb
"""
import sys, os, math, pcbnew

OFF_X, OFF_Y = 86.88, 76.70          # absolute = local + this

# ref: (local_x, local_y, rotation_deg)
PLACEMENT = {
    # --- host side ---
    # C6/C7 swap. C7 was originally frozen, but the ORDER rule "C6 inboard of
    # C7 at U4.2" is unsatisfiable with C7 at 2.0625 mm: U4's and C7's
    # courtyards leave a 0.080 mm gap on the only approach, and an exhaustive
    # sweep puts C6's floor at 2.1943 mm even with courtyards touching exactly.
    # Alex unfroze C7 (ruling recorded in task-4-report.md) on two grounds:
    # the freeze existed to protect working routing and Task 3 ripped
    # /VBUS_HOST entirely, so there is nothing to disturb; and the schematic
    # already specifies this arrangement -- C6's Description reads "place
    # immediately at U4 pin 2, inboard of C7", C7's reads "outboard of C6".
    # C6 takes C7's old slot (2.069 mm); C7 lifts ~3.5 mm north (2.619 mm,
    # inside its own 3.5 mm budget). This is the datasheet arrangement: the
    # 0.1 uF ceramic at the VCC pin, the bulk behind it.
    'C6':  (50.0525, 11.1034, -90),
    'C7':  (50.0525,  7.6000,  90),
    # C17 (bulk at T1's centre tap) has exactly one home: the 2.27 mm slot
    # between C7's courtyard and T1's. It is 2.05 mm wide on its side, so the
    # rotation is forced and the x position is forced to within 0.11 mm.
    'C17': (52.214, 12.800,  -90),

    # --- zone 4: rectifier -> reservoir -> LDO (isolated, northern strip) ---
    'D1':  (71.320,  7.400,  180),   # side by side with D2 -- NOT in series
    'D2':  (71.320, 11.600,  180),   # 4.20 mm cathode pitch, 0.61 mm courtyard gap
    'C8':  (77.720,  9.500,    0),   # on the cathode centreline y = local 9.50
    'NT2': (81.820,  9.500,    0),   # /DCDC_RECT (W) -> /DCDC_RAW (E)
    'U5':  (86.720, 10.500,  180),   # rot 180 puts inputs 5/8 west, output 1/2 east
    'C9':  (84.570, 14.100,  -90),   # under U5.8
    'C11': (91.820, 11.475,    0),   # at U5.1
    'C10': (91.220, 14.500,    0),   # outboard of C11
    'NT1': (91.620, 18.300,    0),   # /ISO_5V -> VBUS2 / SW / IND

    # --- zone 4b: current-limit switch and its output (isolated) ---
    'C16': (92.8575, 21.300,  90),   # at U6.1, hot pad facing the pin
    'R3':  (95.420, 21.200,   90),   # ILIM_SET, north-east of U6
    'C15': (98.120, 24.0534,   0),   # at U6.6
    'C14': (100.120, 21.100,   0),   # outboard of C15, north of the D+- corridor
    'NT3': (101.120, 24.0534,  0),   # /PORT_VBUS (W) -> /PORT_VBUS_J2 (E)

    # --- ADuM side 2 decoupling (isolated) ---
    'C12': (67.870, 19.2884,   0),   # at U1.20, east -- the barrier blocks west
    'C13': (68.120, 21.800,    0),   # at U1.18, unchanged (2.45 mm)

    # --- unchanged: U6, U3, exit diode, CC resistors ---
    'U6':  (93.995, 25.0034,   0),
    'U3':  (105.995, 25.0034,  0),
    'D6':  (108.220, 28.175, -90),
    'R7':  (111.120, 31.200, 180),
    'R8':  (114.495, 31.200, 180),

    # --- unchanged: indicator cluster in the southern strip ---
    'R9':  (67.370, 24.350,  -90),
    'R10': (76.420, 40.000,  -90),
    'Q1':  (79.995, 40.0034,   0),
    'D3':  (85.995, 40.0034,   0),
    'D4':  (91.995, 40.0034,   0),
    'R4':  (97.995, 40.0034,  90),
    'R5':  (91.995, 44.0034,  90),
    'R6':  (85.995, 44.0034,  90),
}


def place(board):
    missing = []
    for ref, (x, y, rot) in sorted(PLACEMENT.items()):
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            missing.append(ref)
            continue
        ax, ay = x + OFF_X, y + OFF_Y
        fp.SetPosition(pcbnew.VECTOR2I(int(round(ax * 1e6)), int(round(ay * 1e6))))
        fp.SetOrientationDegrees(rot)
        print('  %-5s local (%8.3f, %8.3f) rot %6.1f  ->  absolute (%9.4f, %9.4f)'
              % (ref, x, y, rot, ax, ay))
    return missing


def strip_vbus_host(board):
    """Remove all /VBUS_HOST copper. Task 3 ripped that net and Task 5 routes
    it from scratch, so the invariant at the end of this task is zero.

    Moving C6 re-netted three items GND1 -> /VBUS_HOST: a stub from C6's OLD
    ground pad at (138.7325, 88.5784) absolute down to a stitching via at
    (138.7250, 89.4500), plus the jog between them. That was C6's pad-to-plane
    ground drop; C6 is no longer there, so it connects nothing. It only reads
    as /VBUS_HOST because C17's pad 1 now overlaps its endpoint and pcbnew
    re-derived the net from the pad sitting on it. DRC called it an
    unconnected item rather than a short, and GND1's plane still covers the
    region, but it is an artifact rather than routing anyone designed --
    leaving it would hand Task 5 a via of unknown provenance on the only
    /VBUS_HOST copper on the board.
    """
    doomed = [t for t in board.GetTracks() if t.GetNetname() == '/VBUS_HOST']
    for t in doomed:
        kind = 'via  ' if t.Type() == pcbnew.PCB_VIA_T else 'track'
        p = t.GetPosition()
        print('  removed %s on /VBUS_HOST at (%9.4f, %9.4f)'
              % (kind, p.x / 1e6, p.y / 1e6))
        board.Remove(t)
    return len(doomed)


# F.Cu local power pours that this task's moves stranded: (net, outline bbox mm).
# Matched on net + geometry rather than uuid -- pcbnew's m_Uuid.AsString() returned
# two different strings for the same zone across two runs of the same script, so
# the uuid is not a usable handle here.
STRANDED_POURS = [
    ('/ISO_5V',   (171.000, 175.000, 86.000, 89.250)),
    ('/DCDC_RAW', (158.800, 166.500, 81.750, 91.500)),
]


def strip_stranded_pours(board):
    """Delete the two F.Cu pours that this task's moves left stranded.

    Both were drawn around the OLD positions and both were healthy at 26911ea:
    the /ISO_5V pour contained U5.1, U5.2 and C10.1; the /DCDC_RAW pour
    contained C9.1. Moving U5 east and C9/C10/C11 off them stranded both --
    these are this task's doing, not Task 3 residue.

    What they cover now is the problem. The /ISO_5V outline sits over U5's
    GND2 thermal pad (pad 9, entirely inside), U5.6 (GND2) and U5.5/U5.8
    (/DCDC_RAW, the raw input) -- an /ISO_5V outline ringing an LDO's ground
    pad and its input. The /DCDC_RAW outline sits over D1.1, D2.1 and C8.1
    (all /DCDC_RECT) plus C8.2 (GND2). Neither contains a single pad of its
    own net, and between them they carry 60 mm2 of stale fill.

    Deleted rather than redrawn, for the same reason the orphaned /VBUS_HOST
    stub was deleted: Task 3 ripped all isolated-side copper and Task 5 routes
    these nets from scratch. Redrawing a pour now means authoring copper
    geometry for routing that does not exist yet -- a placement task guessing
    at a routing task's output, which Task 5 would then have to redraw anyway.
    These two zones are isolated-side copper that Task 3's rip-up missed;
    removing them finishes that job and leaves Task 7's refill nothing stale
    to reason about. It also removes the reliance on "island_removal should
    make it vanish at fill time", which is true but is not a state worth
    handing on undocumented.

    The four GND1/GND2 plane zones on GND_SPLIT_A/B and both /RECT_A pours are
    healthy and are left alone.

    Caveat on the safety guard below, considered and accepted: it tests whether
    a pad's CENTRE falls inside the outline, so a pad whose centre sits outside
    but whose copper still clips the edge would not trip it. That is fine for
    the two zones named here -- neither has any pad of its own net within
    millimetres -- but if this function is ever pointed at a pour that hugs its
    pads, tighten the test to pad-shape collision first.
    """
    removed = 0
    for net, (bx0, bx1, by0, by1) in STRANDED_POURS:
        hits = []
        for z in board.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != net:
                continue
            bb = z.Outline().BBox()
            if (abs(pcbnew.ToMM(bb.GetLeft()) - bx0) < 0.01
                    and abs(pcbnew.ToMM(bb.GetRight()) - bx1) < 0.01
                    and abs(pcbnew.ToMM(bb.GetTop()) - by0) < 0.01
                    and abs(pcbnew.ToMM(bb.GetBottom()) - by1) < 0.01):
                hits.append(z)
        if not hits:
            print('  stranded %s pour already absent -- nothing to do' % net)
            continue
        if len(hits) > 1:
            print('  ABORT: expected at most 1 stranded %s pour at that outline, '
                  'found %d' % (net, len(hits)))
            sys.stdout.flush()
            os._exit(1)
        z = hits[0]
        # refuse to delete a pour that still has a pad of its own net in it
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net and z.Outline().Collide(p.GetPosition()):
                    print('  ABORT: %s pour still contains %s.%s -- not stranded'
                          % (net, fp.GetReference(), p.GetNumber()))
                    sys.stdout.flush()
                    os._exit(1)
        print('  removed stranded %-10s pour  x %.3f..%.3f y %.3f..%.3f  (%.3f mm2 fill)'
              % (net, bx0, bx1, by0, by1, z.GetFilledArea() / 1e12))
        board.Remove(z)
        removed += 1
    return removed


def main():
    path = sys.argv[1]
    board = pcbnew.LoadBoard(path)
    missing = place(board)
    if missing:
        print('  REF IN TABLE BUT NOT ON BOARD:', missing)
        sys.stdout.flush()
        os._exit(1)
    n = strip_vbus_host(board)
    z = strip_stranded_pours(board)
    pcbnew.SaveBoard(path, board)
    print('placed %d footprints (18 moved, 14 re-asserted), removed %d orphaned '
          '/VBUS_HOST items and %d stranded pours' % (len(PLACEMENT), n, z))
    sys.stdout.flush()
    os._exit(0)


if __name__ == '__main__':
    main()
