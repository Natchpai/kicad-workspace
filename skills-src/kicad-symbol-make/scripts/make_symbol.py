"""Write a KiCad 10 symbol (.kicad_sym, one root symbol) from a pin table and an optional layout.

Usage:
    python -I make_symbol.py <pins.csv> <out.kicad_sym> [--layout layout.json] [--fp <fp.kicad_mod>]
                             [--newline auto|lf|crlf]

pins.csv (header row required; format in SPEC.md):
    number,name,type,unit,side,alt,shape
    1,PVIN,power_in,,,
    "[13,14,17]",GND,power_in,,bottom,
    23,PA9,bidirectional,,,USART1_TX:bidirectional|TIM1_CH2:bidirectional

number is one pin. A KiCad 10 pin stack "[2,5,8]" is read too (stock round trips), but the house
style draws every pin separately. unit and side may be empty (unit 1, auto side).
side is left, right, top, bottom or hidden (hidden is only for no_connect pins, KLC S4.6).
A row with no number and no name is an empty row on its side; an empty name is an unnamed pin. Rows starting with # are comments.

layout.json (optional): name, reference, footprint, datasheet, description, keywords, fp_filters
(list), pin_length, stack (default false: every pin drawn separately; true stacks same-name power pins
on one unit, KLC S4.3),
units ({"1": "A", ...} unit names), interchangeable (multi-unit only; default false writes ki_locked).
The symbol name is the output file name unless layout.json gives the same name.

Drawing follows KLC: 2.54 mm grid, pins all one length (2.54, 3.81 when a pin number has 3 or more
characters, or pin_length), name offset 0.508, text 1.27, body stroke 0.254 filled with background.
nRESET, RESET# and /RESET are written as ~{RESET} (S4.7); each rename is printed.

--fp compares pin numbers (stacks expanded) with the footprint's pad numbers and writes nothing on
a mismatch. --newline auto copies the line ending of a .kicad_sym found near the output folder.
The script never overwrites an existing file.
"""
import argparse
import csv
import json
import math
import os
import re
import sys

GRID = 2.54
OFFSET = 0.508   # pin name offset, KLC S3.6; KiCad's default, so the file has no pin_names
CHAR_W = 1.1     # estimated advance of one 1.27 mm character
HALF_H = 0.7     # half the estimated text height
MARGIN = 0.25
TYPES = {'input', 'output', 'bidirectional', 'tri_state', 'passive', 'free', 'unspecified',
         'power_in', 'power_out', 'open_collector', 'open_emitter', 'no_connect'}
SHAPES = {'line', 'inverted', 'clock', 'inverted_clock', 'input_low', 'clock_low', 'output_low',
          'edge_clock_high', 'non_logic'}
SIDES = {'left', 'right', 'top', 'bottom', 'hidden'}
REFS = {'A', 'AE', 'BT', 'C', 'D', 'DS', 'F', 'FB', 'FD', 'FL', 'H', 'J', 'JP', 'K', 'L', 'LS', 'M',
        'MK', 'P', 'Q', 'R', 'RN', 'RT', 'RV', 'SW', 'T', 'TC', 'TJ', 'TP', 'U', 'Y', 'Z'}
GROUND = re.compile(r'^([ADPS]?GND|V(SS|EE)|V-|EP|PAD|EPAD)\w*$', re.I)
PORT = re.compile(r'^P([A-Z])(\d+)')
RIGHT_TYPES = {'output', 'open_collector', 'open_emitter', 'tri_state', 'power_out', 'no_connect'}


class SpecError(Exception):
    pass


def n(v):
    v = round(v, 4)
    return f'{v:g}' if v else '0'


def q(s):
    """Escape a string for a KiCad s-expression."""
    return str(s).replace('\\', '\\\\').replace('"', '\\"')


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def members(number):
    """Pin numbers in one CSV number cell: '5' or a stack '[2,5,8]'."""
    s = number.strip()
    if s.startswith('['):
        if not s.endswith(']'):
            raise SpecError(f'bad pin stack {number!r}')
        out = [m.strip() for m in s[1:-1].split(',')]
        if len(out) < 2 or '' in out:
            raise SpecError(f'bad pin stack {number!r}')
        return out
    if ',' in s:
        raise SpecError(f'pin number {number!r}: write a stack as "[a,b]"')
    return [s]


def stack_text(nums):
    nums = sorted(nums, key=natkey)
    return nums[0] if len(nums) == 1 else '[' + ','.join(nums) + ']'


def pin_order(placed):
    """KiCad's save order: single pins by number, then stacks."""
    nums = placed[0]['nums']
    return (len(nums) > 1, natkey(stack_text(nums)))


def sort_auto(lst, key):
    """Stable sort of the auto-placed pins only; pins with a side from the CSV keep their places."""
    idx = [i for i, p in enumerate(lst) if p is not None and not p['side']]
    for i, p in zip(idx, sorted((lst[i] for i in idx), key=key)):
        lst[i] = p


def active_low(name):
    """KLC S4.7: datasheet active-low marks become ~{...}."""
    for pat in (r'^n([A-Z][A-Z0-9_]*)$', r'^([A-Z][A-Z0-9_]*)#$', r'^/([A-Z][A-Z0-9_]*)$'):
        m = re.match(pat, name)
        if m:
            return '~{' + m.group(1) + '}'
    return name


def shown(name):
    """Name as drawn: overbar, subscript and superscript marks removed."""
    return re.sub(r'[~_^]\{([^}]*)\}', r'\1', name)


def snap_up(v):
    return math.ceil(round(v / GRID, 6)) * GRID


def side_x(count):
    """x positions for top or bottom pins, on the grid and centered."""
    if count % 2:
        return [(i - (count - 1) / 2) * GRID for i in range(count)]
    half = count // 2
    return [k * GRID for k in range(-half, 0)] + [k * GRID for k in range(1, half + 1)]


def text_len(name):
    return 0 if name == '~' else len(shown(name)) * CHAR_W


def overlap(a, b):
    return (a[0] < b[1] + MARGIN and b[0] < a[1] + MARGIN and
            a[2] < b[3] + MARGIN and b[2] < a[3] + MARGIN)


def inner_nodes(hw, ty, by):
    """Grid nodes strictly inside the body, top row first."""
    return [(x * GRID, y * GRID) for y in range(int(round(ty / GRID)) - 1, int(round(by / GRID)), -1)
            for x in range(int(round(-hw / GRID)) + 1, int(round(hw / GRID)))]


def layout(left, right, top, bottom, hidden=0):
    """Body with the smallest area (2.54 mm steps) where no pin names overlap and `hidden` pins find a
    grid node inside, trying wider and taller bodies. Lists hold pin dicts or None."""
    rows = max(len(left), len(right))
    y0 = math.floor((rows - 1) / 2) * GRID if rows else 0
    ys = [y0 - i * GRID for i in range(rows)]
    ty0 = (y0 + GRID) if rows else GRID
    by0 = (ys[-1] - GRID) if rows else -GRID
    tx, bx = side_x(len(top)), side_x(len(bottom))
    best = None
    for extra in range(0, 41):
        ty, by = ty0 + extra * GRID, by0 - extra * GRID
        if best and 2 * GRID * (ty - by) >= best[0] - 1e-9:
            break
        hw = fit(left, right, top, bottom, ys, ty, by, tx, bx, hidden)
        if hw and (best is None or 2 * hw * (ty - by) < best[0] - 1e-9):
            best = (2 * hw * (ty - by), hw, ty, by)
    if best is None:
        raise SpecError('pin names do not fit in any body up to 203 mm')
    _, hw, ty, by = best
    return hw, ty, by, ys, tx, bx


def fit(left, right, top, bottom, ys, ty, by, tx, bx, hidden=0):
    """Smallest half width for this body height, or None."""
    for hw in [GRID * k for k in range(1, 81)]:
        boxes = []
        for side, sign in ((left, -1), (right, 1)):
            for y, p in zip(ys, side):
                if p and p['name'] not in ('', '~'):
                    inner = sign * (hw - OFFSET)
                    x1, x2 = sorted((inner, inner - sign * text_len(p['name'])))
                    boxes.append((x1, x2, y - HALF_H, y + HALF_H))
        for xs, side, edge, sign in ((tx, top, ty, -1), (bx, bottom, by, 1)):
            for x, p in zip(xs, side):
                if p and p['name'] not in ('', '~'):
                    inner = edge + sign * OFFSET
                    y1, y2 = sorted((inner, inner + sign * text_len(p['name'])))
                    boxes.append((x - HALF_H, x + HALF_H, y1, y2))
        inside = all(b[0] > -hw and b[1] < hw and b[2] > by and b[3] < ty for b in boxes)
        clear = not any(overlap(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1:])
        if inside and clear and hw > max([abs(x) for x in tx + bx] + [0]) and                 len(inner_nodes(hw, ty, by)) >= hidden:
            return hw
    return None


def font(ind, justify=None):
    t = '\t' * ind
    s = [f'{t}(effects', f'{t}\t(font', f'{t}\t\t(size 1.27 1.27)', f'{t}\t)']
    if justify:
        s.append(f'{t}\t(justify {justify})')
    s.append(f'{t})')
    return s


def read_pins(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        rows = [r for r in csv.reader(fh)]
    while rows and (not any(c.strip() for c in rows[0]) or rows[0][0].lstrip().startswith('#')):
        rows.pop(0)
    if not rows:
        raise SpecError('pins.csv is empty')
    head = [h.strip().lower() for h in rows[0]]
    for need in ('number', 'name', 'type'):
        if need not in head:
            raise SpecError(f'pins.csv header has no "{need}" column')
    pins = []
    for i, row in enumerate(rows[1:], start=2):
        if not row or not any(c.strip() for c in row) or row[0].lstrip().startswith('#'):
            continue
        r = {h: (row[k].strip() if k < len(row) else '') for k, h in enumerate(head)}
        side = r.get('side', '').lower()
        if side and side not in SIDES:
            raise SpecError(f'line {i}: side {side!r} is not one of {sorted(SIDES)}')
        unit = r.get('unit', '') or '1'
        if not unit.isdigit() or int(unit) < 1:
            raise SpecError(f'line {i}: unit {unit!r} must be a number from 1')
        if not r['number'] and not r['name']:
            pins.append({'gap': True, 'unit': int(unit), 'side': side, 'line': i})
            continue
        if not r['number']:
            raise SpecError(f'line {i}: pin {r["name"]!r} has no number')
        typ = r['type'].lower()
        if typ not in TYPES:
            raise SpecError(f'line {i}: type {r["type"]!r} is not a KiCad pin type')
        shape = (r.get('shape') or 'line').lower()
        if shape not in SHAPES:
            raise SpecError(f'line {i}: shape {shape!r} is not a KiCad pin shape')
        alts = []
        for a in filter(None, (x.strip() for x in r.get('alt', '').split('|'))):
            an, _, at = a.partition(':')
            at = (at or typ).strip().lower()
            if at not in TYPES:
                raise SpecError(f'line {i}: alternate {a!r} type is not a KiCad pin type')
            alts.append((an.strip(), at))
        try:
            nums = members(r['number'])
        except SpecError as e:
            raise SpecError(f'line {i}: {e}')
        pins.append({'nums': nums, 'name': r['name'], 'type': typ, 'shape': shape, 'unit': int(unit),
                     'side': side, 'alts': alts, 'line': i, 'explicit_stack': len(nums) > 1})
    return pins


class Symbol:
    def __init__(self, pins, lay, name):
        self.lay, self.name = lay, name
        self.notes, self.warns, self.hidden = [], [], []
        self.pins = [p for p in pins if not p.get('gap')]
        self.gaps = [p for p in pins if p.get('gap')]
        if not self.pins:
            raise SpecError('no pins')
        self.rename()
        if lay.get('stack', False):
            self.stack()
        else:
            for p in self.pins:
                if p['explicit_stack']:
                    self.notes.append(f'house style draws pins separately; the table stacks {p["name"]} '
                                      f'{stack_text(p["nums"])}')
        self.validate()
        self.units = sorted({p['unit'] for p in self.pins})
        if self.units != list(range(1, len(self.units) + 1)):
            raise SpecError(f'units must run 1..N with no gap, got {self.units}')
        self.pin_len = self.length()

    def rename(self):
        for p in self.pins:
            new = active_low(p['name'])
            if new != p['name']:
                self.notes.append(f'S4.7 renamed {p["name"]} -> {new} (pin {stack_text(p["nums"])})')
                p['name'] = new
            if p['shape'] in ('inverted', 'inverted_clock') and '~{' in p['name']:
                raise SpecError(f'pin {p["name"]}: inverted shape and overbar name (KLC S4.4 double inversion)')

    def stack(self):
        """KLC S4.3: same-name power pins on one unit become one stack."""
        out, seen = [], {}
        for p in self.pins:
            key = (p['unit'], p['name'], p['type'])
            if p['type'] in ('power_in', 'power_out') and p['side'] != 'hidden':
                first = seen.get(key)
                if first and first['side'] and p['side'] and first['side'] != p['side']:
                    self.notes.append(f'S4.3 not stacked {p["name"]} {stack_text(p["nums"])}: side {p["side"]} '
                                      f'differs from {stack_text(first["nums"])} ({first["side"]})')
                elif first:
                    first['nums'] += p['nums']
                    first['side'] = first['side'] or p['side']
                    first['alts'] += [a for a in p['alts'] if a not in first['alts']]
                    continue
                else:
                    seen[key] = p
            out.append(p)
        for p in out:
            if len(p['nums']) > 1 and not p['explicit_stack']:
                self.notes.append(f'S4.3 stacked {p["name"]}: {stack_text(p["nums"])}')
        self.pins = out

    def validate(self):
        allnums = [m for p in self.pins for m in p['nums']]
        dup = sorted({m for m in allnums if allnums.count(m) > 1}, key=natkey)
        if dup:
            raise SpecError(f'duplicate pin numbers {dup} (KLC S4.1; a stack lists each number once)')
        for p in self.pins:
            if p['side'] == 'hidden' and p['type'] != 'no_connect':
                raise SpecError(f'pin {p["nums"][0]} {p["name"]}: only no_connect pins may be hidden (KLC S4.6)')
            if len(p['nums']) > 1 and p['type'] == 'no_connect':
                raise SpecError(f'pin stack {stack_text(p["nums"])}: no_connect pins must not be stacked (KLC S4.3)')
        self.count = len(allnums)

    def length(self):
        want = self.lay.get('pin_length')
        if want is not None:
            if isinstance(want, bool) or not isinstance(want, (int, float)):
                raise SpecError(f'pin_length {want!r} is not a number')
            if want < 2.54 - 1e-6 or want > 7.62 + 1e-6 or abs(want / 1.27 - round(want / 1.27)) > 1e-6:
                raise SpecError(f'pin_length {want}: 2.54 to 7.62 in 1.27 steps (KLC S4.1)')
            return float(want)
        chars = max(len(m) for p in self.pins for m in p['nums'])
        return 3.81 if chars >= 3 else 2.54

    def classify(self, unit):
        """Pins of one unit sorted to sides (KLC S4.2). Returns dict side -> list of pin dict or None."""
        pins = [p for p in self.pins if p['unit'] == unit]
        conv = any(p['type'] == 'power_out' for p in pins)
        ports = [p for p in pins if not p['side'] and PORT.match(p['name'])]
        mcu = len(ports) >= 16
        sides = {s: [] for s in SIDES}
        auto_ports, passives = [], []
        for p in pins:
            s = p['side']
            if not s:
                if mcu and p in ports:
                    auto_ports.append(p)
                    continue
                if p['type'] in ('power_in', 'passive') and GROUND.match(shown(p['name'])):
                    s = 'bottom'
                elif p['type'] == 'power_in':
                    s = 'left' if conv else 'top'
                elif p['type'] in RIGHT_TYPES:
                    s = 'right'
                elif p['type'] == 'passive':
                    passives.append(p)
                    continue
                else:
                    s = 'left'
            sides[s].append(p)
        # passive pins (set resistors and capacitors, reserved pins) go together on the shorter side
        sides['right' if len(sides['right']) < len(sides['left']) else 'left'] += passives
        if conv:   # power conversion: input power first on the left, output power first on the right
            for s, t in (('left', 'power_in'), ('right', 'power_out')):
                sort_auto(sides[s], lambda p: 0 if p['type'] == t else 1)
        for s in ('left', 'right'):   # NC pins go last
            sort_auto(sides[s], lambda p: 1 if p['type'] == 'no_connect' else 0)
        if auto_ports:
            groups = {}
            for p in sorted(auto_ports, key=lambda p: (PORT.match(p['name']).group(1), int(PORT.match(p['name']).group(2)))):
                groups.setdefault(PORT.match(p['name']).group(1), []).append(p)
            half = len(auto_ports) / 2
            right = []
            letters = sorted(groups)
            while letters and sum(len(groups[l]) for l in right) < half:
                right.append(letters.pop(0))
            for side, lets in (('right', right), ('left', letters)):
                for l in lets:
                    if sides[side]:
                        sides[side].append(None)
                    sides[side] += groups[l]
        for g in self.gaps:   # explicit empty rows from the CSV, in file order
            if g['unit'] == unit and g['side'] in ('left', 'right', 'top', 'bottom'):
                anchor = [p for p in pins if p['side'] == g['side'] and p['line'] < g['line']]
                lst = sides[g['side']]
                idx = lst.index(anchor[-1]) + 1 if anchor and anchor[-1] in lst else 0
                lst.insert(idx, None)
        return sides

    def draw_unit(self, unit):
        sides = self.classify(unit)
        hidden = sides['hidden']
        hw, ty, by, ys, tx, bx = layout(sides['left'], sides['right'], sides['top'], sides['bottom'], len(hidden))
        L = self.pin_len
        placed = []
        for side, x, rot in (('left', -hw - L, 0), ('right', hw + L, 180)):
            placed += [(p, x, y, rot, False) for y, p in zip(ys, sides[side]) if p]
        for side, xs, y, rot in (('top', tx, ty + L, 270), ('bottom', bx, by - L, 90)):
            placed += [(p, x, y, rot, False) for x, p in zip(xs, sides[side]) if p]
        # hidden NC pins (side=hidden): connection point on grid nodes inside the body (KLC S4.6)
        placed += [(p, x, y, 0, True) for p, (x, y) in zip(hidden, inner_nodes(hw, ty, by))]
        self.hidden += [stack_text(p['nums']) for p in hidden]
        return hw, ty, by, placed

    def build(self):
        name, lay = self.name, self.lay
        ref = lay.get('reference', 'U')
        if ref not in REFS:
            self.warns.append(f'S6.1 reference {ref!r} is not in the KLC table')
        drawn = {u: self.draw_unit(u) for u in self.units}
        hw = max(d[0] for d in drawn.values())
        ty = max(d[1] for d in drawn.values())
        by = min(d[2] for d in drawn.values())
        has_top = any(rot == 270 for d in drawn.values() for _, _, _, rot, _ in d[3])
        ref_y = ty + (self.pin_len + 1.27 if has_top else 1.27)
        fp = lay.get('footprint', '')
        if fp and not re.match(r'^[^:\s]+:[^:\s]+$', fp):
            raise SpecError(f'footprint {fp!r} is not lib:name (KLC S5.1)')
        filters = self.filters()
        props = [('Reference', ref, -hw, ref_y, False, 'left'),
                 ('Value', name, hw, ref_y, False, 'right')]
        y = by - self.pin_len - GRID
        for key, val in (('Footprint', fp), ('Datasheet', lay.get('datasheet', '')),
                         ('Description', lay.get('description', ''))):
            props.append((key, val, 0, y, True, None))
            y -= GRID
        multi = len(self.units) > 1
        if multi and not lay.get('interchangeable', False):
            props.append(('ki_locked', '', 0, 0, None, None))
        if lay.get('keywords'):
            props.append(('ki_keywords', lay['keywords'], 0, 0, True, None))
        if filters:
            props.append(('ki_fp_filters', ' '.join(filters), 0, 0, True, None))

        out = ['(kicad_symbol_lib', '\t(version 20251024)', '\t(generator "kicad_symbol_editor")',
               '\t(generator_version "10.0")', f'\t(symbol "{q(name)}"', '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)',
               '\t\t(on_board yes)', '\t\t(in_pos_files yes)', '\t\t(duplicate_pin_numbers_are_jumpers no)']
        for key, val, x, y, hide, just in props:
            out += [f'\t\t(property "{key}" "{q(val)}"', f'\t\t\t(at {n(x)} {n(y)} 0)', '\t\t\t(show_name no)',
                    '\t\t\t(do_not_autoplace no)']
            if hide:
                out.append('\t\t\t(hide yes)')
            out += font(3, just) + ['\t\t)']

        def rect(t, h, top, bot):
            return [f'{t}(rectangle', f'{t}\t(start {n(-h)} {n(top)})', f'{t}\t(end {n(h)} {n(bot)})',
                    f'{t}\t(stroke', f'{t}\t\t(width 0.254)', f'{t}\t\t(type default)', f'{t}\t)',
                    f'{t}\t(fill', f'{t}\t\t(type background)', f'{t}\t)', f'{t})']

        names = {str(k): v for k, v in (lay.get('units') or {}).items()}
        for u in self.units:
            uh, ut, ub, placed = drawn[u]
            if not multi:
                out += [f'\t\t(symbol "{q(name)}_0_1"'] + rect('\t\t\t', uh, ut, ub) + ['\t\t)',
                        f'\t\t(symbol "{q(name)}_1_1"']
            else:
                out.append(f'\t\t(symbol "{q(name)}_{u}_1"')
                if names.get(str(u)):
                    out.append(f'\t\t\t(unit_name "{q(names[str(u)])}")')
                out += rect('\t\t\t', uh, ut, ub)
            for p, x, y, rot, hide in sorted(placed, key=pin_order):
                out += [f'\t\t\t(pin {p["type"]} {p["shape"]}', f'\t\t\t\t(at {n(x)} {n(y)} {rot})',
                        f'\t\t\t\t(length {n(self.pin_len)})']
                if hide:
                    out.append('\t\t\t\t(hide yes)')
                out += [f'\t\t\t\t(name "{q(p["name"])}"'] + font(5) + ['\t\t\t\t)',
                        f'\t\t\t\t(number "{q(stack_text(p["nums"]))}"'] + font(5) + ['\t\t\t\t)']
                out += [f'\t\t\t\t(alternate "{q(an)}" {at} line)' for an, at in p['alts']]
                out.append('\t\t\t)')
            out.append('\t\t)')
        out += ['\t\t(embedded_fonts no)', '\t)', ')']
        self.size = {u: (2 * d[0], d[1] - d[2]) for u, d in drawn.items()}
        return '\n'.join(out) + '\n'

    def filters(self):
        """KLC S5.2: each filter ends with *, - and _ written as ?."""
        raw = self.lay.get('fp_filters') or []
        if isinstance(raw, str):
            raw = raw.split()
        out = []
        for f in raw:
            g = re.sub(r'[-_]', '?', f)
            if not g.endswith('*'):
                g += '*'
            if g != f:
                self.notes.append(f'S5.2 filter {f} -> {g}')
            if re.search(rf'[-_?]{self.count}([^0-9.x]|$)', g.split(':')[-1]):
                self.warns.append(f'S5.2 filter {g} holds the pin count {self.count}; leave it out unless pins are omitted')
            out.append(g)
        return out

    def summary(self):
        stacks = [stack_text(p['nums']) + ' ' + p['name'] for p in self.pins if len(p['nums']) > 1]
        shown_nc = [stack_text(p['nums']) for p in self.pins if p['type'] == 'no_connect' and p['side'] != 'hidden']
        lines = [f'pins {self.count} ({len(self.pins)} drawn), units {len(self.units)}, pin length {n(self.pin_len)}',
                 'body ' + ', '.join(f'unit {u} {n(w)} x {n(h)}' for u, (w, h) in self.size.items())]
        if stacks:
            lines.append('stacks: ' + '; '.join(stacks))
        if shown_nc:
            lines.append('NC shown: ' + ', '.join(shown_nc))
        if self.hidden:
            lines.append('hidden NC: ' + ', '.join(self.hidden))
        lines += [f'NOTE {x}' for x in self.notes] + [f'WARN {x}' for x in self.warns]
        return '\n'.join(lines)


def footprint_pads(path):
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    pads = set()
    for m in re.finditer(r'\(pad\s+"((?:[^"\\]|\\.)*)"\s+(\w+)', text):
        if m.group(1) and m.group(2) != 'np_thru_hole':
            pads.add(re.sub(r'\\(.)', r'\1', m.group(1)))
    return pads


def detect_newline(out_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(out_path)))
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            if f.endswith('.kicad_sym'):
                with open(os.path.join(dirpath, f), 'rb') as fh:
                    return '\r\n' if b'\r\n' in fh.readline() else '\n'
    return '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pins')
    ap.add_argument('out')
    ap.add_argument('--layout')
    ap.add_argument('--fp')
    ap.add_argument('--newline', choices=('auto', 'lf', 'crlf'), default='auto')
    a = ap.parse_args()

    if os.path.exists(a.out):
        sys.exit(f'refusing to overwrite {a.out}')
    name = os.path.splitext(os.path.basename(a.out))[0]
    try:
        lay = {}
        if a.layout:
            with open(a.layout, encoding='utf-8') as fh:
                lay = json.load(fh)
            if not isinstance(lay, dict):
                raise SpecError('layout.json must hold one object')
        if lay.get('name', name) != name:
            sys.exit(f'layout name {lay["name"]!r} does not match file name {name!r}')
        sym = Symbol(read_pins(a.pins), lay, name)
        text = sym.build()
    except (SpecError, TypeError, ValueError, KeyError, AttributeError) as e:
        sys.exit(f'spec error: {e}')

    if a.fp:
        pads = footprint_pads(a.fp)
        nums = {m for p in sym.pins for m in p['nums']}
        if pads != nums:
            sys.exit(f'PIN/PAD MISMATCH: symbol only {sorted(nums - pads, key=natkey)}, '
                     f'footprint only {sorted(pads - nums, key=natkey)}; nothing written')
        print(f'pins match footprint pads ({len(pads)})')

    nl = {'lf': '\n', 'crlf': '\r\n'}.get(a.newline) or detect_newline(a.out)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline=nl) as fh:
        fh.write(text)
    print(f'wrote {a.out} ({"CRLF" if nl == chr(13) + chr(10) else "LF"})')
    print(sym.summary())


if __name__ == '__main__':
    main()
