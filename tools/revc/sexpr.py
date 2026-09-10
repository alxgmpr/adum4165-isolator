"""Small, lossless s-expression helpers for the Rev C source generators."""
from pathlib import Path
import sexpdata as sx

S = sx.Symbol


def node(key, *args):
    return [S(key), *args]


def children(tree, key):
    return [x for x in tree if isinstance(x, list) and x and str(x[0]) == key]


def child(tree, key, default=None):
    return next(iter(children(tree, key)), default)


def value(tree, key, default=None):
    c = child(tree, key)
    return c[1] if c is not None and len(c) > 1 else default


def read(path):
    return sx.loads(Path(path).read_text())


def format_tree(tree, depth=0):
    if not isinstance(tree, list):
        return sx.dumps(tree)
    if not any(isinstance(x, list) for x in tree):
        return '(' + ' '.join(sx.dumps(x) for x in tree) + ')'
    prefix = []
    rest = []
    for x in tree:
        (rest if isinstance(x, list) or rest else prefix).append(x)
    return '(' + ' '.join(sx.dumps(x) for x in prefix) + ''.join(
        '\n' + '  ' * (depth + 1) + format_tree(x, depth + 1) for x in rest
    ) + '\n' + '  ' * depth + ')'


def write(path, tree):
    Path(path).write_text(format_tree(tree) + '\n')
