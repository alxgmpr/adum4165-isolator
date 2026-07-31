"""Placement assertions for Task 4. Independent of Gate 1: this checks the
mechanical constraints from the schematic's binding text block, not the barrier."""
import sys, itertools, pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
M = pcbnew.ToMM
fail = []
CROSSERS = ('U1', 'T1', 'CY1')


def crtyd(ref):
    fp = b.FindFootprintByReference(ref)
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    return M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetRight()), M(bb.GetBottom())


refs = [f.GetReference() for f in b.GetFootprints()]

# 1. every courtyard inside the copper band, and clear of the barrier keepout
for r in refs:
    x0, y0, x1, y1 = crtyd(r)
    if y0 < 2.0 or y1 > 48.0:
        fail.append("%s courtyard outside copper band y[2,48]: %.2f..%.2f" % (r, y0, y1))
    if r not in CROSSERS and x1 > 55.85 and x0 < 64.15:
        fail.append("%s intrudes into the barrier keepout and is not a permitted crossing "
                    "(x %.2f..%.2f)" % (r, x0, x1))

# 2. no courtyard overlaps.
# Uses exact polygon collision, not bounding boxes. The USB-C receptacle
# courtyard is notched, so U2/U3 legitimately nest against J1/J2's bbox without
# actually overlapping -- a bbox test reports those as false positives and
# disagrees with KiCad's own courtyards_overlap DRC.
def poly(ref):
    return b.FindFootprintByReference(ref).GetCourtyard(pcbnew.F_CrtYd)


for a, c in itertools.combinations(refs, 2):
    if poly(a).Collide(poly(c)):
        fail.append("courtyard overlap: %s and %s" % (a, c))

# 3. D1 and D2 side by side, not in series
d1, d2 = crtyd('D1'), crtyd('D2')
if not (abs(d1[0] - d2[0]) < 2.0 and (d1[3] < d2[1] or d2[3] < d1[1])):
    fail.append("D1/D2 are not side by side (D1 x0=%.2f y=%.2f..%.2f, D2 x0=%.2f y=%.2f..%.2f)"
                % (d1[0], d1[1], d1[3], d2[0], d2[1], d2[3]))

# 4. ESD arrays within 5 mm of the connector they protect
for esd, conn in (('U2', 'J1'), ('U3', 'J2')):
    e, c = crtyd(esd), crtyd(conn)
    gap = max(c[0] - e[2], e[0] - c[2], 0.0)
    if gap > 5.0:
        fail.append("%s is %.2f mm from %s, limit 5 mm" % (esd, gap, conn))

# 5. barrier crossers actually straddle the barrier
for r in CROSSERS:
    x0, _, x1, _ = crtyd(r)
    if not (x0 < 55.85 and x1 > 64.15):
        fail.append("%s does not straddle the barrier (x %.2f..%.2f)" % (r, x0, x1))

for f in fail:
    print("  FAIL ", f)
print("\nplacement assertions: %d failures" % len(fail))
sys.exit(1 if fail else 0)
