"""Gate 5: every decoupling capacitor sits within budget of the pin it serves.

This gate exists because of a specific failure. /ISO_5V once carried U5's
output, U1's VBUS2 pin and U6's input under one name, and the board satisfied
C12 -- drawn on the sheet as U1's bypass -- at U6 instead, 26.21 mm from the pin
it belonged to. The schematic pass fixed the netlist so that can no longer
happen by accident. This gate covers what the netlist still cannot say: a
capacitor on the correct net, placed too far from its own pin.

Distances are pad-centre to pad-centre with footprint rotation applied. The
ordering rules matter as much as the distances -- a bulk cap inboard of the
ceramic it is meant to back up is a defect even when both are within budget.

Usage: <kicad python3> decoupling.py <board.kicad_pcb>
"""
import sys, os, math, pcbnew

# (cap, [owner pins], budget mm). Nearest owner pin wins unless the cap is
# listed in FARTHEST below.
OWNS = [
    ('C12', [('U1', '20')], 3.0),
    ('C13', [('U1', '18')], 3.0),
    ('C16', [('U6', '1')],  3.0),
    ('C15', [('U6', '6')],  3.0),
    ('C14', [('U6', '6')],  6.0),
    ('C11', [('U5', '1')],  3.0),
    ('C10', [('U5', '1')],  4.0),
    ('C9',  [('U5', '8')],  3.5),
    ('C8',  [('D1', '1'), ('D2', '1')], 4.5),   # FARTHER of the two -- see FARTHEST
    ('C6',  [('U4', '2')],  2.5),
    ('C7',  [('U4', '2')],  3.5),
    ('C17', [('T1', '2')],  4.0),
    ('C4',  [('U1', '1')],  3.5),
    ('C5',  [('U1', '3')],  4.0),
]

# Caps measured to the FARTHER of their owner pins rather than the nearest.
# C8 is the full-wave rectifier reservoir: D1.1 and D2.1 both feed it and sit
# 6.21 mm apart, so "nearest wins" would let C8 hug one diode while sitting
# 5.6 mm from the other and still report compliant. Farther-of is what actually
# expresses "reservoir at the cathode junction".
FARTHEST = {'C8'}

# (inner, outer, shared owner pin) -- inner must be strictly nearer than outer.
# C6 inboard of C7 follows SN6505B Sec 10 ("0.1 uF as close as possible to the
# VCC pin"); Sec 11.1's competing "bulk closest to VIN" is satisfied by C17 at
# the centre tap, which is why C17 exists. Do not invert this to match Sec 11.1.
ORDER = [
    ('C11', 'C10', ('U5', '1')),
    ('C15', 'C14', ('U6', '6')),
    ('C6',  'C7',  ('U4', '2')),
]


def pad_xy(board, ref, pad_name):
    fp = board.FindFootprintByReference(ref)
    if fp is None:
        return None
    for p in fp.Pads():
        if p.GetNumber() == pad_name:
            v = p.GetPosition()
            return (v.x / 1e6, v.y / 1e6)
    return None


def nearest(board, cap, owners):
    c = pad_xy(board, cap, '1')
    if c is None:
        return None, None
    best, who = None, None
    for ref, pin in owners:
        t = pad_xy(board, ref, pin)
        if t is None:
            continue
        d = math.hypot(c[0] - t[0], c[1] - t[1])
        better = (best is None
                  or (d > best if cap in FARTHEST else d < best))
        if better:
            best, who = d, '%s.%s' % (ref, pin)
    return best, who


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    fails = 0
    for cap, owners, budget in OWNS:
        d, who = nearest(board, cap, owners)
        if d is None:
            print('  FAIL  %-5s footprint or pad missing from the board' % cap)
            fails += 1
            continue
        verdict = 'ok  ' if d <= budget else 'FAIL'
        if d > budget:
            fails += 1
        print('  %s  %-5s %6.2f mm to %-6s (budget %4.1f)' % (verdict, cap, d, who, budget))
    for inner, outer, pin in ORDER:
        di, _ = nearest(board, inner, [pin])
        do, _ = nearest(board, outer, [pin])
        if di is None or do is None:
            print('  FAIL  order %s/%s: a footprint is missing' % (inner, outer))
            fails += 1
            continue
        if di < do:
            print('  ok    %-5s (%.2f) is inboard of %-5s (%.2f) at %s.%s'
                  % (inner, di, outer, do, pin[0], pin[1]))
        else:
            print('  FAIL  %-5s (%.2f) must be INBOARD of %-5s (%.2f) at %s.%s'
                  % (inner, di, outer, do, pin[0], pin[1]))
            fails += 1
    print('\ndecoupling placement: %d failures' % fails)
    print('VERDICT:', 'PASS' if not fails else 'FAIL')
    sys.stdout.flush()
    os._exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
