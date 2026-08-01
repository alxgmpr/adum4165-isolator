"""Route the eight branch power nets plus /VBUS_HOST, through the three net ties.

The point of this pass is the STAR TOPOLOGY. Each branch reaches its trunk only
through its net tie, so every segment below is anchored on a tie pad or on a
pad of the branch itself -- nothing is left for a pour to close. Both pads of
every tie are routed explicitly, from opposite sides, and no via sits on a tie
pad.

Coordinates are ABSOLUTE mm, as stored in the .kicad_pcb. `tools/place_iso.py`
uses a board-local frame (absolute = local + 86.88, 76.70); this file does not.

Widths come from the netclass, not from taste:
  PWR       0.5 mm, clearance 0.15, via 0.7/0.35 -- the seven 5 V branches and
            /VBUS_HOST.
  ISO_SIDE  0.2 mm, via 0.6/0.3 -- /ISO_5V_IND only. It carries single-digit
            milliamps to three LED resistors over ~30 mm and is deliberately
            not optimised.
Fine-pitch approaches into U5's 0.5 mm-tall pads neck to 0.25 mm: a 0.5 mm
trunk entering a pin sits exactly 0.15 mm from its neighbour, which is the
clearance limit rather than a margin. Same idiom as tools/route_remaining.py.

--------------------------------------------------------------------------
Geometry that drove the waypoints
--------------------------------------------------------------------------

/DCDC_RECT  NT2.1 <- C8.1 is NOT a straight shot: the direct line runs through
    C8's OWN GND2 pad (x 165.500..166.650, y 84.850..87.550). The trunk drops
    south to y 88.300, clears C8's body, climbs at x 167.400 and enters NT2.1
    from the WEST.

/DCDC_RAW   U5.5 and U5.8 are two pins apart in the same column with GND2 (6)
    and a NC (7) between them, so they cannot be joined along the pad column.
    A trunk at x 170.0875 sits in the 1.275 mm lane between NT2.2 and U5's left
    edge and stubs east into both pins and south into C9.

/ISO_5V     U5.1/U5.2 are adjacent and link directly. NT1.1 is entered from the
    north down the x 177.925 column through C11 and C10.

/ISO_5V_VBUS2  NT1.2 is the NE pad and has to reach U1.20, 27 mm WEST, so it
    must cross /ISO_5V's descent into NT1.1. There is no y that avoids this:
    NT1.1 is the west pad and NT1.2 the east one, so the two branches are
    handed the wrong way round for their destinations. It crosses on B.Cu, a
    3 mm hop; measured, the closest /ISO_5V to /ISO_5V_VBUS2 copper anywhere on
    the board is 0.475 mm, that via to the /ISO_5V column. U1.20 sits
    0.745 mm east of the barrier keepout; the run stops at the pad centre
    (151.775), 0.495 mm clear of the keepout edge.

/ISO_5V_SW / /ISO_5V_IND  Same inversion, one row down: NT1.3 (SW pad) serves
    C16/U6 to the EAST, NT1.4 (SE pad) serves the indicator strip to the
    SOUTH-WEST. NT1.4 is also the pinched pad -- C16's GND2 pad starts 12.5 um
    east of it and 1.03 mm south. /ISO_5V_IND therefore leaves NT1.4 straight
    south for 0.8 mm and drops to B.Cu immediately, which clears both the pinch
    and the crossing in one move.

    That B.Cu run also crosses the /PORT_D+- corridor (x 153..190, y
    103.5..111) at x 179.000. Crossing it on B.Cu, not F.Cu, is what the board
    did before this effort (2c1167d put a via at 179.7375, 103.5664 and ran
    B.Cu to 115.074 for exactly this). F.Cu meander room in the corridor is
    untouched.

/PORT_VBUS  NT3.1 cannot be entered from the west: C15's GND2 pad (x
    185.325..186.225) is in the way. It leaves NORTH to y 99.600, runs west
    over C15, and drops into C15.1; C14 stubs north off the same run.

/PORT_VBUS_J2  NT3.2 <- U3.5 is NOT a straight shot either: the direct line
    crosses U3.2 (GND2) and U3.1 is adjacent. NT3.2 leaves EAST, climbs to
    y 99.350 and runs to J2.A9/B4 north of U3. U3.5 is reached down the 0.95 mm
    gap between U3's two pad columns (0.225 mm each side) -- NOT from the east,
    because x 194.675..196.975 at y 100.4..103.0 is the only lane the
    differential pair has to get from U3.6/U3.4 into J2, and Task 6 needs it.
    D6, J2.A4/B9 and R7/R8 sit south of that same lane, so the link to them
    drops to B.Cu at x 196.000 and comes back up at y 104.175, above and below
    the pair's band. The southern spine then runs at x 194.200, clear of the
    corridor's x 190 edge.

/VBUS_HOST  Ripped wholesale in Task 3 and rebuilt here. The J1 -> D5/C3 ->
    U2.5 -> U4 -> C4/U1.1 topology is restored from 2c1167d, which is still
    correct: none of those parts moved. Three things are new.
      * U2.5 still escapes east on B.Cu -- it is boxed in between U2's own D+
        and D- runs. The via column moved from x 103.2217 to 103.150: at the
        old x a 0.7 mm PWR via clears the D- diagonal by 0.150 mm, which is the
        limit and not a margin.
      * C7 moved north in Task 4 and is fenced off from the U4->T1 corridor by
        the /PP_B winding (y 85.7634..86.0634, x 134.87..142.17). No F.Cu
        crossing exists anywhere along that winding, so C7 is fed by a 1.81 mm
        B.Cu hop.
      * C17 is new and is fenced the same way by /PP_A (y 87.6634..87.9634) to
        its north, T1.3 to its east and C17's own GND1 pad to its south. Also
        a B.Cu hop, 1.81 mm. It runs at x 138.050, not 137.900: a 0.7 mm PWR
        via at 137.900 clears C6's GND1 pad by 0.1425 mm, under the limit.
    C7 and C17 were also nudged 0.20 mm north and 0.12 mm south respectively in
    this task -- as Task 4 placed them, both pads sat inside DRC clearance of
    the winding that fences them (0.0134 and 0.0866 mm against 0.15). The
    ruling and the numbers are recorded in tools/place_iso.py; the fencing that
    forces the B.Cu hops is unchanged by the nudge.

--------------------------------------------------------------------------
Orphaned teardrops
--------------------------------------------------------------------------

Task 3 ripped the isolated side's tracks and vias but not the teardrop ZONES
hanging off them, and Task 4's moves stranded a few more on the host side.
KiCad stores teardrops as zones with island_removal_mode NEVER, so they keep
their fill whether or not anything of their net still touches them: 72 of them
survive a refill as floating copper, several with the pre-split net name on a
pad that now belongs to a sibling branch. Four sit directly in the
NT2.2 -> U5.5/U5.8 corridor and two more bracket the only lane around C8.

strip_orphan_teardrops() removes a teardrop zone only when NO pad, track or via
of its own net overlaps it -- such a zone contributes nothing to connectivity
by definition, so removing it cannot change the netlist. It refuses to touch
anything that is not a teardrop, and prints every deletion.

Usage: <kicad python3> route_iso.py <board.kicad_pcb>
"""
import sys, os, pcbnew

IU, MM = pcbnew.FromMM, pcbnew.ToMM
FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu
LAYER = {'F': FCU, 'B': BCU}
CLEAR = 0.15                      # Default/HOST_SIDE/ISO_SIDE/PWR all specify
                                  # 0.15; USB_DIFF90 specifies 0.127, and the
                                  # only place 0.127 actually applies is inside
                                  # J1/J2's courtyards, via the kicad_dru rule
                                  # `connector-neckdown`. See Obstacles.

W_PWR, W_ISO = 0.5, 0.2
VIA_PWR, DRL_PWR = 0.7, 0.35      # PWR netclass
VIA_ISO, DRL_ISO = 0.6, 0.3       # ISO_SIDE netclass


# -------------------------------------------------------------- obstacles ---
def V(x, y):
    return pcbnew.VECTOR2I(IU(x), IU(y))


_CU = []


def copper_layers(board):
    """Every enabled copper layer id. Enumerated, not hard-coded: this board's
    four are F.Cu(0), B.Cu(2), GND_SPLIT_A(4), GND_SPLIT_B(6), and the inner
    ids move between KiCad versions."""
    if not _CU:
        _CU.extend(l for l in board.GetEnabledLayers().Seq()
                   if pcbnew.IsCopperLayer(l))
    return _CU


class Obstacles(object):
    """Every copper item on the board, as its REAL shape.

    Bounding boxes are not good enough here. The first version of this checker
    used them and rejected four segments restored verbatim from `2c1167d` --
    which is DRC-clean, 0 violations -- because J1's round through-hole legs and
    R2's roundrect pad both lose a lot of area at the corners of their bbox.
    These are `GetEffectiveShape()` polygons and `SHAPE::Collide`, the same
    geometry DRC uses.

    Clearance is 0.15 mm everywhere except inside J1's and J2's courtyards,
    where isolator.kicad_dru's `connector-neckdown` rule relaxes it to
    0.127 mm so tracks can escape the 0.5 mm-pitch USB-C pad field.

    NOTE ON LIFETIME: `GetEffectiveShape()` hands back a shared_ptr that this
    binding does not keep alive, so caching the returned proxy and calling
    Collide on it later segfaults. Board items are therefore kept as ITEMS and
    their shape is fetched inside the Collide expression. Shapes this script
    constructs itself (its own tracks and vias) are owned by Python and are
    cached normally.
    """

    def __init__(self, board):
        self.board = []           # (net, layer, item, label) -- shape on demand
        self.mine = []            # (net, layer, shape, label) -- Python-owned
        for f in board.GetFootprints():
            ref = f.GetReference()
            for p in f.Pads():
                for lid in (FCU, BCU):
                    if p.IsOnLayer(lid):
                        self.board.append((p.GetNetname(), lid, p,
                                           'pad %s.%s [%s]'
                                           % (ref, p.GetNumber(), p.GetNetname())))
        for t in board.GetTracks():
            pos, s, e = t.GetPosition(), t.GetStart(), t.GetEnd()
            if t.GetClass() == 'PCB_VIA':
                lab = 'via [%s] at (%.3f,%.3f)' % (t.GetNetname(), MM(pos.x), MM(pos.y))
                for lid in (FCU, BCU):
                    self.board.append((t.GetNetname(), lid, t, lab))
            else:
                self.board.append((t.GetNetname(), t.GetLayer(), t,
                                   'track [%s] (%.3f,%.3f)-(%.3f,%.3f)'
                                   % (t.GetNetname(), MM(s.x), MM(s.y), MM(e.x), MM(e.y))))
        self.necks = [r for r in ('J1', 'J2')
                      if board.FindFootprintByReference(r) is not None]
        self._board = board

    # ---- clearance that applies at these points ----
    def clearance_at(self, pts):
        for x, y in pts:
            v = V(x, y)
            for ref in self.necks:
                if self._board.FindFootprintByReference(ref) \
                        .GetCourtyard(pcbnew.F_CrtYd).Collide(v):
                    return 0.127
        return CLEAR

    def _probe(self, shape, net, lid, clr):
        c = IU(clr)
        for n, l, it, label in self.board:
            if n == net or l != lid:
                continue
            if it.GetClass() == 'PAD':
                if it.GetEffectiveShape(l).Collide(shape, c):
                    return label
            elif it.GetEffectiveShape().Collide(shape, c):
                return label
        for n, l, sh, label in self.mine:
            if n == net or l != lid:
                continue
            if sh.Collide(shape, c):
                return label
        return None

    def add_seg(self, p1, p2, w, net, lid):
        self.mine.append((net, lid, pcbnew.SHAPE_SEGMENT(V(*p1), V(*p2), IU(w)),
                          'track [%s] (%.3f,%.3f)-(%.3f,%.3f)'
                          % (net, p1[0], p1[1], p2[0], p2[1])))

    def add_via(self, x, y, dia, net):
        for lid in (FCU, BCU):
            self.mine.append((net, lid, pcbnew.SHAPE_SEGMENT(V(x, y), V(x, y), IU(dia)),
                              'via [%s] at (%.3f,%.3f)' % (net, x, y)))

    def hit_seg(self, p1, p2, w, net, lid):
        cand = pcbnew.SHAPE_SEGMENT(V(*p1), V(*p2), IU(w))
        return self._probe(cand, net, lid, self.clearance_at((p1, p2)))

    def hit_via(self, x, y, dia, net):
        cand = pcbnew.SHAPE_SEGMENT(V(x, y), V(x, y), IU(dia))
        for lid in (FCU, BCU):
            why = self._probe(cand, net, lid, self.clearance_at(((x, y),)))
            if why:
                return why
        return None


# ------------------------------------------------------- orphan teardrops ---
# board.Remove() detaches a ZONE without deleting it, and this binding has no
# destructor for ZONE*, so letting the last Python reference go while the C++
# object is orphaned segfaults the interpreter. Park them here for the run.
_DETACHED = []


def strip_orphan_teardrops(board):
    """Delete teardrop zones with no copper of their own net touching them.

    Such a zone cannot be carrying current -- nothing of its net reaches it --
    so this can only remove floating copper. The overlap test is bounding-box
    (deliberately over-inclusive: a zone is kept on the slightest doubt).
    """
    items = []
    for f in board.GetFootprints():
        for p in f.Pads():
            items.append((p.GetNetname(), p, p.GetBoundingBox()))
    for t in board.GetTracks():
        items.append((t.GetNetname(), t, t.GetBoundingBox()))

    doomed = []
    for z in board.Zones():
        if not (hasattr(z, 'IsTeardropArea') and z.IsTeardropArea()):
            continue
        zbb, zn, zl = z.GetBoundingBox(), z.GetNetname(), z.GetLayer()
        if any(n == zn and it.IsOnLayer(zl) and zbb.Intersects(bb) for n, it, bb in items):
            continue
        doomed.append(z)

    for z in doomed:
        bb = z.GetBoundingBox()
        print('  orphan teardrop removed: %-14s %-6s %7.4f mm2  (%.3f,%.3f)-(%.3f,%.3f)'
              % (z.GetNetname(), board.GetLayerName(z.GetLayer()),
                 z.GetFilledArea() / 1e12,
                 MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())))
        board.Remove(z)
        _DETACHED.append(z)
    print('  orphan teardrops removed: %d' % len(doomed))
    return len(doomed)


# ------------------------------------------------------------------ routes --
# (net, layer, [waypoints], width). Consecutive waypoints become one segment.
#
# TODO (deferred by ruling, 2026-08-01 -- do not do this while Tasks 6 and 7
# are still to run against this file): the waypoints that land ON A PAD are
# hard-coded pad centres, so moving a footprint silently invalidates them.
# The cost is real and already paid once: nudging C7 0.20 mm and C17 0.12 mm
# forced four /VBUS_HOST waypoints and two vias to be re-derived by hand, and
# nothing here would have complained if they had not been -- the tracks still
# landed inside the moved pads, so every check would have passed while the
# routing pointed at where the parts used to be.
# The fix is to look pad centres up from the footprint at build time --
# e.g. PAD('C17', '1') resolved against the board -- and leave only the
# genuinely geometric waypoints (lane centres, corner positions, the y 88.300
# detour round C8) as literals. That is a refactor of this table's core data
# structure, which is why it is deferred rather than done.
P, I = W_PWR, W_ISO

ROUTES = [
    # ---- /DCDC_RECT: D1.1 and D2.1 and C8.1 -> NT2.1, entering from the west
    ('/DCDC_RECT', 'F', [(160.200, 84.100), (163.125, 84.100)], P),
    ('/DCDC_RECT', 'F', [(163.125, 84.100), (163.125, 88.300)], P),
    ('/DCDC_RECT', 'F', [(160.200, 88.300), (163.125, 88.300)], P),
    ('/DCDC_RECT', 'F', [(163.125, 88.300), (167.400, 88.300),
                         (167.400, 86.200), (168.200, 86.200)], P),

    # ---- /DCDC_RAW: NT2.2 -> east, trunk south to C9, stubs into U5.5/U5.8
    ('/DCDC_RAW', 'F', [(169.200, 86.200), (170.0875, 86.200)], P),
    ('/DCDC_RAW', 'F', [(170.0875, 86.200), (170.0875, 90.025), (171.450, 90.025)], P),
    ('/DCDC_RAW', 'F', [(170.0875, 86.225), (171.450, 86.225)], 0.25),
    ('/DCDC_RAW', 'F', [(170.0875, 88.175), (171.450, 88.175)], 0.25),

    # ---- /ISO_5V: U5.1/U5.2 -> C11 -> C10 -> NT1.1 from the north
    ('/ISO_5V', 'F', [(175.750, 88.175), (175.750, 87.525)], 0.25),
    ('/ISO_5V', 'F', [(175.750, 88.175), (176.900, 88.175)], 0.25),
    ('/ISO_5V', 'F', [(176.900, 88.175), (177.925, 88.175), (177.925, 91.200)], P),
    ('/ISO_5V', 'F', [(177.925, 91.200), (176.625, 91.200)], P),
    ('/ISO_5V', 'F', [(177.925, 91.200), (177.925, 94.500)], P),

    # ---- /ISO_5V_VBUS2: NT1.2 -> north, under /ISO_5V on B.Cu, then west
    ('/ISO_5V_VBUS2', 'F', [(179.000, 94.500), (179.000, 93.400)], P),
    ('/ISO_5V_VBUS2', 'B', [(179.000, 93.400), (176.000, 93.400)], P),
    ('/ISO_5V_VBUS2', 'F', [(176.000, 93.400), (153.975, 93.400),
                            (153.975, 95.988), (151.775, 95.988)], P),

    # ---- /ISO_5V_SW: NT1.3 -> south -> C16.1 -> U6.1, round U6.2 to U6.3
    ('/ISO_5V_SW', 'F', [(178.000, 95.500), (178.000, 98.775),
                         (179.738, 98.775), (179.738, 100.753)], P),
    ('/ISO_5V_SW', 'F', [(179.738, 100.753), (178.500, 100.753),
                         (178.500, 102.653), (179.738, 102.653)], P),

    # ---- /ISO_5V_IND: NT1.4 -> south, B.Cu under the D+- corridor, then R4/R5/R6
    ('/ISO_5V_IND', 'F', [(179.000, 95.500), (179.000, 96.300)], I),
    ('/ISO_5V_IND', 'B', [(179.000, 96.300), (179.000, 114.3365),
                          (182.4673, 117.8038)], I),
    ('/ISO_5V_IND', 'F', [(182.4673, 117.8038), (184.5996, 117.8038),
                          (184.8750, 117.5284)], I),
    ('/ISO_5V_IND', 'F', [(182.4673, 117.8038), (182.4673, 117.9361),
                          (178.8750, 121.5284), (172.8750, 121.5284)], I),

    # ---- /PORT_VBUS: NT3.1 -> north over C15's GND pad -> C15.1 -> U6.6, C14 stub
    ('/PORT_VBUS', 'F', [(187.500, 100.753), (187.500, 99.600),
                         (184.225, 99.600), (184.225, 100.753)], P),
    ('/PORT_VBUS', 'F', [(186.050, 99.600), (186.050, 97.800)], P),
    ('/PORT_VBUS', 'F', [(184.225, 100.753), (182.012, 100.753)], P),

    # ---- /PORT_VBUS_J2: NT3.2 -> east and north of U3 -> J2.A9/B4
    ('/PORT_VBUS_J2', 'F', [(188.500, 100.753), (189.400, 100.753),
                            (189.400, 99.350), (197.700, 99.350)], P),
    #      U3.5 down the gap between U3's two pad columns, leaving the
    #      x 194.675..196.975 lane free for Task 6's pair
    ('/PORT_VBUS_J2', 'F', [(192.875, 99.350), (192.875, 101.703),
                            (194.012, 101.703)], P),
    #      under the pair's band on B.Cu to the southern group
    ('/PORT_VBUS_J2', 'B', [(196.000, 99.350), (196.000, 104.175)], P),
    ('/PORT_VBUS_J2', 'F', [(195.100, 104.175), (197.700, 104.175)], P),
    ('/PORT_VBUS_J2', 'F', [(195.100, 104.175), (194.200, 104.175),
                            (194.200, 109.400), (202.200, 109.400)], P),
    ('/PORT_VBUS_J2', 'F', [(198.825, 109.400), (198.825, 107.900)], P),
    ('/PORT_VBUS_J2', 'F', [(202.200, 109.400), (202.200, 107.900)], P),

    # ---- /VBUS_HOST, host side. J1 -> C3/D5 restored from 2c1167d.
    ('/VBUS_HOST', 'F', [(96.0500, 99.2534), (95.3374, 99.2534), (94.6110, 99.9798),
                         (94.6110, 103.4270), (95.3374, 104.1534), (96.0500, 104.1534),
                         (96.8535, 104.1534), (98.3555, 105.7034), (100.1230, 105.7034),
                         (100.7750, 105.0034)], P),
    ('/VBUS_HOST', 'F', [(100.7750, 105.0034), (101.0250, 104.7534),
                         (103.0750, 104.7534)], P),
    ('/VBUS_HOST', 'F', [(103.1500, 104.6034), (103.1500, 103.6500)], P),
    ('/VBUS_HOST', 'B', [(103.1500, 103.6500), (103.1500, 99.5784)], P),
    ('/VBUS_HOST', 'F', [(103.1500, 101.7000), (102.1335, 101.7000)], P),
    ('/VBUS_HOST', 'F', [(103.1500, 99.5784), (108.0932, 94.6352),
                         (122.8000, 94.6352)], P),
    ('/VBUS_HOST', 'F', [(122.8000, 94.6352), (130.5718, 86.8634),
                         (132.5950, 86.8634), (134.8700, 86.8634)], P),
    ('/VBUS_HOST', 'F', [(122.8000, 94.6352), (139.8068, 94.6352)], P),
    ('/VBUS_HOST', 'F', [(139.9230, 94.7514), (141.1600, 95.9884),
                         (141.9750, 95.9884)], P),
    #      U4.2 -> C6.1 -> T1.2 down the lane between the /PP_B and /PP_A windings
    ('/VBUS_HOST', 'F', [(134.8700, 86.8634), (142.1700, 86.8634)], P),
    #      C7 is fenced north of /PP_B, C17 south of /PP_A: both hop on B.Cu
    ('/VBUS_HOST', 'B', [(135.850, 86.8634), (135.850, 85.050)], P),
    ('/VBUS_HOST', 'F', [(135.850, 85.050), (136.9325, 85.050)], P),
    ('/VBUS_HOST', 'B', [(138.050, 86.8634), (138.050, 88.670)], P),
    ('/VBUS_HOST', 'F', [(138.050, 88.670), (139.0940, 88.670)], P),
]

# (x, y, net, diameter, drill) -- none of these sits on a net-tie pad.
VIAS = [
    (179.000, 93.400, '/ISO_5V_VBUS2', VIA_PWR, DRL_PWR),
    (176.000, 93.400, '/ISO_5V_VBUS2', VIA_PWR, DRL_PWR),
    (179.000, 96.300, '/ISO_5V_IND', VIA_ISO, DRL_ISO),
    (182.4673, 117.8038, '/ISO_5V_IND', VIA_ISO, DRL_ISO),
    (196.000, 99.350, '/PORT_VBUS_J2', VIA_PWR, DRL_PWR),
    (196.000, 104.175, '/PORT_VBUS_J2', VIA_PWR, DRL_PWR),
    (103.1500, 103.6500, '/VBUS_HOST', VIA_PWR, DRL_PWR),
    (103.1500, 101.7000, '/VBUS_HOST', VIA_PWR, DRL_PWR),
    (103.1500, 99.5784, '/VBUS_HOST', VIA_PWR, DRL_PWR),
    (135.850, 86.8634, '/VBUS_HOST', VIA_PWR, DRL_PWR),
    (135.850, 85.050, '/VBUS_HOST', VIA_PWR, DRL_PWR),
    (138.050, 86.8634, '/VBUS_HOST', VIA_PWR, DRL_PWR),
    (138.050, 88.670, '/VBUS_HOST', VIA_PWR, DRL_PWR),
]

# guards, checked rather than trusted
BARRIER_X = (142.72, 151.03)
BAND_Y = (78.70, 124.70)
CORRIDOR = (153.0, 103.5, 190.0, 111.0)   # /PORT_D+- meander room, Task 6's
NETS = ('/ISO_5V', '/ISO_5V_VBUS2', '/ISO_5V_SW', '/ISO_5V_IND', '/DCDC_RECT',
        '/DCDC_RAW', '/PORT_VBUS', '/PORT_VBUS_J2', '/VBUS_HOST')
TIES = {'NT1': ('/ISO_5V', '/ISO_5V_VBUS2', '/ISO_5V_SW', '/ISO_5V_IND'),
        'NT2': ('/DCDC_RECT', '/DCDC_RAW'),
        'NT3': ('/PORT_VBUS', '/PORT_VBUS_J2')}


def seg_box_hit(a, b, r, box):
    """Does the segment a-b, inflated by r, touch the axis-aligned box?

    Slab clip on the box grown by r. Approximating the round cap by a square
    one over-reports slightly at the corners, which is the safe direction for a
    keepout check.
    """
    x0, y0, x1, y1 = box[0] - r, box[1] - r, box[2] + r, box[3] + r
    t0, t1 = 0.0, 1.0
    for p, q in ((-(b[0] - a[0]), a[0] - x0), (b[0] - a[0], x1 - a[0]),
                 (-(b[1] - a[1]), a[1] - y0), (b[1] - a[1], y1 - a[1])):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / float(p)
        if p < 0:
            if t > t1:
                return False
            t0 = max(t0, t)
        else:
            if t < t0:
                return False
            t1 = min(t1, t)
    return t0 <= t1


def verify(board):
    """Assertions that a rejected-segment count cannot make for you.

    Connectivity here is computed over TRACKS, VIAS and PADS only -- zones are
    deliberately excluded. A branch that reads as connected because a pour
    happens to bridge it is the exact defect the net-tie split exists to
    eliminate, so a pour must not be able to make this check pass.
    """
    bad = 0
    print('\n== connectivity (tracks/vias/pads only, zones excluded) ==')
    for net in NETS:
        pads, elems = [], []       # elems: (layers, kind, obj)
        for f in board.GetFootprints():
            for p in f.Pads():
                if p.GetNetname() != net:
                    continue
                lay = frozenset(l for l in (FCU, BCU) if p.IsOnLayer(l))
                pads.append(len(elems))
                elems.append((lay, 'PAD', p))
        for t in board.GetTracks():
            if t.GetNetname() != net:
                continue
            lay = frozenset((FCU, BCU)) if t.GetClass() == 'PCB_VIA' \
                else frozenset((t.GetLayer(),))
            elems.append((lay, 'TRK', t))
        if not pads:
            print('  FAIL  %-15s no pads on this net' % net)
            bad += 1
            continue

        parent = list(range(len(elems)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(elems)):
            for j in range(i + 1, len(elems)):
                li, ki, oi = elems[i]
                lj, kj, oj = elems[j]
                common = li & lj
                if not common:
                    continue
                lid = sorted(common)[0]
                si = oi.GetEffectiveShape(lid) if ki == 'PAD' else oi.GetEffectiveShape()
                sj = oj.GetEffectiveShape(lid) if kj == 'PAD' else oj.GetEffectiveShape()
                if si.Collide(sj, 0):
                    parent[find(i)] = find(j)

        roots = set(find(i) for i in pads)
        biggest = max((sum(1 for i in pads if find(i) == r), r) for r in roots)
        ok = len(roots) == 1
        print('  %s  %-15s %2d pads, %d cluster(s) (largest %d)'
              % ('ok  ' if ok else 'FAIL', net, len(pads), len(roots), biggest[0]))
        if not ok:
            bad += 1

    print('\n== net ties: both pads routed, from opposite sides ==')
    for ref, nets in sorted(TIES.items()):
        fp = board.FindFootprintByReference(ref)
        for p in fp.Pads():
            if p.GetNetname() not in nets:
                continue
            c = p.GetPosition()
            cx, cy = MM(c.x), MM(c.y)
            bb = p.GetBoundingBox()
            box = (MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom()))
            # "No pour touches a tie pad" is the single most important thing
            # this file asserts, so it is tested against the pad's real SHAPE
            # on EVERY copper layer -- not against its centre point, which
            # would miss a pour lapping the pad's edge, and not on one layer,
            # which would miss the inner planes entirely.
            pour = []
            for z in board.Zones():
                if z.GetFilledArea() <= 0:
                    continue
                for lid in copper_layers(board):
                    if not (z.IsOnLayer(lid) and p.IsOnLayer(lid)):
                        continue
                    if z.GetFilledPolysList(lid).Collide(p.GetEffectiveShape(lid), 0):
                        pour.append('%s on %s' % (z.GetNetname(),
                                                  board.GetLayerName(lid)))
            legs, via_on_pad = [], []
            for t in board.GetTracks():
                if t.GetNetname() != p.GetNetname():
                    continue
                if t.GetClass() == 'PCB_VIA':
                    q = t.GetPosition()
                    if box[0] <= MM(q.x) <= box[2] and box[1] <= MM(q.y) <= box[3]:
                        via_on_pad.append((MM(q.x), MM(q.y)))
                    continue
                for a, b in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
                    ax, ay = MM(a.x), MM(a.y)
                    if box[0] <= ax <= box[2] and box[1] <= ay <= box[3]:
                        legs.append((MM(b.x) - cx, MM(b.y) - cy))
            dirs = set()
            for dx, dy in legs:
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    continue
                dirs.add(('W' if dx < -0.05 else 'E' if dx > 0.05 else '')
                         + ('N' if dy < -0.05 else 'S' if dy > 0.05 else ''))
            # Every tie pad on this board is routed with EXACTLY one leg. Two
            # legs means either a duplicated run or an unintended tee, and the
            # first of those is what a second run of this script produces --
            # _probe skips same-net items, so a re-run collides with nothing
            # and silently doubles the copper. This row is what catches it.
            status = 'ok  '
            notes = []
            if len(legs) != 1:
                status, bad = 'FAIL', bad + 1
                notes.append('EXPECTED EXACTLY 1 TRACK LEG, FOUND %d' % len(legs))
            if via_on_pad:
                status, bad = 'FAIL', bad + 1
                notes.append('VIA ON TIE PAD %r' % (via_on_pad,))
            if pour:
                status, bad = 'FAIL', bad + 1
                notes.append('FED BY POUR %r' % (pour,))
            print('  %s  %s.%-2s %-15s %d track leg(s), leaving %-8s %-9s %s'
                  % (status, ref, p.GetNumber(), p.GetNetname(), len(legs),
                     '/'.join(sorted(d for d in dirs if d)) or '-',
                     'POUR!' if pour else 'no pour', '  '.join(notes)))

    print('\n== barrier keepout / copper band / D+- corridor ==')
    bx0, bx1 = BARRIER_X
    by0, by1 = BAND_Y
    cx0, cy0, cx1, cy1 = CORRIDOR
    hits = []
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            # PCB_VIA::GetWidth() warns without a layer argument in this build
            r = MM(t.GetBoundingBox().GetWidth()) / 2.0
            q = t.GetPosition()
            a = b = (MM(q.x), MM(q.y))
            on_f = True
        else:
            r = MM(t.GetWidth()) / 2.0
            s, e = t.GetStart(), t.GetEnd()
            a, b = (MM(s.x), MM(s.y)), (MM(e.x), MM(e.y))
            on_f = t.GetLayer() == FCU
        lo_x, hi_x = min(a[0], b[0]) - r, max(a[0], b[0]) + r
        lo_y, hi_y = min(a[1], b[1]) - r, max(a[1], b[1]) + r
        where = '(%.3f,%.3f)-(%.3f,%.3f)' % (a[0], a[1], b[0], b[1])
        if hi_x > bx0 and lo_x < bx1:
            hits.append(('BARRIER', t.GetNetname(), where))
        if lo_y < by0 or hi_y > by1:
            hits.append(('BAND', t.GetNetname(), where))
        # F.Cu only: the corridor reserves F.Cu meander room, and the board's
        # own pre-existing solution for getting past it was a B.Cu detour.
        if on_f and seg_box_hit(a, b, r, (cx0, cy0, cx1, cy1)):
            hits.append(('CORRIDOR', t.GetNetname(), where))
    # The corridor reserves F.Cu meander room, so PADS and ZONE FILL count as
    # much as tracks do. Checking only tracks made this assertion narrower than
    # the claim it was being quoted for. Inner planes and B.Cu are exempt by
    # definition: the plane pours must cross the corridor, and the board's own
    # pre-existing way past it was a B.Cu detour.
    rect = pcbnew.SHAPE_RECT(pcbnew.VECTOR2I(IU(cx0), IU(cy0)),
                             IU(cx1 - cx0), IU(cy1 - cy0))
    for f in board.GetFootprints():
        for p in f.Pads():
            if not p.IsOnLayer(FCU):
                continue
            if rect.Collide(p.GetEffectiveShape(FCU), 0):
                hits.append(('CORRIDOR-PAD', p.GetNetname(),
                             '%s.%s' % (f.GetReference(), p.GetNumber())))
    for z in board.Zones():
        if z.GetLayer() != FCU or z.GetFilledArea() <= 0:
            continue
        if z.GetFilledPolysList(FCU).Collide(rect, 0):
            bb = z.GetBoundingBox()
            hits.append(('CORRIDOR-ZONE', z.GetNetname(),
                         '(%.3f,%.3f)-(%.3f,%.3f)'
                         % (MM(bb.GetLeft()), MM(bb.GetTop()),
                            MM(bb.GetRight()), MM(bb.GetBottom()))))

    for kind, net, where in hits:
        print('  FAIL  %-14s %-15s %s' % (kind, net, where))
    bad += len(hits)
    if not hits:
        print('  ok    no track or via enters x %.2f..%.2f or leaves y %.2f..%.2f'
              % (bx0, bx1, by0, by1))
        print('  ok    no F.Cu track, via, pad or zone fill in the corridor'
              ' x %.0f..%.0f y %.1f..%.1f' % (cx0, cx1, cy0, cy1))
    return bad


def main():
    board_path = sys.argv[1]
    board = pcbnew.LoadBoard(board_path)
    if board is None:
        print('LoadBoard returned None -- is %r a *.kicad_pcb?' % board_path)
        sys.exit(2)

    # This script routes all nine nets from scratch and has no incremental
    # mode, so any existing copper on them means it has already run. Without
    # this guard a second run is SILENT: _probe skips same-net items, so every
    # segment collides with nothing, 93 duplicates are added, and connectivity,
    # the tie-pad check, the keepout check and DRC all still pass. verify()
    # now also asserts one track leg per tie pad, which catches partial
    # duplication; this catches the wholesale case before anything is written.
    print('== pre-flight ==')
    existing = {}
    for t in board.GetTracks():
        n = t.GetNetname()
        if n in NETS:
            existing[n] = existing.get(n, 0) + 1
    if existing:
        for n in sorted(existing):
            print('  %-15s already carries %d copper item(s)' % (n, existing[n]))
        print('\nREFUSING TO RUN: these nets are already routed. This script is')
        print('not idempotent -- re-running would silently double the copper.')
        print('Restore the board to its pre-routing state first, e.g.')
        print('  git show <task-4-commit>:isolator.kicad_pcb > isolator.kicad_pcb')
        print('  <kicad python3> tools/place_iso.py isolator.kicad_pcb')
        sys.stdout.flush()
        os._exit(1)
    print('  ok    none of the nine nets carries copper yet')

    print('\n== orphaned teardrops ==')
    strip_orphan_teardrops(board)

    obs = Obstacles(board)
    added = rejected = 0

    print('\n== tracks ==')
    for net, layer, pts, w in ROUTES:
        lid = LAYER[layer]
        ni = board.FindNet(net)
        if ni is None:
            print('  MISSING NET %s' % net)
            rejected += 1
            continue
        for p1, p2 in zip(pts, pts[1:]):
            if p1 == p2:
                continue
            why = obs.hit_seg(p1, p2, w, net, lid)
            if why:
                print('  REJECT %-14s %s.Cu (%.4f,%.4f)->(%.4f,%.4f) w %.2f: hits %s'
                      % (net, layer, p1[0], p1[1], p2[0], p2[1], w, why))
                rejected += 1
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(IU(p1[0]), IU(p1[1])))
            t.SetEnd(pcbnew.VECTOR2I(IU(p2[0]), IU(p2[1])))
            t.SetWidth(IU(w))
            t.SetLayer(lid)
            t.SetNetCode(ni.GetNetCode())
            board.Add(t)
            obs.add_seg(p1, p2, w, net, lid)
            added += 1

    print('\n== vias ==')
    placed = set()
    for x, y, net, dia, drill in VIAS:
        if (x, y, net) in placed:
            continue
        placed.add((x, y, net))
        why = obs.hit_via(x, y, dia, net)
        if why:
            print('  REJECT via %-14s (%.4f,%.4f) d %.2f: hits %s' % (net, x, y, dia, why))
            rejected += 1
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(IU(x), IU(y)))
        v.SetWidth(IU(dia))
        v.SetDrill(IU(drill))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(FCU, BCU)
        v.SetNetCode(board.FindNet(net).GetNetCode())
        board.Add(v)
        obs.add_via(x, y, dia, net)
        added += 1

    print('\nitems added: %d, rejected: %d' % (added, rejected))
    if rejected:
        print('REFUSING TO SAVE -- a rejected segment means an unrouted branch.')
        sys.stdout.flush()
        os._exit(1)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    bad = verify(board)
    if bad:
        print('\nVERIFY FAILED (%d): not saving.' % bad)
        sys.stdout.flush()
        os._exit(1)
    print('\nverify: all checks pass')

    pcbnew.SaveBoard(board_path, board)
    print('saved %s' % board_path)
    sys.stdout.flush()
    os._exit(0)


if __name__ == '__main__':
    main()
