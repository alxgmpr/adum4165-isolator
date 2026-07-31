"""Undo tools/stitch_ground.py: remove the 0.25 mm-wide GND stub tracks it added
and the via at the far end of each."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM
stubs = [t for t in b.GetTracks() if t.GetClass() != 'PCB_VIA'
         and abs(M(t.GetWidth()) - 0.25) < 1e-6 and t.GetNetname() in ('GND1', 'GND2')]
ends = {(round(M(t.GetEnd().x), 4), round(M(t.GetEnd().y), 4)) for t in stubs}
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA'
        and (round(M(t.GetPosition().x), 4), round(M(t.GetPosition().y), 4)) in ends]
for t in stubs + vias:
    b.Remove(t)
print("removed %d stub tracks and %d vias" % (len(stubs), len(vias)))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[1], b)
