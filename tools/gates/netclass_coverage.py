"""Every copper net must be in exactly one of HOST_SIDE / ISO_SIDE, and both
differential pairs must be USB_DIFF90.

A net in neither domain never triggers the barrier rules in isolator.kicad_dru,
which key off A.hasNetclass('HOST_SIDE') && B.hasNetclass('ISO_SIDE'). That is a
silent hole, not a visible failure, which is why it is gated.
"""
import sys, os, json, re, fnmatch

# Six single-pad nets with no routed copper. Exempt by name, deliberately.
EXEMPT_PREFIX = 'unconnected-('
DIFF_PAIRS = ['/HOST_D+', '/HOST_D-', '/PORT_D+', '/PORT_D-']


def nets_from_netlist(path):
    txt = open(path).read()
    blk = txt[txt.index('(nets'):]
    return sorted(set(re.findall(r'\(name "([^"]*)"\)', blk)))


def classes_for(net, patterns):
    return {c for c, p in patterns if fnmatch.fnmatch(net, p)}


def check(pro_path, netlist_path):
    pro = json.load(open(pro_path))
    pats = [(p['netclass'], p['pattern']) for p in pro['net_settings']['netclass_patterns']]
    side = [(c, p) for c, p in pats if c in ('HOST_SIDE', 'ISO_SIDE')]
    diff = [(c, p) for c, p in pats if c == 'USB_DIFF90']

    unclassified, both = [], []
    for n in nets_from_netlist(netlist_path):
        if n.startswith(EXEMPT_PREFIX):
            continue
        hits = classes_for(n, side)
        if not hits:
            unclassified.append(n)
        elif len(hits) > 1:
            both.append(n)

    diffpair_missing = [n for n in DIFF_PAIRS if not classes_for(n, diff)]
    ok = not unclassified and not both and not diffpair_missing
    return ok, unclassified, both, diffpair_missing


def main():
    ok, unclassified, both, missing = check(sys.argv[1], sys.argv[2])
    for n in unclassified:
        print("  FAIL  %-28s in NEITHER HOST_SIDE nor ISO_SIDE" % n)
    for n in both:
        print("  FAIL  %-28s in BOTH HOST_SIDE and ISO_SIDE" % n)
    for n in missing:
        print("  FAIL  %-28s not matched by any USB_DIFF90 pattern" % n)
    print("\nnetclass coverage: %d unclassified, %d ambiguous, %d diff-pair nets off USB_DIFF90"
          % (len(unclassified), len(both), len(missing)))
    print("VERDICT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
