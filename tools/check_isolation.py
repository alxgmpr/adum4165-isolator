#!/usr/bin/env python3
"""
check_isolation.py — verify no component bridges the GND1/GND2 isolation
barrier except the explicitly-allowed parts.

Method: read the kicad-cli KiCad-XML netlist, and for every TWO-PIN
component (resistors, capacitors, diodes, inductors — i.e. anything that is
a genuine two-terminal galvanic/AC bridge between whatever nets its two pins
sit on) union those two nets together with a union-find structure. Multi-pin
parts (ICs, connectors, 3-pin transistors) are *not* unioned pin-to-pin,
since internal IC connectivity between pins is a functional design matter,
not a direct short — assuming otherwise would produce false positives on
every IC that happens to touch both a GND-referenced pin and a signal pin.

Components in ALLOWED_BRIDGES are skipped entirely (they are permitted, by
design, to have pins on both ground domains): the ADuM4165 digital isolator
(U1), the push-pull transformer (T1), and the Y-capacitor CY1 (added in a
later task).

After unioning, the two ground-reference nets (GND1, GND2 by default) must
land in different union-find groups. If they don't, isolation is broken:
print every two-pin component on the path that merged them and exit 1.
Prints nothing and exits 0 if isolation holds.

Usage:
    python3 tools/check_isolation.py netlist.xml
    python3 tools/check_isolation.py netlist.xml --gnd1 GND1 --gnd2 GND2
"""

import sys
import argparse
import xml.etree.ElementTree as ET

ALLOWED_BRIDGES = {"U1", "T1", "CY1"}


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("netlist_xml", help="kicad-cli 'sch export netlist --format kicadxml' output")
    ap.add_argument("--gnd1", default="GND1")
    ap.add_argument("--gnd2", default="GND2")
    args = ap.parse_args()

    tree = ET.parse(args.netlist_xml)

    # ref -> pin_count, from the components/comp list
    pin_counts = {}
    for comp in tree.findall(".//components/comp"):
        ref = comp.get("ref")
        pin_counts[ref] = 0  # filled in below from the net list itself

    # net_name -> [(ref, pin)]
    nets = {}
    for net in tree.findall(".//nets/net"):
        name = net.get("name")
        nodes = [(nd.get("ref"), nd.get("pin")) for nd in net.findall("node")]
        nets[name] = nodes

    # ref -> set of net names it appears on, and ref -> pin count actually seen
    ref_nets = {}
    ref_pin_count = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            ref_nets.setdefault(ref, set()).add(name)
            ref_pin_count[ref] = ref_pin_count.get(ref, 0) + 1

    uf = UnionFind()
    for name in nets:
        uf.find(name)  # ensure every net has a group even if isolated

    bridging_components = []
    for ref, netset in ref_nets.items():
        if ref in ALLOWED_BRIDGES:
            continue
        if ref_pin_count.get(ref, 0) != 2:
            continue  # only genuine two-terminal parts bridge nets here
        if len(netset) < 2:
            continue  # both pins on the same net — not a bridge
        net_list = sorted(netset)
        # a 2-pin component should have exactly 2 distinct nets; union them
        for i in range(1, len(net_list)):
            uf.union(net_list[0], net_list[i])
        bridging_components.append((ref, net_list))

    if args.gnd1 not in nets or args.gnd2 not in nets:
        print(f"WARNING: '{args.gnd1}' or '{args.gnd2}' not found as a net in {args.netlist_xml}; "
              f"available nets include: {', '.join(sorted(nets)[:20])}...", file=sys.stderr)
        return 2

    g1 = uf.find(args.gnd1)
    g2 = uf.find(args.gnd2)

    if g1 != g2:
        return 0  # isolation holds — print nothing, per convention

    # Isolation broken: report every two-pin component whose union touches
    # a net reachable from GND1's side as a diagnostic aid.
    print(f"ISOLATION VIOLATION: '{args.gnd1}' and '{args.gnd2}' are electrically joined.")
    print("Two-pin components that bridge nets (excluding allowed U1/T1/CY1):")
    for ref, net_list in sorted(bridging_components):
        print(f"  {ref}: {' <-> '.join(net_list)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
