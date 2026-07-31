"""Gate 1: minimum HOST_SIDE <-> ISO_SIDE copper separation, every layer, >= 8.3 mm.

Creepage-aware on F.Cu. Where the straight line between two copper features
crosses a board cutout (the routed slot under T1), the measured path runs around
the cutout, because that is the surface path a contaminant film follows. This is
what lets T1's 7.5100 mm land pattern pass on the strength of its slot rather
than by exemption.

On In1/In2/B.Cu the assertion is straight-line: T1 has no pads there, and
creepage is a surface phenomenon -- inner layers face solid dielectric.
"""
import sys, os, json, fnmatch, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_board as L
import netclass_coverage as NC
import pcbnew

REQUIRED_MM = 8.3


def _domain_map(pro_path, netlist_path):
    pro = json.load(open(pro_path))
    pats = [(p['netclass'], p['pattern']) for p in pro['net_settings']['netclass_patterns']
            if p['netclass'] in ('HOST_SIDE', 'ISO_SIDE')]
    out = {}
    for net in NC.nets_from_netlist(netlist_path):
        hits = {c for c, p in pats if fnmatch.fnmatch(net, p)}
        if len(hits) == 1:
            out[net] = hits.pop()
    return out


def _slots(board):
    """Bounding boxes (mm) of Edge.Cuts cutouts -- routed slots, not the perimeter.

    A cutout is an Edge.Cuts item lying STRICTLY inside the board outline. Testing
    "is it smaller than the board" instead is wrong twice over: rounded corner
    arcs are small but are part of the perimeter, and a barrier slot may legally
    span almost the whole board height -- this one is 46.06 mm of a 50 mm board,
    which a 90%-of-height test silently discarded, taking Gate 1's credit for the
    slot with it and reporting T1's bare 7.51 mm clearance as a failure.
    """
    bx0, by0, bx1, by1 = L.board_box(board)
    M = 0.5                      # margin inside which an item counts as perimeter
    out = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        bb = d.GetBoundingBox()
        x0, y0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
        x1, y1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
        if x0 > bx0 + M and y0 > by0 + M and x1 < bx1 - M and y1 < by1 - M:
            out.append((x0, y0, x1, y1))
    if not out:
        return []
    # merge overlapping cutout fragments into single rectangles
    merged = []
    for s in out:
        for i, m in enumerate(merged):
            if not (s[2] < m[0] - 0.2 or m[2] < s[0] - 0.2 or
                    s[3] < m[1] - 0.2 or m[3] < s[1] - 0.2):
                merged[i] = (min(s[0], m[0]), min(s[1], m[1]),
                             max(s[2], m[2]), max(s[3], m[3]))
                break
        else:
            merged.append(s)
    return merged


def _gap(a, b):
    """Straight-line gap in mm between two axis-aligned bboxes."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(bx0 - ax1, ax0 - bx1, 0.0)
    dy = max(by0 - ay1, ay0 - by1, 0.0)
    return math.hypot(dx, dy)


def _crosses(a, b, slot):
    """True if a straight path between a and b passes through the slot: the slot
    lies in the x-gap between them and their y ranges overlap it."""
    sx0, sy0, sx1, sy1 = slot
    lo, hi = min(a[2], b[2]), max(a[0], b[0])
    if not (lo <= sx0 and hi >= sx1):
        return False
    ylo, yhi = min(a[1], b[1]), max(a[3], b[3])
    return not (yhi < sy0 or ylo > sy1)


def _creepage(a, b, slots):
    """Straight-line gap, or the detour around a slot end when one intervenes."""
    g = _gap(a, b)
    for s in slots:
        if _crosses(a, b, s):
            sx0, sy0, sx1, sy1 = s
            mid_y = (a[1] + a[3] + b[1] + b[3]) / 4.0
            # distance the path must travel to clear the nearer slot end, there and back
            to_top = max(mid_y - sy0, 0.0)
            to_bot = max(sy1 - mid_y, 0.0)
            g = g + 2.0 * min(to_top, to_bot)
    return g


def check(board, pro_path, netlist_path):
    dom = _domain_map(pro_path, netlist_path)
    slots = _slots(board)
    by_layer = {}
    for lid, lname, kind, net, bb in L.copper_items(board):
        if net in dom:
            by_layer.setdefault(lname, {'HOST_SIDE': [], 'ISO_SIDE': []})[dom[net]].append((kind, net, bb))

    per_layer, failures = {}, []
    for lname, sides in sorted(by_layer.items()):
        worst, worst_pair = float('inf'), None
        for hk, hn, hb in sides['HOST_SIDE']:
            for ik, inn, ib in sides['ISO_SIDE']:
                g = _creepage(hb, ib, slots) if lname == 'F.Cu' else _gap(hb, ib)
                if g < worst:
                    worst, worst_pair = g, (hk, hn, ik, inn)
        if worst_pair is None:
            continue
        per_layer[lname] = worst
        if worst < REQUIRED_MM:
            failures.append(dict(layer=lname, gap=round(worst, 4),
                                 host='%s (%s)' % (worst_pair[0], worst_pair[1]),
                                 iso='%s (%s)' % (worst_pair[2], worst_pair[3])))
    return (not failures), per_layer, failures


def main():
    board_path, pro_path, netlist_path = sys.argv[1], sys.argv[2], sys.argv[3]

    cov_ok, unclassified, both, missing = NC.check(pro_path, netlist_path)
    if not cov_ok:
        print("  FAIL  netclass coverage is incomplete -- the barrier rules do not")
        print("        police every net, so this gate cannot be trusted. Fix first:")
        for n in unclassified + both + missing:
            print("          ", n)
        print("VERDICT: FAIL")
        sys.exit(1)

    board = L.load(board_path)
    ok, per_layer, failures = check(board, pro_path, netlist_path)
    for lname, g in per_layer.items():
        mode = 'creepage ' if lname == 'F.Cu' else 'clearance'
        print("  %-12s min HOST<->ISO %s: %8.4f mm" % (lname, mode, g))
    for f in failures:
        print("  FAIL  %(layer)s  %(gap).4f mm  between %(host)s and %(iso)s" % f)
    print("\nGate 1 (barrier >= %.1f mm): %d layer(s) failing" % (REQUIRED_MM, len(failures)))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
