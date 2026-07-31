"""Task 5: split ground pours. Both inner layers carry GND1 host-side and GND2
isolated-side. A single continuous inner plane would bridge the barrier."""
import sys, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)

# Host side stops before the barrier keepout, isolated side starts after it.
# The keepout itself would clip the fill anyway; stating the bounds explicitly
# means the intent survives even if the keepout is ever edited.
REGIONS = [
    ('GND1', 2.0, 2.0, 55.85, 48.0),
    ('GND2', 64.15, 2.0, 118.0, 48.0),
]

for lid in (pcbnew.In1_Cu, pcbnew.In2_Cu):
    for net_name, x0, y0, x1, y1 in REGIONS:
        net = b.FindNet(net_name)
        if net is None:
            print("  net not found:", net_name)
            sys.exit(1)
        z = pcbnew.ZONE(b)
        z.SetLayer(lid)
        z.SetNet(net)
        z.SetIsFilled(True)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        pts = pcbnew.VECTOR_VECTOR2I()
        for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            pts.append(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        z.AddPolygon(pts)
        b.Add(z)

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)

for z in b.Zones():
    if not z.GetIsRuleArea():
        print("%-12s %-6s filled %8.2f mm^2" % (b.GetLayerName(z.GetLayer()), z.GetNetname(),
                                                pcbnew.ToMM(pcbnew.ToMM(z.GetFilledArea()))))
