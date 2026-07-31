"""Shared helpers for the board verification gates. Run with KiCad's python."""
import pcbnew

BOARD_LEN_MM = 120.0
BOARD_WID_MM = 50.0
COPPER_LAYERS = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]


def MM(iu):
    return pcbnew.ToMM(iu)


def IU(mm):
    return pcbnew.FromMM(mm)


def load(path):
    return pcbnew.LoadBoard(path)


def _bbox_mm(item):
    b = item.GetBoundingBox()
    return (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))


def copper_items(board):
    """Yield (layer_id, layer_name, kind, net_name, bbox_mm) for all copper."""
    for t in board.GetTracks():
        kind = 'via' if t.GetClass() == 'PCB_VIA' else 'track'
        if kind == 'via':
            for lid in COPPER_LAYERS:
                if t.IsOnLayer(lid):
                    yield (lid, board.GetLayerName(lid), kind, t.GetNetname(), _bbox_mm(t))
        else:
            lid = t.GetLayer()
            yield (lid, board.GetLayerName(lid), kind, t.GetNetname(), _bbox_mm(t))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            for lid in COPPER_LAYERS:
                if pad.IsOnLayer(lid):
                    yield (lid, board.GetLayerName(lid),
                           'pad:%s.%s' % (fp.GetReference(), pad.GetNumber()),
                           pad.GetNetname(), _bbox_mm(pad))
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        for lid in COPPER_LAYERS:
            if not z.IsOnLayer(lid):
                continue
            poly = z.GetFilledPolysList(lid)
            for oi in range(poly.OutlineCount()):
                out = poly.Outline(oi)
                xs = [MM(out.CPoint(i).x) for i in range(out.PointCount())]
                ys = [MM(out.CPoint(i).y) for i in range(out.PointCount())]
                yield (lid, board.GetLayerName(lid), 'zone', z.GetNetname(),
                       (min(xs), min(ys), max(xs), max(ys)))
