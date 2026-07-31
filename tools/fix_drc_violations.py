"""Fix the two DRC violation classes left after the host-side routing pass.

1. hole_to_hole: the four HOST_D+/HOST_D- crossover vias sit on a 0.7 mm
   horizontal pitch. With 0.3 mm drills that is a 0.400 mm hole gap against a
   0.4995 mm minimum. Spread the two columns to a 0.9 mm pitch (0.600 mm gap).
   Vertical pitch is 0.8 mm (0.500 mm gap) and already passes, so only x moves.
   Every track endpoint sitting on a moved via moves with it, or the crossover
   comes apart.

2. clearance: the /VBUS_HOST run threads between R2's two pads. The channel is
   0.850 mm (pad 1 bottom 28.575, pad 2 top 29.425); a 0.5 mm track needs
   0.800 mm, so there is 0.05 mm of slack in total. The track sits at y=28.952,
   hard against pad 1 at 0.127 mm. Centre it at y=29.000 for 0.175 mm on both
   sides.
"""
import sys, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)
MM, IU = pcbnew.ToMM, pcbnew.FromMM
EPS = 0.0005

# ---------- 1. via cluster ----------
REGION = (23.0, 24.0, 25.4, 25.7)          # x0, y0, x1, y1
XMAP = {23.800: 23.700, 24.500: 24.600}    # old x -> new x


def in_region(x, y):
    return REGION[0] < x < REGION[2] and REGION[1] < y < REGION[3]


def remap_x(x, y):
    if not in_region(x, y):
        return None
    for old, new in XMAP.items():
        if abs(x - old) < EPS:
            return new
    return None


moved_vias = moved_ends = 0
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        nx = remap_x(MM(p.x), MM(p.y))
        if nx is not None:
            t.SetPosition(pcbnew.VECTOR2I(IU(nx), p.y))
            moved_vias += 1
    else:
        for getter, setter in ((t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)):
            p = getter()
            nx = remap_x(MM(p.x), MM(p.y))
            if nx is not None:
                setter(pcbnew.VECTOR2I(IU(nx), p.y))
                moved_ends += 1

print("via cluster: %d vias and %d track endpoints moved" % (moved_vias, moved_ends))

# ---------- 2. VBUS_HOST channel between R2's pads ----------
OLD_Y, NEW_Y = 28.952, 29.000
XLO, XHI = 9.9, 14.0
moved_seg = 0
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA' or t.GetNetname() != '/VBUS_HOST':
        continue
    for getter, setter in ((t.GetStart, t.SetStart), (t.GetEnd, t.SetEnd)):
        p = getter()
        x, y = MM(p.x), MM(p.y)
        if abs(y - OLD_Y) < EPS and XLO < x < XHI:
            setter(pcbnew.VECTOR2I(p.x, IU(NEW_Y)))
            moved_seg += 1

print("VBUS_HOST channel: %d endpoints moved from y=%.3f to y=%.3f" % (moved_seg, OLD_Y, NEW_Y))

pcbnew.SaveBoard(BOARD, b)
print("saved")
