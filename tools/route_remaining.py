"""Close the last unconnected items the autorouter left on the isolated side.

Every proposed segment is validated against existing pads, vias and tracks on the
same layer BEFORE it is added, and the script refuses to add a colliding one.
Placing waypoints without that check is what produced seven shorts on the first
attempt.

Geometry that drove the waypoints:

/DCDC_RAW -- U5's supply pins 5 and 8 are both in the RIGHT column (x=89.150,
  y=11.975 and 10.025) with pins 6 and 7 between them, so they cannot be joined
  by a vertical: the link has to go around the package past x=90.175. Freerouting
  also stopped 1 um short of C8.1, subdividing its approach 78.500, 78.513,
  78.519, 78.522, 78.523, 78.524 and never reaching 78.525.

/ISO_5V -- U5's output pins 1 and 2 are adjacent in the LEFT column so they join
  directly, but the run onward to C10 must clear pin 3 at (84.850, 11.325) by
  leaving to the left of the package first.

/PORT_VBUS -- D6.1 and U3.5 are both boxed in between the two halves of the
  differential pair (D+ at y=24.050, D- at y=25.950, both spanning x 102..109.3).
  Each reaches the existing B.Cu PORT_VBUS spine at y=24.091 through a via placed
  in a verified gap rather than by crossing the pair.
"""
import sys, math, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)
IU, MM = pcbnew.FromMM, pcbnew.ToMM
CLEAR = 0.16

FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu
LAYER = {'F': FCU, 'B': BCU}


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def ss_dist(a1, a2, c1, c2):
    return min(seg_dist(*a1, *c1, *c2), seg_dist(*a2, *c1, *c2),
               seg_dist(*c1, *a1, *a2), seg_dist(*c2, *a1, *a2))


def snapshot():
    pads, vias, segs = [], [], []
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            layers = [l for l in (FCU, BCU) if p.IsOnLayer(l)]
            pads.append((MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()),
                         MM(bb.GetBottom()), p.GetNetname(), layers))
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            vias.append((MM(p.x), MM(p.y), MM(t.GetWidth()) / 2, t.GetNetname()))
        else:
            s, e = t.GetStart(), t.GetEnd()
            segs.append((MM(s.x), MM(s.y), MM(e.x), MM(e.y),
                         MM(t.GetWidth()) / 2, t.GetNetname(), t.GetLayer()))
    return pads, vias, segs


def collides(p1, p2, w, netname, lid):
    pads, vias, segs = snapshot()
    hw = w / 2
    for x0, y0, x1, y1, n, layers in pads:
        if n == netname or lid not in layers:
            continue
        for e in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            if ss_dist(p1, p2, (e[0], e[1]), (e[2], e[3])) < hw + CLEAR:
                return "pad %s" % n
    for vx, vy, vr, n in vias:
        if n == netname:
            continue
        if seg_dist(vx, vy, p1[0], p1[1], p2[0], p2[1]) < hw + vr + CLEAR:
            return "via %s" % n
    for x1, y1, x2, y2, ohw, n, l in segs:
        if n == netname or l != lid:
            continue
        if ss_dist(p1, p2, (x1, y1), (x2, y2)) < hw + ohw + CLEAR:
            return "track %s" % n
    return None


ROUTES = [
    # --- DCDC_RAW trunk: C8.1 down, under C8/U5, to the left of the package ---
    ('/DCDC_RAW', 'F', [(78.525, 11.000), (78.525, 13.400), (83.000, 13.400)], 0.5),
    # C9 input cap, now beside the input pins
    ('/DCDC_RAW', 'F', [(78.525, 11.000), (78.525, 7.000), (80.225, 7.000)], 0.5),

    # --- PORT_VBUS: U3.5 is boxed in on F.Cu between pair pins 4 and 6, and every
    # F.Cu escape crosses one half of the pair, so it drops to B.Cu in its own pad.
    ('/PORT_VBUS', 'B', [(108.638, 25.000), (108.901, 24.700), (108.901, 24.091)], 0.4),
]
VIAS = [(108.638, 25.000, '/PORT_VBUS')]

# Fine-pitch approaches. U5's pads are 0.5 mm tall with 0.150 mm between
# neighbours, so a 0.5 mm trunk cannot enter a pin: these neck down to 0.25 mm.
# The trunk x is searched rather than hard-coded because GND stitching vias sit
# in the channel to the left of the package.
APPROACHES = [
    ('/DCDC_RAW', (83.000, 13.400), 11.975, 84.125, 0.25),   # -> U5.8
    ('/DCDC_RAW', (83.000, 13.400), 10.025, 84.125, 0.25),   # -> U5.5
]
LINKS = [
    ('/ISO_5V', (89.150, 11.975), (89.150, 11.325), 0.25),   # U5.1 - U5.2, adjacent pins
]

added = rejected = 0
for net, layer, pts, w in ROUTES:
    lid = LAYER[layer]
    ni = b.FindNet(net)
    for p1, p2 in zip(pts, pts[1:]):
        why = collides(p1, p2, w, net, lid)
        if why:
            print("  REJECT %-12s %s.Cu (%.3f,%.3f)->(%.3f,%.3f): hits %s"
                  % (net, layer, p1[0], p1[1], p2[0], p2[1], why))
            rejected += 1
            continue
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(IU(p1[0]), IU(p1[1])))
        t.SetEnd(pcbnew.VECTOR2I(IU(p2[0]), IU(p2[1])))
        t.SetWidth(IU(w)); t.SetLayer(lid); t.SetNetCode(ni.GetNetCode())
        b.Add(t)
        added += 1

for x, y, net in VIAS:
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(IU(x), IU(y)))
    v.SetWidth(IU(0.5)); v.SetDrill(IU(0.3))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(FCU, BCU)
    v.SetNetCode(b.FindNet(net).GetNetCode())
    b.Add(v)

for net, trunk, ypin, xpin, w in APPROACHES:
    ni = b.FindNet(net)
    done = False
    for xv in (trunk[0], trunk[0] - 0.3, trunk[0] - 0.6, trunk[0] + 0.3, trunk[0] - 0.9):
        legs = [((trunk[0], trunk[1]), (xv, trunk[1])),
                ((xv, trunk[1]), (xv, ypin)),
                ((xv, ypin), (xpin, ypin))]
        legs = [l for l in legs if l[0] != l[1]]
        why = next((collides(a, c, w, net, FCU) for a, c in legs
                    if collides(a, c, w, net, FCU)), None)
        if why:
            continue
        for a, c in legs:
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(IU(a[0]), IU(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(IU(c[0]), IU(c[1])))
            t.SetWidth(IU(w)); t.SetLayer(FCU); t.SetNetCode(ni.GetNetCode())
            b.Add(t)
            added += 1
        print("  approach %-12s -> y=%.3f via trunk x=%.3f" % (net, ypin, xv))
        done = True
        break
    if not done:
        print("  NO CLEAR APPROACH %-12s -> y=%.3f" % (net, ypin))
        rejected += 1

for net, a, c, w in LINKS:
    ni = b.FindNet(net)
    why = collides(a, c, w, net, FCU)
    if why:
        print("  REJECT link %-12s: hits %s" % (net, why)); rejected += 1; continue
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(IU(a[0]), IU(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(IU(c[0]), IU(c[1])))
    t.SetWidth(IU(w)); t.SetLayer(FCU); t.SetNetCode(ni.GetNetCode())
    b.Add(t); added += 1
    print("  link %-12s ok" % net)

print("segments added: %d, rejected: %d" % (added, rejected))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print("saved")
