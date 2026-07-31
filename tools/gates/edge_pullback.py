"""Gate 2: no copper comes within 1 mm of the board edge.

Measured as true distance from copper geometry to the actual board outline
polygon, arcs included.

The previous version compared bounding boxes against a straight y = top / y =
bottom pair. That is blind to exactly the case this board hit: with 6.2 mm corner
radii, a pour inset 2 mm from the NOMINAL square corner sat 0.605 mm from the
arc, and a bbox test against the straight edges reported it as 2 mm and passed.
Anything measuring against idealised edges instead of the real outline will miss
corner intrusion.

Constraint 2 pulls copper back from the long edges -- the ones the extrusion's
slots grip -- and exempts the short ends where the connectors sit flush. That
exemption is deliberately NOT encoded as a skip: the whole outline is measured, so
if an end-edge item ever needs to sit closer it appears as a named failure to be
reasoned about rather than being silently ignored.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_board as L
import pcbnew

FLOOR_MM = 1.0
TARGET_MM = 2.0


def outline_edges(board):
    sps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(sps, True)
    edges = []
    for oi in range(sps.OutlineCount()):
        o = sps.Outline(oi)
        pts = [(L.MM(o.CPoint(i).x), L.MM(o.CPoint(i).y)) for i in range(o.PointCount())]
        edges += list(zip(pts, pts[1:] + pts[:1]))
        for hi in range(sps.HoleCount(oi)):
            h = sps.Hole(oi, hi)
            hp = [(L.MM(h.CPoint(i).x), L.MM(h.CPoint(i).y)) for i in range(h.PointCount())]
            edges += list(zip(hp, hp[1:] + hp[:1]))
    return edges


def _seg_d(px, py, ax, ay, cx, cy):
    dx, dy = cx - ax, cy - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def check(board, floor_mm=FLOOR_MM, target_mm=TARGET_MM):
    edges = outline_edges(board)

    def d2e(px, py):
        return min(_seg_d(px, py, a[0], a[1], c[0], c[1]) for a, c in edges)

    violations, warnings = [], []

    def record(layer, kind, net, gap):
        rec = dict(layer=layer, kind=kind, net=net, gap_mm=round(gap, 4))
        if gap < floor_mm:
            violations.append(rec)
        elif gap < target_mm:
            warnings.append(rec)

    for t in board.GetTracks():
        r = L.MM(t.GetWidth()) / 2
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            record('via', 'via', t.GetNetname(), d2e(L.MM(p.x), L.MM(p.y)) - r)
        else:
            s, e = t.GetStart(), t.GetEnd()
            g = min(d2e(L.MM(s.x), L.MM(s.y)), d2e(L.MM(e.x), L.MM(e.y))) - r
            record(board.GetLayerName(t.GetLayer()), 'track', t.GetNetname(), g)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            # Shape-aware, because a bounding box is a poor stand-in for a round
            # pad: the square around a 6.4 mm circle overshoots by 1.33 mm at its
            # corners and reported the mounting holes as 1.672 mm from the edge
            # when the copper is actually 3.000 mm away.
            p = pad.GetPosition()
            sz = pad.GetSize()
            w, h = L.MM(sz.x), L.MM(sz.y)
            if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                r = w / 2.0
            elif pad.GetShape() == pcbnew.PAD_SHAPE_OVAL:
                r = max(w, h) / 2.0
            else:
                r = math.hypot(w, h) / 2.0     # circumscribed, conservative
            g = d2e(L.MM(p.x), L.MM(p.y)) - r
            record('pad', 'pad:%s.%s' % (fp.GetReference(), pad.GetNumber()),
                   pad.GetNetname(), g)
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for lid in L.COPPER_LAYERS:
            if not z.IsOnLayer(lid):
                continue
            poly = z.GetFilledPolysList(lid)
            for oi in range(poly.OutlineCount()):
                o = poly.Outline(oi)
                worst = min(d2e(L.MM(o.CPoint(i).x), L.MM(o.CPoint(i).y))
                            for i in range(o.PointCount()))
                record(board.GetLayerName(lid), 'zone', z.GetNetname(), worst)
    return (not violations), violations, warnings


def main():
    board = L.load(sys.argv[1])
    ok, violations, warnings = check(board)
    for w in sorted(warnings, key=lambda r: r['gap_mm'])[:20]:
        print("  WARN  %(layer)-12s %(kind)-22s %(net)-14s %(gap_mm)7.3f mm to edge" % w)
    for v in sorted(violations, key=lambda r: r['gap_mm'])[:40]:
        print("  FAIL  %(layer)-12s %(kind)-22s %(net)-14s %(gap_mm)7.3f mm to edge" % v)
    print("\nGate 2 (edge pullback): %d below %.1f mm, %d inside the %.1f mm target"
          % (len(violations), FLOOR_MM, len(warnings), TARGET_MM))
    print("Distance is to the real outline polygon, arcs included, not idealised edges.")
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
