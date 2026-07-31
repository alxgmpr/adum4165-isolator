"""Rename schematic net labels by exact (name, x, y) identity.

Connectivity in this schematic is carried by local labels, so renaming a label
IS a net change. Keying on coordinates rather than on the name alone is what
makes a partial rename expressible -- three of eleven ISO_5V labels, say -- and
what makes it reviewable afterwards. Any edit that does not match exactly once
aborts the whole run without writing, because a zero-match or two-match rename
silently produces a netlist nobody designed.

Usage: import and call rename(path, edits).
"""
import re, sys


def rename(path, edits):
    txt = open(path).read()
    for old, x, y, new in edits:
        pat = re.compile(r'(\(label ")' + re.escape(old) +
                         r'("\s*\n\s*\(at ' + re.escape(x) + ' ' + re.escape(y) + ' )')
        txt, n = pat.subn(lambda m: m.group(1) + new + m.group(2), txt, count=1)
        if n != 1:
            sys.exit('ABORT: label %s at (%s, %s) matched %d times, expected 1'
                     % (old, x, y, n))
    open(path, 'w').write(txt)
    for old, x, y, new in edits:
        print('  %-12s (%s, %s)  ->  %s' % (old, x, y, new))
    print('%d labels renamed' % len(edits))
