"""Populate the board with every footprint and net from the schematic netlist.

Parks all footprints in a grid at y = 70 mm, clear of the 120x50 outline.
Placement is a separate pass (tools/place.py) so that a schematic-parity
failure here cannot be confused with a placement error.
"""
import sys, os, re, pcbnew

BOARD, NETLIST = sys.argv[1], sys.argv[2]
FPLIB_SYS = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
FPLIB_PRJ = os.path.join(os.path.dirname(os.path.abspath(BOARD)), "isolator-lib.pretty")


def parse(text):
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    stack, cur = [], []
    for t in toks:
        if t == '(':
            n = []
            cur.append(n)
            stack.append(cur)
            cur = n
        elif t == ')':
            cur = stack.pop()
        elif t.startswith('"'):
            cur.append(t[1:-1])
        else:
            cur.append(t)
    return cur[0]


def find(n, k):
    return [c for c in n if isinstance(c, list) and c and c[0] == k]


def val(n, k, d=None):
    f = find(n, k)
    return f[0][1] if f and len(f[0]) > 1 else d


root = parse(open(NETLIST).read())

comps = {}
for sec in find(root, 'components'):
    for c in find(sec, 'comp'):
        comps[val(c, 'ref')] = val(c, 'footprint')

pad_nets = {}
for sec in find(root, 'nets'):
    for n in find(sec, 'net'):
        name = val(n, 'name')
        for nd in find(n, 'node'):
            pad_nets[(val(nd, 'ref'), val(nd, 'pin'))] = name

b = pcbnew.LoadBoard(BOARD)

# nets first -- a pad cannot be bound to a net the board does not know
for name in sorted(set(pad_nets.values())):
    if b.FindNet(name) is None:
        b.Add(pcbnew.NETINFO_ITEM(b, name))

placed, bound, missing = 0, 0, []
for i, (ref, fpid) in enumerate(sorted(comps.items())):
    nick, name = fpid.split(':', 1)
    lib = FPLIB_PRJ if nick == 'isolator-lib' else os.path.join(FPLIB_SYS, nick + '.pretty')
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        missing.append((ref, fpid))
        continue
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(10 + (i % 8) * 14),
                                   pcbnew.FromMM(70 + (i // 8) * 14)))
    b.Add(fp)
    placed += 1
    for pad in fp.Pads():
        net = pad_nets.get((ref, pad.GetNumber()))
        if net:
            pad.SetNet(b.FindNet(net))
            bound += 1

print("footprints placed: %d / %d" % (placed, len(comps)))
print("pads bound to nets: %d / %d" % (bound, len(pad_nets)))
for ref, fpid in missing:
    print("  MISSING FOOTPRINT:", ref, fpid)
if missing:
    sys.exit(1)
pcbnew.SaveBoard(BOARD, b)
print("saved")
