"""Rebuild GND stitching as ONE grid per side, plus a via fence along both USB pairs.

Supersedes the add_gnd_stitching_vias pass. That tool's `around_refs` strategy
anchors a fresh grid on each named reference, so five refs on the isolated side
produced five interleaved phases (x mod 6 mm = 0.88, 2.20, 4.10, 5.72, 5.88) and
three on the host side. Evenness is the whole point of a stitch grid, so this
uses a single board-anchored phase and lets density come from the pitch.

The fence exists mainly to tie down the outer pour beside the pairs. F.Cu breaks
into 19 fill regions; the strips flanking each pair would otherwise be held only
by whatever pad they happen to touch. It is not doing much as a shield -- both
pairs already reference GND_SPLIT_A through 0.2104 mm of prepreg -- but a strip
of pour that long with one connection is worth nailing down.

Fence geometry holds the same 0.65 mm keepaway the pour uses, for the same
reason: guard copper closer than ~3x the dielectric height starts loading the
line, and diffpair.py computes Zdiff from w/s/h/Er alone so it would not see it.
Candidates BETWEEN the two legs are rejected by requiring the clearance against
every diff-pair centerline, not just the one being walked.
"""
import sys, math, pcbnew

BOARD = sys.argv[1]
ORIG = sys.argv[2]                 # board revision whose vias are routing vias, to keep

GRID_MM = 4.0                      # was 6.0 and read as too sparse
FENCE_PITCH_MM = 2.5               # ~lambda/20 at 2.4 GHz in FR4 (Er_eff ~3.17)
FENCE_OFFSET_MM = 1.5              # from the walked centerline
VIA_D, DRILL_D = 0.6, 0.3
COPPER_GAP = 0.20                  # extra beyond via radius + obstacle half-width
HOLE_GAP = 1.00                    # via centre-to-centre; board min hole-to-hole is 0.4995
DIFF_CLEAR = 1.40                  # via centre to ANY diff-pair centreline
POUR_MARGIN = 0.55                 # via edge must sit this far inside the plane fill
DIFF = {'/HOST_D+', '/HOST_D-', '/PORT_D+', '/PORT_D-'}
R = VIA_D / 2.0

mm = pcbnew.ToMM

# ORIG is read as text, not via LoadBoard: two LoadBoard calls in one process
# leave the second board's Tracks() returning a bare SwigPyObject.
import re
keep = {(round(float(a), 3), round(float(c), 3))
        for a, c in re.findall(r'\(via[^()]*(?:\([^()]*\)[^()]*)*?\(at ([-\d.]+) ([-\d.]+)\)',
                               open(ORIG).read())}
assert keep, "no vias parsed from %s" % ORIG

b = pcbnew.LoadBoard(BOARD)

# Snapshot the track list ONCE. b.Remove() invalidates the container, and a later
# b.GetTracks() then returns a bare SwigPyObject that will not iterate.
tracks = list(b.GetTracks())
drop = [t for t in tracks if t.GetClass() == 'PCB_VIA'
        and (round(mm(t.GetPosition().x), 3), round(mm(t.GetPosition().y), 3)) not in keep]
for t in drop:
    b.Remove(t)
dropped = len(drop)
survivors = [t for t in tracks if t not in drop]

# --- obstacle model -------------------------------------------------------
segs, pads, holes = [], [], []
for t in survivors:
    if t.GetClass() == 'PCB_VIA':
        holes.append((mm(t.GetPosition().x), mm(t.GetPosition().y)))
        continue
    segs.append((t.GetNetname(), mm(t.GetStart().x), mm(t.GetStart().y),
                 mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2.0))
for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        pads.append((p.GetNetname(), mm(bb.GetLeft()), mm(bb.GetTop()),
                     mm(bb.GetRight()), mm(bb.GetBottom())))
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            holes.append((mm(p.GetPosition().x), mm(p.GetPosition().y)))

planes = {}
for z in b.Zones():
    if z.GetIsRuleArea() or b.GetLayerName(z.GetLayer()) != 'GND_SPLIT_A':
        continue
    planes[z.GetNetname()] = z.GetFilledPolysList(z.GetLayer())

diff_segs = [s for s in segs if s[0] in DIFF]


def d_seg(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


RING = [(math.cos(a * math.pi / 6.0), math.sin(a * math.pi / 6.0)) for a in range(12)]


def net_at(px, py):
    """Which GND pour owns this point, with the via annulus fully inside it.

    SHAPE_POLY_SET.Distance() returns 0 for a point inside the polygon, so it
    cannot measure clearance to the boundary from within. Sampling a ring at the
    required radius does, and needs nothing the SWIG bindings do not expose.
    """
    def inside(poly, x, y):
        return poly.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))

    for name, poly in planes.items():
        if not inside(poly, px, py):
            continue
        r = R + POUR_MARGIN
        if all(inside(poly, px + dx * r, py + dy * r) for dx, dy in RING):
            return name
    return None


def ok(px, py, net, placed):
    for d in diff_segs:
        if d_seg(px, py, d[1], d[2], d[3], d[4]) < DIFF_CLEAR:
            return False
    for n, x0, y0, x1, y1, hw in segs:
        if n == net:
            continue
        if d_seg(px, py, x0, y0, x1, y1) < R + hw + COPPER_GAP:
            return False
    for n, x0, y0, x1, y1 in pads:
        if n == net:
            continue
        if (x0 - R - COPPER_GAP <= px <= x1 + R + COPPER_GAP
                and y0 - R - COPPER_GAP <= py <= y1 + R + COPPER_GAP):
            return False
    for hx, hy in holes:
        if math.hypot(px - hx, py - hy) < HOLE_GAP:
            return False
    for qx, qy in placed:
        if math.hypot(px - qx, py - qy) < HOLE_GAP:
            return False
    return True


def add(px, py, net, placed):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(px), pcbnew.FromMM(py)))
    v.SetWidth(pcbnew.FromMM(VIA_D))
    v.SetDrill(pcbnew.FromMM(DRILL_D))
    v.SetNet(b.FindNet(net))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    b.Add(v)
    placed.append((px, py))


placed = []
bb = b.GetBoardEdgesBoundingBox()
x0, y0, x1, y1 = mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())

# --- fence first: it has the tighter geometric constraint --------------------
fence = 0
for n, sx, sy, ex, ey, hw in diff_segs:
    L = math.hypot(ex - sx, ey - sy)
    if L < 1e-6:
        continue
    ux, uy = (ex - sx) / L, (ey - sy) / L
    nx, ny = -uy, ux
    steps = max(1, int(L / FENCE_PITCH_MM))
    for i in range(steps + 1):
        t = L * i / steps
        cx, cy = sx + ux * t, sy + uy * t
        for sgn in (1, -1):
            px, py = cx + nx * FENCE_OFFSET_MM * sgn, cy + ny * FENCE_OFFSET_MM * sgn
            net = net_at(px, py)
            if net and ok(px, py, net, placed):
                add(px, py, net, placed)
                fence += 1

# --- then the even grid ------------------------------------------------------
grid = 0
gx = x0 + GRID_MM
while gx < x1:
    gy = y0 + GRID_MM
    while gy < y1:
        net = net_at(gx, gy)
        if net and ok(gx, gy, net, placed):
            add(gx, gy, net, placed)
            grid += 1
        gy += GRID_MM
    gx += GRID_MM

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print("removed %d prior stitching vias, kept %d routing vias" % (dropped, len(keep)))
print("fence vias: %d   grid vias: %d   total added: %d" % (fence, grid, len(placed)))
print("board vias now:", len(keep) + len(placed))
