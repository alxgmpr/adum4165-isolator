"""Round the ground pours' outer corners so copper-to-edge clearance is constant.

The pours were rectangles inset 2 mm from the board's NOMINAL square corners. With
a 6.2 mm corner radius the board edge curves away from that square corner, so the
pour crowded the arc: measured 0.605 mm at the bottom-left against 2 mm along the
straight edges.

An inward offset of a circular arc is a concentric arc, so the fix is exact: each
outer pour corner becomes an arc of radius (board_R - inset) about the SAME centre
as the board's corner arc. Every point of the pour boundary is then `inset` from
the board edge, corners included.

The inner edges facing the isolation barrier are left alone -- they are set by the
barrier keepout, not by the outline.
"""
import sys, math, pcbnew

BOARD = sys.argv[1]
INSET = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
BOARD_R = float(sys.argv[3]) if len(sys.argv) > 3 else 6.2
SEGS = 16                      # segments per quarter arc

b = pcbnew.LoadBoard(BOARD)
IU, MM = pcbnew.FromMM, pcbnew.ToMM
R = BOARD_R - INSET

bb = b.GetBoardEdgesBoundingBox()
x0, y0 = MM(bb.GetLeft()) + 0.05, MM(bb.GetTop()) + 0.05
x1, y1 = MM(bb.GetRight()) - 0.05, MM(bb.GetBottom()) - 0.05
# centres of the board's corner arcs
CTL = (x0 + BOARD_R, y0 + BOARD_R)
CTR = (x1 - BOARD_R, y0 + BOARD_R)
CBL = (x0 + BOARD_R, y1 - BOARD_R)
CBR = (x1 - BOARD_R, y1 - BOARD_R)
print("board x %.3f..%.3f y %.3f..%.3f, corner R=%.2f -> pour corner R=%.2f at inset %.2f"
      % (x0, x1, y0, y1, BOARD_R, R, INSET))


def arc_pts(c, a_from, a_to):
    out = []
    for i in range(SEGS + 1):
        t = math.radians(a_from + (a_to - a_from) * i / SEGS)
        out.append((c[0] + R * math.cos(t), c[1] + R * math.sin(t)))
    return out


def left_outline(inner_x):
    """Host-side pour: rounded at the two LEFT corners, square at the barrier."""
    pts = [(CTL[0], y0 + INSET)]                       # top edge, tangent point
    pts += [(inner_x, y0 + INSET), (inner_x, y1 - INSET)]
    pts += [(CBL[0], y1 - INSET)]                      # bottom edge, tangent point
    pts += arc_pts(CBL, 90, 180)                       # bottom-left
    pts += arc_pts(CTL, 180, 270)                      # top-left
    return pts


def right_outline(inner_x):
    """Isolated-side pour: rounded at the two RIGHT corners."""
    pts = [(inner_x, y0 + INSET), (CTR[0], y0 + INSET)]
    pts += arc_pts(CTR, 270, 360)                      # top-right
    pts += arc_pts(CBR, 0, 90)                         # bottom-right
    pts += [(inner_x, y1 - INSET)]
    return pts


done = 0
for z in b.Zones():
    if z.GetIsRuleArea():
        continue
    o = z.Outline().Outline(0)
    if o.PointCount() != 4:
        continue                                       # only the big rectangles
    xs = [MM(o.CPoint(i).x) for i in range(4)]
    ys = [MM(o.CPoint(i).y) for i in range(4)]
    if max(ys) - min(ys) < 40:
        continue                                       # not a full-height pour
    left = min(xs) < (x0 + x1) / 2
    inner = max(xs) if left else min(xs)
    pts = left_outline(inner) if left else right_outline(inner)
    z.RemoveAllContours()
    vv = pcbnew.VECTOR_VECTOR2I()
    for px, py in pts:
        vv.append(pcbnew.VECTOR2I(IU(px), IU(py)))
    z.AddPolygon(vv)
    done += 1
    print("  %-12s %-5s -> %d pts, %s corners rounded"
          % (b.GetLayerName(z.GetLayer()), z.GetNetname(), len(pts), 'left' if left else 'right'))

print("pours reshaped:", done)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print("saved")
