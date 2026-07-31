"""Move footprint reference text off pads.

All remaining DRC violations are silkscreen: refdes text sitting over copper or
over a neighbour's silk. Fabs clip silk over pads anyway, but a clean DRC is
worth having. For each offending footprint the reference is tried at several
offsets outside its own courtyard and placed at the first that clears every pad
and every other visible reference.
"""
import sys, math, pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
IU, MM = pcbnew.FromMM, pcbnew.ToMM
GAP = 0.20


def boxes():
    pads = []
    for f in b.GetFootprints():
        for p in f.Pads():
            bb = p.GetBoundingBox()
            pads.append((MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())))
    return pads


def txt_box(t):
    bb = t.GetBoundingBox()
    return (MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom()))


def overlap(a, c, gap=GAP):
    return not (a[2] + gap < c[0] or c[2] + gap < a[0] or a[3] + gap < c[1] or c[3] + gap < a[1])


PADS = boxes()
texts = [f.Reference() for f in b.GetFootprints() if f.Reference().IsVisible()]
moved = 0
for f in b.GetFootprints():
    ref = f.Reference()
    if not ref.IsVisible():
        continue
    cy = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
    cx0, cy0, cx1, cy1 = MM(cy.GetLeft()), MM(cy.GetTop()), MM(cy.GetRight()), MM(cy.GetBottom())
    tb = txt_box(ref)
    w, h = tb[2] - tb[0], tb[3] - tb[1]
    others = [txt_box(t) for t in texts if t is not ref]
    if not any(overlap(tb, p) for p in PADS) and not any(overlap(tb, o) for o in others):
        continue
    fx, fy = MM(f.GetPosition().x), MM(f.GetPosition().y)
    best = None
    for dy in (-(h / 2 + 0.35), (h / 2 + 0.35), -(h / 2 + 0.9), (h / 2 + 0.9)):
        for dx in (0, -(w / 2 + 0.4), (w / 2 + 0.4)):
            ncx = (cx0 + cx1) / 2 + dx
            ncy = (cy0 if dy < 0 else cy1) + dy
            cand = (ncx - w / 2, ncy - h / 2, ncx + w / 2, ncy + h / 2)
            if 2.0 < cand[1] and cand[3] < 48.0 and \
               not any(overlap(cand, p) for p in PADS) and \
               not any(overlap(cand, o) for o in others):
                best = (ncx, ncy)
                break
        if best:
            break
    if best:
        ref.SetPosition(pcbnew.VECTOR2I(IU(best[0]), IU(best[1])))
        moved += 1

print("reference texts moved:", moved)
pcbnew.SaveBoard(sys.argv[1], b)
