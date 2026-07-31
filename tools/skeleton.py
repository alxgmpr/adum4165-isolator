"""Task 1: stackup, board outline, edge-pullback keepouts."""
import sys, pcbnew

BOARD = sys.argv[1]
b = pcbnew.LoadBoard(BOARD)

# --- inner layer names: retire the inherited GND/PWR, both are split ground ---
b.SetLayerName(pcbnew.In1_Cu, "GND_SPLIT_A")
b.SetLayerName(pcbnew.In2_Cu, "GND_SPLIT_B")

# --- board outline: 120 x 50 rectangle on Edge.Cuts ---
for x1, y1, x2, y2 in [(0, 0, 120, 0), (120, 0, 120, 50), (120, 50, 0, 50), (0, 50, 0, 0)]:
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    s.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1))
    b.Add(s)


# --- edge pullback keepouts: 2 mm strips on both long edges, all copper layers ---
def rule_area(board, x0, y0, x1, y1, allow_pads):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    z.SetDoNotAllowPads(not allow_pads)
    lset = pcbnew.LSET()
    for lid in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        lset.addLayer(lid)
    z.SetLayerSet(lset)
    pts = pcbnew.VECTOR_VECTOR2I()
    for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
        pts.append(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    z.AddPolygon(pts)
    board.Add(z)
    return z


rule_area(b, 0, 0, 120, 2, allow_pads=False)     # top long edge
rule_area(b, 0, 48, 120, 50, allow_pads=False)   # bottom long edge

pcbnew.SaveBoard(BOARD, b)
print("skeleton written: outline + 2 edge keepouts, inner layers renamed")
