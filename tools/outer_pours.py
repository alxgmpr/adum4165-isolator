"""Ground pour on both outer layers: GND1 host-side, GND2 isolated-side.

Four zones, not two. A single pour per layer would bridge the barrier -- the
same reason the inner layers are split. The outlines are cloned from the
GND_SPLIT_A planes so the 2 mm edge pullback and the rounded corners match
exactly rather than approximately; letting the board-outline clip produce the
corners instead would leave outer copper 0.3 mm from the corner edge, closer
than the inner layers, on the two layers that actually face the extrusion.

Priority: the new pours sit at 0 and yield to every local pour. One existing
zone -- the rectifier pour at Net-(D1-K) -- also sat at 0, which would have made
the two peers rather than nesting them; it is raised here.
"""
import sys, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)

new = [z for z in b.Zones()
       if not z.GetIsRuleArea()
       and b.GetLayerName(z.GetLayer()) in ('F.Cu', 'B.Cu')
       and z.GetNetname() in ('GND1', 'GND2')
       and z.Outline().FullPointCount() == 36]
assert len(new) == 4, "expected 4 new outer pours, found %d" % len(new)

for z in new:
    z.SetAssignedPriority(0)
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.5))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)

for z in b.Zones():
    if (not z.GetIsRuleArea() and z.GetNetname() == 'Net-(D1-K)'
            and z.GetAssignedPriority() == 0):
        z.SetAssignedPriority(2)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)

for z in new:
    print("%-5s %-5s filled %8.2f mm^2" % (b.GetLayerName(z.GetLayer()), z.GetNetname(),
                                           z.GetFilledArea() / 1e12))
