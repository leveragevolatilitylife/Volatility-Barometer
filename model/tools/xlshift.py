import re

R_START = 5   # insertion row (Metrice)
N_INS = 4

def col2n(c):
    n = 0
    for ch in c: n = n * 26 + ord(ch) - 64
    return n
def n2col(n):
    s = ''
    while n: n, r = divmod(n - 1, 26); s = chr(65 + r) + s
    return s

REF = re.compile(r"(?<![A-Za-z0-9_.$'])((?:'[^']+'|[A-Za-z_][A-Za-z0-9_.]*)!)?(\$?)([A-Z]{1,3})(\$?)(\d+)(?::(\$?)([A-Z]{1,3})(\$?)(\d+))?(?![A-Za-z0-9_(])")

def _map_formula(f, fn):
    # keep string literals intact
    parts = f.split('"')
    for i in range(0, len(parts), 2):
        parts[i] = REF.sub(fn, parts[i])
    return '"'.join(parts)

def translate_rel(f, dr, dc=0):
    def fn(m):
        pre, ac1, c1, ar1, r1, ac2, c2, ar2, r2 = m.groups()
        def one(ac, c, ar, r):
            if not ac: c = n2col(col2n(c) + dc)
            if not ar: r = str(int(r) + dr)
            return f"{ac}{c}{ar}{r}"
        out = (pre or '') + one(ac1, c1, ar1, r1)
        if c2: out += ':' + one(ac2, c2, ar2, r2)
        return out
    return _map_formula(f, fn)

def _outside_rows(a, b):
    """policy for refs from non-moving context. a,b ints (b None for single)."""
    R, N = R_START, N_INS
    if b is None:
        return (a + N if a > R else a), None
    na = a + N if a > R else a
    nb = b + N if b >= R else b
    if a == R and b == R: nb = R
    return na, nb

def shift_outside(f, sheet_match=None):
    def fn(m):
        pre, ac1, c1, ar1, r1, ac2, c2, ar2, r2 = m.groups()
        if pre and sheet_match is not None and sheet_match not in pre: return m.group(0)
        if not pre and sheet_match is not None and sheet_match != '': return m.group(0)
        a = int(r1); b = int(r2) if c2 else None
        na, nb = _outside_rows(a, b)
        out = (pre or '') + f"{ac1}{c1}{ar1}{na}"
        if c2: out += f":{ac2}{c2}{ar2}{nb}"
        return out
    return _map_formula(f, fn)

def shift_moving(f):
    """formula of a cell that physically moves down by N (cell row >= R)."""
    R, N = R_START, N_INS
    def fn(m):
        pre, ac1, c1, ar1, r1, ac2, c2, ar2, r2 = m.groups()
        a = int(r1); b = int(r2) if c2 else None
        # absolute -> outside policy ; relative -> +N if >= R
        def rel(x): return x + N if x >= R else x
        if b is None:
            na = (a + N if a > R else a) if ar1 else rel(a); nb = None
        else:
            na = (a + N if a > R else a) if ar1 else rel(a)
            nb = (b + N if b >= R else b) if ar2 else rel(b)
            if ar1 and ar2 and a == R and b == R: nb = R
        out = (pre or '') + f"{ac1}{c1}{ar1}{na}"
        if c2: out += f":{ac2}{c2}{ar2}{nb}"
        return out
    return _map_formula(f, fn)

def abs_shift_only(f):
    """for brand-new rows: relative refs already translated; shift absolute rows >= R."""
    R, N = R_START, N_INS
    def fn(m):
        pre, ac1, c1, ar1, r1, ac2, c2, ar2, r2 = m.groups()
        a = int(r1); b = int(r2) if c2 else None
        na = (a + N if a > R else a) if ar1 else a
        nb = None if b is None else ((b + N if b >= R else b) if ar2 else b)
        out = (pre or '') + f"{ac1}{c1}{ar1}{na}"
        if c2: out += f":{ac2}{c2}{ar2}{nb}"
        return out
    return _map_formula(f, fn)

def shift_sqref(sq):
    outs = []
    for part in sq.split():
        m = re.fullmatch(r'([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?', part)
        c1, r1, c2, r2 = m.groups()
        a = int(r1); b = int(r2) if r2 else None
        na, nb = _outside_rows(a, b)
        outs.append(f"{c1}{na}" + (f":{c2}{nb}" if c2 else ''))
    return ' '.join(outs)
