"""Two fixes.

(1) U3.5 via-in-pad. U3 pin 5 (PORT_VBUS) is the middle of the right column with
    D+ on pin 6 above and D- on pin 4 below, so its only F.Cu escape is the 0.8 mm
    corridor at y=25.0 between U3's right edge (109.300) and J2's pad field
    (110.100). That corridor was blocked by D-'s diagonal to J2.A7. J2's pads are
    1.45 mm long, so D- reaches A7 the way USB-C interleaved pairs normally do --
    a short B.Cu jumper between vias placed in the far end of the B7 and A7 pads --
    which frees the corridor and lets PORT_VBUS leave U3.5 on F.Cu.

(2) J1/J2 set to the exact minimum inset that keeps all copper on the board.
    Their shield pads reach 0.110 mm past the footprint origin's nominal flush
    position, and the board edge rule is 0.300 mm, so the minimum inset is
    0.410 mm. They were at 0.420; this trims to the minimum so they sit as far
    outboard as the copper allows.
"""
import sys, math, pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
IU, MM = pcbnew.FromMM, pcbnew.ToMM

# ---------- (1) free the y=25.0 corridor ----------
doomed = []
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA' or t.GetNetname() != '/PORT_D-':
        continue
    s, e = (MM(t.GetStart().x), MM(t.GetStart().y)), (MM(t.GetEnd().x), MM(t.GetEnd().y))
    for a, c in (((109.126, 25.750), (110.126, 24.750)),
                 ((110.126, 24.750), (110.825, 24.750))):
        if ({(round(s[0], 3), round(s[1], 3)), (round(e[0], 3), round(e[1], 3))} ==
                {(round(a[0], 3), round(a[1], 3)), (round(c[0], 3), round(c[1], 3))}):
            doomed.append(t)
for t in doomed:
    b.Remove(t)
print("removed %d D- segments blocking the y=25.0 corridor" % len(doomed))

# also drop the old PORT_VBUS via-in-pad and its B.Cu stub
rm = []
for t in b.GetTracks():
    if t.GetNetname() != '/PORT_VBUS':
        continue
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition()
        if abs(MM(p.x) - 108.638) < 0.01 and abs(MM(p.y) - 25.000) < 0.01:
            rm.append(t)
    else:
        s, e = t.GetStart(), t.GetEnd()
        if (abs(MM(s.x) - 108.638) < 0.01 and abs(MM(s.y) - 25.0) < 0.01) or \
           (abs(MM(s.x) - 108.901) < 0.01 and abs(MM(s.y) - 24.700) < 0.01):
            rm.append(t)
for t in rm:
    b.Remove(t)
print("removed %d old PORT_VBUS via-in-pad items" % len(rm))


def track(net, lid, p1, p2, w):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(IU(p1[0]), IU(p1[1])))
    t.SetEnd(pcbnew.VECTOR2I(IU(p2[0]), IU(p2[1])))
    t.SetWidth(IU(w)); t.SetLayer(lid); t.SetNetCode(b.FindNet(net).GetNetCode())
    b.Add(t)


def via(net, x, y, d=0.45, dr=0.25):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(IU(x), IU(y)))
    v.SetWidth(IU(d)); v.SetDrill(IU(dr))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNetCode(b.FindNet(net).GetNetCode()); b.Add(v)


F, B = pcbnew.F_Cu, pcbnew.B_Cu
# D- : B7 -> A7 as a B.Cu jumper between vias in the far end of each pad
track('/PORT_D-', F, (110.825, 25.750), (111.150, 25.750), 0.21)
via('/PORT_D-', 111.150, 25.750)
track('/PORT_D-', B, (111.150, 25.750), (111.150, 24.750), 0.21)
via('/PORT_D-', 111.150, 24.750)
track('/PORT_D-', F, (111.150, 24.750), (110.825, 24.750), 0.21)

# PORT_VBUS : U3.5 out along the freed corridor, then down to the B.Cu spine
track('/PORT_VBUS', F, (108.638, 25.000), (109.700, 25.000), 0.35)
via('/PORT_VBUS', 109.700, 25.000)
track('/PORT_VBUS', B, (109.700, 25.000), (109.700, 24.091), 0.35)
track('/PORT_VBUS', B, (109.700, 24.091), (104.157, 24.091), 0.35)
print("D- B.Cu jumper and PORT_VBUS F.Cu escape added")

# ---------- (2) connectors to the exact minimum inset ----------
for ref, x in (('J1', 5.120), ('J2', 114.880)):
    f = b.FindFootprintByReference(ref)
    p = f.GetPosition()
    f.SetPosition(pcbnew.VECTOR2I(IU(x), p.y))
    xs = [v for pad in f.Pads()
          for v in (MM(pad.GetBoundingBox().GetLeft()), MM(pad.GetBoundingBox().GetRight()))]
    cy = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if ref == 'J1':
        print("  J1 x=%.3f  copper starts %.3f mm from edge; body reaches %.3f mm"
              % (x, min(xs), -MM(cy.GetLeft())))
    else:
        print("  J2 x=%.3f  copper ends %.3f mm from edge; body reaches %.3f mm"
              % (x, 120 - max(xs), MM(cy.GetRight()) - 120))

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[1], b)
print("saved")
