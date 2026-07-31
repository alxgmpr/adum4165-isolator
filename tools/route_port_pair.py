"""Hand-route /PORT_D+ and /PORT_D- as a real coupled differential pair.

Freerouting's attempt was discarded: it put the two halves of the pair on
different layers for 35 mm (no coupling at all) and shorted U3 pins 3-4 with an
external trace, bypassing the ESD array instead of routing in-line through it.

Idiom copied from the host side: a single continuous trace passes THROUGH both
array pads (enter pin 1/3, leave pin 6/4), so the array sits in-line with no
stub, and connectivity closes without an external pin-to-pin jumper.

Geometry, all in mm:
  U1.12 D+ (64.900, 29.445)      U1.13 D- (64.900, 28.175)
  U3 pad1/6 D+ centred y=24.050  U3 pad3/4 D- centred y=25.950
  J2 B6 (110.825,24.250) A6 (110.825,25.250)   A7 (110.825,24.750) B7 (110.825,25.750)
  D6 body x 102.200..104.200, pads y 24.650..25.350 -- D+ passes above, D- below.
"""
import sys, math, pcbnew

BOARD = sys.argv[1]
MEANDER = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0   # added to D- corridor
b = pcbnew.LoadBoard(BOARD)
IU, MM = pcbnew.FromMM, pcbnew.ToMM
W = 0.21
FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu

# ---------- rip up the existing pair ----------
doomed = [t for t in b.GetTracks() if t.GetNetname() in ('/PORT_D+', '/PORT_D-')]
for t in doomed:
    b.Remove(t)
print("ripped up %d items from /PORT_D+ and /PORT_D-" % len(doomed))

# ---------- corridor geometry ----------
Y_UP, Y_LO = 27.900, 28.237      # coupled pair: 0.337 pitch = 0.21 width + 0.127 gap
# The crossover cannot happen at the 0.337 pitch: a 0.5 mm via needs the D- track
# centreline 0.25 + 0.127 + 0.105 = 0.482 mm clear of the via centre, and at
# 0.337 pitch the diagonal only clears 0.316 mm -- which shorts. The host-side
# crossover works because it opens the pair to 0.8 mm first (clears 0.598 mm).
# Same trick here: widen, cross, narrow back.
W_UP, W_LO = 27.700, 28.500      # widened to 0.8 for the crossover
XW0, XW1 = 94.500, 95.500        # widen span
XC0, XC1 = 95.500, 96.400        # crossover span
XN1 = 97.400                     # narrowed back by here
XFAN = 100.500                   # where the pair fans out to the U3 pin heights
XU3_IN, XU3_OUT = 102.000, 107.800

# D+ : starts LOW (U1.12 at 29.445), crosses to UP, ends at U3 y=24.050 (upper)
dp_fcu_a = [(64.900, 29.445), (66.500, Y_LO), (XW0, Y_LO), (XW1, W_LO)]
dp_bcu   = [(XC0, W_LO), (XC1, W_UP)]                       # dips under D-
dp_fcu_b = [(XC1, W_UP), (XN1, Y_UP), (XFAN, Y_UP), (XU3_IN, 24.050), (XU3_OUT, 24.050),
            (108.100, 24.250), (110.825, 24.250),           # into J2.B6
            (111.522, 24.250), (111.831, 24.559), (111.831, 24.930),
            (111.510, 25.250), (110.825, 25.250)]           # loop round to J2.A6

# D- : starts UP (U1.13 at 28.175), ends at U3 y=25.950 (lower). Stays on F.Cu.
dm_fcu = [(64.900, 28.175), (66.000, Y_UP), (XW0, Y_UP), (XW1, W_UP)]
dm_mid = [(XC0, W_UP), (XC1, W_LO)]                          # crosses over D+
# D- is the geometrically shorter half by about 2 mm, so it carries a serpentine
# detour in the corridor. A rectangular detour of amplitude A adds exactly 2A, and
# MEANDER is that amplitude. It sits at x 98.0..99.5, clear of R3 (x 93.2..94.8)
# and below C12 (y 23.5..26.5).
dm_fcu_b = [(XC1, W_LO), (XN1, Y_LO),
            (98.000, Y_LO), (98.000, Y_LO + MEANDER),
            (99.500, Y_LO + MEANDER), (99.500, Y_LO),
            # D- starts its climb 0.5 mm AFTER D+ does. Starting both at XFAN looks
            # like divergence from the endpoints but is not: the perpendicular
            # distance between the two fan-out diagonals dips to 0.184 mm, so at
            # 0.21 mm width they overlap by 0.025 mm. Staggering keeps D- flat and
            # 0.337 mm below while D+ is already descending steeply away.
            (XFAN + 0.500, Y_LO),
            (XU3_IN, 25.950), (XU3_OUT, 25.950),
            (108.100, 25.750), (110.825, 25.750)]            # into J2.B7
# The A7 branch is a separate polyline tee-ing off the B7 run at x=109.300 rather
# than a retrace back along it: listing it as a continuation would lay a second
# track on top of the first, which is duplicate copper on the same net AND
# inflates the length Gate 3 measures.
# It diverges at 109.300, not 108.100, to leave the corridor clear at x~108.5 so
# PORT_VBUS can escape U3.5 to a via in free space instead of a via in its pad.
dm_branch = [(109.300, 25.750), (110.126, 24.750), (110.825, 24.750)]


def net(n):
    return b.FindNet(n)


def add_track(pts, layer, netname):
    total = 0.0
    ni = net(netname)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if (x1, y1) == (x2, y2):
            continue
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(IU(x1), IU(y1)))
        t.SetEnd(pcbnew.VECTOR2I(IU(x2), IU(y2)))
        t.SetWidth(IU(W))
        t.SetLayer(layer)
        t.SetNetCode(ni.GetNetCode())
        b.Add(t)
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def add_via(x, y, netname):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(IU(x), IU(y)))
    v.SetWidth(IU(0.5))
    v.SetDrill(IU(0.3))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(FCU, BCU)
    v.SetNetCode(net(netname).GetNetCode())
    b.Add(v)


lp = add_track(dp_fcu_a, FCU, '/PORT_D+')
lp += add_track(dp_bcu, BCU, '/PORT_D+')
lp += add_track(dp_fcu_b, FCU, '/PORT_D+')
add_via(XC0, W_LO, '/PORT_D+')
add_via(XC1, W_UP, '/PORT_D+')

lm = add_track(dm_fcu, FCU, '/PORT_D-')
lm += add_track(dm_mid, FCU, '/PORT_D-')
lm += add_track(dm_fcu_b, FCU, '/PORT_D-')
lm += add_track(dm_branch, FCU, '/PORT_D-')

print("routed lengths: D+ %.3f mm   D- %.3f mm   skew %.4f mm  (meander=%.3f)"
      % (lp, lm, abs(lp - lm), MEANDER))
pcbnew.SaveBoard(BOARD, b)
print("saved")
