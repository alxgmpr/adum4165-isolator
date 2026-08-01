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

Usage:  <kicad python3> -u tools/place_iso.py isolator.kicad_pcb
"""
import sys, os, math, pcbnew

OFF_X, OFF_Y = 86.88, 76.70          # absolute = local + this

# ref: (local_x, local_y, rotation_deg)
PLACEMENT = {
    # --- host side: the only two host parts this task may touch ---
    # C6 as close to U4.2 as U4's and C7's courtyards permit. See the report:
    # the ORDER rule (C6 inboard of C7) is not satisfiable with C7 frozen.
    'C6':  (50.570,  8.500,    0),
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


def main():
    path = sys.argv[1]
    board = pcbnew.LoadBoard(path)
    missing = place(board)
    if missing:
        print('  REF IN TABLE BUT NOT ON BOARD:', missing)
        sys.stdout.flush()
        os._exit(1)
    pcbnew.SaveBoard(path, board)
    print('placed %d footprints' % len(PLACEMENT))
    sys.stdout.flush()
    os._exit(0)


if __name__ == '__main__':
    main()
