"""Placement corrections found during routing.

U5 (LDO) was rotated 180: its DCDC_RAW input pins sat in the column facing AWAY
from the rectifier and C8, while its ISO_5V output pins faced away from C10, so
both nets had to wrap around the package and thread past the NC pins. Rotating it
puts input beside input and output beside output.

C9 is U5's input bulk cap and followed the input to the left-hand side.

D6 sat between the two halves of the differential pair (D+ at y=24.050, D- at
y=25.950), boxed in with under 0.7 mm either side, so PORT_VBUS could not escape
it without crossing the pair.
"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM
b.FindFootprintByReference('U5').SetOrientationDegrees(180)
b.FindFootprintByReference('D6').SetPosition(
    pcbnew.VECTOR2I(pcbnew.FromMM(103.200), pcbnew.FromMM(29.000)))
b.FindFootprintByReference('C9').SetPosition(
    pcbnew.VECTOR2I(pcbnew.FromMM(81.000), pcbnew.FromMM(7.000)))
for r in ('U5', 'D6', 'C9'):
    f = b.FindFootprintByReference(r)
    print("  %-3s (%8.3f,%8.3f) rot %.0f" % (r, M(f.GetPosition().x), M(f.GetPosition().y),
                                             f.GetOrientationDegrees()))
pcbnew.SaveBoard(sys.argv[1], b)
