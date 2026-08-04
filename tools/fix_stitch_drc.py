"""Clean up after add_gnd_stitching_vias.

Two defects the stitcher leaves behind:

1. Its collision check is copper-to-copper only, so it will drop a via whose
   DRILL lands on top of an existing one -- the worst pair here overlapped at
   0.0162 mm hole-to-hole. Any new via violating the board's hole-to-hole
   minimum against a pre-existing via is removed; the pre-existing one always
   wins, since it was placed to serve a route.

2. Thermal spokes cannot form on pads whose surroundings are too tight -- the
   USB-C shield grounds at 0.5 mm pitch, U5.4 and C10.2 -- leaving single-spoke
   connections that DRC scores as starved. Those pads get a solid connection
   instead. That is the right answer on its own merits for a connector shield
   and an LDO ground; the pours stay thermal everywhere else so small passives
   keep their reflow balance.
"""
import sys, math, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)
mm = pcbnew.ToMM

# Centres reported by add_gnd_stitching_vias in this session.
ADDED = [(140.875, 107.703), (131.725, 85.553), (139.732, 92.863),
         (170.200, 84.700), (164.200, 82.900)]
TOL = 0.01

vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
removed = 0
for cx, cy in ADDED:
    hit = [v for v in vias
           if math.hypot(mm(v.GetPosition().x) - cx, mm(v.GetPosition().y) - cy) < TOL]
    assert len(hit) == 1, "expected 1 via at (%.3f, %.3f), found %d" % (cx, cy, len(hit))
    b.Remove(hit[0])
    removed += 1

SOLID_PADS = [('U5', '4'), ('C10', '2')]
solid = 0
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for p in fp.Pads():
        if (ref in ('J1', 'J2') and p.GetNetname() in ('GND1', 'GND2')) \
           or (ref, p.GetNumber()) in SOLID_PADS:
            p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            solid += 1

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print("removed %d stitching vias, set %d pads to solid zone connection" % (removed, solid))
print("vias now:", sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA'))
