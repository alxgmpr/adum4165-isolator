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


def load_rules(pro_path):
    """Both mechanisms KiCad resolves a net's classes from.

    netclass_patterns are glob-matched; netclass_assignments are explicit
    per-net entries written by Board Setup. Reading only patterns reports a net
    as unclassified while KiCad's DRC engine sees it classed -- the mirror image
    of the silent hole this gate exists to close, and just as misleading.
    """
    ns = json.load(open(pro_path))['net_settings']
    pats = [(p['netclass'], p['pattern']) for p in ns.get('netclass_patterns') or []]
    assigns = {n: list(cs) for n, cs in (ns.get('netclass_assignments') or {}).items()}
    return pats, assigns


def classes_for(net, patterns, assignments=None, restrict=None):
    hits = {c for c, p in patterns if fnmatch.fnmatch(net, p)}
    if assignments:
        hits |= set(assignments.get(net, ()))
    if restrict is not None:
        hits &= set(restrict)
    return hits


def check(pro_path, netlist_path):
    pats, assigns = load_rules(pro_path)

    unclassified, both = [], []
    for n in nets_from_netlist(netlist_path):
        if n.startswith(EXEMPT_PREFIX):
            continue
        hits = classes_for(n, pats, assigns, restrict=('HOST_SIDE', 'ISO_SIDE'))
        if not hits:
            unclassified.append(n)
        elif len(hits) > 1:
            both.append(n)

    diffpair_missing = [n for n in DIFF_PAIRS
                        if not classes_for(n, pats, assigns, restrict=('USB_DIFF90',))]
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
