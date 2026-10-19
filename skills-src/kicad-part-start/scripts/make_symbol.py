"""Write a starting-point KiCad 10 symbol (.kicad_sym, one root symbol) from a JSON pin spec.

Usage:
    python -I make_symbol.py <spec.json> <out.kicad_sym> [--fp <footprint.kicad_mod>] [--newline auto|lf|crlf]

Spec format:
    {
      "name": "ICP-20100",
      "reference": "U",
      "left":   [["1", "CSB", "input"], ["2", "SCL", "input"], null, ...],
      "right":  [null, null, ["8", "RESV", "passive"]],
      "top":    [["10", "VDDIO", "power_in"], ["5", "VDD", "power_in"]],
      "bottom": [["3", "VSS", "power_in"]],
      "properties": {"Footprint": "0_Package_LGA:...", "Datasheet": "https://...",
                     "Description": "...", "ki_keywords": "...", "ki_fp_filters": "..."}
    }

Left and right lists run top to bottom, top and bottom lists run left to right. A null entry
leaves an empty row. Pins sit on the 2.54 mm grid with length 2.54. The body is the smallest
2.54 mm step at which no two pin names overlap (estimated text size), so the result is a
starting point: the user sets the final style.

--fp checks that the symbol's pin numbers equal the footprint's pad numbers.
--newline auto copies the line ending of the first .kicad_sym found next to the output folder.
The script never overwrites an existing file.
"""
import argparse
import json
import math
import os
import re
import sys

GRID = 2.54
PIN_LEN = 2.54
OFFSET = 1.016   # pin_names offset
CHAR_W = 1.1     # estimated advance of one 1.27 mm character
HALF_H = 0.7     # half the estimated text height
MARGIN = 0.25
TYPES = {'input', 'output', 'bidirectional', 'tri_state', 'passive', 'free', 'unspecified',
         'power_in', 'power_out', 'open_collector', 'open_emitter', 'no_connect'}


def n(v):
    v = round(v, 4)
    return f'{v:g}' if v else '0'


def snap_up(v):
    return math.ceil(round(v / GRID, 6)) * GRID


def side_x(count):
    """x positions for top or bottom pins, on the grid and centered."""
    if count % 2:
        return [(i - (count - 1) / 2) * GRID for i in range(count)]
    half = count // 2
    return [k * GRID for k in range(-half, 0)] + [k * GRID for k in range(1, half + 1)]


def text_len(name):
    return 0 if name == '~' else len(name) * CHAR_W


def overlap(a, b):
    return (a[0] < b[1] + MARGIN and b[0] < a[1] + MARGIN and
            a[2] < b[3] + MARGIN and b[2] < a[3] + MARGIN)


def layout(spec):
    left, right = spec.get('left', []), spec.get('right', [])
    top, bottom = spec.get('top', []), spec.get('bottom', [])
    rows = max(len(left), len(right))
    y0 = math.floor((rows - 1) / 2) * GRID if rows else 0
    ys = [y0 - i * GRID for i in range(rows)]
    ty = (y0 + GRID) if rows else GRID
    by = (ys[-1] - GRID) if rows else -GRID
    tx, bx = side_x(len(top)), side_x(len(bottom))
    while True:
        for hw in [GRID * k for k in range(2, 41)]:
            boxes = []
            for side, sign in ((left, -1), (right, 1)):
                for y, p in zip(ys, side):
                    if p and p[1] != '~':
                        inner = sign * (hw - OFFSET)
                        x1, x2 = sorted((inner, inner - sign * text_len(p[1])))
                        boxes.append((x1, x2, y - HALF_H, y + HALF_H))
            for xs, side, edge, sign in ((tx, top, ty, -1), (bx, bottom, by, 1)):
                for x, p in zip(xs, side):
                    if p and p[1] != '~':
                        inner = edge + sign * OFFSET
                        y1, y2 = sorted((inner, inner + sign * text_len(p[1])))
                        boxes.append((x - HALF_H, x + HALF_H, y1, y2))
            inside = all(b[0] > -hw and b[1] < hw and b[2] > by and b[3] < ty for b in boxes)
            clear = not any(overlap(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1:])
            if inside and clear and hw > max([abs(x) for x in tx + bx] + [0]):
                return hw, ty, by, ys, tx, bx
        ty, by = ty + GRID, by - GRID


def font(ind, justify=None):
    t = '\t' * ind
    s = [f'{t}(effects', f'{t}\t(font', f'{t}\t\t(size 1.27 1.27)', f'{t}\t)']
    if justify:
        s.append(f'{t}\t(justify {justify})')
    s.append(f'{t})')
    return s


def build(spec):
    name = spec['name']
    hw, ty, by, ys, tx, bx = layout(spec)
    pins = []
    for side, x, rot in ((spec.get('left', []), -hw - PIN_LEN, 0), (spec.get('right', []), hw + PIN_LEN, 180)):
        pins += [(p, x, y, rot) for y, p in zip(ys, side) if p]
    for side, xs, y, rot in ((spec.get('top', []), tx, ty + PIN_LEN, 270), (spec.get('bottom', []), bx, by - PIN_LEN, 90)):
        pins += [(p, x, y, rot) for x, p in zip(xs, side) if p]

    nums = [p[0] for p, *_ in pins]
    if len(nums) != len(set(nums)):
        sys.exit(f'duplicate pin numbers: {sorted({x for x in nums if nums.count(x) > 1})}')
    bad = [p for p, *_ in pins if p[2] not in TYPES]
    if bad:
        sys.exit(f'unknown electrical type: {bad}')

    props = spec.get('properties', {})
    shown = [('Reference', spec.get('reference', 'U'), -hw, ty + 1.27, False, 'left'),
             ('Value', name, hw, ty + 1.27, False, 'right')]
    y = by - PIN_LEN - GRID if spec.get('bottom') else by - GRID
    hidden = []
    for key in ('Footprint', 'Datasheet', 'Description'):
        hidden.append((key, props.get(key, ''), 0, y, True, None))
        y -= GRID
    for key in ('ki_keywords', 'ki_fp_filters'):
        if props.get(key):
            hidden.append((key, props[key], 0, 0, True, None))

    out = ['(kicad_symbol_lib', '\t(version 20251024)', '\t(generator "kicad_symbol_editor")',
           '\t(generator_version "10.0")', f'\t(symbol "{name}"', '\t\t(pin_names', f'\t\t\t(offset {n(OFFSET)})', '\t\t)',
           '\t\t(exclude_from_sim no)', '\t\t(in_bom yes)', '\t\t(on_board yes)', '\t\t(in_pos_files yes)',
           '\t\t(duplicate_pin_numbers_are_jumpers no)']
    for key, val, x, y, hide, just in shown + hidden:
        out += [f'\t\t(property "{key}" "{val}"', f'\t\t\t(at {n(x)} {n(y)} 0)', '\t\t\t(show_name no)',
                '\t\t\t(do_not_autoplace no)']
        if hide:
            out.append('\t\t\t(hide yes)')
        out += font(3, just) + ['\t\t)']
    out += [f'\t\t(symbol "{name}_0_1"', '\t\t\t(rectangle', f'\t\t\t\t(start {n(-hw)} {n(ty)})', f'\t\t\t\t(end {n(hw)} {n(by)})',
            '\t\t\t\t(stroke', '\t\t\t\t\t(width 0.254)', '\t\t\t\t\t(type default)', '\t\t\t\t)',
            '\t\t\t\t(fill', '\t\t\t\t\t(type background)', '\t\t\t\t)', '\t\t\t)', '\t\t)',
            f'\t\t(symbol "{name}_1_1"']
    for (num, pname, typ), x, y, rot in pins:
        out += [f'\t\t\t(pin {typ} line', f'\t\t\t\t(at {n(x)} {n(y)} {rot})', f'\t\t\t\t(length {n(PIN_LEN)})',
                f'\t\t\t\t(name "{pname}"'] + font(5) + ['\t\t\t\t)', f'\t\t\t\t(number "{num}"'] + font(5) + ['\t\t\t\t)', '\t\t\t)']
    out += ['\t\t)', '\t\t(embedded_fonts no)', '\t)', ')']
    return '\n'.join(out) + '\n', nums, (hw, ty, by)


def detect_newline(out_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(out_path)))
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith('.kicad_sym'):
                with open(os.path.join(dirpath, f), 'rb') as fh:
                    return '\r\n' if b'\r\n' in fh.readline() else '\n'
    return '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('out')
    ap.add_argument('--fp')
    ap.add_argument('--newline', choices=('auto', 'lf', 'crlf'), default='auto')
    a = ap.parse_args()

    with open(a.spec, encoding='utf-8') as f:
        spec = json.load(f)
    if os.path.splitext(os.path.basename(a.out))[0] != spec['name']:
        sys.exit('output file name must equal the symbol name')
    if os.path.exists(a.out):
        sys.exit(f'COLLISION: {a.out} exists')
    text, nums, (hw, ty, by) = build(spec)

    if a.fp:
        with open(a.fp, encoding='utf-8') as f:
            pads = set(re.findall(r'\(pad "([^"]+)"', f.read())) - {''}
        if pads != set(nums):
            sys.exit(f'PIN/PAD MISMATCH: symbol only {sorted(set(nums) - pads)}, footprint only {sorted(pads - set(nums))}')
        print(f'pins match footprint pads ({len(pads)})')

    nl = {'lf': '\n', 'crlf': '\r\n'}.get(a.newline) or detect_newline(a.out)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline=nl) as f:
        f.write(text)
    print(f'wrote {a.out}: {len(nums)} pins, body {n(2 * hw)} x {n(ty - by)} mm, {"CRLF" if nl == chr(13) + chr(10) else "LF"}')


if __name__ == '__main__':
    main()
