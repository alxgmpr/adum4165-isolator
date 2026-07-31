"""Gate 2: no copper within 1 mm of either long board edge, any layer.

The 50 mm end edges are deliberately excluded -- J1 and J2 sit flush there
by constraint 6. Only the 120 mm long edges are gripped by the extrusion's
aluminium slots, and those are the ones that can short GND1 to GND2.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_board as L

FLOOR_MM = 1.0
TARGET_MM = 2.0


def check(board, floor_mm=FLOOR_MM, target_mm=TARGET_MM):
    violations, warnings = [], []
    for lid, lname, kind, net, (x0, y0, x1, y1) in L.copper_items(board):
        top_gap = y0 - 0.0
        bot_gap = L.BOARD_WID_MM - y1
        worst = min(top_gap, bot_gap)
        rec = dict(layer=lname, kind=kind, net=net, gap_mm=round(worst, 4),
                   edge='y=0' if top_gap < bot_gap else 'y=%.0f' % L.BOARD_WID_MM)
        if worst < floor_mm:
            violations.append(rec)
        elif worst < target_mm:
            warnings.append(rec)
    return (not violations), violations, warnings


def main():
    board = L.load(sys.argv[1])
    ok, violations, warnings = check(board)
    for w in warnings:
        print("  WARN  %(layer)-12s %(kind)-22s %(net)-14s %(gap_mm)6.3f mm from %(edge)s" % w)
    for v in violations:
        print("  FAIL  %(layer)-12s %(kind)-22s %(net)-14s %(gap_mm)6.3f mm from %(edge)s" % v)
    print("\nGate 2 (edge pullback): %d violations below %.1f mm, %d inside %.1f mm target"
          % (len(violations), FLOOR_MM, len(warnings), TARGET_MM))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
