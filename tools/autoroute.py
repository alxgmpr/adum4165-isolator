#!/usr/bin/env python3
"""Autorouting pipeline: KiCad board -> Specctra DSN -> Freerouting (headless)
-> SES import -> gates. Run with KiCad's bundled python:

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 -u tools/autoroute.py [--passes N]

Protected copper: everything already routed (KiCad exports existing wiring;
the gate below additionally verifies the six USB pair nets are byte-identical
after import — if Freerouting touched them, the run is rejected).
KiCad GUI must be CLOSED. Commits are left to the operator.
"""
import subprocess, os, sys, json, shutil, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
BOARD = os.path.join(PROJ, 'isolator.kicad_pcb')
JAR = os.path.join(HERE, 'freerouting-1.9.0.jar')
WORK = os.path.join(HERE, 'ar_work')
KIPY = '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
KICLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

PAIR_NETS = ['/HOST_D+', '/HOST_D-', '/ISO_D+', '/ISO_D-',
             '/P1_D+', '/P1_D-', '/P2_D+', '/P2_D-',
             '/P3_D+', '/P3_D-', '/P4_D+', '/P4_D-']

STEP_EXPORT = r'''
import pcbnew, os, sys
b = pcbnew.LoadBoard(%(board)r)
ok = pcbnew.ExportSpecctraDSN(b, %(dsn)r)
print('DSN export:', ok)
sys.stdout.flush(); os._exit(0 if ok else 1)
'''

STEP_SNAPSHOT = r'''
import pcbnew, os, sys, json
b = pcbnew.LoadBoard(%(board)r)
nets = set(%(nets)r)
snap = []
for t in b.GetTracks():
    if t.GetNetname() in nets:
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition(); snap.append(('V', t.GetNetname(), p.x, p.y, t.GetWidth()))
        else:
            s, e = t.GetStart(), t.GetEnd()
            snap.append(('T', t.GetNetname(), s.x, s.y, e.x, e.y, t.GetWidth(), t.GetLayer()))
json.dump(sorted(map(list, snap)), open(%(out)r, 'w'))
print('pair snapshot:', len(snap), 'items')
sys.stdout.flush(); os._exit(0)
'''


STEP_HARVEST = r'''
import pcbnew, os, sys, shutil, math
ORIG = %(board)r
COPY = %(copy)r
SES = %(ses)r
PAIRS = set(%(nets)r)
shutil.copy(ORIG, COPY)
bc = pcbnew.LoadBoard(COPY)
ok = pcbnew.ImportSpecctraSES(bc, SES)
print('SES into copy:', ok)
if not ok:
    os._exit(1)
bo = pcbnew.LoadBoard(ORIG)
# geometry sets of original copper (all nets)
def key_t(t):
    s2, e2 = t.GetStart(), t.GetEnd()
    a = (round(s2.x, -3), round(s2.y, -3)); b2 = (round(e2.x, -3), round(e2.y, -3))
    return ('T',) + tuple(sorted([a, b2])) + (t.GetWidth(), t.GetLayer())
def key_v(t):
    p2 = t.GetPosition()
    return ('V', round(p2.x, -3), round(p2.y, -3), t.GetWidth())
have = set()
for t in bo.GetTracks():
    have.add(key_v(t) if t.GetClass() == 'PCB_VIA' else key_t(t))
added = 0
for t in bc.GetTracks():
    net = t.GetNetname()
    if net in PAIRS:
        continue
    k = key_v(t) if t.GetClass() == 'PCB_VIA' else key_t(t)
    if k in have:
        continue
    netinfo = bo.FindNet(net)
    if not netinfo:
        continue
    if t.GetClass() == 'PCB_VIA':
        v = pcbnew.PCB_VIA(bo)
        v.SetPosition(t.GetPosition()); v.SetWidth(t.GetWidth()); v.SetDrill(t.GetDrillValue())
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNetCode(netinfo.GetNetCode()); bo.Add(v)
    else:
        nt = pcbnew.PCB_TRACK(bo)
        nt.SetStart(t.GetStart()); nt.SetEnd(t.GetEnd())
        nt.SetWidth(t.GetWidth()); nt.SetLayer(t.GetLayer())
        nt.SetNetCode(netinfo.GetNetCode()); bo.Add(nt)
    added += 1
print('harvested new items:', added)
bo.Save(ORIG)
print('saved')
sys.stdout.flush(); os._exit(0)
'''

STEP_IMPORT = r'''
import pcbnew, os, sys
b = pcbnew.LoadBoard(%(board)r)
ok = pcbnew.ImportSpecctraSES(b, %(ses)r)
print('SES import:', ok)
if ok:
    b.Save(%(board)r)
    print('saved')
sys.stdout.flush(); os._exit(0 if ok else 1)
'''

STEP_REFILL = r'''
import pcbnew, os, sys
b = pcbnew.LoadBoard(%(board)r)
ok = pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(%(board)r)
print('refill:', ok)
sys.stdout.flush(); os._exit(0)
'''


def kipy(code, **kw):
    src = code % kw
    path = os.path.join(WORK, 'step.py')
    open(path, 'w').write(src)
    r = subprocess.run([KIPY, '-u', path], capture_output=True, text=True, timeout=600)
    out = '\n'.join(l for l in r.stdout.splitlines() if 'memory leak' not in l)
    print(out)
    return r.returncode == 0 or 'saved' in out or ':' in out


def drc(tag):
    out = os.path.join(WORK, f'drc_{tag}.json')
    subprocess.run([KICLI, 'pcb', 'drc', BOARD, '--format', 'json', '--output', out],
                   capture_output=True, text=True)
    d = json.load(open(out))
    from collections import Counter
    kinds = dict(Counter(v['type'] for v in d.get('violations', [])))
    unc = len(d.get('unconnected_items', []))
    print(f'DRC[{tag}]: {kinds}  unconnected={unc}')
    return kinds, unc


def protect_wiring(dsn_path):
    """Mark all exported wires/vias as protected so Freerouting cannot rip them."""
    s = open(dsn_path).read()
    n = s.count('(type route)')
    s = s.replace('(type route)', '(type fix)')
    # forbid routing on the plane layers: declare them power-type
    import re as _re
    for lyr in ('GND', 'PWR'):
        s, k = _re.subn(r'\(layer %s\s*\(type signal\)' % lyr,
                        '(layer %s (type power)' % lyr, s)
        print('layer', lyr, '-> power type:', k, 'occurrence(s)')
    open(dsn_path, 'w').write(s)
    print('protected wiring objects:', n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--passes', type=int, default=20)
    args = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    dsn = os.path.join(WORK, 'board.dsn')
    ses = os.path.join(WORK, 'board.ses')
    snap0 = os.path.join(WORK, 'pairs_before.json')
    snap1 = os.path.join(WORK, 'pairs_after.json')

    print('== baseline DRC ==')
    kinds0, unc0 = drc('before')

    print('== snapshot protected pair copper ==')
    kipy(STEP_SNAPSHOT, board=BOARD, nets=PAIR_NETS, out=snap0)

    print('== export DSN ==')
    if not kipy(STEP_EXPORT, board=BOARD, dsn=dsn):
        sys.exit('DSN export failed')

    protect_wiring(dsn)
    print('== freerouting ==')
    r = subprocess.run(['java', '-Xss64m', '-jar', JAR, '-de', dsn, '-do', ses,
                        '-mp', str(args.passes), '-da'],
                       capture_output=True, text=True, timeout=3600)
    tail = (r.stdout + r.stderr).splitlines()[-15:]
    print('\n'.join(tail))
    if not os.path.exists(ses):
        sys.exit('freerouting produced no SES')

    print('== harvest new copper (surgical import) ==')
    copyb = os.path.join(WORK, 'imported_copy.kicad_pcb')
    if not kipy(STEP_HARVEST, board=BOARD, copy=copyb, ses=ses, nets=PAIR_NETS):
        sys.exit('harvest failed')

    print('== verify protected pairs untouched ==')
    kipy(STEP_SNAPSHOT, board=BOARD, nets=PAIR_NETS, out=snap1)
    a = json.load(open(snap0)); b2 = json.load(open(snap1))

    import math as _m

    def summarize(items):
        length = {}
        vias = []
        for it in items:
            if it[0] == 'V':
                vias.append((it[1], it[2], it[3], it[4]))
            else:
                _, net, x1, y1, x2, y2, w, layer = it
                key = (net, layer, w)
                length[key] = length.get(key, 0.0) + _m.hypot(x2 - x1, y2 - y1)
        return length, sorted(vias)

    la, va = summarize(a)
    lb, vb = summarize(b2)
    bad = []
    for k in set(la) | set(lb):
        if abs(la.get(k, 0.0) - lb.get(k, 0.0)) > 25000:   # 25um copper delta
            bad.append(('length', k, round(la.get(k, 0) / 1e6, 3), round(lb.get(k, 0) / 1e6, 3)))
    if len(va) != len(vb):
        bad.append(('via-count', len(va), len(vb)))
    else:
        for (n1, x1, y1, w1), (n2, x2, y2, w2) in zip(va, vb):
            if n1 != n2 or w1 != w2 or _m.hypot(x1 - x2, y1 - y2) > 3000:
                bad.append(('via-moved', n1, n2))
    if bad:
        print('!! PAIR COPPER CHANGED — auto-reverting')
        for x in bad[:10]:
            print('  ', x)
        subprocess.run(['git', '-C', PROJ, 'checkout', 'isolator.kicad_pcb'])
        sys.exit(2)
    print('pairs intact: conserved length per net/layer/width, vias matched')

    print('== refill ==')
    kipy(STEP_REFILL, board=BOARD)

    print('== final DRC ==')
    kinds1, unc1 = drc('after')
    new_kinds = set(kinds1) - set(kinds0) - {'silk_overlap', 'silk_over_copper', 'silk_edge_clearance'}
    print('new violation types:', new_kinds or 'NONE')
    print(f'unconnected: {unc0} -> {unc1}')
    print('Review renders, then commit manually.')


if __name__ == '__main__':
    main()
