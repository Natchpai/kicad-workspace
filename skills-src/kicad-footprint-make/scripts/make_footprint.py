"""Write a KiCad 10 footprint (.kicad_mod) from a JSON spec of datasheet land-pattern values.

Usage:
    python -I make_footprint.py <spec.json> <out.kicad_mod> [--newline auto|lf|crlf]

The spec format is in SPEC.md next to this folder. In short: "rows" (dual or quad pad rows),
"grid" (BGA/LGA), "pads" (free list, SMD or THT) and "ep" (exposed pads with tabs, thermal vias
and stencil apertures) can be combined. Every dimension is in mm and comes from the datasheet;
the script computes only layout (positions from pitch and span) and the generated layers.

Generated: F.Fab body rectangle with a filled pin 1 dot (or a pin 1 bevel, or none) and ${REFERENCE},
F.SilkS outline at body + silk offset (default 0.1 mm), 0.15 mm wide, cut back 0.2 mm from copper, a
filled pin 1 triangle, F.CrtYd rectangle around body and copper (0.25 mm; 0.15 mm when both body sides
are under 1.5 mm; 1.0 mm with "grid") on a 0.01 mm grid, properties (Value hidden) and model.
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
        ratio = r.get('ratio')
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
            sx, sy = r['span_x'], r['span_y']
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
                self.pad(name, 'smd', shape, x, y, size[0], size[1], ratio=g.get('ratio'),
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
                 layers=q.get('layers'), ratio=q.get('ratio'), paste=q.get('paste', True),
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
        er = number(e.get('ratio', self.o['ep_ratio']), f'exposed pad {num} ratio', False)
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
            self.pad('', 'smd', 'roundrect', ax, ay, aw, ah, layers=['F.Paste'],
                     ratio=rratio(aw, ah, pr, self.o['max_radius']))
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

        # pin 1 corner
        p1 = next((p for p in self.pads if p['num'] in ('1', 'A1')), self.pads[0])
        sxn = -1 if p1['x'] - bcx <= EPS else 1
        syn = -1 if p1['y'] - bcy <= EPS else 1

        # silkscreen outline, cut back from copper
        o = self.o
        sw, so, sc = o['silk_width'], o['silk_offset'], o['silk_clearance']
        k = sc + sw / 2
        X, Y = bx / 2 + so, by / 2 + so
        edges = [((bcx - X, bcy - Y), (bcx + X, bcy - Y)), ((bcx + X, bcy - Y), (bcx + X, bcy + Y)),
                 ((bcx + X, bcy + Y), (bcx - X, bcy + Y)), ((bcx - X, bcy + Y), (bcx - X, bcy - Y))]
        silk = []
        for (x0, y0), (x1, y1) in edges:
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
                if s1 - s0 >= o['silk_min_len']:
                    silk.append(((s0, fixed), (s1, fixed)) if horiz else ((fixed, s0), (fixed, s1)))

        # pin 1 triangle at the silk corner, moved out until it clears copper
        m, g = o['marker_size'], sw / 4
        cxs, cys = bcx + sxn * X, bcy + syn * Y
        shift = 0.0
        for _ in range(60):
            tri = [(cxs + sxn * g, cys + syn * shift), (cxs + sxn * (g + m), cys + syn * shift),
                   (cxs + sxn * g, cys + syn * (shift + m))]
            tb = (min(t[0] for t in tri) - k, min(t[1] for t in tri) - k,
                  max(t[0] for t in tri) + k, max(t[1] for t in tri) + k)
            if not any(tb[0] < c[2] and c[0] < tb[2] and tb[1] < c[3] and c[1] < tb[3]
                       for c in keep):
                break
            shift += 0.05
        else:
            self.warns.append('pin 1 silk triangle overlaps copper; move it by hand')

        # courtyard around body and copper only (KLC F5.3: BGA 1.0; 0.15 when the part is
        # under 1.5 mm in both directions, as the stock KiCad generators read the rule)
        clr = s.get('courtyard', 1.0 if s.get('grid') else 0.15 if max(bx, by) < 1.5 else 0.25)
        clr = number(clr, 'courtyard')
        cb = bbox_union([body] + keep)
        cb = (cb[0] - clr, cb[1] - clr, cb[2] + clr, cb[3] + clr)
        cb = (math.floor(cb[0] * 100 + EPS) / 100, math.floor(cb[1] * 100 + EPS) / 100,
              math.ceil(cb[2] * 100 - EPS) / 100, math.ceil(cb[3] * 100 - EPS) / 100)

        # fab outline: plain rectangle with a pin 1 dot (default), or a pin 1 bevel (KLC F5.2)
        mark = s.get('fab_pin1', 'dot')
        if mark not in ('dot', 'bevel', 'none'):
            raise SpecError('"fab_pin1" must be dot, bevel or none')
        bev = min(1.0, 0.25 * min(bx, by))
        corners = [(body[0], body[1]), (body[2], body[1]), (body[2], body[3]), (body[0], body[3])]
        ci = {(-1, -1): 0, (1, -1): 1, (1, 1): 2, (-1, 1): 3}[(sxn, syn)]
        dot = None
        if mark == 'dot':
            d = max(0.2, min(0.5, math.floor(0.1 * min(bx, by) * 20) / 20))
            ins = d / 2 + 0.1
            dot = (corners[ci][0] - sxn * ins, corners[ci][1] - syn * ins, d / 2)
        poly = []
        for i, (px, py) in enumerate(corners):
            if i == ci and mark == 'bevel':
                prv, nxt = corners[i - 1], corners[(i + 1) % 4]
                def toward(q):
                    d = math.hypot(q[0] - px, q[1] - py)
                    return (px + (q[0] - px) * bev / d, py + (q[1] - py) * bev / d)
                poly += [toward(prv), toward(nxt)]
            else:
                poly.append((px, py))
        fab = [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
        fs = max(0.5, min(1.0, math.floor(min(bx * 0.22, by * 0.5) * 20) / 20))
        # Reference above the courtyard and the pin 1 triangle, Value below
        top = min(cb[1], min(t[1] for t in tri) - sw / 2)
        bot = max(cb[3], max(t[1] for t in tri) + sw / 2)
        self.geo = {'silk': silk, 'tri': tri, 'crtyd': cb, 'fab': fab, 'fab_text': fs,
                    'body_at': (bcx, bcy), 'fab_dot': dot, 'ref_y': top - 0.75,
                    'val_y': bot + 0.85}
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
        props = [('Reference', 'REF**', bc[0], g['ref_y'], 'F.SilkS', False, 1, 0.15),
                 ('Value', name, bc[0], g['val_y'], 'F.Fab', True, 1, 0.15),
                 ('Datasheet', s.get('datasheet', ''), 0, 0, 'F.Fab', True, 1.27, 0.15),
                 ('Description', '', 0, 0, 'F.Fab', True, 1.27, 0.15)]
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

        for a, b in g['silk']:
            line(a, b, o['silk_width'], 'F.SilkS')
        pts = ' '.join(f'(xy {f(x)} {f(y)})' for x, y in g['tri'] + [g['tri'][0]])
        w(f'\t(fp_poly\n\t\t(pts\n\t\t\t{pts}\n\t\t)\n\t\t(stroke\n\t\t\t(width {f(o["silk_width"])})\n'
          f'\t\t\t(type solid)\n\t\t)\n\t\t(fill yes)\n\t\t(layer "F.SilkS")\n\t\t(uuid "{uid()}")\n\t)')
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
        fs = g['fab_text']
        w(f'\t(fp_text user "${{REFERENCE}}"\n\t\t(at {f(bc[0])} {f(bc[1])} 0)\n\t\t(layer "F.Fab")\n'
          f'\t\t(uuid "{uid()}")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {f(fs)} {f(fs)})\n'
          f'\t\t\t\t(thickness {f(round(fs * 0.15, 2))})\n\t\t\t)\n\t\t)\n\t)')

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
        lines.append(f'pads: {len([p for p in self.pads if p["num"] and not p["via"]])} '
                     f'numbered, {len(nums)} unique numbers, '
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
