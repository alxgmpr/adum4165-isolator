"""Rip up autorouted isolated-side copper, keeping the hand-routed pairs and all
host-side routing. Run before re-running the autorouter with the pairs protected."""
import sys, pcbnew
KEEP = {'/HOST_D+', '/HOST_D-', '/PORT_D+', '/PORT_D-',
        '/VBUS_HOST', '/VDD1', '/XTALIN', '/XTALOUT', '/PP_A', '/PP_B',
        'GND1', 'Net-(J1-CC1)', 'Net-(J1-CC2)'}
b = pcbnew.LoadBoard(sys.argv[1])
doomed = [t for t in b.GetTracks() if t.GetNetname() not in KEEP]
from collections import Counter
c = Counter(t.GetNetname() for t in doomed)
for t in doomed:
    b.Remove(t)
for n, k in sorted(c.items()):
    print("  ripped %-16s %d items" % (n, k))
print("total ripped:", len(doomed))
pcbnew.SaveBoard(sys.argv[1], b)
