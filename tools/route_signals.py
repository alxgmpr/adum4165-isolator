"""Route /PORT_D+- as a matched pair, plus the remaining isolated-side signals.

Coordinates are ABSOLUTE mm, as stored in the .kicad_pcb -- same convention as
tools/route_iso.py, not the board-local frame tools/place_iso.py uses.

Obstacle testing, the refuse-to-save-on-reject discipline and the Obstacles
class itself are reused from tools/route_iso.py; only the clearance model is
extended, because a differential pair needs two different numbers (see
PairObstacles below).

--------------------------------------------------------------------------
The differential pair
--------------------------------------------------------------------------

Backbone. U3, J2 and U1 did not move in this plan, so the pair's F.Cu backbone
is 2c1167d's -- symmetric fan-in at U1, one crossover, parallel 45 degree
fan-out into U3, and the lane geometry through U3 into J2. That geometry is
already known DRC-clean against this footprint set. Two things are new:

  * the crossover is rebuilt symmetrically (see below);
  * U3.1 -> U3.6 can no longer be a straight trace, and D- carries a tuned
    meander instead of 2c1167d's untuned one.

Crossover. At U1, D+ is SOUTH (y 106.1484) and D- NORTH (104.8784); at U3, D+
is NORTH (100.7534) and D- SOUTH (102.6534), so the pair must swap. It swaps at
x 167.225..169.225, in the middle of the F.Cu corridor Task 5 verified clear
(x 153..190, y 103.5..111). D+ takes the B.Cu dip; D- crosses over it on F.Cu.
The pair opens from its 0.337 pitch to 1.337 first: at 0.337 a 0.5 mm via would
sit 0.316 mm from the other polarity's centreline and short it. Both halves
travel the same distance through the crossover -- 0.5*sqrt(2) in, the same
diagonal across, 0.5*sqrt(2) out -- so it is length-neutral by construction.

It is NOT sited at x 179.000: /ISO_5V_IND crosses the corridor there on B.Cu.

U3.1 -> U3.6. 2c1167d ran D+ straight across the gap between U3's two pad
columns at y 100.7534, and reached U3.5 with a via in its own pad. Task 5
inverted that: /PORT_VBUS_J2 now comes DOWN that 0.95 mm gap (x 192.625..193.125
after width) to reach U3.5 from the north, which closes y 100.7534 to F.Cu --
a 0.21 mm trace needs 0.505 mm of centreline clearance there and the gap offers
at most 0.475 mm on either side, and both ends of the crossing are pad edges.
There is no way round it either: /PORT_VBUS_J2 also walls off the north at
y 99.350 (x 189.4..197.7), and the south is U3's own GND2 and D- pads.

So D+ hops the spine on B.Cu, north of the pad row, between two vias that clear
the spine by 0.225 mm edge-to-edge and the y 99.350 run by 0.30 mm. The hop is
1.45 mm of B.Cu and costs D+ about 0.72 mm of extra path, which the D- meander
pays back. The eight power nets were not touched to make room -- they are
routed, verified and reviewed, and /PORT_VBUS_J2 is one of them.

Length matching. Gate 3 measures the SHORTEST path from the driver pad to the
NEARER of the two connector pads, so what has to match is U1.12 -> J2.B6 against
U1.13 -> J2.B7. The A/B tie beyond the near pad is reported separately and is
not matched -- it cannot be, the pads interleave at 0.5 mm pitch. Everything
above is symmetric except the U3 hop and the fan-out (D+ climbs 1.563 mm more
than D- to reach its U3 pin), so D- carries a three-tooth 45 degree serpentine
in the corridor. MEANDER_A is solved, not guessed: run this file with --tune and
it prints the amplitude that zeroes the skew.

--------------------------------------------------------------------------
The remaining signals
--------------------------------------------------------------------------

/PGOOD2, /VDD2, /nFAULT, /PG_LED_A, /PG_LED_K, /FAULT_LED_A, /PORT_CC1 and
/PORT_CC2 connect parts that did not move in this plan, so they are restored
from 2c1167d verbatim and re-checked against the copper Tasks 4 and 5 added.
/PGOOD2's B.Cu leg passes under the pair; the reference plane for both is the
inner GND_SPLIT layer, so that crossing costs the pair nothing, and its via at
(154.450, 104.500) sits 0.845 mm off the D- centreline.

/RECT_A and /RECT_B are new: D1 and D2 both moved in Task 4. Both are the
shortest legal run at 0.5 mm -- straight for /RECT_A, one 45 degree step for
/RECT_B, which has to climb 1.61 mm into D2.2.

/ILIM_SET is the one that got worse. In 2c1167d R3 sat beside U6 and the link
was 1.9 mm of F.Cu. Task 4 moved R3 to (182.300, 98.725), and U6.5 is now boxed
in: north is U6.6 plus /PORT_VBUS's 0.5 mm trunk at y 100.753 (x 181.762..
184.475 with caps) plus that net's teardrop, east is C15.1, and the one F.Cu
slot left -- between the y 99.600 trunk and C15's pad tops -- is 0.428 mm where
a 0.2 mm trace needs 0.5 mm. Going round the outside of U6 measures ~11.5 mm.
So it hops on B.Cu: 0.888 mm of F.Cu east out of U6.5, 2.23 mm of B.Cu, 0.825 mm
of F.Cu into R3.1 -- 3.94 mm total. SLVS841F wants this node short; 3.94 mm with
two vias is the shortest thing available without moving a reviewed part.

GND1/GND2 are NOT this file's job: the ground planes are on the inner layers and
their pads reach them through stitching vias, which Task 7 re-places.

Usage:
    <kicad python3> route_signals.py <board.kicad_pcb> [--tune]
"""
import sys, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
import route_iso as RI

IU, MM = pcbnew.FromMM, pcbnew.ToMM
FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu
LAYER = {'F': FCU, 'B': BCU}

W_DIFF = 0.21                     # USB_DIFF90
VIA_DIFF, DRL_DIFF = 0.5, 0.3
W_SIG = 0.2                       # ISO_SIDE
VIA_SIG, DRL_SIG = 0.6, 0.3
W_RECT = 0.5                      # rectifier legs, as in 2c1167d
GAP_DIFF = 0.127                  # USB_DIFF90 clearance, D+ against D-

DP, DM = '/PORT_D+', '/PORT_D-'
SIBLING = {DP: DM, DM: DP}

# ---- pair rails and waypoints (see module docstring) ----
YA = 105.6819          # south rail: D+ before the crossover, D- after
YB = 105.3449          # north rail: D- before the crossover, D+ after
XC0, XC1 = 167.225, 169.225                 # crossover span
YW_S, YW_N = 106.1819, 104.8449             # opened rails inside it
X_FAN_P, X_FAN_M = 185.4936, 185.6332       # where each half starts its descent
MEANDER_X0 = 156.500                        # D- serpentine, first tooth
MEANDER_TEETH, MEANDER_W, MEANDER_PITCH = 3, 0.600, 0.800
MEANDER_A = 0.2911                          # solved by --tune; see docstring


def meander(x0, y, amp, teeth=MEANDER_TEETH, w=MEANDER_W, gap=MEANDER_PITCH):
    """45-degree serpentine on a rail at y, bulging NORTH (away from D+).

    Each tooth adds exactly 2*amp*(sqrt(2)-1); returns waypoints from (x0, y)
    to the rail again, so it splices into a straight run.
    """
    pts, x = [(x0, y)], x0
    for _ in range(teeth):
        pts += [(x + amp, y - amp), (x + amp + w, y - amp), (x + 2 * amp + w, y)]
        x += 2 * amp + w + gap
        pts.append((x, y))
    return pts


def pair_routes(amp):
    """(net, layer, [pts], width) for both halves, plus the pair's vias."""
    dp_a = [(151.7750, 106.1484), (152.9000, 106.1484), (153.3665, YA),
            (XC0, YA), (XC0 + 0.5, YW_S)]
    dp_b = [(XC0 + 0.5, YW_S), (XC1 - 0.5, YW_N)]                    # B.Cu dip
    dp_c = [(XC1 - 0.5, YW_N), (XC1, YB), (X_FAN_P, YB),
            (189.3036, 101.5349), (189.9622, 101.5349),
            (190.7437, 100.7534), (191.7375, 100.7534),
            (192.1500, 100.3409), (192.1500, 100.1500)]              # into hop
    dp_d = [(192.1500, 100.1500), (193.6000, 100.1500)]              # B.Cu hop
    dp_e = [(193.6000, 100.1500), (193.6000, 100.3409), (194.0125, 100.7534),
            (195.0063, 100.7534), (195.7878, 101.5349), (196.4573, 101.5349),
            (196.9208, 101.0714), (197.5820, 101.0714), (197.7000, 100.9534)]
    #      A/B tie: round the east of J2.A7, exactly 2c1167d's loop. It leans on
    #      isolator.kicad_dru's connector-neckdown 0.127 mm inside J2.
    dp_tie = [(197.7000, 100.9534), (198.4250, 100.9534), (198.6570, 101.1854),
              (198.6570, 101.7214), (198.4250, 101.9534), (197.7000, 101.9534)]

    dm_a = ([(151.7750, 104.8784), (152.9000, 104.8784), (153.3665, YB)]
            + meander(MEANDER_X0, YB, amp)
            + [(XC0, YB), (XC0 + 0.5, YW_N), (XC1 - 0.5, YW_S),
               (XC1, YA), (X_FAN_M, YA),
               (189.4432, 101.8719), (189.9622, 101.8719),
               (190.7437, 102.6534), (191.7375, 102.6534),
               (194.0125, 102.6534), (195.0063, 102.6534),
               (195.7878, 101.8719), (196.4573, 101.8719),
               (196.7430, 102.1576), (196.9208, 102.3354),
               (197.5820, 102.3354), (197.7000, 102.4534)])
    #      A/B tie tees off the main run rather than retracing it: a retrace is
    #      duplicate copper on the same net AND inflates what Gate 3 measures.
    dm_tie = [(196.7430, 102.1576), (196.7430, 101.7492),
              (197.0388, 101.4534), (197.7000, 101.4534)]

    routes = [(DP, 'F', dp_a, W_DIFF), (DP, 'B', dp_b, W_DIFF),
              (DP, 'F', dp_c, W_DIFF), (DP, 'B', dp_d, W_DIFF),
              (DP, 'F', dp_e, W_DIFF), (DP, 'F', dp_tie, W_DIFF),
              (DM, 'F', dm_a, W_DIFF), (DM, 'F', dm_tie, W_DIFF)]
    vias = [(XC0 + 0.5, YW_S, DP, VIA_DIFF, DRL_DIFF),
            (XC1 - 0.5, YW_N, DP, VIA_DIFF, DRL_DIFF),
            (192.1500, 100.1500, DP, VIA_DIFF, DRL_DIFF),
            (193.6000, 100.1500, DP, VIA_DIFF, DRL_DIFF)]
    return routes, vias


SIGNALS = [
    # ---- /RECT_A: T1.6 -> D1.2, straight; D1.2's pad is 2.5 x 1.8 mm
    ('/RECT_A', 'F', [(151.5800, 83.8134), (156.2000, 83.8134)], W_RECT),
    # ---- /RECT_B: T1.4 -> D2.2, one 45 degree step up into the pad
    ('/RECT_B', 'F', [(151.5800, 89.9134), (154.3000, 89.9134),
                      (155.9134, 88.3000), (156.2000, 88.3000)], W_RECT),

    # ---- /ILIM_SET: U6.5 east, B.Cu over /PORT_VBUS's trunk, into R3.1
    ('/ILIM_SET', 'F', [(182.0125, 101.7034), (182.9000, 101.7034)], W_SIG),
    ('/ILIM_SET', 'B', [(182.9000, 101.7034), (182.3000, 99.5500)], W_SIG),
    ('/ILIM_SET', 'F', [(182.3000, 99.5500), (182.3000, 98.7250)], W_SIG),

    # ---- /nFAULT: U6.4 -> B.Cu south past the LED strip -> R4.2 -> D4.1
    ('/nFAULT', 'F', [(182.0125, 102.6534), (182.9840, 102.6534),
                      (183.7500, 103.4194)], W_SIG),
    ('/nFAULT', 'B', [(183.7500, 103.4194), (183.7500, 109.3575),
                      (184.8750, 110.4825), (184.8750, 115.0175)], W_SIG),
    ('/nFAULT', 'F', [(184.8750, 115.0175), (184.8750, 115.8784)], W_SIG),
    ('/nFAULT', 'F', [(184.8750, 115.8784), (178.9125, 115.8784),
                      (178.0875, 116.7034)], W_SIG),

    # ---- /PGOOD2: U1.14 -> R9.2, and U1.14 -> B.Cu -> R10.1 -> Q1.1
    ('/PGOOD2', 'F', [(151.7750, 103.6084), (152.5166, 103.6084),
                      (154.2500, 101.8750)], W_SIG),
    ('/PGOOD2', 'F', [(152.5166, 103.6084), (153.5584, 103.6084),
                      (154.4500, 104.5000)], W_SIG),
    ('/PGOOD2', 'B', [(154.4500, 104.5000), (154.4500, 108.5000),
                      (161.7000, 115.7500)], W_SIG),
    ('/PGOOD2', 'F', [(161.7000, 115.7500), (163.1750, 115.7500)], W_SIG),
    ('/PGOOD2', 'F', [(165.9375, 115.7534), (163.4216, 115.7534)], W_SIG),

    # ---- /VDD2: U1.18 -> C13.1 -> R9.1
    ('/VDD2', 'F', [(151.7750, 98.5284), (154.1966, 98.5284)], W_SIG),
    ('/VDD2', 'F', [(154.2250, 98.5000), (154.2250, 100.2000)], W_SIG),

    # ---- indicator LEDs, restored from 2c1167d
    ('/PG_LED_K', 'F', [(167.8125, 116.7034), (172.0875, 116.7034)], W_SIG),
    ('/PG_LED_A', 'F', [(173.6625, 116.7034), (173.6625, 119.0909),
                        (172.8750, 119.8784)], W_SIG),
    ('/FAULT_LED_A', 'F', [(179.6625, 116.7034), (179.6625, 119.0909),
                           (178.8750, 119.8784)], W_SIG),

    # ---- CC pull-ups: both go round the east of J2's pad field
    #      2c1167d ran the return leg at y 106.7504, which clears J2's shield
    #      pad by 0.126976 mm -- 24 nm under the connector-neckdown rule it was
    #      cut to. It is 0.05 mm further south here so the number is a margin
    #      and not a rounding coin-flip; the diagonal into R7.2 is unchanged.
    ('/PORT_CC1', 'F', [(197.7000, 102.9534), (198.4653, 102.9534),
                        (199.8920, 104.3801), (199.8920, 106.3745),
                        (199.4661, 106.8004), (198.2746, 106.8004),
                        (197.1750, 107.9000)], W_SIG),
    ('/PORT_CC2', 'F', [(197.7000, 99.9534), (198.4250, 99.9534),
                        (200.5500, 102.0784), (200.5500, 107.9000)], W_SIG),
]

SIGNAL_VIAS = [
    (182.9000, 101.7034, '/ILIM_SET', VIA_SIG, DRL_SIG),
    (182.3000, 99.5500, '/ILIM_SET', VIA_SIG, DRL_SIG),
    (183.7500, 103.4194, '/nFAULT', VIA_SIG, DRL_SIG),
    (184.8750, 115.0175, '/nFAULT', VIA_SIG, DRL_SIG),
    (154.4500, 104.5000, '/PGOOD2', VIA_SIG, DRL_SIG),
    (161.7000, 115.7500, '/PGOOD2', VIA_SIG, DRL_SIG),
]

NETS = [DP, DM, '/nFAULT', '/PGOOD2', '/ILIM_SET', '/PG_LED_A', '/PG_LED_K',
        '/FAULT_LED_A', '/PORT_CC1', '/PORT_CC2', '/RECT_A', '/RECT_B', '/VDD2']

BARRIER_X = (142.72, 151.03)
BAND_Y = (78.70, 124.70)


class PairObstacles(RI.Obstacles):
    """route_iso.Obstacles, but with the pair's second clearance number.

    /PORT_D+ resolves to netclass "USB_DIFF90,ISO_SIDE". Against everything on
    the board that means max(0.127, 0.15) = 0.15 -- but against its own sibling
    both sides are USB_DIFF90, so the number is 0.127, which is exactly the
    designed gap at the 0.337 mm pitch. Probing the sibling at 0.15 would reject
    the pair's own coupling; probing everything at 0.127 would under-check.
    """

    def _probe_split(self, shape, net, lid, clr):
        sib = SIBLING.get(net)
        for n, l, it, label in self.board:
            if n == net or l != lid:
                continue
            c = IU(min(clr, GAP_DIFF)) if n == sib else IU(clr)
            if it.GetClass() == 'PAD':
                if it.GetEffectiveShape(l).Collide(shape, c):
                    return label
            elif it.GetEffectiveShape().Collide(shape, c):
                return label
        for n, l, sh, label in self.mine:
            if n == net or l != lid:
                continue
            c = IU(min(clr, GAP_DIFF)) if n == sib else IU(clr)
            if sh.Collide(shape, c):
                return label
        return None

    def hit_seg(self, p1, p2, w, net, lid):
        cand = pcbnew.SHAPE_SEGMENT(RI.V(*p1), RI.V(*p2), IU(w))
        return self._probe_split(cand, net, lid, self.clearance_at((p1, p2)))

    def hit_via(self, x, y, dia, net):
        cand = pcbnew.SHAPE_SEGMENT(RI.V(x, y), RI.V(x, y), IU(dia))
        for lid in (FCU, BCU):
            why = self._probe_split(cand, net, lid, self.clearance_at(((x, y),)))
            if why:
                return why
        return None


def polyline(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def tune():
    """Solve MEANDER_A so the two measured paths are equal.

    The measured path is driver -> nearer connector pad, so it is the main chain
    of each half and NOT the A/B tie. Each meander tooth adds exactly
    2*A*(sqrt(2)-1), so one evaluation at A=0 fixes the answer.
    """
    routes, _ = pair_routes(0.0)
    keep = {DP: [0, 1, 2, 3, 4], DM: [6]}      # indices of the main chains
    length = {}
    for net in (DP, DM):
        length[net] = sum(polyline(routes[i][2]) for i in keep[net])
    excess = length[DP] - length[DM]
    per = 2.0 * (math.sqrt(2.0) - 1.0) * MEANDER_TEETH
    amp = excess / per
    print('  D+ main chain  %.4f mm' % length[DP])
    print('  D- main chain  %.4f mm  (meander amplitude 0)' % length[DM])
    print('  D+ excess      %.4f mm' % excess)
    print('  %d teeth add 2*A*(sqrt2-1) each -> MEANDER_A = %.4f mm'
          % (MEANDER_TEETH, amp))
    routes, _ = pair_routes(amp)
    chk = {net: sum(polyline(routes[i][2]) for i in keep[net]) for net in (DP, DM)}
    print('  check: D+ %.4f  D- %.4f  skew %.6f mm'
          % (chk[DP], chk[DM], abs(chk[DP] - chk[DM])))
    return amp


def verify(board):
    bad = 0
    print('\n== connectivity (tracks/vias/pads only, zones excluded) ==')
    for net in NETS:
        pads, elems = [], []
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
        ok = len(roots) == 1
        print('  %s  %-15s %2d pads, %d cluster(s)'
              % ('ok  ' if ok else 'FAIL', net, len(pads), len(roots)))
        if not ok:
            bad += 1

    print('\n== barrier keepout / copper band ==')
    bx0, bx1 = BARRIER_X
    by0, by1 = BAND_Y
    hits = []
    for t in board.GetTracks():
        if t.GetNetname() not in NETS:
            continue
        if t.GetClass() == 'PCB_VIA':
            r = MM(t.GetBoundingBox().GetWidth()) / 2.0
            q = t.GetPosition()
            a = b = (MM(q.x), MM(q.y))
        else:
            r = MM(t.GetWidth()) / 2.0
            s, e = t.GetStart(), t.GetEnd()
            a, b = (MM(s.x), MM(s.y)), (MM(e.x), MM(e.y))
        lo_x, hi_x = min(a[0], b[0]) - r, max(a[0], b[0]) + r
        lo_y, hi_y = min(a[1], b[1]) - r, max(a[1], b[1]) + r
        where = '(%.3f,%.3f)-(%.3f,%.3f)' % (a[0], a[1], b[0], b[1])
        if hi_x > bx0 and lo_x < bx1:
            hits.append(('BARRIER', t.GetNetname(), where))
        if lo_y < by0 or hi_y > by1:
            hits.append(('BAND', t.GetNetname(), where))
    for kind, net, where in hits:
        print('  FAIL  %-10s %-15s %s' % (kind, net, where))
    bad += len(hits)
    if not hits:
        print('  ok    nothing added enters x %.2f..%.2f or leaves y %.2f..%.2f'
              % (bx0, bx1, by0, by1))

    board.BuildConnectivity()
    conn = board.GetConnectivity()
    conn.RecalculateRatsnest()
    n = conn.GetUnconnectedCount(False)
    print('\n== ratsnest ==\n  board-wide unconnected items: %d' % n)
    print('  (GND1/GND2 reach their inner planes through stitching vias,')
    print('   which Task 7 re-places -- those are not this file\'s to close.)')
    return bad


def main():
    board_path = sys.argv[1]
    tune_only = '--tune' in sys.argv
    board = pcbnew.LoadBoard(board_path)
    if board is None:
        print('LoadBoard returned None -- is %r a *.kicad_pcb?' % board_path)
        sys.exit(2)

    print('== meander solve ==')
    solved = tune()
    if tune_only:
        sys.stdout.flush()
        os._exit(0)
    if abs(solved - MEANDER_A) > 5e-4:
        print('\nMEANDER_A is %.4f but the geometry now wants %.4f -- update it.'
              % (MEANDER_A, solved))
        sys.stdout.flush()
        os._exit(1)

    print('\n== pre-flight ==')
    existing = {}
    for t in board.GetTracks():
        n = t.GetNetname()
        if n in NETS:
            existing[n] = existing.get(n, 0) + 1
    if existing:
        for n in sorted(existing):
            print('  %-15s already carries %d copper item(s)' % (n, existing[n]))
        print('\nREFUSING TO RUN: these nets are already routed. This script is')
        print('not idempotent -- a re-run would silently double the copper,')
        print('because same-net items are skipped by the obstacle test.')
        sys.stdout.flush()
        os._exit(1)
    print('  ok    none of the %d nets carries copper yet' % len(NETS))

    routes, vias = pair_routes(MEANDER_A)
    routes = routes + SIGNALS
    vias = vias + SIGNAL_VIAS

    obs = PairObstacles(board)
    added = rejected = 0

    print('\n== tracks ==')
    for net, layer, pts, w in routes:
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
    print('  %d segments added' % added)

    print('\n== vias ==')
    for x, y, net, dia, drill in vias:
        why = obs.hit_via(x, y, dia, net)
        if why:
            print('  REJECT via %-14s (%.4f,%.4f) d %.2f: hits %s'
                  % (net, x, y, dia, why))
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
    print('  %d vias placed' % len(vias))

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
