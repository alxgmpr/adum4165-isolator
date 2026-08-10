#!/usr/bin/env python3
"""
check_sch_text_overlap.py — detect overlapping visible text in a KiCad .kicad_sch file.

Parses the schematic's S-expression tree and extracts every visible text item
(symbol Reference/Value/other non-hidden properties, net labels, power-symbol
values, and free-standing text annotations), computes an approximate bounding
box for each (honouring justify), and reports any pair of boxes that overlap.

Approximations (documented, intentionally conservative — see task brief):
  - glyph advance width  ~= 0.85 * font_size_mm  per character
  - text block height    ~= font_size_mm
  - default justify (no `justify` tag present) is CENTER/CENTER, matching
    KiCad's default for symbol fields.
  - `hide yes` properties are skipped entirely (not drawn).

This is a filter, not proof — it is expected to over-report slightly rather
than under-report. Exits non-zero if any overlap is found (CI-style gate).

Usage:
    python3 tools/check_sch_text_overlap.py hub.kicad_sch [--margin 0.0]
"""

import sys
import argparse


# ---------------------------------------------------------------------------
# Minimal S-expression tokenizer / parser for the KiCad sexpr dialect.
# Everything is kept as strings (atoms) or nested lists; callers convert
# to float/etc. as needed. Quoted strings have their quotes stripped and
# escape sequences resolved.
# ---------------------------------------------------------------------------

def tokenize(text):
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == "(" or c == ")":
            tokens.append(c)
            i += 1
            continue
        if c == '"':
            j = i + 1
            buf = []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            tokens.append(("STR", "".join(buf)))
            i = j + 1
            continue
        # bare atom
        j = i
        while j < n and text[j] not in " \t\r\n()":
            j += 1
        tokens.append(text[i:j])
        i = j
    return tokens


def parse(tokens):
    pos = [0]

    def parse_expr():
        tok = tokens[pos[0]]
        if tok == "(":
            pos[0] += 1
            lst = []
            while tokens[pos[0]] != ")":
                lst.append(parse_expr())
            pos[0] += 1  # consume ')'
            return lst
        else:
            pos[0] += 1
            if isinstance(tok, tuple) and tok[0] == "STR":
                return tok[1]
            return tok

    exprs = []
    while pos[0] < len(tokens):
        exprs.append(parse_expr())
    return exprs


def atom(node):
    """Return the string value of a leaf atom (bare or quoted)."""
    return node


def car(node):
    return node[0] if isinstance(node, list) and node else None


def find_all(node, tag):
    """Direct children of `node` (a list) whose car == tag."""
    if not isinstance(node, list):
        return []
    return [c for c in node if isinstance(c, list) and c and c[0] == tag]


def find_one(node, tag):
    r = find_all(node, tag)
    return r[0] if r else None


# ---------------------------------------------------------------------------
# Text item extraction
# ---------------------------------------------------------------------------

class TextItem:
    def __init__(self, owner, field, text, x, y, size, just_h, just_v, angle):
        self.owner = owner      # e.g. "U1" or "(label)" or "(text)"
        self.field = field      # e.g. "Reference", "Value", "label", "text"
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.just_h = just_h    # 'left' | 'center' | 'right'
        self.just_v = just_v    # 'top' | 'center' | 'bottom'
        self.angle = angle

    def bbox(self):
        """Return (xmin, xmax, ymin, ymax) in mm.

        Rotation is ignored for boxes (angle 0/90/180/270 all treated as
        axis-aligned using the *unrotated* width/height) — deliberately
        conservative: a 90-degree-rotated label's true footprint is a tall
        thin box, but treating it as if horizontal still catches genuine
        collisions and merely risks a few extra false positives, which is
        the accepted tradeoff here.
        """
        # Multi-line text: width is the LONGEST line, not the sum of every
        # character. Summing made a wrapped note span the whole page and
        # collide with everything, which cost Task 4 several fix iterations
        # chasing false positives.
        #
        # Note that KiCad's own parser rejects raw newlines inside a
        # (text ...) value -- kicad-cli fails with "Failed to load schematic"
        # even though direct SVG rasterisation renders it fine. The working
        # convention on this project is one single-line text node per line,
        # so multi-line values should be rare; this stays correct either way.
        lines = self.text.split("\n") or [""]
        width = max(max(len(ln) for ln in lines), 1) * 0.85 * self.size
        height = self.size * len(lines)

        if self.angle in (90, 270):
            width, height = height, width

        if self.just_h == "left":
            xmin, xmax = self.x, self.x + width
        elif self.just_h == "right":
            xmin, xmax = self.x - width, self.x
        else:  # center
            xmin, xmax = self.x - width / 2, self.x + width / 2

        if self.just_v == "top":
            ymin, ymax = self.y, self.y + height
        elif self.just_v == "bottom":
            ymin, ymax = self.y - height, self.y
        else:  # center
            ymin, ymax = self.y - height / 2, self.y + height / 2

        return xmin, xmax, ymin, ymax

    def label(self):
        return f'{self.owner}.{self.field} "{self.text}"'


def parse_at(at_node):
    # (at x y [angle])
    x = float(at_node[1])
    y = float(at_node[2])
    angle = int(float(at_node[3])) if len(at_node) > 3 else 0
    return x, y, angle


def parse_justify(effects_node):
    just_h, just_v = "center", "center"
    if effects_node is None:
        return just_h, just_v
    j = find_one(effects_node, "justify")
    if j is None:
        return just_h, just_v
    for tok in j[1:]:
        if tok in ("left", "right", "center"):
            just_h = tok
        elif tok in ("top", "bottom"):
            just_v = tok
        # 'mirror' ignored
    return just_h, just_v


def parse_size(effects_node, default=1.27):
    if effects_node is None:
        return default
    font = find_one(effects_node, "font")
    if font is None:
        return default
    size_node = find_one(font, "size")
    if size_node is None:
        return default
    # (size w h) -- use height
    return float(size_node[2])


def is_hidden(prop_node):
    # Normally `(hide yes)` is a direct child of the property node, e.g.
    # (property "Reference" "#PWR1" (at ...) (hide yes) (effects ...)).
    # At least one MCP tool used on this project (kicad's
    # batch_set_schematic_property_positions with visible=false) instead
    # nests it one level down, inside `effects`:
    #   (effects (font ...) (hide yes))
    # KiCad's own parser accepts both placements and hides the field either
    # way (confirmed by rendering: text hidden this way does not appear in
    # `kicad-cli sch export svg` output). Check both spots so this checker
    # doesn't report false-positive overlaps against text that is actually
    # invisible on the real schematic.
    if find_one(prop_node, "hide") is not None:
        return True
    effects = find_one(prop_node, "effects")
    if effects is not None and find_one(effects, "hide") is not None:
        return True
    return False


def extract_property_items(symbol_node, owner_ref):
    items = []
    for prop in find_all(symbol_node, "property"):
        # (property "Name" "Value" (at x y angle) (hide yes)? (effects ...)?)
        if len(prop) < 3:
            continue
        name = prop[1]
        value = prop[2]
        if not isinstance(value, str) or value == "":
            continue
        if is_hidden(prop):
            continue
        at_node = find_one(prop, "at")
        if at_node is None:
            continue
        x, y, angle = parse_at(at_node)
        effects = find_one(prop, "effects")
        size = parse_size(effects)
        just_h, just_v = parse_justify(effects)
        items.append(TextItem(owner_ref, name, value, x, y, size, just_h, just_v, angle))
    return items


def get_reference(symbol_node):
    for prop in find_all(symbol_node, "property"):
        if len(prop) >= 3 and prop[1] == "Reference":
            return prop[2]
    return "?"


def extract_items(tree):
    items = []
    root = None
    for e in tree:
        if isinstance(e, list) and car(e) == "kicad_sch":
            root = e
            break
    if root is None:
        raise SystemExit("Could not find (kicad_sch ...) root")

    for child in root:
        if not isinstance(child, list) or not child:
            continue
        tag = child[0]

        if tag == "symbol":
            # Placed instance: (symbol (lib_id ...) (at ...) ...)
            # (lib_symbols definitions are a *separate* top-level node,
            # (lib_symbols (symbol "Name" ...) ...), so they never appear
            # here as direct children of kicad_sch with tag=="symbol".)
            ref = get_reference(child)
            items.extend(extract_property_items(child, ref))

        elif tag == "label":
            # (label "TEXT" (at x y angle) (effects ...))
            if len(child) < 2 or not isinstance(child[1], str):
                continue
            text = child[1]
            at_node = find_one(child, "at")
            if at_node is None:
                continue
            x, y, angle = parse_at(at_node)
            effects = find_one(child, "effects")
            size = parse_size(effects)
            just_h, just_v = parse_justify(effects)
            items.append(TextItem("(net label)", "label", text, x, y, size, just_h, just_v, angle))

        elif tag == "text":
            # (text "TEXT" (at x y angle) (effects ...))
            if len(child) < 2 or not isinstance(child[1], str):
                continue
            text = child[1]
            at_node = find_one(child, "at")
            if at_node is None:
                continue
            x, y, angle = parse_at(at_node)
            effects = find_one(child, "effects")
            size = parse_size(effects)
            just_h, just_v = parse_justify(effects)
            items.append(TextItem("(text)", "text", text, x, y, size, just_h, just_v, angle))

    return items


# ---------------------------------------------------------------------------
# Overlap detection
# ---------------------------------------------------------------------------

def boxes_overlap(b1, b2, margin=0.0):
    x1min, x1max, y1min, y1max = b1
    x2min, x2max, y2min, y2max = b2
    x1min -= margin; x1max += margin
    y1min -= margin; y1max += margin
    ox = min(x1max, x2max) - max(x1min, x2min)
    oy = min(y1max, y2max) - max(y1min, y2min)
    if ox > 0 and oy > 0:
        return ox, oy
    return None


REF_VALUE_CLEARANCE_MM = 2.54   # a Reference and its own Value
GENERAL_CLEARANCE_MM = 1.27     # everything else (grid unit)


def required_clearance(a, b):
    """Minimum gap required between two text items' boxes.

    A Reference/Value pair belonging to the *same* owner gets the larger
    2.54 mm rule of thumb; every other pair (including a Reference/Value
    against a third item, or two different components' fields) gets one
    grid unit, 1.27 mm.
    """
    if a.owner == b.owner and {a.field, b.field} == {"Reference", "Value"}:
        return REF_VALUE_CLEARANCE_MM
    return GENERAL_CLEARANCE_MM


# Page sizes in mm, landscape. KiCad draws a frame inset from the sheet edge
# and reserves the bottom-right corner for the title block; TITLE_BLOCK_MM is
# a conservative rectangle covering it.
PAGE_SIZES_MM = {
    "A5": (210.0, 148.0), "A4": (297.0, 210.0), "A3": (420.0, 297.0),
    "A2": (594.0, 420.0), "A1": (841.0, 594.0), "A0": (1189.0, 841.0),
    "A": (279.4, 215.9), "B": (431.8, 279.4), "C": (558.8, 431.8),
    "D": (863.6, 558.8), "E": (1117.6, 863.6),
}
FRAME_INSET_MM = 10.0
TITLE_BLOCK_W_MM = 105.0
TITLE_BLOCK_H_MM = 30.0


def get_paper(tree):
    """Return (width_mm, height_mm) for the sheet's (paper "...") setting."""
    for expr in tree:
        for node in find_all(expr, "paper"):
            name = node[1] if len(node) > 1 else "A4"
            portrait = len(node) > 2 and node[2] == "portrait"
            dims = PAGE_SIZES_MM.get(name)
            if dims is None:
                return None
            return (dims[1], dims[0]) if portrait else dims
    return PAGE_SIZES_MM["A4"]


def check_page_bounds(items, paper):
    """Text outside the drawable frame, or under the title block.

    This is the failure the pairwise overlap test cannot see: a note whose
    anchor is on-page but which is centre- or right-justified extends left of
    that anchor and runs off the sheet, where it is silently clipped on plot.
    An A4 sheet on this project accumulated several of these while the
    pairwise check reported zero problems.
    """
    if paper is None:
        return []
    w, h = paper
    xlo, xhi = FRAME_INSET_MM, w - FRAME_INSET_MM
    ylo, yhi = FRAME_INSET_MM, h - FRAME_INSET_MM
    tb_x, tb_y = xhi - TITLE_BLOCK_W_MM, yhi - TITLE_BLOCK_H_MM

    bad = []
    for it in items:
        x0, x1, y0, y1 = it.bbox()
        if x0 < xlo or x1 > xhi or y0 < ylo or y1 > yhi:
            bad.append((it, "outside the frame"))
        elif x1 > tb_x and y1 > tb_y:
            bad.append((it, "under the title block"))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sch_file")
    ap.add_argument("--margin", type=float, default=None,
                     help=("Required clearance in mm, applied uniformly to every pair. "
                           "If omitted, uses the project rule of thumb: 2.54mm between a "
                           "Reference and its own Value, 1.27mm for everything else."))
    args = ap.parse_args()

    with open(args.sch_file, "r", encoding="utf-8") as f:
        text = f.read()

    tree = parse(tokenize(text))
    items = extract_items(tree)

    print(f"Extracted {len(items)} visible text items from {args.sch_file}")

    overlaps = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            margin = args.margin if args.margin is not None else required_clearance(a, b)
            ov = boxes_overlap(a.bbox(), b.bbox(), margin=margin)
            if ov is not None:
                overlaps.append((a, b, ov))

    paper = get_paper(tree)
    offpage = check_page_bounds(items, paper)
    if paper:
        print(f"Page {paper[0]:.0f}x{paper[1]:.0f} mm")

    if offpage:
        print(f"\n{len(offpage)} item(s) off-page or under the title block:\n")
        for it, why in offpage:
            x0, x1, y0, y1 = it.bbox()
            print(f"  {it.label()} @ ({it.x:.2f},{it.y:.2f}) "
                  f"box=({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f}) -- {why}")
        print()

    if not overlaps and not offpage:
        print("No overlaps found.")
        return 0

    if not overlaps:
        return 1

    print(f"\n{len(overlaps)} overlap(s) found:\n")
    for a, b, (ox, oy) in overlaps:
        abox = a.bbox()
        bbox = b.bbox()
        print(f"  {a.label()} @ ({a.x:.2f},{a.y:.2f}) box=({abox[0]:.2f},{abox[2]:.2f})-({abox[1]:.2f},{abox[3]:.2f})")
        print(f"    vs {b.label()} @ ({b.x:.2f},{b.y:.2f}) box=({bbox[0]:.2f},{bbox[2]:.2f})-({bbox[1]:.2f},{bbox[3]:.2f})")
        print(f"    overlap: {ox:.2f}mm x {oy:.2f}mm")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
