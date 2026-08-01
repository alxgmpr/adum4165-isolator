"""Bring the board up to the schematic's netlist without disturbing placement.

Unlike build_board.py, which populates an empty board, this runs against a board
that is already placed and routed: it adds only the footprints that are missing,
parks them below the outline, and rebinds every pad to whatever net the netlist
now says. The eight branch nets from the schematic split arrive here.

Note: build_board.py's parse/find/val helpers and FPLIB_SYS/FPLIB_PRJ constants
are copied here verbatim rather than imported. build_board.py executes its work
(LoadBoard, footprint placement, SaveBoard) at module scope keyed off sys.argv,
so importing it would re-run that whole script -- against this same board and
netlist, since sys.argv is shared -- as a side effect of the import. It is left
untouched as the record of how the board was originally built.
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


PARK_X, PARK_Y, PARK_DX = 96.88, 136.70, 5.0     # absolute mm, below the outline

root = parse(open(NETLIST).read())

comps, paths = {}, {}
for sec in find(root, 'components'):
    for c in find(sec, 'comp'):
        ref = val(c, 'ref')
        comps[ref] = val(c, 'footprint')
        ts = val(c, 'tstamps')
        if ts:
            paths[ref] = '/' + ts

pad_nets = {}
for sec in find(root, 'nets'):
    for n in find(sec, 'net'):
        name = val(n, 'name')
        for nd in find(n, 'node'):
            pad_nets[(val(nd, 'ref'), val(nd, 'pin'))] = name

b = pcbnew.LoadBoard(BOARD)

created = []
for name in sorted(set(pad_nets.values())):
    if b.FindNet(name) is None:
        b.Add(pcbnew.NETINFO_ITEM(b, name))
        created.append(name)

added, missing = [], []
have = {fp.GetReference() for fp in b.GetFootprints()}
for i, ref in enumerate(sorted(set(comps) - have)):
    nick, name = comps[ref].split(':', 1)
    lib = FPLIB_PRJ if nick == 'isolator-lib' else os.path.join(FPLIB_SYS, nick + '.pretty')
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        missing.append((ref, comps[ref]))
        continue
    fp.SetReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(PARK_X + i * PARK_DX),
                                   pcbnew.FromMM(PARK_Y)))
    if ref in paths:
        fp.SetPath(pcbnew.KIID_PATH(paths[ref]))
    b.Add(fp)
    added.append(ref)

rebound = 0
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        want = pad_nets.get((ref, pad.GetNumber()))
        if want and pad.GetNetname() != want:
            pad.SetNet(b.FindNet(want))
            rebound += 1

print('nets created:      %s' % (', '.join(created) or 'none'))
print('footprints added:  %s' % (', '.join(added) or 'none'))
print('pads rebound:      %d' % rebound)
for ref, fpid in missing:
    print('  MISSING FOOTPRINT:', ref, fpid)
if missing:
    sys.stdout.flush()
    os._exit(1)
pcbnew.SaveBoard(BOARD, b)
print('saved')
sys.stdout.flush()
os._exit(0)
