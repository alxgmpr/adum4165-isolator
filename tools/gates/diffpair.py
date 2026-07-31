"""Gate 3: differential pairs are length-matched and hit 90 ohm against the
stackup actually in the board file -- not a nominal one.

Reading the real stackup is the point of this gate: it is what catches the board
being fabricated on a substrate the trace geometry was never tuned for.
"""
import sys, os, re, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_board as L
import pcbnew

PAIRS = [('/HOST_D+', '/HOST_D-'), ('/PORT_D+', '/PORT_D-')]
SKEW_LIMIT_MM = 0.15
Z_TARGET, Z_TOL = 90.0, 0.10
DIFF_GAP_MM = 0.127   # USB_DIFF90 diff_pair_gap


def stackup_from_file(path):
    """Outer-layer geometry: prepreg thickness and Er between F.Cu and In1.Cu."""
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
    """Edge-coupled microstrip. IPC-2141 single-ended Z0, then the standard
    coupling correction for differential pairs."""
    z0 = (87.0 / math.sqrt(er + 1.41)) * math.log(5.98 * h / (0.8 * w + t))
    return 2.0 * z0 * (1.0 - 0.48 * math.exp(-0.96 * s / h))


def net_length(board, net):
    return sum(pcbnew.ToMM(t.GetLength()) for t in board.GetTracks()
               if t.GetNetname() == net and t.GetClass() != 'PCB_VIA')


def pair_widths(board, net):
    return {round(pcbnew.ToMM(t.GetWidth()), 4) for t in board.GetTracks()
            if t.GetNetname() == net and t.GetClass() != 'PCB_VIA'}


def check(board, board_path):
    su = stackup_from_file(board_path)
    results, ok = [], True
    if su is None:
        return False, [dict(pair='-', error='no (stackup ...) block in the board file; '
                                            '90 ohm cannot be checked against anything')]
    for a, c in PAIRS:
        la, lc = net_length(board, a), net_length(board, c)
        skew = abs(la - lc)
        widths = pair_widths(board, a) | pair_widths(board, c)
        if la == 0 or lc == 0:
            results.append(dict(pair=a + '/' + c, error='unrouted'))
            ok = False
            continue
        if len(widths) != 1:
            results.append(dict(pair=a + '/' + c,
                                error='mixed track widths %s -- impedance is not '
                                      'well-defined' % sorted(widths)))
            ok = False
            continue
        w = widths.pop()
        z = z_diff_microstrip(w, DIFF_GAP_MM, su['h'], su['er'], su['t'])
        pass_skew = skew <= SKEW_LIMIT_MM
        pass_z = abs(z - Z_TARGET) <= Z_TARGET * Z_TOL
        ok = ok and pass_skew and pass_z
        results.append(dict(pair=a + '/' + c, len_a=la, len_b=lc, skew=skew,
                            w=w, s=DIFF_GAP_MM, h=su['h'], er=su['er'], z=z,
                            pass_skew=pass_skew, pass_z=pass_z))
    return ok, results


def main():
    path = sys.argv[1]
    board = L.load(path)
    ok, results = check(board, path)
    for r in results:
        if 'error' in r:
            print("  FAIL  %-22s %s" % (r['pair'], r['error']))
            continue
        print("  %-22s len %.3f / %.3f mm  skew %.4f mm  [%s]"
              % (r['pair'], r['len_a'], r['len_b'], r['skew'],
                 'OK' if r['pass_skew'] else 'FAIL'))
        print("  %-22s w=%.3f s=%.3f h=%.4f er=%.2f -> Zdiff %.2f ohm  [%s]"
              % ('', r['w'], r['s'], r['h'], r['er'], r['z'],
                 'OK' if r['pass_z'] else 'FAIL'))
    print("\nGate 3 (diff pairs): skew limit %.2f mm, Zdiff %.0f ohm +/-%d%%"
          % (SKEW_LIMIT_MM, Z_TARGET, int(Z_TOL * 100)))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
