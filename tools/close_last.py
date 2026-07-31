"""Close the final unconnected items, with the same pre-validation as
route_remaining.py: nothing is added unless it clears existing copper."""
import sys, math, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
IU, MM = pcbnew.FromMM, pcbnew.ToMM
CLEAR = 0.16
FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def ss(a1, a2, c1, c2):
    return min(seg_dist(*a1, *c1, *c2), seg_dist(*a2, *c1, *c2),
               seg_dist(*c1, *a1, *a2), seg_dist(*c2, *a1, *a2))


def snap():
    pads, vias, segs = [], [], []
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            pads.append((MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()),
                         MM(bb.GetBottom()), p.GetNetname(),
                         [l for l in (FCU, BCU) if p.IsOnLayer(l)]))
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            vias.append((MM(p.x), MM(p.y), MM(t.GetWidth()) / 2, t.GetNetname()))
        else:
            s, e = t.GetStart(), t.GetEnd()
            segs.append((MM(s.x), MM(s.y), MM(e.x), MM(e.y),
                         MM(t.GetWidth()) / 2, t.GetNetname(), t.GetLayer()))
    return pads, vias, segs


def hit_seg(p1, p2, w, net, lid):
    pads, vias, segs = snap()
    hw = w / 2
    for x0, y0, x1, y1, n, ls in pads:
        if n == net or lid not in ls:
            continue
        for e in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            if ss(p1, p2, (e[0], e[1]), (e[2], e[3])) < hw + CLEAR:
                return "pad " + n
    for vx, vy, vr, n in vias:
        if n != net and seg_dist(vx, vy, *p1, *p2) < hw + vr + CLEAR:
            return "via " + n
    for x1, y1, x2, y2, ohw, n, l in segs:
        if n != net and l == lid and ss(p1, p2, (x1, y1), (x2, y2)) < hw + ohw + CLEAR:
            return "track " + n
    return None


def hit_via(x, y, net):
    pads, vias, segs = snap()
    r = 0.25
    for x0, y0, x1, y1, n, ls in pads:
        if n == net:
            continue
        if x + r + CLEAR > x0 and x - r - CLEAR < x1 and y + r + CLEAR > y0 and y - r - CLEAR < y1:
            return "pad " + n
    for vx, vy, vr, n in vias:
        if n != net and math.hypot(x - vx, y - vy) < r + vr + CLEAR:
            return "via " + n
    for x1, y1, x2, y2, ohw, n, l in segs:
        if n != net and seg_dist(x, y, x1, y1, x2, y2) < r + ohw + CLEAR:
            return "track " + n
    return None


def add_seg(net, lid, p1, p2, w):
    why = hit_seg(p1, p2, w, net, lid)
    if why:
        print("  REJECT seg %-12s (%.3f,%.3f)->(%.3f,%.3f): %s" % (net, *p1, *p2, why))
        return False
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(IU(p1[0]), IU(p1[1])))
    t.SetEnd(pcbnew.VECTOR2I(IU(p2[0]), IU(p2[1])))
    t.SetWidth(IU(w)); t.SetLayer(lid); t.SetNetCode(b.FindNet(net).GetNetCode())
    b.Add(t); return True


def add_via(net, x, y):
    why = hit_via(x, y, net)
    if why:
        print("  REJECT via %-12s (%.3f,%.3f): %s" % (net, x, y, why))
        return False
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(IU(x), IU(y)))
    v.SetWidth(IU(0.5)); v.SetDrill(IU(0.3))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(FCU, BCU)
    v.SetNetCode(b.FindNet(net).GetNetCode()); b.Add(v); return True


# 1. PORT_VBUS: carry the U3.5 B.Cu stub across to the B.Cu riser at x=104.157
add_seg('/PORT_VBUS', BCU, (108.901, 24.091), (104.157, 24.091), 0.4)

# 2/3. Ground pads the stitcher could not fit: try several offsets each
for ref, net, cand in (
        ('R3.2', 'GND2', [(95.100, 30.175), (92.900, 30.175), (94.000, 28.900), (95.400, 29.400)]),
        ('D6.2', 'GND2', [(104.900, 29.000), (103.900, 30.100), (104.900, 30.000), (103.900, 27.900)])):
    for x, y in cand:
        if add_via(net, x, y):
            src = (94.000, 30.175) if ref == 'R3.2' else (103.900, 29.000)
            if add_seg(net, FCU, src, (x, y), 0.25):
                print("  stitched %s via (%.3f,%.3f)" % (ref, x, y))
                break

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[1], b)
print("saved")
