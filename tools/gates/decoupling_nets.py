"""Gate 4: the isolated-side supply nets have exactly their designed members.

This gate exists because of a specific failure. /ISO_5V used to carry U5's
output, U1's VBUS2 pin and U6's input under one name, so nothing in the design
files said which capacitor served which pin -- and the board put U1's bypass cap
26.46 mm from U1 while U6 borrowed it from 2.01 mm away. The schematic recorded
the intent as drawing position, which no tool reads. Net membership is the
machine-readable form of that intent, so it is asserted here.

Reads the netlist, not the board: this is valid during a schematic-only pass,
when the board still holds the previous netlist and the board gates cannot pass.

Usage: python3 decoupling_nets.py <netlist.net>
"""
import sys, re

# (ref, pin) sets. PWR_FLAG pins are power symbols and never appear as nodes.
EXPECT = {
    '/ISO_5V':        {('U5', '1'), ('U5', '2'), ('C10', '1'), ('C11', '1'), ('NT1', '1')},
    '/ISO_5V_VBUS2':  {('U1', '20'), ('C12', '1'), ('NT1', '2')},
    '/ISO_5V_SW':     {('U6', '1'), ('U6', '3'), ('C16', '1'), ('NT1', '3')},
    '/ISO_5V_IND':    {('R4', '1'), ('R5', '1'), ('R6', '1'), ('NT1', '4')},
    '/DCDC_RECT':     {('D1', '1'), ('D2', '1'), ('C8', '1'), ('NT2', '1')},
    '/DCDC_RAW':      {('U5', '5'), ('U5', '8'), ('C9', '1'), ('NT2', '2')},
    '/PORT_VBUS':     {('U6', '6'), ('C14', '1'), ('C15', '1'), ('NT3', '1')},
    '/PORT_VBUS_J2':  {('J2', 'A4'), ('J2', 'A9'), ('J2', 'B4'), ('J2', 'B9'),
                       ('D6', '1'), ('U3', '5'), ('R7', '1'), ('R8', '1'), ('NT3', '2')},
    '/VBUS_HOST':     {('J1', 'A4'), ('J1', 'A9'), ('J1', 'B4'), ('J1', 'B9'),
                       ('D5', '1'), ('U2', '5'), ('U1', '1'), ('C3', '1'), ('C4', '1'),
                       ('U4', '2'), ('U4', '5'), ('C6', '1'), ('C7', '1'),
                       ('T1', '2'), ('C17', '1')},
}

# /ISO_5V_IND is deliberately NOT in PWR: it carries a few mA and belongs at the
# ISO_SIDE default width, not the 0.5 mm power width.
CLASSES = {
    '/ISO_5V':       {'PWR', 'ISO_SIDE'},
    '/ISO_5V_VBUS2': {'PWR', 'ISO_SIDE'},
    '/ISO_5V_SW':    {'PWR', 'ISO_SIDE'},
    '/ISO_5V_IND':   {'ISO_SIDE'},
    '/DCDC_RECT':    {'PWR', 'ISO_SIDE'},
    '/DCDC_RAW':     {'PWR', 'ISO_SIDE'},
    '/PORT_VBUS':    {'PWR', 'ISO_SIDE'},
    '/PORT_VBUS_J2': {'PWR', 'ISO_SIDE'},
    '/VBUS_HOST':    {'PWR', 'HOST_SIDE'},
}


def parse(path):
    txt = open(path).read()
    blk = txt[txt.index('(nets'):]
    hdr = re.compile(r'\(net\s*\n\s*\(code "\d+"\)\s*\n\s*\(name "([^"]*)"\)'
                     r'\s*\n\s*\(class "([^"]*)"\)')
    out = {}
    marks = list(hdr.finditer(blk))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(blk)
        seg = blk[m.end():end]
        nodes = set(re.findall(r'\(ref "([^"]+)"\)\s*\n\s*\(pin "([^"]+)"\)', seg))
        out[m.group(1)] = (nodes, set(m.group(2).split(',')))
    return out


def main():
    actual = parse(sys.argv[1])
    fails = 0
    for net in sorted(EXPECT):
        want = EXPECT[net]
        if net not in actual:
            print("  FAIL  %-16s net does not exist" % net)
            fails += 1
            continue
        got, cls = actual[net]
        if got != want:
            fails += 1
            print("  FAIL  %-16s membership" % net)
            for r, p in sorted(want - got):
                print("           missing  %s.%s" % (r, p))
            for r, p in sorted(got - want):
                print("           unexpected %s.%s" % (r, p))
        wantc = CLASSES[net]
        if cls != wantc:
            fails += 1
            print("  FAIL  %-16s netclass %s, expected %s"
                  % (net, ','.join(sorted(cls)), ','.join(sorted(wantc))))
        if got == want and cls == wantc:
            print("  ok    %-16s %d nodes, %s" % (net, len(got), ','.join(sorted(cls))))
    print("\ndecoupling nets: %d failures" % fails)
    print("VERDICT:", "PASS" if not fails else "FAIL")
    sys.exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
