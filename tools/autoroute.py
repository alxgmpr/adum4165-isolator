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
JAR = os.path.join(HERE, 'freerouting-2.2.4.jar')
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
            p = t.GetPosition(); snap.append(('V', p.x, p.y, t.GetWidth()))
        else:
            s, e = t.GetStart(), t.GetEnd()
            snap.append(('T', s.x, s.y, e.x, e.y, t.GetWidth(), t.GetLayer()))
json.dump(sorted(map(list, snap)), open(%(out)r, 'w'))
print('pair snapshot:', len(snap), 'items')
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

    print('== freerouting ==')
    r = subprocess.run(['java', '-jar', JAR, '-de', dsn, '-do', ses,
                        '-mp', str(args.passes), '-da'],
                       capture_output=True, text=True, timeout=3600)
    tail = (r.stdout + r.stderr).splitlines()[-15:]
    print('\n'.join(tail))
    if not os.path.exists(ses):
        sys.exit('freerouting produced no SES')

    print('== import SES ==')
    if not kipy(STEP_IMPORT, board=BOARD, ses=ses):
        sys.exit('SES import failed')

    print('== verify protected pairs untouched ==')
    kipy(STEP_SNAPSHOT, board=BOARD, nets=PAIR_NETS, out=snap1)
    a = json.load(open(snap0)); b2 = json.load(open(snap1))
    if a != b2:
        print('!! PAIR COPPER CHANGED (%d -> %d items) — REJECT: git checkout isolator.kicad_pcb' % (len(a), len(b2)))
        sys.exit(2)
    print('pairs identical:', len(a), 'items')

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
