"""Give the mounting holes an even border by making them concentric with the
board's corner arcs.

The border cannot be made even at the present geometry. The hole's pad radius is
3.2 mm and the corner radius was 3.0 mm; with the pad larger than the corner,
every position on the 45-degree diagonal leaves the arc further from the pad than
the straight edges are, so the gap is always wider at the corner than along the
edges.

It becomes exact when the corner radius equals the hole inset and the hole sits at
the arc centre: the distance from that centre to the arc is R, and to each
adjacent straight edge is also R, so subtracting the pad radius leaves the same
border in every direction. Hence R = pad_radius + border.

Rebuilds the perimeter as four straight segments plus four arcs at the new
radius, keeping the board's size and position exactly. The T1 barrier slot is an
interior cutout and is left untouched.
"""
import sys, math, pcbnew

BOARD = sys.argv[1]
BORDER = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
STAGE = sys.argv[3] if len(sys.argv) > 3 else 'all'
PAD_R = 3.2
R = PAD_R + BORDER

b = pcbnew.LoadBoard(BOARD)
IU, MM = pcbnew.FromMM, pcbnew.ToMM

bb = b.GetBoardEdgesBoundingBox()
x0, y0 = MM(bb.GetLeft()) + 0.05, MM(bb.GetTop()) + 0.05
x1, y1 = MM(bb.GetRight()) - 0.05, MM(bb.GetBottom()) - 0.05
print("board: x %.3f..%.3f  y %.3f..%.3f  (%.2f x %.2f)  new corner R=%.2f, border=%.2f"
      % (x0, x1, y0, y1, x1 - x0, y1 - y0, R, BORDER))

if STAGE in ('all', 'strip'):
  # --- drop the old perimeter, keep interior cutouts (the T1 slot) ---
M = 0.5
removed = kept = 0
_keep = []   # hold removed objects so Python does not free them
for d in list(b.GetDrawings()):
    if d.GetLayer() != pcbnew.Edge_Cuts:
        continue
    q = d.GetBoundingBox()
    ix0, iy0 = MM(q.GetLeft()), MM(q.GetTop())
    ix1, iy1 = MM(q.GetRight()), MM(q.GetBottom())
    interior = (ix0 > x0 + M and iy0 > y0 + M and ix1 < x1 - M and iy1 < y1 - M)
    if interior:
        kept += 1
    else:
        b.Remove(d)
        _keep.append(d)
        removed += 1
print("perimeter items removed: %d, interior cutouts kept: %d" % (removed, kept))


def seg(ax, ay, cx, cy):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(IU(ax), IU(ay)))
    s.SetEnd(pcbnew.VECTOR2I(IU(cx), IU(cy)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(IU(0.1))
    b.Add(s)


def arc(cx, cy, a_start, a_end):
    """Arc of radius R about (cx, cy), angles in degrees, CCW in screen terms."""
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    p0 = (cx + R * math.cos(math.radians(a_start)), cy + R * math.sin(math.radians(a_start)))
    p1 = (cx + R * math.cos(math.radians(a_end)), cy + R * math.sin(math.radians(a_end)))
    mid = (a_start + a_end) / 2.0
    pm = (cx + R * math.cos(math.radians(mid)), cy + R * math.sin(math.radians(mid)))
    # KiCad 10 exposes SetArcGeometry(start, mid, end); there is no SetArcMid.
    s.SetArcGeometry(pcbnew.VECTOR2I(IU(p0[0]), IU(p0[1])),
                     pcbnew.VECTOR2I(IU(pm[0]), IU(pm[1])),
                     pcbnew.VECTOR2I(IU(p1[0]), IU(p1[1])))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(IU(0.1))
    b.Add(s)


# straight edges between the tangent points
seg(x0 + R, y0, x1 - R, y0)          # top
seg(x0 + R, y1, x1 - R, y1)          # bottom
seg(x0, y0 + R, x0, y1 - R)          # left
seg(x1, y0 + R, x1, y1 - R)          # right
# corner arcs, centres at the hole positions
arc(x0 + R, y0 + R, 180, 270)        # top-left
arc(x1 - R, y0 + R, 270, 360)        # top-right
arc(x1 - R, y1 - R, 0, 90)           # bottom-right
arc(x0 + R, y1 - R, 90, 180)         # bottom-left
print("perimeter rebuilt: 4 segments + 4 arcs")

# --- holes concentric with the arcs ---
# FindFootprintByReference can hand back an unwrapped SwigPyObject on this
# build; iterating GetFootprints() gives properly wrapped FOOTPRINTs.
by_ref = {f.GetReference(): f for f in b.GetFootprints()}
for ref, cx, cy in (('H1', x0 + R, y0 + R), ('H2', x0 + R, y1 - R),
                    ('H3', x1 - R, y0 + R), ('H4', x1 - R, y1 - R)):
    f = by_ref[ref]
    f.SetPosition(pcbnew.VECTOR2I(IU(cx), IU(cy)))
    print("  %-3s -> board (%6.2f, %6.2f)   border %.2f mm to arc and to both edges"
          % (ref, cx - x0, cy - y0, R - PAD_R))

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print("saved")
