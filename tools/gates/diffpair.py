"""Gate 3: differential pairs are length-matched and hit 90 ohm against the
stackup actually in the board file -- not a nominal one.

Length is the SHORTEST PATH between the driver pad and the connector pad, found
by Dijkstra over the track graph. It is deliberately NOT the sum of all copper on
the net. These nets legitimately branch -- a USB-C receptacle ties A6 to B6 for
the same signal -- so a naive sum counts the branch as if the signal travelled
it, and it also silently counts any duplicated or retraced copper. Both effects
were present on this board and both made a mismatched pair look matched.

Reading the real stackup is the point of the impedance half: it is what catches
the board being fabricated on a substrate the geometry was never tuned for. The
closed form is an estimate -- see the caveat printed with the result.
"""
import sys, os, re, math, heapq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_board as L
import pcbnew

# (net, driver pad, both connector pads). The matched length is driver -> the
# NEARER of the two connector pads: that is the common signal path. The remaining
# hop to the far pad is the A/B tie a reversible USB-C receptacle requires, and it
# cannot be made symmetric here -- a balanced tee from a midpoint would have to
# cross the other polarity's pad, because the pads interleave at 0.5 mm pitch.
# That tie is reported separately rather than folded into the skew number.
PAIRS = [
    (('/HOST_D+', 'U1.8', ('J1.A6', 'J1.B6')), ('/HOST_D-', 'U1.9', ('J1.A7', 'J1.B7'))),
    (('/PORT_D+', 'U1.12', ('J2.A6', 'J2.B6')), ('/PORT_D-', 'U1.13', ('J2.A7', 'J2.B7'))),
]
SKEW_LIMIT_MM = 0.15
Z_TARGET, Z_TOL = 90.0, 0.10
DIFF_GAP_MM = 0.127
SNAP = 0.005
TOL = 0.02        # mm; endpoints this close are the same node


def stackup_from_file(path):
    txt = open(path).read()
    i = txt.find('(stackup')
    if i < 0:
        return None
    d = 0
    for j in range(i, len(txt)):
        if txt[j] == '(':
            d += 1
        elif txt[j] == ')':
            d -= 1
            if d == 0:
                break
    blk = txt[i:j + 1]
    d1 = re.search(r'\(layer "dielectric 1".*?\(thickness ([\d.]+)\).*?\(epsilon_r ([\d.]+)\)', blk, re.S)
    cu = re.search(r'\(layer "F\.Cu".*?\(thickness ([\d.]+)\)', blk, re.S)
    if not (d1 and cu):
        return None
    return dict(h=float(d1.group(1)), er=float(d1.group(2)), t=float(cu.group(1)))


def z_diff_microstrip(w, s, h, er, t):
    z0 = (87.0 / math.sqrt(er + 1.41)) * math.log(5.98 * h / (0.8 * w + t))
    return 2.0 * z0 * (1.0 - 0.48 * math.exp(-0.96 * s / h))


def pad_xy(board, spec):
    ref, num = spec.split('.')
    fp = board.FindFootprintByReference(ref)
    if fp is None:
        return None
    for p in fp.Pads():
        if p.GetNumber() == num:
            q = p.GetPosition()
            return (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
    return None


def path_length(board, net, a, c):
    """Shortest path a->c along the net's copper. Vias join layers at a point, so
    the graph is keyed on (x, y) only."""
    if a is None or c is None:
        return None, set()
    # Nodes are merged when they coincide within TOL, but each keeps its EXACT
    # coordinate so lengths stay exact. Bucketing on a grid instead would split a
    # net whose endpoints differ by a few microns (seen here: 167.730 vs 167.725
    # landed either side of a bucket boundary and broke the net in two), and
    # coarsening the grid enough to avoid that would inject its own error into
    # the very lengths this gate exists to measure.
    nodes = []
    index = {}

    def key(p):
        cell = (int(p[0] / TOL), int(p[1] / TOL))
        for cx in (cell[0] - 1, cell[0], cell[0] + 1):
            for cy in (cell[1] - 1, cell[1], cell[1] + 1):
                for i in index.get((cx, cy), ()):
                    if math.hypot(nodes[i][0] - p[0], nodes[i][1] - p[1]) <= TOL:
                        return i
        nodes.append(p)
        index.setdefault(cell, []).append(len(nodes) - 1)
        return len(nodes) - 1

    raw, widths = [], set()
    for t in board.GetTracks():
        if t.GetNetname() != net or t.GetClass() == 'PCB_VIA':
            continue
        raw.append(((pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)),
                    (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))))
        widths.add(round(pcbnew.ToMM(t.GetWidth()), 4))
    if not raw:
        return None, widths

    # Split segments at T-junctions. A branch may tee off part-way along another
    # segment; KiCad's connectivity handles that, but a graph keyed only on
    # endpoints would leave the branch unreachable and report a false "no path".
    endpoints = {p for seg in raw for p in seg}

    def on_seg(p, a, c):
        ax, ay = a; cx, cy = c; px, py = p
        dx, dy = cx - ax, cy - ay
        if dx == 0 and dy == 0:
            return False
        t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
        if not (1e-6 < t < 1 - 1e-6):
            return False
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy)) < SNAP

    adj = {}
    # NB: loop variables are s0/s1, not a/c -- a and c are this function's source
    # and destination pads, and rebinding them here silently made every path
    # measure from the last segment's endpoint instead of from the pad.
    for s0, s1 in raw:
        cuts = sorted((p for p in endpoints if on_seg(p, s0, s1)),
                      key=lambda p: math.hypot(p[0] - s0[0], p[1] - s0[1]))
        chain = [s0] + cuts + [s1]
        for u, v in zip(chain, chain[1:]):
            d = math.hypot(v[0] - u[0], v[1] - u[1])
            if d <= 0:
                continue
            adj.setdefault(key(u), []).append((key(v), d))
            adj.setdefault(key(v), []).append((key(u), d))

    # Tracks also connect THROUGH pads. The pair is routed in-line across each ESD
    # array, so a trace ends on pin 1 and another starts on pin 6 with no copper
    # between them -- the pad itself is the link. Without this the net looks broken
    # into separate components and the gate reports a false "no continuous path".
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() != net:
                continue
            bb = pad.GetBoundingBox()
            px0, py0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
            px1, py1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
            inside = [i for i in adj
                      if px0 <= nodes[i][0] <= px1 and py0 <= nodes[i][1] <= py1]
            for i in range(len(inside)):
                for j in range(i + 1, len(inside)):
                    u, v = inside[i], inside[j]
                    d = math.hypot(nodes[u][0] - nodes[v][0], nodes[u][1] - nodes[v][1])
                    adj[u].append((v, d))
                    adj[v].append((u, d))

    def nearest(pt):
        best, bk = None, None
        for i in adj:
            d = math.hypot(nodes[i][0] - pt[0], nodes[i][1] - pt[1])
            if best is None or d < best:
                best, bk = d, i
        return bk, best

    ka, da = nearest(a)
    kc, dc = nearest(c)
    if ka is None or kc is None or da > 1.5 or dc > 1.5:
        return None, widths
    dist = {ka: 0.0}
    pq = [(0.0, ka)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == kc:
            return d + da + dc, widths
        if d > dist.get(u, float('inf')):
            continue
        for v, w in adj.get(u, ()):
            nd = d + w
            if nd < dist.get(v, float('inf')) - 1e-9:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return None, widths


def check(board, board_path):
    su = stackup_from_file(board_path)
    results, ok = [], True
    if su is None:
        return False, [dict(pair='-', error='no (stackup ...) block; 90 ohm is not '
                                            'checkable against anything')]
    def best(net, src, dsts):
        vals, w = [], set()
        for d in dsts:
            l, ww = path_length(board, net, pad_xy(board, src), pad_xy(board, d))
            w |= ww
            if l is not None:
                vals.append(l)
        return (min(vals) if vals else None), (max(vals) - min(vals) if len(vals) > 1 else 0.0), w

    for (na, sa, ta), (nb, sb, tb) in PAIRS:
        la, tie_a, wa = best(na, sa, ta)
        lb, tie_b, wb = best(nb, sb, tb)
        label = na + '/' + nb
        if la is None or lb is None:
            results.append(dict(pair=label, error='unrouted or no continuous path'))
            ok = False
            continue
        widths = wa | wb
        if len(widths) != 1:
            results.append(dict(pair=label, error='mixed track widths %s -- impedance '
                                                  'is not well-defined' % sorted(widths)))
            ok = False
            continue
        w = widths.pop()
        z = z_diff_microstrip(w, DIFF_GAP_MM, su['h'], su['er'], su['t'])
        skew = abs(la - lb)
        ps, pz = skew <= SKEW_LIMIT_MM, abs(z - Z_TARGET) <= Z_TARGET * Z_TOL
        ok = ok and ps and pz
        results.append(dict(pair=label, len_a=la, len_b=lb, skew=skew, w=w,
                            s=DIFF_GAP_MM, h=su['h'], er=su['er'], z=z,
                            pass_skew=ps, pass_z=pz, tie_a=tie_a, tie_b=tie_b))
    return ok, results


def main():
    path = sys.argv[1]
    board = L.load(path)
    ok, results = check(board, path)
    for r in results:
        if 'error' in r:
            print("  FAIL  %-22s %s" % (r['pair'], r['error']))
            continue
        print("  %-22s path %.3f / %.3f mm  skew %.4f mm  [%s]"
              % (r['pair'], r['len_a'], r['len_b'], r['skew'],
                 'OK' if r['pass_skew'] else 'FAIL'))
        print("  %-22s w=%.3f s=%.3f h=%.4f er=%.2f -> Zdiff %.2f ohm  [%s]"
              % ('', r['w'], r['s'], r['h'], r['er'], r['z'],
                 'OK' if r['pass_z'] else 'FAIL'))
        print("  %-22s USB-C A/B tie adds %.3f / %.3f mm beyond the near pad"
              % ('', r['tie_a'], r['tie_b']))
    print("\nGate 3 (diff pairs): skew limit %.2f mm, Zdiff %.0f ohm +/-%d%%"
          % (SKEW_LIMIT_MM, Z_TARGET, int(Z_TOL * 100)))
    print("Lengths are driver-to-connector shortest path, not total copper on the net.")
    print("Zdiff is an IPC-2141 estimate; it ignores solder mask and etch taper, both")
    print("of which lower it. Treat it as a geometry/stackup consistency check and")
    print("defer to the fabricator's impedance table for the real number.")
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
