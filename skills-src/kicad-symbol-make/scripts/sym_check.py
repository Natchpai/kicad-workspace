"""Read-only check of one KiCad symbol: pin table, KLC symbol checks, and compare with a pin table,
another symbol or a footprint.

Usage:
    python -I sym_check.py <lib.kicad_sym> [--name <symbol>] [--ref pins.csv | --vs <other.kicad_sym>[:name]]
                           [--fp <fp.kicad_mod>] [--dump pins.csv] [--quiet]
    python -I sym_check.py <stock lib.kicad_sym> --ref pins.csv --scan

<lib.kicad_sym> is a one-symbol file or a whole library (then --name picks the symbol; default: the
only root symbol). extends is resolved: pins and body from the parent, fields from the child.

KLC checks print WARN or INFO with the rule number (S3.1 .. S6.2). They never change the exit code.
--ref    compare with a pin table (pins.csv, format in SPEC.md): DIFF on a missing or extra number,
         a name or type mismatch, a missing alternate, or a CSV stack the symbol does not have.
         Names compare after case folding and active-low normalization (nRESET = RESET# = ~{RESET}).
--vs     the same compare with another symbol, plus stacks both ways; fields are INFO.
--fp     pin numbers (stacks expanded) against pad numbers; NPTH holes are ignored.
--scan   rank every symbol in the library against the pin table (pin numbers not in both, name and type
         differences) and print the best 10; exit 0 when one matches on numbers and names.
--quiet  skip the pin table; KLC lines and DIFF lines still print.
DIFF lines show the symbol's value first, then the table's or the other symbol's.
--dump   write the symbol as pins.csv and <stem>.layout.json (fields, pin length, unit names, stack off)
         so make_symbol.py can rebuild it.
Exit code 1 on any DIFF, 2 on a read error.
"""
import argparse
import csv
import json
import math
import os
import re
import sys

EPS = 1e-4
GRID = 2.54
TYPES = {'input', 'output', 'bidirectional', 'tri_state', 'passive', 'free', 'unspecified',
         'power_in', 'power_out', 'open_collector', 'open_emitter', 'no_connect'}
REFS = {'A', 'AE', 'BT', 'C', 'D', 'DS', 'F', 'FB', 'FD', 'FL', 'H', 'J', 'JP', 'K', 'L', 'LS', 'M',
        'MK', 'P', 'Q', 'R', 'RN', 'RT', 'RV', 'SW', 'T', 'TC', 'TJ', 'TP', 'U', 'Y', 'Z'}
FIELDS = {'Reference', 'Value', 'Footprint', 'Datasheet', 'Description', 'ki_keywords', 'ki_fp_filters',
          'ki_locked'}
POWER_NAME = re.compile(r'^(VCC|VDD|VSS|GND|AGND|DGND|PGND|AVDD|DVDD|VBAT|VIN|PVIN|AVIN|VIO|VDDIO|VDDA|VSSA|VCCIO)'
                        r'([_\d]\w*)?$', re.I)
DISCRETE = {'C', 'D', 'F', 'FB', 'L', 'Q', 'R', 'RT', 'RV', 'Z'}
ACTIVE_LOW = (r'^n([A-Z][A-Z0-9_]*)$', r'^([A-Z][A-Z0-9_]*)#$', r'^/([A-Z][A-Z0-9_]*)$')


# ---- s-expression (same tokenizer as kicad-footprint-make/fp_check.py) ---------------------------
def unq(t):
    return re.sub(r'\\(.)', r'\1', t[1:-1])


def parse(text):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack, cur = [], []
    for t in tokens:
        if t == '(':
            stack.append(cur)
            cur = []
        elif t == ')':
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(unq(t) if t.startswith('"') else t)
    return cur[0]


def kids(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def kid(node, key):
    k = kids(node, key)
    return k[0] if k else None


def flag(node, key):
    """(hide yes), (hide) or a bare hide token."""
    k = kid(node, key)
    if k is not None:
        return len(k) == 1 or k[1] == 'yes'
    return key in node


def g(v):
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def expand(number):
    """'5' -> ['5']; KiCad 10 stack '[2,5,8]' or '[1-4,7]' -> members."""
    s = number.strip()
    if not (s.startswith('[') and s.endswith(']')):
        return [s]
    out = []
    for part in s[1:-1].split(','):
        part = part.strip()
        m = re.match(r'^([A-Z]*)(\d+)-\1?(\d+)$', part)
        if m and int(m.group(3)) >= int(m.group(2)):
            out += [f'{m.group(1)}{k}' for k in range(int(m.group(2)), int(m.group(3)) + 1)]
        elif part:
            out.append(part)
    return out


def norm(name):
    """Name for compare: case folded, active-low marks made the same."""
    s = name.strip()
    for pat in ACTIVE_LOW:
        m = re.match(pat, s)
        if m:
            s = '~{' + m.group(1) + '}'
            break
    s = re.sub(r'~\{([^}]*)\}', r'~\1', s)
    s = re.sub(r'[_^]\{([^}]*)\}', r'\1', s)
    return re.sub(r'\s+', '', s).upper()


def shown(name):
    return re.sub(r'[~_^]\{([^}]*)\}', r'\1', name)


def font_size(node):
    eff = kid(node, 'effects')
    f = kid(eff, 'font') if eff else None
    s = kid(f, 'size') if f else None
    return float(s[1]) if s else None


# ---- symbol model -------------------------------------------------------------------------------
class Symbol:
    def __init__(self, path, name=None, lib=None):
        self.path = path
        if lib is None:
            with open(path, encoding='utf-8') as fh:
                lib = parse(fh.read())
        roots = {s[1]: s for s in kids(lib, 'symbol')}
        if not roots:
            raise ValueError(f'{path}: no symbol')
        if name is None:
            if len(roots) > 1:
                raise ValueError(f'{path} holds {len(roots)} symbols; pick one with --name')
            name = next(iter(roots))
        if name not in roots:
            raise ValueError(f'{path}: no symbol {name!r}')
        self.name = name
        node = roots[name]
        ext = kid(node, 'extends')
        body = node
        if ext:
            if ext[1] not in roots:
                raise ValueError(f'{name} extends {ext[1]!r}, which is not in {path}')
            body = roots[ext[1]]
            self.parent = ext[1]
        else:
            self.parent = None
        self.props = {}
        for src in ([body, node] if ext else [node]):
            for p in kids(src, 'property'):
                at = kid(p, 'at')
                self.props[p[1]] = {'value': p[2], 'hide': flag(p, 'hide') or flag(kid(p, 'effects') or [], 'hide'),
                                    'size': font_size(p), 'at': (float(at[1]), float(at[2])) if at else None}
        pn = kid(body, 'pin_names')
        self.name_offset = 0.508   # KiCad default when pin_names is absent
        self.names_hidden = False
        if pn is not None:
            off = kid(pn, 'offset')
            self.name_offset = float(off[1]) if off else None
            self.names_hidden = flag(pn, 'hide')
        self.numbers_hidden = flag(kid(body, 'pin_numbers') or [], 'hide')
        self.pins, self.rects, self.unit_names = [], [], {}
        base = body[1]
        for sub in kids(body, 'symbol'):
            m = re.match(re.escape(base) + r'_(\d+)_(\d+)$', sub[1])
            if not m:
                continue
            unit, style = int(m.group(1)), int(m.group(2))
            if style > 1:   # De Morgan body style repeats the pins
                continue
            un = kid(sub, 'unit_name')
            if un:
                self.unit_names[unit] = un[1]
            for r in kids(sub, 'rectangle'):
                (x1, y1), (x2, y2) = [tuple(map(float, kid(r, k)[1:3])) for k in ('start', 'end')]
                st = kid(kid(r, 'stroke') or [], 'width')
                fl = kid(kid(r, 'fill') or [], 'type')
                self.rects.append({'unit': unit, 'box': (min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)),
                                   'width': float(st[1]) if st else None, 'fill': fl[1] if fl else None})
            for p in kids(sub, 'pin'):
                at = kid(p, 'at')
                nm, nb = kid(p, 'name'), kid(p, 'number')
                self.pins.append({
                    'unit': unit, 'type': p[1], 'shape': p[2] if len(p) > 2 and isinstance(p[2], str) else 'line',
                    'x': float(at[1]), 'y': float(at[2]), 'rot': int(float(at[3])) if len(at) > 3 else 0,
                    'length': float(kid(p, 'length')[1]) if kid(p, 'length') else 0.0,
                    'hide': flag(p, 'hide'), 'name': nm[1] if nm else '', 'number': nb[1] if nb else '',
                    'nums': expand(nb[1]) if nb else [], 'name_size': font_size(nm) if nm else None,
                    'num_size': font_size(nb) if nb else None,
                    'alts': [(a[1], a[2]) for a in kids(p, 'alternate')]})
        self.units = sorted({p['unit'] for p in self.pins} or {1})
        self.multi = len([u for u in self.units if u > 0]) > 1

    def side(self, p):
        if p['hide']:
            return 'hidden'
        return {0: 'left', 180: 'right', 270: 'top', 90: 'bottom'}.get(p['rot'] % 360, 'left')

    def by_number(self):
        out = {}
        for p in self.pins:
            for m in p['nums']:
                out.setdefault(m, []).append(p)
        return out

    def unit_box(self, unit):
        boxes = [r['box'] for r in self.rects if r['unit'] in (unit, 0)]
        if not boxes:
            return None
        return (min(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), max(b[3] for b in boxes))


# ---- pin table ----------------------------------------------------------------------------------
def read_table(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        rows = [r for r in csv.reader(fh)]
    while rows and (not any(c.strip() for c in rows[0]) or rows[0][0].lstrip().startswith('#')):
        rows.pop(0)
    head = [h.strip().lower() for h in rows[0]] if rows else []
    for need in ('number', 'name', 'type'):
        if need not in head:
            raise ValueError(f'{path}: header has no "{need}" column')
    out = []
    for i, row in enumerate(rows[1:], start=2):
        if not row or not any(c.strip() for c in row) or row[0].lstrip().startswith('#'):
            continue
        r = {h: (row[k].strip() if k < len(row) else '') for k, h in enumerate(head)}
        if not r['number'] and not r['name']:
            continue
        alts = []
        for a in filter(None, (x.strip() for x in r.get('alt', '').split('|'))):
            an, _, at = a.partition(':')
            alts.append((an.strip(), (at or r['type']).strip().lower()))
        out.append({'line': i, 'number': r['number'], 'nums': expand(r['number']), 'name': r['name'],
                    'type': r['type'].lower(), 'alts': alts})
    return out


# ---- report helpers -----------------------------------------------------------------------------
def compress(nums):
    nums = sorted(nums, key=natkey)
    if len(nums) > 12:
        return ', '.join(nums[:12]) + f' .. ({len(nums)})'
    return ', '.join(nums)


def table(sym):
    print(f'symbol {sym.name}' + (f' (extends {sym.parent})' if sym.parent else '') +
          f': {sum(len(p["nums"]) for p in sym.pins)} pin numbers, {len(sym.pins)} pins drawn, '
          f'units {len([u for u in sym.units if u > 0]) or 1}')
    print(f'  {"unit":>4}  {"number":<16} {"name":<22} {"type":<15} {"side":<7} alternates')
    for p in sorted(sym.pins, key=lambda p: (p['unit'], natkey(p['nums'][0] if p['nums'] else ''))):
        alts = ', '.join(a for a, _ in p['alts'])
        if len(alts) > 50:
            alts = alts[:47] + '...'
        print(f'  {p["unit"]:>4}  {p["number"]:<16} {p["name"]:<22} {p["type"]:<15} {sym.side(p):<7} {alts}')


def checks(sym):
    """KLC symbol checks. Returns list of (level, rule, text)."""
    out = []

    def add(level, rule, text):
        out.append((level, rule, text))

    pins = sym.pins
    vis = [p for p in pins if not p['hide']]
    # S3.1 origin
    boxes = [r['box'] for r in sym.rects]
    if boxes:
        x1, x2 = min(b[0] for b in boxes), max(b[1] for b in boxes)
        y1, y2 = min(b[2] for b in boxes), max(b[3] for b in boxes)
        if not (x1 - EPS <= 0 <= x2 + EPS and y1 - EPS <= 0 <= y2 + EPS):
            add('WARN', 'S3.1', f'origin (0,0) is outside the body {g(x1)}..{g(x2)} x {g(y1)}..{g(y2)}')
        elif abs((x1 + x2) / 2) > GRID or abs((y1 + y2) / 2) > GRID:
            add('INFO', 'S3.1', f'body center ({g((x1 + x2) / 2)}, {g((y1 + y2) / 2)}) is more than 2.54 from the origin')
    # S3.2 text
    for k, v in sym.props.items():
        if k in ('Reference', 'Value', 'Footprint', 'Datasheet', 'Description') and v['size'] and abs(v['size'] - 1.27) > EPS:
            add('WARN', 'S3.2', f'{k} text {g(v["size"])} mm, KLC wants 1.27')
    small = sorted({g(s) for p in pins for s in (p['name_size'], p['num_size']) if s and abs(s - 1.27) > EPS})
    if small:
        bad = [s for s in small if float(s) < 0.508 - EPS or float(s) > 1.27 + EPS]
        add('WARN' if bad else 'INFO', 'S3.2', f'pin text sizes {", ".join(small)} mm (1.27 normal, 0.508 smallest)')
    # S3.3 body: the largest rectangle of each unit, one line per finding
    bodies = {}
    for r in sym.rects:
        area = (r['box'][1] - r['box'][0]) * (r['box'][3] - r['box'][2])
        if area > bodies.get(r['unit'], (0, None))[0]:
            bodies[r['unit']] = (area, r)
    strokes = sorted({g(r['width']) for _, r in bodies.values()
                      if r['width'] is not None and r['width'] != 0 and abs(r['width'] - 0.254) > EPS})
    if strokes:
        add('INFO', 'S3.3', f'body stroke {", ".join(strokes)} mm (KLC 0.254)')
    fills = sorted({r['fill'] for _, r in bodies.values() if r['fill'] not in ('background', None)})
    if fills:
        add('INFO', 'S3.3', f'body fill {", ".join(fills)} (black-box symbols use background)')
    # S3.5 pin ends outside the body
    for p in vis:
        b = sym.unit_box(p['unit'])
        if b and b[0] + EPS < p['x'] < b[1] - EPS and b[2] + EPS < p['y'] < b[3] - EPS:
            add('WARN', 'S3.5', f'pin {p["number"]} {p["name"]}: connection point inside the body')
    # S3.6 name offset
    if sym.name_offset is not None and not sym.names_hidden and sym.name_offset > 0:
        if sym.name_offset > 1.27 + EPS or sym.name_offset < 0.508 - EPS:
            add('WARN', 'S3.6', f'pin name offset {g(sym.name_offset)} mm, KLC range 0.508 to 1.27')
        elif abs(sym.name_offset - 0.508) > EPS:
            add('INFO', 'S3.6', f'pin name offset {g(sym.name_offset)} mm (KLC prefers 0.508)')
    # S3.8 power unit
    if sym.multi:
        for u in sym.units:
            up = [p for p in pins if p['unit'] == u]
            pw = [p for p in up if p['type'] in ('power_in', 'power_out')]
            if pw and len(pw) < len(up) and len([v for v in sym.units if v > 0]) > 1 and \
                    any(p['type'] not in ('power_in', 'power_out') for p in up):
                add('INFO', 'S3.8', f'unit {u} mixes power pins ({compress([m for p in pw for m in p["nums"]])}) '
                                    'with logic pins; drawn-apart units share power through a separate unit')
                break
    # S4.1 grid, length, numbers. Simple discretes and drawn shapes with no rectangle body (logic gates)
    # use other grids and pin lengths, as stock does: INFO.
    ref = sym.props.get('Reference', {}).get('value', '')
    simple = (len(pins) <= 3 and ref in DISCRETE) or not sym.rects
    lvl = 'INFO' if simple else 'WARN'
    off = [p for p in vis if abs(p['x'] / GRID - round(p['x'] / GRID)) > EPS or abs(p['y'] / GRID - round(p['y'] / GRID)) > EPS]
    if off:
        add(lvl, 'S4.1', f'{len(off)} pins off the 2.54 grid: {compress([p["number"] for p in off])}')
    lens = sorted({round(p['length'], 4) for p in vis})
    if len(lens) > 1:
        add(lvl, 'S4.1', f'pin lengths differ: {", ".join(g(v) for v in lens)}')
    for L in lens:
        if L < 2.54 - EPS or L > 7.62 + EPS or abs(L / 1.27 - round(L / 1.27)) > EPS:
            add(lvl, 'S4.1', f'pin length {g(L)}: 2.54 to 7.62 in 1.27 steps')
    chars = max([len(m) for p in pins for m in p['nums']] or [0])
    if lens and chars >= 3 and max(lens) < 3.81 - EPS:
        add('INFO', 'S4.1', f'pin numbers have {chars} characters; KLC uses 3.81 mm pins for 3')
    many = [p['name'] for p in vis if shown(p['name']).count('/') >= 2]
    if many:
        add('INFO', 'S4.1', f'names with more than two functions (KLC: at most two, the rest as alternates): '
                            f'{", ".join(sorted(set(many))[:6])}')
    bn = sym.by_number()
    dup = sorted([m for m, ps in bn.items() if len(ps) > 1], key=natkey)
    if dup:
        add('WARN', 'S4.1', f'pin numbers used more than once: {compress(dup)}')
    # S4.3 stacks
    for p in pins:
        if len(p['nums']) > 1 and p['type'] == 'no_connect':
            add('WARN', 'S4.3', f'stack {p["number"]} is no_connect')
    spots = {}
    for p in pins:
        spots.setdefault((p['unit'], round(p['x'], 3), round(p['y'], 3)), []).append(p)
    same = [ps for ps in spots.values() if len(ps) > 1]
    if same:
        add('WARN', 'S4.3', f'{len(same)} places hold several pins (old stacking workaround; draw each pin separately): '
                            + '; '.join('/'.join(p['number'] for p in ps) for ps in same[:4]))
    stacks = [p for p in pins if len(p['nums']) > 1]
    if stacks:
        add('INFO', 'house', 'pin stacks (house style draws each pin separately): '
                             + '; '.join(f'{p["number"]} {p["name"]}' for p in stacks[:6]))
    # S4.4 types
    if ref == 'U':
        wrong = [p for p in pins if POWER_NAME.match(shown(p['name'])) and p['type'] not in ('power_in', 'power_out')
                 and not p['hide']]
        if wrong:
            add('WARN', 'S4.4', 'power-named pins not power_in/power_out: ' +
                ', '.join(f'{p["number"]} {p["name"]} ({p["type"]})' for p in wrong[:8]))
    for p in pins:
        if p['shape'] in ('inverted', 'inverted_clock') and '~{' in p['name']:
            add('WARN', 'S4.4', f'pin {p["number"]} {p["name"]}: inverted shape and overbar (double inversion)')
    # S4.6 hidden pins
    for p in pins:
        if p['hide'] and p['type'] != 'no_connect':
            add('WARN', 'S4.6', f'hidden pin {p["number"]} {p["name"]} is {p["type"]}; only no_connect pins may be hidden')
        elif p['hide']:
            b = sym.unit_box(p['unit'])
            if b and not (b[0] - EPS <= p['x'] <= b[1] + EPS and b[2] - EPS <= p['y'] <= b[3] + EPS):
                add('INFO', 'S4.6', f'hidden NC pin {p["number"]}: end outside the body outline')
    # S4.7 active low
    marks = [p['name'] for p in pins if any(re.match(pat, p['name']) for pat in ACTIVE_LOW)]
    if marks:
        add('WARN', 'S4.7', f'active-low names to write as ~{{...}}: {", ".join(sorted(set(marks))[:8])}')
    # S5.1 / S5.2 footprint
    fp = sym.props.get('Footprint', {}).get('value', '')
    if fp and not re.match(r'^[^:\s]+:[^:\s]+$', fp):
        add('WARN', 'S5.1', f'Footprint {fp!r} is not lib:name')
    filt = sym.props.get('ki_fp_filters', {}).get('value', '').split()
    count = sum(len(p['nums']) for p in pins)
    for f in filt:
        if not f.endswith('*'):
            add('WARN', 'S5.2', f'filter {f} does not end with *')
        if re.search(r'[-_]', f):
            add('INFO', 'S5.2', f'filter {f} has - or _ (write ? to match both)')
        if re.search(rf'[-_?]{count}([^0-9.x]|$)', f.split(':')[-1]):
            add('INFO', 'S5.2', f'filter {f} holds the pin count {count}; only needed when pins are omitted')
    if fp and filt:
        fname = fp.split(':')[-1]
        if not any(fmatch(f, fp if ':' in f else fname) for f in filt):
            add('WARN', 'S5.2', f'no filter matches the Footprint {fp}')
    # S6.1 / S6.2 fields
    if ref and ref not in REFS and not ref.startswith('#'):
        add('WARN', 'S6.1', f'reference {ref!r} is not in the KLC table')
    for k, want_hidden in (('Reference', False), ('Value', False), ('Footprint', True), ('Datasheet', True),
                           ('Description', True)):
        v = sym.props.get(k)
        if v is None:
            add('WARN', 'S6.2', f'{k} field missing')
        elif v['hide'] != want_hidden:
            add('WARN', 'S6.2', f'{k} should be {"hidden" if want_hidden else "visible"}')
    if sym.props.get('Value', {}).get('value') not in (sym.name, None):
        add('INFO', 'S6.2', f'Value {sym.props["Value"]["value"]!r} differs from the symbol name')
    custom = [k for k in sym.props if k not in FIELDS and not k.startswith('KLC_')]
    if custom:
        add('WARN', 'S6.2', f'custom fields: {", ".join(custom)}')
    if not sym.props.get('Datasheet', {}).get('value'):
        add('INFO', 'S6.2', 'Datasheet is empty (generic symbols use ~)')
    return out


def fmatch(pat, s):
    rx = ''.join('.*' if c == '*' else '.?' if c == '?' else re.escape(c) for c in pat)
    return re.fullmatch(rx, s, re.I) is not None


# ---- compare ------------------------------------------------------------------------------------
def compare_pins(a_pins, b_pins, b_label, stacks_both):
    """a_pins, b_pins: lists of dict with nums, name, type, alts, number. Returns (diffs, infos)."""
    diffs, infos = [], []

    def index(ps):
        out = {}
        for p in ps:
            for m in p['nums']:
                out[m] = p
        return out

    A, B = index(a_pins), index(b_pins)
    only_a = sorted(set(A) - set(B), key=natkey)
    only_b = sorted(set(B) - set(A), key=natkey)
    if only_a:
        diffs.append(f'pins only in the symbol: {compress(only_a)}')
    if only_b:
        diffs.append(f'pins only in {b_label}: {compress(only_b)}')
    names, types, alts, alt_info = [], [], [], []
    for m in sorted(set(A) & set(B), key=natkey):
        a, b = A[m], B[m]
        if norm(a['name']) != norm(b['name']):
            names.append(f'{m}: {a["name"]} vs {b["name"]}')
        if a['type'] != b['type']:
            types.append(f'{m} {a["name"]}: {a["type"]} vs {b["type"]}')
        sa = {(norm(n), t) for n, t in a['alts']}
        sb = {(norm(n), t) for n, t in b['alts']}
        if sb - sa and (b['alts'] or stacks_both):
            alts.append(f'{m}: missing {", ".join(sorted(n for n, _ in sb - sa))[:120]}')
        if sa - sb:
            (alts if stacks_both else alt_info).append(
                f'{m}: extra {", ".join(sorted(n for n, _ in sa - sb))[:120]}')
    for label, lst, sink in (('name', names, diffs), ('type', types, diffs), ('alternate', alts, diffs),
                             ('alternate', alt_info, infos)):
        if lst:
            sink.append(f'{label} differs on {len(lst)} pins (symbol vs {b_label}): ' + '; '.join(lst[:10]) + (' ...' if len(lst) > 10 else ''))
    sa = {tuple(sorted(p['nums'], key=natkey)) for p in a_pins if len(p['nums']) > 1}
    sb = {tuple(sorted(p['nums'], key=natkey)) for p in b_pins if len(p['nums']) > 1}
    if sb - sa:
        diffs.append(f'stacks in {b_label} not in the symbol: ' + '; '.join('[' + ','.join(s) + ']' for s in sorted(sb - sa)))
    if sa - sb:
        (diffs if stacks_both else infos).append(
            'stacks in the symbol not in ' + b_label + ': ' + '; '.join('[' + ','.join(s) + ']' for s in sorted(sa - sb)))
    return diffs, infos


def fp_pads(path):
    with open(path, encoding='utf-8') as fh:
        fp = parse(fh.read())
    return {p[1] for p in kids(fp, 'pad') if p[1] and p[2] != 'np_thru_hole'}


def dump(sym, path):
    multi = len([u for u in sym.units if u > 0]) > 1
    order = {'left': 0, 'right': 1, 'top': 2, 'bottom': 3, 'hidden': 4}

    def key(p):
        s = sym.side(p)
        pos = -p['y'] if s in ('left', 'right') else p['x']
        return (p['unit'], order[s], pos)

    # make_symbol.py needs units from 1 and hides only no_connect pins (KLC S4.6). Shared unit-0 pins
    # of a multi-unit symbol go to a new last unit; other hidden pins (the old stacking workaround) are
    # written with an empty side, so auto grouping places them.
    last = max(sym.units) + 1
    unit0 = multi and any(p['unit'] == 0 for p in sym.pins)
    unhidden = []
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(['number', 'name', 'type', 'unit', 'side', 'alt', 'shape'])
        for p in sorted(sym.pins, key=key):
            num = p['nums'][0] if len(p['nums']) == 1 else '[' + ','.join(p['nums']) + ']'
            side = sym.side(p)
            if side == 'hidden' and p['type'] != 'no_connect':
                side = ''
                unhidden.append(num)
            unit = (last if p['unit'] == 0 else p['unit']) if multi else ''
            w.writerow([num, p['name'], p['type'], unit, side,
                        '|'.join(f'{n}:{t}' for n, t in p['alts']), '' if p['shape'] == 'line' else p['shape']])
    lens = sorted({p['length'] for p in sym.pins if not p['hide']})
    pr = {k: v['value'] for k, v in sym.props.items()}
    lay = {'name': sym.name, 'reference': pr.get('Reference', 'U')}
    for k, f in (('footprint', 'Footprint'), ('datasheet', 'Datasheet'), ('description', 'Description'),
                 ('keywords', 'ki_keywords')):
        if pr.get(f):
            lay[k] = pr[f]
    if pr.get('ki_fp_filters'):
        lay['fp_filters'] = pr['ki_fp_filters'].split()
    if lens and 2.54 - EPS <= lens[-1] <= 7.62 + EPS and abs(lens[-1] / 1.27 - round(lens[-1] / 1.27)) < EPS:
        lay['pin_length'] = lens[-1]
    if sym.unit_names or unit0:
        lay['units'] = {str(k): v for k, v in sym.unit_names.items()}
        if unit0:
            lay['units'].setdefault(str(last), 'PWR')
    if multi and 'ki_locked' not in sym.props:
        lay['interchangeable'] = True
    stem = os.path.splitext(path)[0]
    with open(stem + '.layout.json', 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(lay, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    print(f'dumped {path} and {stem}.layout.json')
    if unhidden:
        print(f'NOTE hidden pins that are not no_connect written as separate pins with an empty side: '
              f'{compress(unhidden)}')
    if unit0:
        print(f'NOTE pins shared by all units (unit 0) moved to unit {last}')


def scan(path, ref_path):
    """Rank every symbol in a library against a pin table. Exit 0 when one matches exactly."""
    lib = parse(open(path, encoding='utf-8').read())
    ref = read_table(ref_path)
    R = {m: r for r in ref for m in r['nums']}
    ranked = []
    for node in kids(lib, 'symbol'):
        s = Symbol(path, node[1], lib)
        S = {m: p for p in s.pins for m in p['nums']}
        common = set(S) & set(R)
        names = sum(norm(S[m]['name']) != norm(R[m]['name']) for m in common)
        types = sum(S[m]['type'] != R[m]['type'] for m in common)
        missing = len(set(S) ^ set(R))
        ranked.append((missing, names, types, s.name))
    ranked.sort()
    print(f'{len(ranked)} symbols in {os.path.basename(path)} against {os.path.basename(ref_path)} '
          f'({len(R)} pins); best 10 (pin numbers not in both / name diffs / type diffs):')
    for missing, names, types, name in ranked[:10]:
        print(f'  {missing:>3} {names:>3} {types:>3}  {name}')
    sys.exit(0 if ranked and ranked[0][:2] == (0, 0) else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('sym')
    ap.add_argument('--name')
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument('--ref')
    grp.add_argument('--vs')
    ap.add_argument('--fp')
    ap.add_argument('--dump')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--scan', action='store_true')
    a = ap.parse_args()
    if a.scan:
        if not a.ref:
            ap.error('--scan needs --ref')
        try:
            scan(a.sym, a.ref)
        except (OSError, ValueError, IndexError, TypeError) as e:
            print(f'read error: {e}')
            sys.exit(2)
    try:
        sym = Symbol(a.sym, a.name)
        other = None
        if a.vs:
            path, _, oname = a.vs.rpartition(':') if re.search(r'\.kicad_sym:[^\\/]+$', a.vs) else (a.vs, '', '')
            other = Symbol(path or a.vs, oname or None)
        ref = read_table(a.ref) if a.ref else None
        pads = fp_pads(a.fp) if a.fp else None
    except (OSError, ValueError, IndexError, TypeError) as e:
        print(f'read error: {e}')
        sys.exit(2)

    if not a.quiet:
        table(sym)
    res = checks(sym)
    for level, rule, text in res:
        print(f'{level} {rule} {text}')
    if not res:
        print('KLC checks: nothing to report')

    diff = False
    if ref is not None or other is not None:
        if ref is not None:
            label = os.path.basename(a.ref)
            bad = [r for r in ref if r['type'] not in TYPES]
            for r in bad:
                print(f'DIFF {label} line {r["line"]}: type {r["type"]!r} is not a KiCad pin type')
            diffs, infos = compare_pins(sym.pins, ref, label, stacks_both=False)
            diffs = [f'{d}' for d in diffs] + ([] if not bad else ['bad types in the table'])
        else:
            label = f'{other.name} ({os.path.basename(other.path)})'
            diffs, infos = compare_pins(sym.pins, other.pins, label, stacks_both=True)
            for k in ('Reference', 'Footprint', 'Datasheet', 'ki_fp_filters'):
                va, vb = sym.props.get(k, {}).get('value', ''), other.props.get(k, {}).get('value', '')
                if va != vb:
                    infos.append(f'{k}: {va!r} vs {vb!r}')
        for d in diffs:
            print(f'DIFF {d}')
        for i in infos:
            print(f'INFO {i}')
        diff = bool(diffs)
        print(('FAIL' if diffs else 'PASS') + f' pins vs {label}: number, name, type, alternates, stacks')
    if pads is not None:
        nums = {m for p in sym.pins for m in p['nums']}
        so, fo = sorted(nums - pads, key=natkey), sorted(pads - nums, key=natkey)
        if so:
            print(f'DIFF pins with no pad: {compress(so)}')
        if fo:
            print(f'DIFF pads with no pin: {compress(fo)}')
        print(('FAIL' if so or fo else 'PASS') + f' pins vs pads of {os.path.basename(a.fp)} ({len(pads)} pads)')
        diff = diff or bool(so or fo)
    if a.dump:
        dump(sym, a.dump)
    sys.exit(1 if diff else 0)


if __name__ == '__main__':
    main()
