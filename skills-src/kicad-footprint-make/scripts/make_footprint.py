"""Write a KiCad 10 footprint (.kicad_mod) from a JSON spec of datasheet land-pattern values.

Usage:
    python -I make_footprint.py <spec.json> <out.kicad_mod> [--newline auto|lf|crlf]

The spec format is in SPEC.md next to this folder. In short: "rows" (dual or quad pad rows),
"grid" (BGA/LGA), "pads" (free list, SMD or THT) and "ep" (exposed pads with tabs, thermal vias
and stencil apertures) can be combined. Every dimension is in mm and comes from the datasheet;
the script computes only layout (positions from pitch and span) and the generated layers.

Generated: F.Fab body rectangle with one pin 1 mark (a filled dot level with pin 1, a filled arrow
for connectors, or none) and ${REFERENCE} (1 x 1 mm, 0.1 mm thick; smaller only
when 5 characters do not fit inside the body),
F.SilkS outline at body + silk offset (default 0.1 mm), 0.15 mm wide, cut back 0.2 mm from copper, a
pin 1 mark beside pin 1 (a filled arrow pointing at it, a + for polarized SMD capacitors, none for
non-polarized parts), REF** 1 x 1 mm, 0.15 mm thick (DFM minimums: silk lines and text 0.15 mm, text
1 x 1 mm, 0.15 mm from copper, pin 1 mark line 0.1 mm when the mark is over 0.15 mm); F.SilkS and
F.Fab points and text positions on a 0.05 mm grid, silk rounded away from body and copper, the fab
outline to the nearest node, F.CrtYd rectangle around body and copper (0.25 mm; 0.15 mm when both body sides
are under 1.5 mm; 1.0 mm with "grid"), grown the same on every side to hold the silk pin 1 mark, on a
0.01 mm grid, properties (Value hidden) and model.
Pads and stencil apertures have rounded corners by default (roundrect, ratio 0.25 for pads,
0.1 for apertures, radius at most 0.25 mm). Exposed pads stay square: rounded tab and pad
primitives leave notches where they join. KLC F6.3 / F4.4: exposed pads, their B.Cu pad and
thermal vias get the heatsink fab property and solid zone connection; grid pads get the BGA
property (set "fab_property": null for LGA).

UUIDs come from uuid5 of the footprint name, so the same spec gives the same bytes.
--newline auto copies the line ending of a .kicad_mod already in the output folder (else LF).
The script never overwrites an existing file. It prints the pad count and the stencil coverage
of each exposed pad.
"""
import argparse
import json
import math
import os
import re
import sys
import uuid

DEFAULTS = {
    'pad_ratio': 0.25, 'ep_ratio': 0, 'paste_ratio': 0.1, 'max_radius': 0.25,
    'silk_width': 0.15, 'silk_offset': 0.1, 'silk_clearance': 0.2, 'silk_min_len': 0.1,
    'fab_width': 0.1, 'crtyd_width': 0.05, 'marker_size': 0.28,
}
SKIP_LETTERS = 'IOQSXZ'
EPS = 1e-9
# DFM house rules: silkscreen lines and text at least 0.15 mm wide, text at least 1 x 1 mm, at least
# 0.15 mm from copper; a filled pin 1 mark may use 0.1 mm lines when it is over 0.15 mm across
SILK_MIN_WIDTH, SILK_MIN_TEXT, SILK_MIN_CLEARANCE = 0.15, 1.0, 0.15
MARK_MIN_WIDTH, MARK_MIN_SIZE = 0.1, 0.15
# F.Fab ${REFERENCE}: 1 x 1 mm, 0.1 mm thick, smaller only when FAB_CHARS characters do not fit
# inside the body (estimated stroke font advance CHAR_ADV x size)
FAB_TEXT, FAB_TEXT_WIDTH, FAB_CHARS, CHAR_ADV = 1.0, 0.1, 5, 0.9
GRAPHIC_GRID = 0.05   # house rule: F.SilkS and F.Fab points and text positions, easy to edit by hand
PLUS_ARM = 0.4        # pin 1 + of polarized capacitors: 0.8 mm across


def center_of(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return round((min(xs) + max(xs)) / 2, 4), round((min(ys) + max(ys)) / 2, 4)


def dot_radius(short):
    """F.Fab pin 1 dot radius from the short body side (house sizes)."""
    for limit, r in ((1.5, 0.1), (3.2, 0.15), (3.9, 0.2), (10, 0.25)):
        if short < limit - EPS:
            return r
    return 0.3


def snap(v, how=0):
    """v on the GRAPHIC_GRID: how < 0 rounds down, > 0 up, 0 to the nearest node."""
    t = v / GRAPHIC_GRID
    t = math.floor(t + 1e-6) if how < 0 else math.ceil(t - 1e-6) if how > 0 else round(t)
    return round(t * GRAPHIC_GRID, 4) + 0.0


class SpecError(Exception):
    pass


def f(v):
    s = f'{v:.6f}'.rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


def q(s):
    """Escape a string for a KiCad s-expression."""
    return str(s).replace('\\', '\\\\').replace('"', '\\"')


def number(v, what, positive=True):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(v):
        raise SpecError(f'{what}: {v!r} is not a number')
    if positive and v <= 0:
        raise SpecError(f'{what}: {v} must be > 0')
    return float(v)


def pair(v, what):
    """A size given as a number or [w, h]."""
    v = v if isinstance(v, list) else [v, v]
    if len(v) != 2:
        raise SpecError(f'{what}: give a number or [w, h]')
    return [number(v[0], what), number(v[1], what)]


PROPS = {'heatsink': 'pad_prop_heatsink', 'bga': 'pad_prop_bga', 'mechanical': 'pad_prop_mechanical'}


def fab_text(bx, by):
    """F.Fab ${REFERENCE} (size, thickness) for a bx x by body: 1 mm and 0.1 mm when FAB_CHARS
    characters fit with 0.1 mm to spare, else the largest size that fits (0.05 mm steps, at least
    0.1 mm), thickness 15% of the size."""
    s = min(FAB_TEXT, (bx - 0.2) / (FAB_CHARS * CHAR_ADV), (by - 0.2) / 1.1)
    s = max(0.1, math.floor(s * 20 + EPS) / 20)
    return s, FAB_TEXT_WIDTH if s >= FAB_TEXT else round(min(FAB_TEXT_WIDTH, 0.15 * s), 2)


def rot_box(cx, cy, w, h, rot):
    """Bounding box of a w x h rectangle at (cx, cy) turned by rot degrees."""
    a = math.radians(rot or 0)
    c, s = abs(math.cos(a)), abs(math.sin(a))
    if c < EPS:
        c = 0.0
    if s < EPS:
        s = 0.0
    return rect_box(cx, cy, w * c + h * s, w * s + h * c)


def rratio(w, h, want, max_r):
    m = min(w, h)
    r = want
    if m > 0 and r * m > max_r:
        r = max_r / m
    return round(r, 4)


def bbox_union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def rect_box(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def union_area(boxes):
    """Exact area of a union of axis-aligned rectangles (coordinate compression)."""
    if not boxes:
        return 0.0
    xs = sorted({b[0] for b in boxes} | {b[2] for b in boxes})
    ys = sorted({b[1] for b in boxes} | {b[3] for b in boxes})
    area = 0.0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            mx, my = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if any(b[0] <= mx <= b[2] and b[1] <= my <= b[3] for b in boxes):
                area += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return area


def row_letters(n, skip):
    out, i = [], 0
    letters = [c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if c not in skip]
    while len(out) < n:
        q, r = divmod(i, len(letters))
        out.append((letters[q - 1] if q else '') + letters[r])
        i += 1
    return out


class Builder:
    def __init__(self, spec):
        self.spec = spec
        self.o = dict(DEFAULTS)
        self.o.update(spec.get('options', {}))
        o = self.o
        o.setdefault('marker_width', MARK_MIN_WIDTH)
        for key, low in (('silk_width', SILK_MIN_WIDTH), ('silk_clearance', SILK_MIN_CLEARANCE),
                         ('marker_width', MARK_MIN_WIDTH)):
            if number(o[key], f'options {key}') < low - EPS:
                raise SpecError(f'options {key} {o[key]} is under the {low} mm DFM minimum')
        if o['marker_width'] < SILK_MIN_WIDTH - EPS and o['marker_size'] <= MARK_MIN_SIZE + EPS:
            raise SpecError(f'a {o["marker_width"]} mm pin 1 mark line needs marker_size over '
                            f'{MARK_MIN_SIZE} mm (DFM)')
        self.pads = []      # dicts, see pad()
        self.ep_info = []   # (number, copper boxes, main pad box, paste boxes, vias, via spec)
        self.warns = []

    # ---- pads -------------------------------------------------------------------------
    def pad(self, num, kind, shape, x, y, w, h, rot=0, drill=None, layers=None, ratio=None,
            paste=True, mask_margin=None, prims=None, via=False, prop=None, zone=None):
        where = f'pad "{num}" at ({x}, {y})'
        w, h = number(w, f'{where} size'), number(h, f'{where} size')
        x, y = number(x, f'{where} x', False), number(y, f'{where} y', False)
        rot = number(rot or 0, f'{where} rotation', False)
        if shape not in ('rect', 'roundrect', 'circle', 'oval', 'custom', 'trapezoid'):
            raise SpecError(f'{where}: unknown shape {shape!r}')
        if shape == 'circle' and abs(w - h) > EPS:
            raise SpecError(f'{where}: a circle pad needs w = h (KiCad uses only w); use oval')
        if ratio is not None:
            ratio = number(ratio, f'{where} ratio', False)
            if not 0 <= ratio <= 0.5:
                raise SpecError(f'{where}: ratio {ratio} outside 0 to 0.5')
        if kind not in ('smd', 'thru_hole', 'np_thru_hole'):
            raise SpecError(f'{where}: unknown type {kind!r}')
        if kind != 'smd':
            if drill is None:
                raise SpecError(f'{where}: a {kind} pad needs "drill"')
            dw, dh = pair(drill, f'{where} drill')
            pw, ph = (h, w) if round(rot) % 180 == 90 else (w, h)
            if dw > pw + EPS or dh > ph + EPS:
                raise SpecError(f'{where}: drill {dw}x{dh} is bigger than the pad {w}x{h}')
            ring = min(pw - dw, ph - dh) / 2
            if kind == 'thru_hole' and ring < 0.15 - EPS:
                self.warns.append(f'{where}: annular ring {f(ring)} mm < 0.15 mm (KLC F7.5)')
        if mask_margin is not None:
            mask_margin = number(mask_margin, f'{where} mask_margin', False)
        if isinstance(paste, dict):
            for k in ('margin', 'ratio'):
                if k in paste:
                    number(paste[k], f'{where} paste {k}', False)
        if prop is not None and prop not in PROPS:
            raise SpecError(f'{where}: fab property must be one of {", ".join(PROPS)}')
        if layers is None:
            if kind == 'smd':
                layers = ['F.Cu', 'F.Mask'] + (['F.Paste'] if paste is not False else [])
            elif via:
                layers = ['*.Cu']
            else:
                layers = ['*.Cu', '*.Mask']
        p = {'num': str(num), 'kind': kind, 'shape': shape, 'x': x, 'y': y, 'w': w, 'h': h,
             'rot': rot, 'drill': drill, 'layers': layers, 'ratio': ratio, 'paste': paste,
             'mask_margin': mask_margin, 'prims': prims, 'via': via, 'prop': prop, 'zone': zone}
        if shape == 'roundrect' and ratio is None:
            p['ratio'] = rratio(w, h, self.o['pad_ratio'], self.o['max_radius'])
        self.pads.append(p)
        return p

    @staticmethod
    def ratio_of(src, w, h):
        """Corner ratio from "radius" (mm, as the datasheet gives it) or "ratio"."""
        if src.get('radius') is not None:
            return round(number(src['radius'], 'radius', False) / min(w, h), 4)
        return src.get('ratio')

    def copper_boxes(self, p):
        if p['shape'] == 'custom':
            return [rect_box(p['x'] + r[0], p['y'] + r[1], r[2], r[3]) for r in p['prims']]
        return [rot_box(p['x'], p['y'], p['w'], p['h'], p['rot'])]

    def is_copper(self, p):
        return any(l in ('F.Cu', '*.Cu') for l in p['layers']) and p['kind'] != 'np_thru_hole'

    def add_rows(self, r):
        layout = r.get('layout', 'dual')
        pitch = r['pitch']
        L, W = r['pad']
        shape = r.get('shape', 'roundrect')
        ratio = self.ratio_of(r, L, W)
        ox, oy = r.get('at', [0, 0])
        paste = r.get('paste', True)
        places = []
        if layout == 'dual':
            if r['pins'] % 2:
                raise SpecError('dual rows need an even "pins" count')
            k = r['pins'] // 2
            s = r['span']
            ys = [(-(k - 1) / 2 + i) * pitch for i in range(k)]
            places += [(-s / 2, y, L, W) for y in ys]
            places += [(s / 2, y, L, W) for y in reversed(ys)]
        elif layout == 'quad':
            kx, ky = r['pins_x'], r['pins_y']
            sx, sy = r.get('span_x', r.get('span')), r.get('span_y', r.get('span'))
            if sx is None or sy is None:
                raise SpecError('quad rows need "span" or "span_x" and "span_y"')
            ys = [(-(ky - 1) / 2 + i) * pitch for i in range(ky)]
            xs = [(-(kx - 1) / 2 + i) * pitch for i in range(kx)]
            places += [(-sx / 2, y, L, W) for y in ys]
            places += [(x, sy / 2, W, L) for x in xs]
            places += [(sx / 2, y, L, W) for y in reversed(ys)]
            places += [(x, -sy / 2, W, L) for x in reversed(xs)]
        else:
            raise SpecError(f'unknown rows layout {layout!r}')
        nums = r.get('numbers') or [str(r.get('start', 1) + i) for i in range(len(places))]
        if len(nums) != len(places):
            raise SpecError(f'"numbers" has {len(nums)} entries for {len(places)} pad places')
        for num, (x, y, w, h) in zip(nums, places):
            if num is None:
                continue
            self.pad(num, 'smd', shape, ox + x, oy + y, w, h, ratio=ratio, paste=paste,
                     mask_margin=r.get('mask_margin'))

    def add_grid(self, g):
        rows, cols = g['rows'], g['cols']
        px, py = (g['pitch'], g['pitch']) if not isinstance(g['pitch'], list) else g['pitch']
        size = pair(g['pad'], 'grid pad')
        shape = g.get('shape', 'circle' if abs(size[0] - size[1]) < EPS else 'oval')
        prop = g.get('fab_property', 'bga')
        empty = set(g.get('empty', []))
        ox, oy = g.get('at', [0, 0])
        corner = g.get('a1', 'top-left')
        if corner not in ('top-left', 'top-right', 'bottom-left', 'bottom-right'):
            raise SpecError(f'grid "a1" must be top-left, top-right, bottom-left or bottom-right')
        on_cols = g.get('letters', 'rows') == 'cols'   # letters count along x instead of y
        nl, nn = (cols, rows) if on_cols else (rows, cols)
        letters = row_letters(nl, g.get('skip_letters', SKIP_LETTERS))
        fx = -1 if corner.endswith('right') else 1
        fy = -1 if corner.startswith('bottom') else 1
        for i, letter in enumerate(letters):
            for j in range(nn):
                name = f'{letter}{j + 1}'
                if name in empty:
                    continue
                c, r = (i, j) if on_cols else (j, i)
                x = ox + fx * (-(cols - 1) / 2 + c) * px
                y = oy + fy * (-(rows - 1) / 2 + r) * py
                self.pad(name, 'smd', shape, x, y, size[0], size[1], ratio=self.ratio_of(g, *size),
                         paste=g.get('paste', True), mask_margin=g.get('mask_margin'), prop=prop)

    def add_free(self, q):
        kind = q.get('type', 'smd')
        x, y = q['at'][0], q['at'][1]
        rot = q['at'][2] if len(q['at']) > 2 else 0
        w, h = pair(q['size'], f'pad "{q.get("number", "")}" size')
        if kind == 'smd':
            shape = q.get('shape', 'roundrect')
        else:
            shape = q.get('shape', 'circle' if abs(w - h) < EPS else 'oval')
        num = '' if kind == 'np_thru_hole' else q.get('number', '')
        prop = q.get('fab_property')
        self.pad(num, kind, shape, x, y, w, h, rot=rot, drill=q.get('drill'),
                 layers=q.get('layers'), ratio=self.ratio_of(q, w, h), paste=q.get('paste', True),
                 mask_margin=q.get('mask_margin'), prop=prop,
                 zone=q.get('zone_connect', 2 if prop == 'heatsink' else None))

    def add_ep(self, e):
        num = str(e['number'])
        w, h = pair(e['size'], f'exposed pad {num} size')
        cx, cy = e.get('at', [0, 0])
        tabs = e.get('tabs', [])
        for t in tabs:
            if not (isinstance(t, list) and len(t) == 4):
                raise SpecError(f'exposed pad {num}: each tab is [cx, cy, w, h]')
            number(t[2], f'exposed pad {num} tab w')
            number(t[3], f'exposed pad {num} tab h')
        paste = e.get('paste')
        if paste is None:
            raise SpecError(f'exposed pad {num}: give "paste" (explicit, grid, pad or none)')
        mode = paste.get('mode')
        er = number(self.ratio_of(e, w, h) if e.get('radius') is not None
                    else e.get('ratio', self.o['ep_ratio']), f'exposed pad {num} ratio', False)
        main = rect_box(cx, cy, w, h)
        copper = [main] + [rect_box(*t) for t in tabs]
        hs = dict(prop='heatsink', zone=2)
        if tabs:
            prims = [(0.0, 0.0, w, h, rratio(w, h, er, self.o['max_radius']))]
            prims += [(t[0] - cx, t[1] - cy, t[2], t[3],
                       rratio(t[2], t[3], er, self.o['max_radius'])) for t in tabs]
            a = round(min(w, h) / 2, 3)
            layers = ['F.Cu', 'F.Mask'] + (['F.Paste'] if mode == 'pad' else [])
            self.pad(num, 'smd', 'custom', cx, cy, a, a, layers=layers, prims=prims,
                     mask_margin=e.get('mask_margin'), **hs)
        else:
            self.pad(num, 'smd', 'roundrect' if er > 0 else 'rect', cx, cy, w, h,
                     paste=(mode == 'pad'), ratio=rratio(w, h, er, self.o['max_radius']),
                     mask_margin=e.get('mask_margin'), **hs)
        vias = e.get('vias')
        via_pts = []
        if vias:
            if 'at' in vias:
                via_pts = [tuple(v) for v in vias['at']]
            else:
                nx, ny = vias['grid']
                vx, vy = vias['pitch']
                via_pts = [(cx + (-(nx - 1) / 2 + i) * vx, cy + (-(ny - 1) / 2 + j) * vy)
                           for j in range(ny) for i in range(nx)]
            for vx_, vy_ in via_pts:
                self.pad(num, 'thru_hole', 'circle', vx_, vy_, vias['dia'], vias['dia'],
                         drill=vias['drill'], via=True, **hs)
            # KLC F4.4.2: B.Cu pad under thermal vias, B.Mask off (default on, false to skip)
            bottom = e.get('bottom', True)
            if bottom:
                bw, bh = (w, h) if bottom is True else pair(bottom, f'exposed pad {num} bottom')
                self.pad(num, 'smd', 'rect', cx, cy, bw, bh, layers=['B.Cu'], paste=False, **hs)
        apertures = []
        pr = paste.get('ratio', self.o['paste_ratio'])
        if mode == 'explicit':
            apertures = [tuple(a) for a in paste['apertures']]
        elif mode == 'grid':
            nx, ny = paste['n']
            cov = paste['coverage']
            if not 0 < cov <= 1:
                raise SpecError('paste coverage must be a fraction, 0 < coverage <= 1')
            s = math.sqrt(cov)
            cw, ch = w / nx, h / ny
            for j in range(ny):
                for i in range(nx):
                    ax = cx - w / 2 + (i + 0.5) * cw
                    ay = cy - h / 2 + (j + 0.5) * ch
                    apertures.append((round(ax, 4), round(ay, 4), round(cw * s, 4),
                                      round(ch * s, 4)))
        elif mode in ('pad', 'none'):
            pass
        else:
            raise SpecError(f'exposed pad {num}: unknown paste mode {mode!r}')
        for ax, ay, aw, ah in apertures:
            ar = (self.ratio_of(paste, aw, ah) if paste.get('radius') is not None
                  else rratio(aw, ah, pr, self.o['max_radius']))
            self.pad('', 'smd', 'roundrect', ax, ay, aw, ah, layers=['F.Paste'], ratio=ar)
        if mode == 'pad':
            pbox = copper
        else:
            pbox = [rect_box(*a) for a in apertures]
        self.ep_info.append((num, copper, main, pbox, via_pts, vias))

    # ---- graphics ---------------------------------------------------------------------
    def build(self):
        s = self.spec
        for r in s.get('rows', []):
            self.add_rows(r)
        if s.get('grid'):
            self.add_grid(s['grid'])
        for q in s.get('pads', []):
            self.add_free(q)
        eps = s.get('ep', [])
        for e in [eps] if isinstance(eps, dict) else eps:
            self.add_ep(e)
        if not self.pads:
            raise SpecError('spec has no pads')
        if not isinstance(s.get('body'), dict):
            raise SpecError('give "body": {"x": .., "y": ..}')
        bx, by = number(s['body']['x'], 'body x'), number(s['body']['y'], 'body y')
        bcx, bcy = s['body'].get('at', [0, 0])
        body = (bcx - bx / 2, bcy - by / 2, bcx + bx / 2, bcy + by / 2)
        cu = [b for p in self.pads if self.is_copper(p) for b in self.copper_boxes(p)]
        holes = [rect_box(p['x'], p['y'], p['w'], p['h']) for p in self.pads
                 if p['kind'] == 'np_thru_hole']
        keep = cu + holes

        # pin 1 corner, and the body side the pin 1 marks use: the one pin 1 is nearer to (x on a tie)
        p1 = next((p for p in self.pads if p['num'] in ('1', 'A1')), self.pads[0])
        sxn = -1 if p1['x'] - bcx <= EPS else 1
        syn = -1 if p1['y'] - bcy <= EPS else 1
        on_x = (-sxn * (p1['x'] - (body[0] if sxn < 0 else body[2]))
                <= -syn * (p1['y'] - (body[1] if syn < 0 else body[3])) + EPS)
        out = sxn if on_x else syn   # outward along the marks' axis
        silk_mark = s.get('silk_pin1')
        fab_mark = s.get('fab_pin1', 'plus' if silk_mark == 'plus' else 'dot')
        if fab_mark not in ('dot', 'arrow', 'plus', 'none'):
            raise SpecError('"fab_pin1" must be dot, arrow, plus or none')
        if silk_mark is None:
            silk_mark = fab_mark if fab_mark in ('plus', 'none') else 'arrow'
        if silk_mark not in ('arrow', 'plus', 'none'):
            raise SpecError('"silk_pin1" must be arrow, plus or none')
        # polarized capacitor base: both pin 1 side corners chamfered; can diameter drawn on F.Fab
        cham = number(s['body'].get('chamfer', 0), 'body chamfer', False)
        can = s['body'].get('d')
        if can is not None:
            can = number(can, 'body d')

        def outline(x0, y0, x1, y1, c):
            """Rectangle corners clockwise from the top left, the two pin 1 side corners cut by c."""
            corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            pts = []
            for i, (px, py) in enumerate(corners):
                side = (-1 if px == x0 else 1) == sxn if on_x else (-1 if py == y0 else 1) == syn
                if c > EPS and side:
                    for qx, qy in (corners[i - 1], corners[(i + 1) % 4]):
                        d = math.hypot(qx - px, qy - py)
                        pts.append((round(px + (qx - px) * c / d, 4), round(py + (qy - py) * c / d, 4)))
                else:
                    pts.append((px, py))
            return [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]

        # silkscreen outline, cut back from copper; on the graphic grid, rounded away from the body
        o = self.o
        sw, so, sc = o['silk_width'], o['silk_offset'], o['silk_clearance']
        k = sc + sw / 2
        L, R = snap(bcx - bx / 2 - so, -1), snap(bcx + bx / 2 + so, 1)
        T, B = snap(bcy - by / 2 - so, -1), snap(bcy + by / 2 + so, 1)
        edges = outline(L, T, R, B, snap(cham + so * (2 - math.sqrt(2)), 1) if cham > EPS else 0)
        silk = []
        for (x0, y0), (x1, y1) in edges:
            if abs(x0 - x1) > EPS and abs(y0 - y1) > EPS:   # chamfer: whole, or left out near copper
                eb = (min(x0, x1) - k, min(y0, y1) - k, max(x0, x1) + k, max(y0, y1) + k)
                if any(eb[0] < c[2] and c[0] < eb[2] and eb[1] < c[3] and c[1] < eb[3] for c in keep):
                    self.warns.append('a silk chamfer line runs near copper and was left out')
                else:
                    silk.append(((x0, y0), (x1, y1)))
                continue
            horiz = abs(y0 - y1) < EPS
            a, b = (min(x0, x1), max(x0, x1)) if horiz else (min(y0, y1), max(y0, y1))
            fixed = y0 if horiz else x0
            blocked = []
            for c in keep:
                lo, hi = (c[1], c[3]) if horiz else (c[0], c[2])
                if lo - k < fixed < hi + k:
                    blocked.append((c[0] - k, c[2] + k) if horiz else (c[1] - k, c[3] + k))
            segs = [(a, b)]
            for bl in blocked:
                nxt = []
                for s0, s1 in segs:
                    if bl[1] <= s0 or bl[0] >= s1:
                        nxt.append((s0, s1))
                        continue
                    if bl[0] > s0:
                        nxt.append((s0, bl[0]))
                    if bl[1] < s1:
                        nxt.append((bl[1], s1))
                segs = nxt
            for s0, s1 in segs:
                s0, s1 = snap(s0, 1), snap(s1, -1)   # cut ends move away from copper
                if s1 - s0 >= o['silk_min_len'] - EPS:
                    silk.append(((s0, fixed), (s1, fixed)) if horiz else ((fixed, s0), (fixed, s1)))

        # pin 1 mark on F.SilkS (KLC F5.1), (u, v) = (outward axis, along the pin 1 side):
        # arrow: beside pin 1 outside the silk outline, level with pin 1, pointing at it;
        # plus (polarized capacitors): over pad 1's outer end, past the pad edge on the pin 1 corner
        # side. Each moves out until it clears copper and the silk outline.
        m = max(GRAPHIC_GRID, snap(o['marker_size']))
        mw = o['marker_width'] if silk_mark == 'arrow' else sw
        k = sc + mw / 2
        along = snap(p1['y'] if on_x else p1['x'])
        to_xy = lambda uv: [(round(u, 4), round(v, 4)) if on_x else (round(v, 4), round(u, 4)) for u, v in uv]
        lines = [bbox_union([(a[0], a[1], a[0], a[1]), (b[0], b[1], b[0], b[1])]) for a, b in silk]
        gap = sw / 2 + mw / 2 + GRAPHIC_GRID

        def hits(pts):
            mb = bbox_union([(x, y, x, y) for x, y in pts])
            near = lambda c, d: (mb[0] - d < c[2] - 1e-6 and c[0] < mb[2] + d - 1e-6
                                 and mb[1] - d < c[3] - 1e-6 and c[1] < mb[3] + d - 1e-6)
            return any(near(c, k) for c in keep) or any(near(c, gap) for c in lines)

        def shape_at(kind, t):
            if kind == 'arrow':
                hw = snap(m * 2 / 3)
                return to_xy([(t, along), (t + out * m, along - hw), (t + out * m, along + hw)])
            u, v = t   # the box of the 1 x 1 mm "+" text
            h = SILK_MIN_TEXT / 2
            return to_xy([(u - h, v), (u + h, v), (u, v - h), (u, v + h)])

        def place(kind):
            if kind == 'arrow':
                edge = (L if sxn < 0 else R) if on_x else (T if syn < 0 else B)
                t = snap(edge + out * (sw / 2 + mw / 2 + GRAPHIC_GRID), out)
            else:
                pb = bbox_union(self.copper_boxes(p1))
                vdir = syn if on_x else sxn
                uo = (pb[0] if out < 0 else pb[2]) if on_x else (pb[1] if out < 0 else pb[3])
                ve = (pb[1] if vdir < 0 else pb[3]) if on_x else (pb[0] if vdir < 0 else pb[2])
                t = (snap(uo - out * SILK_MIN_TEXT / 2, out), snap(ve + vdir * (k + SILK_MIN_TEXT / 2), vdir))
            for _ in range(100):
                pts = shape_at(kind, t)
                if not hits(pts):
                    return pts
                t = round(t + out * GRAPHIC_GRID, 4) if kind == 'arrow' else (round(t[0] + out * GRAPHIC_GRID, 4), t[1])
            self.warns.append('pin 1 silk mark overlaps copper or silk; move it by hand')
            return pts

        mark_pts = place(silk_mark) if silk_mark != 'none' else []
        fab_plus = None
        if fab_mark == 'plus':   # drawn + (0.8 mm) at the center of the silk "+" text
            box = mark_pts if silk_mark == 'plus' else place('plus')
            cx, cy = center_of(box)
            a = PLUS_ARM
            fab_plus = [(cx - a, cy), (cx + a, cy), (cx, cy - a), (cx, cy + a)]

        # courtyard around body and copper (KLC F5.3: BGA 1.0; 0.15 when the part is under 1.5 mm
        # in both directions, as the stock KiCad generators read the rule); grown the same on
        # every side until it holds the pin 1 silk mark
        clr = s.get('courtyard', 1.0 if s.get('grid') else 0.15 if max(bx, by) < 1.5 else 0.25)
        clr = number(clr, 'courtyard')
        cb = bbox_union([body] + keep)
        cb = (cb[0] - clr, cb[1] - clr, cb[2] + clr, cb[3] + clr)
        held = mark_pts + (fab_plus or [])
        if held:
            mb = bbox_union([(x - mw / 2, y - mw / 2, x + mw / 2, y + mw / 2) for x, y in held])
            grow = max(0.0, cb[0] - mb[0], cb[1] - mb[1], mb[2] - cb[2], mb[3] - cb[3])
            cb = (cb[0] - grow, cb[1] - grow, cb[2] + grow, cb[3] + grow)
        cb = (math.floor(cb[0] * 100 + EPS) / 100, math.floor(cb[1] * 100 + EPS) / 100,
              math.ceil(cb[2] * 100 - EPS) / 100, math.ceil(cb[3] * 100 - EPS) / 100)

        # fab outline: rectangle on the graphic grid (the body within 0.025 mm; chamfered for a
        # polarized capacitor base, with the can circle), with one pin 1 mark: a filled dot level
        # with pin 1 (default), for connectors a filled arrow from the body edge pointing at pin 1
        # (KLC F5.2), or for polarized capacitors the + of the silk mark
        fb = [snap(v) for v in body]
        fab = outline(*fb, snap(cham) if cham > EPS else 0)
        circle = (snap(bcx), snap(bcy), snap(can / 2)) if can else None
        cx0, cy0 = (fb[0] if sxn < 0 else fb[2]), (fb[1] if syn < 0 else fb[3])
        dot = arrow = None
        pb = bbox_union(self.copper_boxes(p1))
        short = min(bx, by)
        if fab_mark == 'dot':
            mid = abs((p1['y'] - bcy) if on_x else (p1['x'] - bcx)) < 0.25 * (by if on_x else bx)
            if s.get('grid') and short >= 5 - EPS:   # BGA: on ball A1
                dot = (snap(p1['x']), snap(p1['y']), 0.35)
            elif mid:   # pin 1 in the middle of a side (diodes, LEDs): level with it, at its pad's outer end
                r = dot_radius(short) + 0.05
                u = snap((pb[0] if out < 0 else pb[2]) if on_x else (pb[1] if out < 0 else pb[3]))
                dot = ((u, along) if on_x else (along, u)) + (r,)
            else:   # on the body diagonal, 3 radii in from the pin 1 corner
                r = dot_radius(short)
                ins = snap(min(3 * r, short / 2))
                dot = (round(cx0 - sxn * ins, 4), round(cy0 - syn * ins, 4), r)
        elif fab_mark == 'arrow':
            # on pad 1's long axis, on the body side, tip 0.2 mm off the pad end, pointing at the pad
            pw, ph = pb[2] - pb[0], pb[3] - pb[1]
            ax = pw > ph + EPS or (abs(pw - ph) <= EPS and abs(bcx - p1['x']) >= abs(bcy - p1['y']))
            c, pc = (bcx, p1['x']) if ax else (bcy, p1['y'])
            d = 1 if c >= pc - EPS else -1
            al, ahw = (0.3, 0.2) if min(pw, ph) < 1 - EPS else (0.5, 0.3)
            tip = snap(((pb[2] if d > 0 else pb[0]) if ax else (pb[3] if d > 0 else pb[1])) + d * 0.2)
            v = snap(p1['y'] if ax else p1['x'])
            uv = [(tip, v), (tip + d * al, v - ahw), (tip + d * al, v + ahw)]
            arrow = [(round(u, 4), round(w, 4)) if ax else (round(w, 4), round(u, 4)) for u, w in uv]
        # Reference above the courtyard and the pin 1 mark, Value below
        top = min([cb[1]] + [y - mw / 2 for _, y in held])
        bot = max([cb[3]] + [y + mw / 2 for _, y in held])
        self.geo = {'silk': silk, 'mark': (silk_mark, mark_pts, mw), 'crtyd': cb, 'fab': fab,
                    'fab_text': fab_text(bx, by), 'body_at': (snap(bcx), snap(bcy)), 'fab_dot': dot,
                    'fab_arrow': arrow, 'fab_plus': fab_plus, 'fab_circle': circle,
                    'ref_y': snap(top - 0.75, -1), 'val_y': snap(bot + 0.85, 1)}
        return self

    # ---- output -----------------------------------------------------------------------
    def render(self):
        s, o, g = self.spec, self.o, self.geo
        name = s['name']
        counter = [0]

        def uid():
            counter[0] += 1
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f'kicad-footprint-make/{name}/{counter[0]}'))

        out = []
        w = out.append
        w(f'(footprint "{q(name)}"')
        w('\t(version 20260206)')
        w('\t(generator "pcbnew")')
        w('\t(generator_version "10.0")')
        w('\t(layer "F.Cu")')
        if s.get('descr'):
            w(f'\t(descr "{q(s["descr"])}")')
        if s.get('tags'):
            w(f'\t(tags "{q(s["tags"])}")')
        cb = g['crtyd']
        bc = g['body_at']
        props = [('Reference', 'REF**', bc[0], g['ref_y'], 'F.SilkS', False, SILK_MIN_TEXT, SILK_MIN_WIDTH),
                 ('Value', name, bc[0], g['val_y'], 'F.Fab', True, 1, 0.15),
                 ('Datasheet', s.get('datasheet', ''), 0, 0, 'F.Fab', True, 1.27, 0.15),
                 ('Description', '', 0, 0, 'F.Fab', True, 1.27, 0.15)]
        kind, pts, mw = g['mark']
        if kind == 'plus':   # silk + of a polarized capacitor: a 1 x 1 mm text, as hand edits do
            props.append(('Polar', '+', *center_of(pts), 'F.SilkS', False, SILK_MIN_TEXT, SILK_MIN_WIDTH))
        for key, val, x, y, layer, hide, size, th in props:
            w(f'\t(property "{key}" "{q(val)}"')
            w(f'\t\t(at {f(x)} {f(y)} 0)')
            if hide and key != 'Value':
                w('\t\t(unlocked yes)')
            w(f'\t\t(layer "{layer}")')
            if hide:
                w('\t\t(hide yes)')
            w(f'\t\t(uuid "{uid()}")')
            w(f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {f(size)} {f(size)})\n'
              f'\t\t\t\t(thickness {f(th)})\n\t\t\t)\n\t\t)')
            w('\t)')
        tht = any(p['kind'] == 'thru_hole' and not p['via'] for p in self.pads)
        w(f'\t(attr {s.get("attr", "through_hole" if tht else "smd")})')
        w('\t(duplicate_pad_numbers_are_jumpers no)')

        def line(a, b, width, layer):
            w(f'\t(fp_line\n\t\t(start {f(a[0])} {f(a[1])})\n\t\t(end {f(b[0])} {f(b[1])})\n'
              f'\t\t(stroke\n\t\t\t(width {f(width)})\n\t\t\t(type solid)\n\t\t)\n'
              f'\t\t(layer "{layer}")\n\t\t(uuid "{uid()}")\n\t)')

        def fill_poly(pts, width, layer):
            xy = ' '.join(f'(xy {f(x)} {f(y)})' for x, y in pts + [pts[0]])
            w(f'\t(fp_poly\n\t\t(pts\n\t\t\t{xy}\n\t\t)\n\t\t(stroke\n\t\t\t(width {f(width)})\n'
              f'\t\t\t(type solid)\n\t\t)\n\t\t(fill yes)\n\t\t(layer "{layer}")\n\t\t(uuid "{uid()}")\n\t)')

        for a, b in g['silk']:
            line(a, b, o['silk_width'], 'F.SilkS')
        if kind == 'arrow':
            fill_poly(pts, mw, 'F.SilkS')
        c = [(cb[0], cb[1]), (cb[2], cb[1]), (cb[2], cb[3]), (cb[0], cb[3])]
        for i in range(4):
            line(c[i], c[(i + 1) % 4], o['crtyd_width'], 'F.CrtYd')
        for a, b in g['fab']:
            line(a, b, o['fab_width'], 'F.Fab')
        if g['fab_dot']:
            x, y, r = g['fab_dot']
            w(f'\t(fp_circle\n\t\t(center {f(x)} {f(y)})\n\t\t(end {f(x + r)} {f(y)})\n'
              f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill yes)\n'
              f'\t\t(layer "F.Fab")\n\t\t(uuid "{uid()}")\n\t)')
        if g['fab_arrow']:
            fill_poly(g['fab_arrow'], o['fab_width'], 'F.Fab')
        if g['fab_plus']:
            line(g['fab_plus'][0], g['fab_plus'][1], o['fab_width'], 'F.Fab')
            line(g['fab_plus'][2], g['fab_plus'][3], o['fab_width'], 'F.Fab')
        if g['fab_circle']:
            x, y, r = g['fab_circle']
            w(f'\t(fp_circle\n\t\t(center {f(x)} {f(y)})\n\t\t(end {f(x + r)} {f(y)})\n'
              f'\t\t(stroke\n\t\t\t(width {f(o["fab_width"])})\n\t\t\t(type solid)\n\t\t)\n\t\t(fill no)\n'
              f'\t\t(layer "F.Fab")\n\t\t(uuid "{uid()}")\n\t)')
        fs, ft = g['fab_text']
        w(f'\t(fp_text user "${{REFERENCE}}"\n\t\t(at {f(bc[0])} {f(bc[1])} 0)\n\t\t(layer "F.Fab")\n'
          f'\t\t(uuid "{uid()}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {f(fs)} {f(fs)})\n'
          f'\t\t\t\t(thickness {f(ft)})\n\t\t\t)\n\t\t)\n\t)')

        def arc_rect(cx, cy, pw, ph, r):
            x0, y0, x1, y1 = cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2
            if r <= 0:
                return ' '.join(f'(xy {f(x)} {f(y)})' for x, y in
                                ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))
            kk = r * (1 - 1 / math.sqrt(2))
            arcs = [((x1 - r, y0), (x1 - kk, y0 + kk), (x1, y0 + r)),
                    ((x1, y1 - r), (x1 - kk, y1 - kk), (x1 - r, y1)),
                    ((x0 + r, y1), (x0 + kk, y1 - kk), (x0, y1 - r)),
                    ((x0, y0 + r), (x0 + kk, y0 + kk), (x0 + r, y0))]
            return ' '.join(f'(arc (start {f(a[0])} {f(a[1])}) (mid {f(b[0])} {f(b[1])}) '
                            f'(end {f(e[0])} {f(e[1])}))' for a, b, e in arcs)

        def sortkey(p):
            n = p['num']
            return (n != '', [int(t) if t.isdigit() else t for t in
                              re.split(r'(\d+)', n)], p['via'])

        for p in sorted(self.pads, key=sortkey):
            rot = f' {f(p["rot"])}' if p['rot'] else ''
            w(f'\t(pad "{p["num"]}" {p["kind"]} {p["shape"]}')
            w(f'\t\t(at {f(p["x"])} {f(p["y"])}{rot})')
            w(f'\t\t(size {f(p["w"])} {f(p["h"])})')
            d = p['drill']
            if d is not None:
                if isinstance(d, list):
                    w(f'\t\t(drill oval {f(d[0])} {f(d[1])})')
                else:
                    w(f'\t\t(drill {f(d)})')
            if p['prop']:
                w(f'\t\t(property {PROPS[p["prop"]]})')
            w('\t\t(layers ' + ' '.join(f'"{l}"' for l in p['layers']) + ')')
            if p['via'] or p['kind'] == 'thru_hole':
                w('\t\t(remove_unused_layers no)')
            if p['shape'] == 'roundrect':
                w(f'\t\t(roundrect_rratio {f(p["ratio"])})')
            if isinstance(p['paste'], dict):
                if 'margin' in p['paste']:
                    w(f'\t\t(solder_paste_margin {f(p["paste"]["margin"])})')
                if 'ratio' in p['paste']:
                    w(f'\t\t(solder_paste_margin_ratio {f(p["paste"]["ratio"])})')
            if p['mask_margin'] is not None:
                w(f'\t\t(solder_mask_margin {f(p["mask_margin"])})')
            if p['zone'] is not None:
                w(f'\t\t(zone_connect {int(p["zone"])})')
            if p['shape'] == 'custom':
                w('\t\t(options\n\t\t\t(clearance outline)\n\t\t\t(anchor circle)\n\t\t)')
                w('\t\t(primitives')
                for px, py, pw, ph, r in p['prims']:
                    rr = r * min(pw, ph)
                    w(f'\t\t\t(gr_poly\n\t\t\t\t(pts {arc_rect(px, py, pw, ph, rr)})\n'
                      f'\t\t\t\t(width 0)\n\t\t\t\t(fill yes)\n\t\t\t)')
                w('\t\t)')
            w(f'\t\t(uuid "{uid()}")')
            w('\t)')
        w('\t(embedded_fonts no)')
        if s.get('model'):
            w(f'\t(model "{q(s["model"])}"\n\t\t(offset\n\t\t\t(xyz 0 0 0)\n\t\t)\n'
              f'\t\t(scale\n\t\t\t(xyz 1 1 1)\n\t\t)\n\t\t(rotate\n\t\t\t(xyz 0 0 0)\n\t\t)\n\t)')
        w(')')
        return '\n'.join(out) + '\n'

    def summary(self):
        lines = []
        nums = sorted({p['num'] for p in self.pads if p['num']},
                      key=lambda n: [int(t) if t.isdigit() else t
                                     for t in re.split(r'(\d+)', n)])
        top = [p for p in self.pads if p['num'] and not p['via'] and 'B.Cu' not in p['layers']]
        bot = [p for p in self.pads if p['num'] and not p['via'] and 'B.Cu' in p['layers']]
        lines.append(f'pads: {len(top)} top, {len(bot)} B.Cu, {len(nums)} unique numbers, '
                     f'{len([p for p in self.pads if p["via"]])} thermal vias, '
                     f'{len([p for p in self.pads if not p["num"]])} paste-only apertures')
        for num, copper, main, pbox, via_pts, vias in self.ep_info:
            ca = union_area(copper)
            pa = union_area(pbox)
            txt = f'exposed pad {num}: copper {ca:.4f} mm2, paste {pa:.4f} mm2, coverage {100 * pa / ca:.1f}%'
            if len(copper) > 1:
                pm = union_area([b for b in pbox if b[0] >= main[0] - EPS and b[2] <= main[2] + EPS
                                 and b[1] >= main[1] - EPS and b[3] <= main[3] + EPS])
                txt += f' (main pad alone {100 * pm / union_area([main]):.1f}%)'
            lines.append(txt)
            if not 0.5 <= pa / ca <= 0.8 and pa > 0:
                lines.append(f'  WARN coverage outside 50 to 80% (KLC F6.3; follow the datasheet if it says so)')
            if vias:
                r = vias['drill'] / 2
                for vx, vy in via_pts:
                    if any(b[0] < vx + r - 1e-6 and vx - r < b[2] - 1e-6 and b[1] < vy + r - 1e-6
                           and vy - r < b[3] - 1e-6
                           for b in pbox):
                        kind = 'WARN' if vias['drill'] >= 0.3 - EPS else 'INFO'
                        lines.append(f'  {kind} via at ({f(vx)}, {f(vy)}) drill {f(vias["drill"])} is under '
                                     'paste' + (': fill or plug it, or move the aperture (KLC F4.4.3)'
                                                if kind == 'WARN' else ' (allowed under 0.3 mm, KLC F4.4.3)'))
        lines += [f'WARN {m}' for m in self.warns]
        return '\n'.join(lines)


def build_text(spec):
    b = Builder(spec).build()
    return b.render(), b


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('spec')
    ap.add_argument('out')
    ap.add_argument('--newline', choices=['auto', 'lf', 'crlf'], default='auto')
    a = ap.parse_args()
    if os.path.exists(a.out):
        sys.exit(f'refusing to overwrite {a.out}')
    with open(a.spec, encoding='utf-8') as fh:
        spec = json.load(fh)
    want = os.path.splitext(os.path.basename(a.out))[0]
    if spec.get('name') != want:
        sys.exit(f'spec name {spec.get("name")!r} does not match file name {want!r}')
    try:
        text, b = build_text(spec)
    except KeyError as e:
        sys.exit(f'spec error: missing key {e}')
    except (SpecError, TypeError, ValueError, IndexError) as e:
        sys.exit(f'spec error: {e}')
    nl = '\n'
    if a.newline == 'crlf':
        nl = '\r\n'
    elif a.newline == 'auto':
        folder = os.path.dirname(os.path.abspath(a.out))
        for fn in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            if fn.endswith('.kicad_mod'):
                with open(os.path.join(folder, fn), 'rb') as fh:
                    nl = '\r\n' if b'\r\n' in fh.read(4096) else '\n'
                break
    with open(a.out, 'w', encoding='utf-8', newline=nl) as fh:
        fh.write(text)
    print(f'wrote {a.out}')
    print(b.summary())


if __name__ == '__main__':
    main()
