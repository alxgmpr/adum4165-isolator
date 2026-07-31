"""Drop stitching vias so GND pads reach the inner ground pours.

The inner layers are declared 'power' type in the DSN so Freerouting cannot route
on them -- that is what stops it bridging the isolation barrier through a plane.
The side effect is that it also cannot connect an F.Cu ground pad down to the
pour, so those connections are made here instead.

Collision rules, learned the hard way: a THROUGH via occupies every copper layer,
so it must clear tracks on all four, not just F.Cu, and the test has to be true
point-to-segment distance. An earlier version tested bounding boxes and ignored
tracks entirely, which put 56 vias straight through routed copper and produced 20
shorts. A long diagonal track's bounding box also covers a huge area, so a bbox
test is both unsound and uselessly conservative.

A pad is skipped if it already has a same-net via within NEAR_MM -- it is already
tied to the pours.
"""
import sys, math, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)
IU, MM = pcbnew.FromMM, pcbnew.ToMM

VIA_D, VIA_DRILL = 0.5, 0.3
TRACK_W = 0.25
CLEAR = 0.18
NEAR_MM = 1.4
BARRIER = (55.85, 64.15)
BAND = (2.0, 48.0)
GND_NETS = {'GND1', 'GND2'}

VIA_R = VIA_D / 2


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


# --- obstacle sets -----------------------------------------------------------
pad_boxes, via_pts, segments = [], [], []
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox()
        pad_boxes.append((MM(bb.GetLeft()), MM(bb.GetTop()),
                          MM(bb.GetRight()), MM(bb.GetBottom()), p.GetNetname()))
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        via_pts.append((MM(p.x), MM(p.y), MM(t.GetWidth()) / 2, t.GetNetname()))
    else:
        s, e = t.GetStart(), t.GetEnd()
        segments.append((MM(s.x), MM(s.y), MM(e.x), MM(e.y),
                         MM(t.GetWidth()) / 2, t.GetNetname()))


def seg_seg_dist(a1, a2, b1, b2):
    """Minimum distance between two 2-D segments."""
    return min(seg_dist(a1[0], a1[1], b1[0], b1[1], b2[0], b2[1]),
               seg_dist(a2[0], a2[1], b1[0], b1[1], b2[0], b2[1]),
               seg_dist(b1[0], b1[1], a1[0], a1[1], a2[0], a2[1]),
               seg_dist(b2[0], b2[1], a1[0], a1[1], a2[0], a2[1]))


def stub_ok(px, py, cx, cy, netname):
    """The pad-to-via stub is copper too: it must clear other nets' pads and
    tracks. Validating only the via position let a stub run straight across a
    neighbouring pad."""
    hw = TRACK_W / 2
    for x0, y0, x1, y1, n in pad_boxes:
        if n == netname:
            continue
        # distance from the stub segment to the pad rectangle, sampled on its edges
        for ex1, ey1, ex2, ey2 in ((x0, y0, x1, y0), (x1, y0, x1, y1),
                                   (x1, y1, x0, y1), (x0, y1, x0, y0)):
            if seg_seg_dist((px, py), (cx, cy), (ex1, ey1), (ex2, ey2)) < hw + CLEAR:
                return False
    for x1, y1, x2, y2, ohw, n in segments:
        if n == netname:
            continue
        if seg_seg_dist((px, py), (cx, cy), (x1, y1), (x2, y2)) < hw + ohw + CLEAR:
            return False
    return True


def free(x, y, netname):
    if not (BAND[0] + VIA_R < y < BAND[1] - VIA_R):
        return False
    if BARRIER[0] - VIA_R < x < BARRIER[1] + VIA_R:
        return False
    for x0, y0, x1, y1, n in pad_boxes:
        if n == netname:
            continue
        if (x + VIA_R + CLEAR > x0 and x - VIA_R - CLEAR < x1 and
                y + VIA_R + CLEAR > y0 and y - VIA_R - CLEAR < y1):
            return False
    for vx, vy, vr, n in via_pts:
        if math.hypot(x - vx, y - vy) < VIA_R + vr + (0 if n == netname else CLEAR):
            return False
    for x1, y1, x2, y2, hw, n in segments:
        if n == netname:
            continue
        if seg_dist(x, y, x1, y1, x2, y2) < VIA_R + hw + CLEAR:
            return False
    return True


placed, skipped = 0, []
for f in b.GetFootprints():
    for p in f.Pads():
        net = p.GetNetname()
        if net not in GND_NETS:
            continue
        pc = p.GetPosition()
        px, py = MM(pc.x), MM(pc.y)
        if any(n == net and math.hypot(px - vx, py - vy) < NEAR_MM
               for vx, vy, vr, n in via_pts):
            continue
        bb = p.GetBoundingBox()
        halfw = (MM(bb.GetRight()) - MM(bb.GetLeft())) / 2
        halfh = (MM(bb.GetBottom()) - MM(bb.GetTop())) / 2
        spot = None
        for d in (0.55, 0.7, 0.9, 1.1, 1.4, 1.8):
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0),
                           (0.71, 0.71), (-0.71, 0.71), (0.71, -0.71), (-0.71, -0.71)):
                cx, cy = px + dx * (halfw + d), py + dy * (halfh + d)
                if free(cx, cy, net) and stub_ok(px, py, cx, cy, net):
                    spot = (cx, cy)
                    break
            if spot:
                break
        if not spot:
            skipped.append((f.GetReference(), p.GetNumber(), net))
            continue
        cx, cy = spot
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(IU(cx), IU(cy)))
        v.SetWidth(IU(VIA_D)); v.SetDrill(IU(VIA_DRILL))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNetCode(p.GetNetCode())
        b.Add(v)
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(IU(px), IU(py)))
        t.SetEnd(pcbnew.VECTOR2I(IU(cx), IU(cy)))
        t.SetWidth(IU(TRACK_W)); t.SetLayer(pcbnew.F_Cu)
        t.SetNetCode(p.GetNetCode())
        b.Add(t)
        via_pts.append((cx, cy, VIA_R, net))
        segments.append((px, py, cx, cy, TRACK_W / 2, net))
        placed += 1

print("stitching vias placed:", placed)
for r in skipped:
    print("  NO ROOM:", r)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print("saved")
