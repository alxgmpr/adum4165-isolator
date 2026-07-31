"""Run every layout gate plus DRC. Exit 0 only if all pass."""
import subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
KIPY = '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
KCLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
BOARD = os.path.join(PROJ, 'isolator.kicad_pcb')
SCH = os.path.join(PROJ, 'isolator.kicad_sch')
PRO = os.path.join(PROJ, 'isolator.kicad_pro')
NET = '/tmp/net.net'

subprocess.run([KCLI, 'sch', 'export', 'netlist', SCH, '-o', NET], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

steps = [
    ('netclass coverage', ['python3', os.path.join(HERE, 'netclass_coverage.py'), PRO, NET]),
    ('Gate 1 barrier',    [KIPY, os.path.join(HERE, 'barrier.py'), BOARD, PRO, NET]),
    ('Gate 2 edge',       [KIPY, os.path.join(HERE, 'edge_pullback.py'), BOARD]),
    ('Gate 3 diff pairs', [KIPY, os.path.join(HERE, 'diffpair.py'), BOARD]),
    ('DRC + parity',      [KCLI, 'pcb', 'drc', BOARD, '-o', '/tmp/drc.rpt',
                           '--severity-error', '--schematic-parity',
                           '--refill-zones', '--exit-code-violations']),
]

failed = []
for name, cmd in steps:
    print("\n" + "=" * 64 + "\n== " + name + "\n" + "=" * 64)
    if subprocess.run(cmd, stderr=subprocess.DEVNULL).returncode != 0:
        failed.append(name)

print("\n" + "=" * 64)
print("FAILED: " + ", ".join(failed) if failed else "ALL GATES PASS")
sys.exit(1 if failed else 0)
