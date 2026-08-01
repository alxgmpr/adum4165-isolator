"""Rip every track east of the barrier, plus the whole VBUS_HOST rail.

ripup_iso.py rips by net-name allowlist, which is the wrong shape here: this
pass clears the isolated side by GEOMETRY, including nets that also carry
host-side copper. VBUS_HOST goes too, despite being host-side, because C6 moves
inboard of C7 and C17 is new at T1's centre tap -- the rail has to be re-routed
to serve the new arrangement either way.

Zones are deliberately untouched. Planes and their stitching are re-done in the
final task, after placement settles.
"""
import sys, os, pcbnew
from collections import Counter

BARRIER_W, BARRIER_E = 142.72, 151.03      # absolute mm
ALWAYS_RIP = {'/VBUS_HOST'}
NEVER_RIP = {'/HOST_D+', '/HOST_D-'}       # host-side; frozen by the plan, not
                                            # by being correct -- Gate 3 reports
                                            # ~2.9 mm skew on this pair and always has

b = pcbnew.LoadBoard(sys.argv[1])
doomed, straddling = [], []

for t in b.GetTracks():
    net = t.GetNetname()
    if net in NEVER_RIP:
        continue
    xs = [t.GetStart().x / 1e6, t.GetEnd().x / 1e6]
    # Full-span detector, not an any-intrusion one: this only catches a track
    # that crosses the *entire* keepout (one endpoint west of BARRIER_W and
    # the other east of BARRIER_E). A track with one endpoint inside the
    # keepout and the other short of the far edge is neither ripped nor
    # flagged. Not tightened deliberately -- U1/T1/CY1 have pads legitimately
    # inside the keepout span, and a naive "any endpoint inside" check would
    # false-positive on them.
    if min(xs) < BARRIER_W and max(xs) > BARRIER_E:
        straddling.append((net, xs))
        continue
    if net in ALWAYS_RIP or min(xs) >= BARRIER_E:
        doomed.append(t)

if straddling:
    print('STOP: %d track(s) cross the barrier keepout -- Gate 1 should have caught this:'
          % len(straddling))
    for net, xs in straddling[:10]:
        print('   %-16s x %.3f .. %.3f' % (net, min(xs), max(xs)))
    sys.stdout.flush()
    os._exit(1)

c = Counter(t.GetNetname() for t in doomed)
for t in doomed:
    b.Remove(t)
for n, k in sorted(c.items()):
    print('  ripped %-18s %d items' % (n, k))
print('total ripped: %d' % len(doomed))
pcbnew.SaveBoard(sys.argv[1], b)
sys.stdout.flush()
os._exit(0)
