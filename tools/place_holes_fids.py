"""Position the mounting holes and fiducials in the board corners.

Constraints, in order of authority:

- Copper pullback (constraint 2). H1-H4 carry a 6.4 mm GND pad, which is copper,
  so the pad edge -- not the hole centre -- must stay >= 2 mm from both LONG
  edges. That puts the centre at least 5.2 mm in, which is as "corner" as a
  6.4 mm pad can legally get on a 50 mm board.
- Barrier (constraint 4). H1/H2 are GND1 and H3/H4 are GND2, so the GND1 pair
  must stay entirely host-side of the barrier and the GND2 pair entirely
  isolated-side. A GND1 pad drifting past the barrier would bridge the domains.
- Corner radii. The board now has 3 mm corner arcs, so clearance near a corner is
  measured to the arc centre, not to a square corner.
- Everything else: no overlap with existing pads, vias, tracks or courtyards.

Each part is placed at the position closest to its corner that satisfies all of
the above, found by search rather than by hand-picked coordinates.
"""
import sys, math, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)
IU, MM = pcbnew.FromMM, pcbnew.ToMM

PULLBACK = 2.0        # from the long edges, constraint 2 target
END_CLEAR = 0.5       # from the short end edges (fab rule is 0.3)
CORNER_R = 3.0
CLEAR = 0.30          # to other nets' copper
FID_CLEAR = 1.00      # copper-free ring wanted around a fiducial

bx0, by0, bx1, by1 = (MM(b.GetBoardEdgesBoundingBox().GetLeft()),
                      MM(b.GetBoardEdgesBoundingBox().GetTop()),
                      MM(b.GetBoardEdgesBoundingBox().GetRight()),
                      MM(b.GetBoardEdgesBoundingBox().GetBottom()))
# outline centrelines, allowing for the 0.1 mm edge line width
bx0 += 0.05; by0 += 0.05; bx1 -= 0.05; by1 -= 0.05
print("board outline: x %.3f..%.3f  y %.3f..%.3f  (%.2f x %.2f)"
      % (bx0, bx1, by0, by1, bx1 - bx0, by1 - by0))

# barrier keepout, taken from the rule area rather than assumed
barrier = None
for z in b.Zones():
    if z.GetIsRuleArea():
        bb = z.GetBoundingBox()
        w = MM(bb.GetRight()) - MM(bb.GetLeft())
        h = MM(bb.GetBottom()) - MM(bb.GetTop())
        if w < 20 and h > 40:
            barrier = (MM(bb.GetLeft()), MM(bb.GetRight()))
print("barrier keepout x: %s" % (("%.3f..%.3f" % barrier) if barrier else "not found"))

MOVERS = {'H1', 'H2', 'H3', 'H4', 'FID1', 'FID2', 'FID3', 'FID4'}


def obstacles():
    pads, vias, segs, courts = [], [], [], []
    for f in b.GetFootprints():
        if f.GetReference() in MOVERS:
            continue
        for p in f.Pads():
            bb = p.GetBoundingBox()
            pads.append((MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()),
                         MM(bb.GetBottom()), p.GetNetname()))
        cy = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
        courts.append((MM(cy.GetLeft()), MM(cy.GetTop()), MM(cy.GetRight()), MM(cy.GetBottom())))
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            vias.append((MM(p.x), MM(p.y), MM(t.GetWidth()) / 2, t.GetNetname()))
        else:
            s, e = t.GetStart(), t.GetEnd()
            segs.append((MM(s.x), MM(s.y), MM(e.x), MM(e.y),
                         MM(t.GetWidth()) / 2, t.GetNetname()))
    return pads, vias, segs, courts


PADS, VIAS, SEGS, COURTS = obstacles()


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def inside_board(cx, cy, r, pullback):
    """Circle of radius r fits inside the rounded-rectangle outline, keeping
    `pullback` from the long edges and END_CLEAR from the short ends.

    The board is a rounded rectangle: near a corner the boundary is an arc of
    radius CORNER_R whose centre is inboard at (bx0+R, by0+R) etc. A point is in
    that corner's quadrant only when it is within R of BOTH edges; there the
    limit is the arc, everywhere else it is the straight edge.
    """
    if not (by0 + pullback + r <= cy <= by1 - pullback - r):
        return False
    if not (bx0 + END_CLEAR + r <= cx <= bx1 - END_CLEAR - r):
        return False
    for ax, ay in ((bx0 + CORNER_R, by0 + CORNER_R), (bx1 - CORNER_R, by0 + CORNER_R),
                   (bx0 + CORNER_R, by1 - CORNER_R), (bx1 - CORNER_R, by1 - CORNER_R)):
        in_quadrant = ((cx < ax) if ax - bx0 < bx1 - ax else (cx > ax)) and \
                      ((cy < ay) if ay - by0 < by1 - ay else (cy > ay))
        if not in_quadrant:
            continue
        if math.hypot(cx - ax, cy - ay) + r + min(END_CLEAR, pullback) > CORNER_R:
            return False
    return True


def clear_of_copper(cx, cy, r, net, extra=CLEAR):
    for x0, y0, x1, y1, n in PADS:
        if n == net:
            continue
        dx = max(x0 - cx, 0, cx - x1)
        dy = max(y0 - cy, 0, cy - y1)
        if math.hypot(dx, dy) < r + extra:
            return False
    for vx, vy, vr, n in VIAS:
        if n == net:
            continue
        if math.hypot(cx - vx, cy - vy) < r + vr + extra:
            return False
    for x1, y1, x2, y2, hw, n in SEGS:
        if n == net:
            continue
        if seg_dist(cx, cy, x1, y1, x2, y2) < r + hw + extra:
            return False
    return True


def clear_of_courtyards(cx, cy, r):
    for x0, y0, x1, y1 in COURTS:
        dx = max(x0 - cx, 0, cx - x1)
        dy = max(y0 - cy, 0, cy - y1)
        if math.hypot(dx, dy) < r:
            return False
    return True


def side_ok(cx, r, net):
    if barrier is None:
        return True
    if net == 'GND1':
        return cx + r < barrier[0]
    if net == 'GND2':
        return cx - r > barrier[1]
    return True


placed = []


def place(ref, corner, r, net, pullback, extra):
    """Search outward from the corner for the closest legal spot."""
    tx = bx0 if corner[0] == 'L' else bx1
    ty = by0 if corner[1] == 'T' else by1
    best = None
    step = 0.25
    lo = pullback + r
    for di in range(0, 160):
        d = lo + di * step
        for dj in range(0, 160):
            e = END_CLEAR + r + dj * step
            cx = tx + e if corner[0] == 'L' else tx - e
            cy = ty + d if corner[1] == 'T' else ty - d
            if not inside_board(cx, cy, r, pullback):
                continue
            if not side_ok(cx, r, net):
                continue
            if not clear_of_copper(cx, cy, r, net, extra):
                continue
            if not clear_of_courtyards(cx, cy, r + 0.2):
                continue
            if any(math.hypot(cx - px, cy - py) < r + pr + 0.5 for px, py, pr in placed):
                continue
            dist = math.hypot(cx - tx, cy - ty)
            if best is None or dist < best[0]:
                best = (dist, cx, cy)
        if best:
            break
    if best is None:
        print("  %-5s NO LEGAL POSITION near %s" % (ref, corner))
        return
    _, cx, cy = best
    f = b.FindFootprintByReference(ref)
    f.SetPosition(pcbnew.VECTOR2I(IU(cx), IU(cy)))
    placed.append((cx, cy, r))
    print("  %-5s -> (%8.3f,%8.3f)   board (%6.2f,%6.2f)   corner %s%s"
          % (ref, cx, cy, cx - bx0, cy - by0, corner[0], corner[1]))


# 6.4 mm pad -> radius 3.2. GND1 pair on the host (left) side, GND2 on the
# isolated (right) side, so neither can bridge the barrier.
place('H1', ('L', 'T'), 3.2, 'GND1', PULLBACK, CLEAR)
place('H2', ('L', 'B'), 3.2, 'GND1', PULLBACK, CLEAR)
place('H3', ('R', 'T'), 3.2, 'GND2', PULLBACK, CLEAR)
place('H4', ('R', 'B'), 3.2, 'GND2', PULLBACK, CLEAR)

# Fiducials: 1.5 mm mask, want a clear copper ring, no net.
place('FID1', ('L', 'T'), 0.75, None, PULLBACK, FID_CLEAR)
place('FID2', ('L', 'B'), 0.75, None, PULLBACK, FID_CLEAR)
place('FID3', ('R', 'T'), 0.75, None, PULLBACK, FID_CLEAR)
place('FID4', ('R', 'B'), 0.75, None, PULLBACK, FID_CLEAR)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print("saved")
