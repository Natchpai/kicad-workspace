"""Measure a KiCad footprint, check it, and compare it with datasheet values or another footprint.
Read-only.

Usage:
    python -I fp_check.py <fp.kicad_mod> [--ref <spec.json> | --vs <other.kicad_mod>]
                          [--tol 0.01] [--stencil 0.125] [--courtyard <mm>] [--quiet]

Without --ref or --vs it prints a measurement table and the checks.
--ref compares with a make_footprint.py spec (the datasheet values), built in memory.
--vs compares with another footprint, for example a stock or vendor candidate.
The compare covers copper pads (position, size, type, shape, drill, layers, mask margin, custom
pad area), thermal vias, NPTH holes and paste openings. Courtyard, fab outline, fab properties
and model are reported as INFO only; silkscreen is not compared.

Checks (WARN lines; INFO where KLC only recommends): square pad corners (exposed pads excepted);
Value property not hidden; paste outside copper; exposed-pad paste coverage (KLC F6.3: 50 to 80%);
exposed pad to other pads >= 0.2 mm (F6.3); paste over a via drill >= 0.3 mm (F4.4.3); via
number differs from its exposed pad (F4.3); B.Cu pad under thermal vias (F4.4.2); heatsink fab
property and solid zone connection on exposed pads and vias (F6.3); copper graphics outside a
pad; courtyard clearance (0.25 mm; 0.15 mm when the body is under 1.5 mm both ways) and 0.01 mm
grid (F5.3); silkscreen to copper (at least 0.15 mm DFM, the line width and the mask margin, 0.2 mm
recommended, F5.1); DFM silkscreen: lines >= 0.15 mm (a filled pin 1 mark over 0.15 mm across:
>= 0.1 mm), visible text >= 1 x 1 mm and 0.15 mm thick, text >= 0.15 mm from copper (estimated box),
no filled dot on silkscreen, filled pin 1 mark inside the courtyard (F5.1);
F.Fab ${REFERENCE} 1 x 1 mm, 0.1 mm thick, smaller only to fit a small body (house rule); F.SilkS
and F.Fab points and text positions on the 0.05 mm grid (house rule, INFO); pin 1 (or A1) at the top left (F4.2); annular ring >= 0.15 mm (F7.5); THT pin 1 shape
(F7.3, INFO); stencil area ratio < 0.66 or aspect ratio < 1.5 (IPC-7525) at --stencil thickness.

Copper is measured as polygons: rect, roundrect, circle (KiCad uses the x size) and oval
outlines, custom pad primitives (poly, rect, circle, line and arc, with stroke width), shape
offset and rotation. Paste openings are bounding boxes with their corner radius. Footprint-level
paste and mask margins apply when a pad has none; board-level margins are taken as zero.
Text outlines are estimated (0.9 x size per character, centered). Output lines start with PASS, WARN, DIFF or INFO. Exit code 1
when any DIFF is found.
"""
import argparse
import importlib.util
import json
import math
import os
import re
import sys

EPS = 1e-6


def load_maker():
    """make_footprint.py from this folder: the DFM limits, fab_text() and the spec builder."""
    here = os.path.dirname(os.path.abspath(__file__))
    spec_mod = importlib.util.spec_from_file_location('make_footprint',
                                                      os.path.join(here, 'make_footprint.py'))
    sys.dont_write_bytecode = True  # keep the skill folder clean
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)
    return mod


MF = load_maker()
SILK_MIN_WIDTH, SILK_MIN_TEXT, SILK_MIN_CLEARANCE = MF.SILK_MIN_WIDTH, MF.SILK_MIN_TEXT, MF.SILK_MIN_CLEARANCE
MARK_MIN_WIDTH, MARK_MIN_SIZE = MF.MARK_MIN_WIDTH, MF.MARK_MIN_SIZE


# ---- s-expression ---------------------------------------------------------------------------
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


def num(v):
    return float(v)


def xy(node, key):
    k = kid(node, key)
    return (num(k[1]), num(k[2])) if k else None


# ---- geometry -------------------------------------------------------------------------------
def rot_pt(x, y, deg):
    if not deg:
        return x, y
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def box_of(pts, grow=0.0):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs) - grow, min(ys) - grow, max(xs) + grow, max(ys) + grow)


def union_area(boxes):
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


def arc_pts(s, m, e, n=8):
    """Points from s through m to e on the circle through all three."""
    ax, ay = s
    bx, by = m
    cx, cy = e
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return [s, m, e]
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    a0 = math.atan2(ay - uy, ax - ux)
    a1 = math.atan2(by - uy, bx - ux)
    a2 = math.atan2(cy - uy, cx - ux)
    span = (a2 - a0) % (2 * math.pi)
    if (a1 - a0) % (2 * math.pi) > span:
        span -= 2 * math.pi
    return [(ux + r * math.cos(a0 + span * k / n), uy + r * math.sin(a0 + span * k / n))
            for k in range(n + 1)]


def poly_pts(node):
    """Outline points of a gr_poly / fp_poly, with arc segments interpolated."""
    pts = []
    for q in kid(node, 'pts')[1:]:
        if q[0] == 'xy':
            pts.append((num(q[1]), num(q[2])))
        elif q[0] == 'arc':
            pts += arc_pts(xy(q, 'start'), xy(q, 'mid'), xy(q, 'end'))
    return pts


def circle_pts(cx, cy, r, n=16):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))
            for k in range(n)]


def rrect_poly(w, h, r, n=8):
    """Ordered outline of a w x h box centered at 0 with corner radius r."""
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= EPS:
        return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
                       (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        pts += [(cx + r * math.cos(math.radians(a0 + 90 * k / n)),
                 cy + r * math.sin(math.radians(a0 + 90 * k / n))) for k in range(n + 1)]
    return pts


def thick_seg(a, b, w):
    """Rectangle polygon around segment a-b with width w (round caps as square caps)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1e-9
    ux, uy = dx / L * w / 2, dy / L * w / 2
    nx, ny = -uy, ux
    return [(a[0] - ux + nx, a[1] - uy + ny), (b[0] + ux + nx, b[1] + uy + ny),
            (b[0] + ux - nx, b[1] + uy - ny), (a[0] - ux - nx, a[1] - uy - ny)]


def rect_poly(b):
    return [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]


def poly_contains(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def seg_dist(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / L))
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)


def seg_cross(a, b, c, d):
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    d1, d2, d3, d4 = o(c, d, a), o(c, d, b), o(a, b, c), o(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def seg_seg_dist(a, b, c, d):
    if seg_cross(a, b, c, d):
        return 0.0
    return min(seg_dist(*a, c, d), seg_dist(*b, c, d), seg_dist(*c, a, b), seg_dist(*d, a, b))


def poly_dist(x, y, poly):
    """0 inside the polygon, else the distance to its outline."""
    if poly_contains(x, y, poly):
        return 0.0
    return min(seg_dist(x, y, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def seg_poly_dist(a, b, poly):
    if poly_contains(*a, poly) or poly_contains(*b, poly):
        return 0.0
    return min(seg_seg_dist(a, b, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def poly_poly_dist(p, q):
    if poly_contains(*p[0], q) or poly_contains(*q[0], p):
        return 0.0
    return min(seg_poly_dist(p[i], p[(i + 1) % len(p)], q) for i in range(len(p)))


def poly_union_area(polys, step=None):
    """Area of a union of polygons, sampled on a grid (cell centers)."""
    if not polys:
        return 0.0
    b = box_of([pt for p in polys for pt in p])
    if step is None:
        step = max(0.005, math.sqrt((b[2] - b[0]) * (b[3] - b[1])) / 300)
    nx = max(1, int(math.ceil((b[2] - b[0]) / step)))
    ny = max(1, int(math.ceil((b[3] - b[1]) / step)))
    boxes = [box_of(p) for p in polys]
    hit = 0
    for i in range(nx):
        x = b[0] + (i + 0.5) * step
        cand = [(p, bb) for p, bb in zip(polys, boxes) if bb[0] <= x <= bb[2]]
        for j in range(ny):
            y = b[1] + (j + 0.5) * step
            if any(bb[1] <= y <= bb[3] and poly_contains(x, y, p) for p, bb in cand):
                hit += 1
    return hit * step * step


def overlap(a, b):
    return a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS


def near(a, b, d):
    return a[0] - d <= b[2] and b[0] - d <= a[2] and a[1] - d <= b[3] and b[1] - d <= a[3]


def center(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def dims(b):
    return (b[2] - b[0], b[3] - b[1])


def g(v):
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('', '-0') else s


def natkey(n):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', n)]


def front(p):
    return any(l in ('F.Cu', '*.Cu') for l in p['layers'])


# ---- footprint model ------------------------------------------------------------------------
class Footprint:
    def __init__(self, text, label):
        self.label = label
        root = parse(text)
        self.name = root[1]
        self.fp_margin = {k: num(kid(root, k)[1]) if kid(root, k) else None
                          for k in ('solder_mask_margin', 'solder_paste_margin', 'solder_paste_ratio')}
        self.pads = []
        self.graphics = []
        self.texts = []
        for c in root:
            if not isinstance(c, list):
                continue
            if c[0] == 'pad':
                self.pads.append(self.read_pad(c))
            elif c[0] in ('fp_line', 'fp_rect', 'fp_poly', 'fp_circle', 'fp_arc'):
                self.graphics.append(self.read_graphic(c))
            elif c[0] in ('property', 'fp_text') and kid(c, 'layer'):
                self.texts.append(self.read_text(c))
        m = kid(root, 'model')
        self.model = m[1] if m else None
        a = kid(root, 'attr')
        self.attr = a[1] if a and len(a) > 1 else None
        v = [c for c in kids(root, 'property') if c[1] == 'Value']
        self.value_hidden = bool(v) and (any(h[1:] == ['yes'] for h in kids(v[0], 'hide'))
                                         or 'hide' in (kid(v[0], 'effects') or []))
        self.derive()

    def read_pad(self, c):
        p = {'num': c[1], 'kind': c[2], 'shape': c[3]}
        p['x'], p['y'] = xy(c, 'at')
        at = kid(c, 'at')
        p['rot'] = num(at[3]) if len(at) > 3 else 0.0
        p['w'], p['h'] = xy(c, 'size')
        p['layers'] = kid(c, 'layers')[1:]
        d = kid(c, 'drill')
        p['drill'] = None
        p['drill_oval'] = False
        ox = oy = 0.0
        if d:
            vals = [v for v in d[1:] if not isinstance(v, list)]
            if vals and vals[0] == 'oval':
                p['drill'] = (num(vals[1]), num(vals[2]) if len(vals) > 2 else num(vals[1]))
                p['drill_oval'] = True
            elif vals:
                p['drill'] = (num(vals[0]), num(vals[0]))
            if kid(d, 'offset'):
                ox, oy = xy(d, 'offset')
        p['props'] = {v for pr in kids(c, 'property') for v in pr[1:]}
        z = kid(c, 'zone_connect')
        p['zone'] = int(z[1]) if z else None
        rr = kid(c, 'roundrect_rratio')
        p['ratio'] = num(rr[1]) if rr else None

        def margin(key, fp_key):
            k = kid(c, key)
            if k:
                return num(k[1])
            return self.fp_margin.get(fp_key)
        p['mask_margin'] = margin('solder_mask_margin', 'solder_mask_margin')
        p['paste_margin'] = margin('solder_paste_margin', 'solder_paste_margin') or 0.0
        p['paste_ratio'] = margin('solder_paste_margin_ratio', 'solder_paste_ratio') or 0.0

        def place(pts):
            """Pad-local points (shape offset applied) to footprint coordinates."""
            out = []
            for x, y in pts:
                rx, ry = rot_pt(x + ox, y + oy, p['rot'])
                out.append((p['x'] + rx, p['y'] + ry))
            return out

        w, h = p['w'], p['h']
        shape = p['shape']
        if shape == 'circle':
            local = circle_pts(0, 0, w / 2)          # KiCad draws a circle from the x size
        elif shape == 'oval':
            local = rrect_poly(w, h, min(w, h) / 2, 6)
        elif shape == 'roundrect':
            local = rrect_poly(w, h, (p['ratio'] or 0) * min(w, h))
        elif shape == 'custom':
            opts = kid(c, 'options')
            anc = kid(opts, 'anchor') if opts else None
            local = circle_pts(0, 0, w / 2) if anc and anc[1] == 'circle' else rrect_poly(w, h, 0)
        else:
            local = rrect_poly(w, h, 0)
        pieces = []
        prims = kid(c, 'primitives')
        for pr_ in (prims[1:] if prims else []):
            if not isinstance(pr_, list):
                continue
            wd = kid(pr_, 'width')
            st = kid(pr_, 'stroke')
            sw = num(wd[1]) if wd else (num(kid(st, 'width')[1]) if st and kid(st, 'width') else 0.0)
            if pr_[0] == 'gr_poly':
                pts = poly_pts(pr_)
                pieces.append(pts)
                if sw > 0:
                    pieces += [thick_seg(pts[i], pts[(i + 1) % len(pts)], sw) for i in range(len(pts))]
            elif pr_[0] == 'gr_rect':
                pieces.append(rect_poly(box_of([xy(pr_, 'start'), xy(pr_, 'end')], sw / 2)))
            elif pr_[0] == 'gr_circle':
                cx, cy = xy(pr_, 'center')
                ex, ey = xy(pr_, 'end')
                pieces.append(circle_pts(cx, cy, math.hypot(ex - cx, ey - cy) + sw / 2))
            elif pr_[0] == 'gr_line':
                pieces.append(thick_seg(xy(pr_, 'start'), xy(pr_, 'end'), max(sw, 1e-4)))
            elif pr_[0] == 'gr_arc':
                pts = arc_pts(xy(pr_, 'start'), xy(pr_, 'mid'), xy(pr_, 'end'))
                pieces += [thick_seg(pts[i], pts[i + 1], max(sw, 1e-4)) for i in range(len(pts) - 1)]
        p['polys'] = [place(local)] + [place(pc) for pc in pieces]
        p['box'] = box_of([pt for poly in p['polys'] for pt in poly])
        p['pieces'] = [box_of(poly) for poly in p['polys']]
        p['cu'] = any(l.endswith('.Cu') for l in p['layers']) and p['kind'] != 'np_thru_hole'
        p['paste'] = 'F.Paste' in p['layers']
        return p

    @staticmethod
    def read_text(c):
        """Property or fp_text: text, layer, hidden, font size (h, w), thickness, at (x, y, rot)."""
        eff = kid(c, 'effects') or []
        font = kid(eff, 'font') or []
        size = xy(font, 'size') or (1.27, 1.27)
        th = kid(font, 'thickness')
        at = kid(c, 'at')
        hidden = (any(h[1:] == ['yes'] for h in kids(c, 'hide') + kids(eff, 'hide'))
                  or 'hide' in c or 'hide' in eff)
        return {'text': c[2], 'layer': kid(c, 'layer')[1], 'hidden': hidden, 'size': size,
                'thick': num(th[1]) if th else min(size) / 8,   # KiCad's default pen
                'auto': not th,
                'at': (num(at[1]), num(at[2]),   # older files write (at x y unlocked)
                       num(at[3]) if len(at) > 3 and re.match(r'-?[\d.]+$', at[3]) else 0.0)}

    def read_graphic(self, c):
        gr = {'type': c[0], 'layer': kid(c, 'layer')[1]}
        st = kid(c, 'stroke')
        wd = kid(st, 'width') if st else kid(c, 'width')
        gr['width'] = num(wd[1]) if wd else 0.0
        f = kid(c, 'fill')
        gr['filled'] = bool(f) and f[1] in ('yes', 'solid')
        segs = []
        if c[0] == 'fp_line':
            pts = [xy(c, 'start'), xy(c, 'end')]
            segs = [(pts[0], pts[1])]
        elif c[0] == 'fp_rect':
            (x0, y0), (x1, y1) = xy(c, 'start'), xy(c, 'end')
            pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            segs = [(pts[i], pts[(i + 1) % 4]) for i in range(4)]
        elif c[0] == 'fp_poly':
            pts = poly_pts(c)
            segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        elif c[0] == 'fp_circle':
            (cx, cy), (ex, ey) = xy(c, 'center'), xy(c, 'end')
            pts = circle_pts(cx, cy, math.hypot(ex - cx, ey - cy), 24)
            segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        else:   # fp_arc
            pts = arc_pts(xy(c, 'start'), xy(c, 'mid'), xy(c, 'end'))
            segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        gr['pts'] = pts
        gr['segs'] = segs
        # points as written (an arc's mid point is off the grid by nature)
        gr['raw'] = pts if c[0] == 'fp_poly' else [xy(c, k) for k in ('start', 'end', 'center') if kid(c, k)]
        gr['box'] = box_of(pts, gr['width'] / 2)
        return gr

    def derive(self):
        smd = [p for p in self.pads if p['cu'] and p['kind'] == 'smd' and p['num'] and front(p)]
        tht = [p for p in self.pads if p['kind'] == 'thru_hole']
        area = lambda p: (p['box'][2] - p['box'][0]) * (p['box'][3] - p['box'][1])
        med = sorted(area(p) for p in smd)[len(smd) // 2] if smd else 0

        def has_vias(p):
            return any(v['num'] == p['num'] and p['box'][0] < v['x'] < p['box'][2]
                       and p['box'][1] < v['y'] < p['box'][3] for v in tht)
        def among(p):
            """Center inside the spread of the other pad centers (not a side mounting pad)."""
            o = [q for q in smd if q['num'] != p['num']]
            return (len(o) > 1 and min(q['x'] for q in o) < p['x'] < max(q['x'] for q in o)
                    and min(q['y'] for q in o) < p['y'] < max(q['y'] for q in o))
        self.eps = [p for p in smd if p['shape'] == 'custom' or 'pad_prop_heatsink' in p['props']
                    or has_vias(p) or (len(smd) > 2 and area(p) >= 4 * med and among(p))]
        self.vias = [p for p in tht if any(
            e['box'][0] < p['x'] < e['box'][2] and e['box'][1] < p['y'] < e['box'][3] for e in self.eps)]
        self.bottom = [p for p in self.pads if p['kind'] == 'smd' and p['cu'] and not front(p)]
        self.main_pads = [p for p in self.pads if p['cu'] and p not in self.vias]
        self.npth = [p for p in self.pads if p['kind'] == 'np_thru_hole' and p['drill']]
        self.loose_cu = [gr for gr in self.graphics if gr['layer'] in ('F.Cu', 'B.Cu')]
        self.copper = [poly for p in self.pads if p['cu'] and front(p) for poly in p['polys']]
        self.copper += [gr['pts'] if gr['type'] == 'fp_poly' else rect_poly(gr['box'])
                        for gr in self.loose_cu if gr['layer'] == 'F.Cu']
        self.copper_boxes = [box_of(c) for c in self.copper]
        # paste regions: (box, source, corner radius); source 'pad' (copper pad) or 'aperture'
        self.paste = []
        for p in self.pads:
            if not p['paste']:
                continue
            for b in (p['pieces'] if p['shape'] == 'custom' else [p['pieces'][0]]):
                w, h = dims(b)
                mx = p['paste_margin'] + p['paste_ratio'] * w
                my = p['paste_margin'] + p['paste_ratio'] * h
                pb = (b[0] - mx, b[1] - my, b[2] + mx, b[3] + my)
                if pb[2] - pb[0] <= EPS or pb[3] - pb[1] <= EPS:
                    continue  # margin removes the paste
                r = (p['ratio'] or 0) * min(dims(pb)) if p['shape'] == 'roundrect' else 0
                if p['shape'] in ('circle', 'oval'):
                    r = min(dims(pb)) / 2
                self.paste.append((pb, 'pad' if p['cu'] else 'aperture', r))
        for gr in self.graphics:
            if gr['layer'] == 'F.Paste':
                # corner radius, or the outline itself for a drawn polygon
                r = gr['width'] / 2 if gr['type'] == 'fp_line' else (
                    gr['pts'] if gr['type'] == 'fp_poly' and gr['width'] == 0 else 0)
                self.paste.append((gr['box'], 'aperture', r))
        crt = [gr for gr in self.graphics if gr['layer'] == 'F.CrtYd']
        self.crtyd = box_of([pt for gr in crt for pt in gr['pts']]) if crt else None
        self.crtyd_pts = [pt for gr in crt for pt in gr['pts']
                          if gr['type'] in ('fp_line', 'fp_rect', 'fp_poly')]
        # fab outline: the body, without the pin 1 marks (filled shapes, circles, lines with a free end)
        fab = [gr for gr in self.graphics if gr['layer'] == 'F.Fab' and gr['type'] != 'fp_circle'
               and not gr['filled']]
        # an outline end meets another line end within 0.05 mm (hand-drawn outlines leave small gaps)
        ends = [pt for gr in fab if gr['type'] == 'fp_line' for pt in gr['pts']]
        joined = lambda pt: sum(math.hypot(pt[0] - q[0], pt[1] - q[1]) <= 0.05 for q in ends) > 1
        body = [gr for gr in fab if gr['type'] != 'fp_line' or all(joined(pt) for pt in gr['pts'])]
        fab = body or fab
        self.fab = box_of([pt for gr in fab for pt in gr['pts']]) if fab else None
        self.silk = [gr for gr in self.graphics if gr['layer'] == 'F.SilkS']


# ---- report ---------------------------------------------------------------------------------
def compress(nums):
    nums = sorted(nums, key=natkey)
    if nums and all(n.isdigit() for n in nums):
        out, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and int(nums[j + 1]) == int(nums[j]) + 1:
                j += 1
            out.append(nums[i] if i == j else f'{nums[i]}-{nums[j]}')
            i = j + 1
        return ','.join(out)
    nums = [n or '""' for n in nums]
    return ','.join(nums) if len(nums) <= 12 else f'{nums[0]}..{nums[-1]} ({len(nums)})'


def table(fp):
    print(f'== {fp.label}: {fp.name}')
    groups = {}
    for p in fp.main_pads:
        w, h = dims(p['box'])
        key = (p['kind'], p['shape'], g(w), g(h), p['drill'], p['ratio'], tuple(p['layers']))
        groups.setdefault(key, []).append(p)
    for (kind, shape, w, h, drill, ratio, layers), ps in groups.items():
        xs = sorted({g(p['x']) for p in ps}, key=float)
        ys = sorted({g(p['y']) for p in ps}, key=float)
        extra = f' drill {g(drill[0])}x{g(drill[1])}' if drill else ''
        extra += f' r{g(ratio)}' if ratio is not None else ''
        extra += '' if any(l in ('F.Cu', '*.Cu') for l in layers) else f' {"/".join(layers)}'
        print(f'  pads {compress([p["num"] for p in ps])}: {kind} {shape} {w}x{h}{extra}'
              f'  x={",".join(xs[:8])}{"..." if len(xs) > 8 else ""}'
              f'  y={",".join(ys[:8])}{"..." if len(ys) > 8 else ""}')
    for v in fp.vias:
        print(f'  via {v["num"]} at ({g(v["x"])}, {g(v["y"])}) pad {g(v["w"])} drill {g(v["drill"][0])}')
    for h in fp.npth:
        print(f'  npth at ({g(h["x"])}, {g(h["y"])}) drill {g(h["drill"][0])}x{g(h["drill"][1])}')
    for b, src, _ in fp.paste:
        if src == 'aperture':
            c, d = center(b), dims(b)
            print(f'  paste aperture at ({g(c[0])}, {g(c[1])}) {g(d[0])}x{g(d[1])}')
    if fp.crtyd:
        print(f'  courtyard x[{g(fp.crtyd[0])}, {g(fp.crtyd[2])}] y[{g(fp.crtyd[1])}, {g(fp.crtyd[3])}]')
    if fp.fab:
        print(f'  fab outline {g(dims(fp.fab)[0])}x{g(dims(fp.fab)[1])}')
    print(f'  model {fp.model}')


def text_box(t):
    """Estimated outline of a centered text: CHAR_ADV x width per character, plus the pen."""
    h, w = t['size']
    hw = len(t['text']) * MF.CHAR_ADV * w / 2 + t['thick'] / 2
    hh = h / 2 + t['thick'] / 2
    if round(t['at'][2]) % 180 == 90:
        hw, hh = hh, hw
    x, y = t['at'][:2]
    return (x - hw, y - hh, x + hw, y + hh)


def silk_dfm(fp):
    """DFM house rules: silkscreen lines >= 0.15 mm (a filled pin 1 mark over 0.15 mm across may
    use 0.1 mm), visible silkscreen text >= 1 x 1 mm and 0.15 mm thick, text >= 0.15 mm from copper."""
    out = []
    bad = {}
    for gr in fp.silk:
        mark = gr['filled'] and gr['type'] in ('fp_poly', 'fp_circle')
        need = MARK_MIN_WIDTH if mark and max(dims(gr['box'])) > MARK_MIN_SIZE + EPS else SILK_MIN_WIDTH
        if gr['width'] < need - 0.001:
            k = f'{"filled pin 1 mark" if mark else gr["type"]} {g(gr["width"])} mm (needs {g(need)})'
            bad[k] = bad.get(k, 0) + 1
    if bad:
        out.append('WARN  silkscreen line width under the DFM minimum: '
                   + '; '.join(f'{n}x {k}' for k, n in bad.items()))
    elif fp.silk:
        out.append(f'PASS  silkscreen lines >= {g(SILK_MIN_WIDTH)} mm (pin 1 mark >= {g(MARK_MIN_WIDTH)})')
    if any(gr['type'] == 'fp_circle' and gr['filled'] for gr in fp.silk):
        out.append('WARN  filled dot on silkscreen; the house pin 1 mark is an arrow (+ for polarized SMD capacitors)')
    c = fp.crtyd
    if c and any(gr['filled'] and not (c[0] - 0.001 <= gr['box'][0] and gr['box'][2] <= c[2] + 0.001
                                       and c[1] - 0.001 <= gr['box'][1] and gr['box'][3] <= c[3] + 0.001)
                 for gr in fp.silk):
        out.append('WARN  pin 1 silk mark outside the courtyard (KLC F5.1)')
    for t in fp.texts:
        if not t['layer'].endswith('.SilkS') or t['hidden']:
            continue
        h, w = t['size']
        name = f'silkscreen text "{t["text"]}" {g(h)}x{g(w)} mm, {g(t["thick"])} thick'
        if min(h, w) < SILK_MIN_TEXT - 0.001 or t['thick'] < SILK_MIN_WIDTH - 0.001:
            out.append(f'WARN  {name}: DFM needs >= {g(SILK_MIN_TEXT)}x{g(SILK_MIN_TEXT)} mm, '
                       f'>= {g(SILK_MIN_WIDTH)} thick')
        else:
            out.append(f'PASS  {name}')
        tb = text_box(t)
        gap = min((0.0 if overlap(tb, cb) else poly_poly_dist(rect_poly(tb), c)
                   for c, cb in zip(fp.copper, fp.copper_boxes) if near(cb, tb, 1.0)), default=None)
        if gap is not None and gap < SILK_MIN_CLEARANCE - 0.001:
            out.append(f'WARN  silkscreen text "{t["text"]}" about {g(gap)} mm from copper (estimated text box; '
                       f'DFM {g(SILK_MIN_CLEARANCE)} mm)')
    return out


def graphic_grid(fp):
    """House rule: F.SilkS and F.Fab points and text positions on the 0.05 mm grid (INFO)."""
    G = MF.GRAPHIC_GRID
    off = lambda v: abs(v / G - round(v / G)) > 1e-4
    bad = {}
    for gr in fp.graphics:
        if gr['layer'] in ('F.SilkS', 'F.Fab') and any(off(x) or off(y) for x, y in gr['raw']):
            bad[gr['layer']] = bad.get(gr['layer'], 0) + 1
    for t in fp.texts:
        if t['layer'] in ('F.SilkS', 'F.Fab') and not t['hidden'] and (off(t['at'][0]) or off(t['at'][1])):
            bad[t['layer']] = bad.get(t['layer'], 0) + 1
    if bad:
        return [f'INFO  off the {g(G)} mm grid (house rule): '
                + ', '.join(f'{n} {k} item(s)' for k, n in sorted(bad.items()))]
    return [f'PASS  silkscreen and fab on the {g(G)} mm grid']


def fab_reference(fp):
    """House rule: ${REFERENCE} on F.Fab 1 x 1 mm and 0.1 mm thick; smaller only when the body has
    no room for 5 characters, then no bigger than fab_text() of the fab outline."""
    refs = [t for t in fp.texts if t['layer'] == 'F.Fab' and t['text'] == '${REFERENCE}']
    if not refs:
        return ['WARN  no ${REFERENCE} text on F.Fab (KLC F5.2)']
    t = refs[0]
    h, w = t['size']
    fit, _ = MF.fab_text(*dims(fp.fab)) if fp.fab else (MF.FAB_TEXT, MF.FAB_TEXT_WIDTH)
    name = f'F.Fab ${{REFERENCE}} {g(h)}x{g(w)} mm, {g(t["thick"])} thick'
    if round(t['at'][2]) % 180 == 90:   # turned along a tall body (SOT-23): any size that fits
        fit = MF.fab_text(*reversed(dims(fp.fab)))[0] if fp.fab else MF.FAB_TEXT
        ok = max(h, w) <= fit + 0.001 and t['thick'] <= MF.FAB_TEXT_WIDTH + 0.001
        return [f'{"PASS" if ok else "WARN"}  {name}, turned 90 deg (at most {g(fit)} mm to fit, <= '
                f'{g(MF.FAB_TEXT_WIDTH)} thick)']
    if abs(h - w) > 0.001 and max(h, w) <= max(fit, MF.FAB_TEXT) + 0.001:
        # height and width set apart on purpose, to tell the footprint apart at a glance
        return [f'INFO  {name} (height and width differ: hand-set style, not checked)']
    if fit >= MF.FAB_TEXT:
        ok = (abs(h - MF.FAB_TEXT) < 0.001 and abs(w - MF.FAB_TEXT) < 0.001
              and abs(t['thick'] - MF.FAB_TEXT_WIDTH) < 0.001)
        need = f'house rule {g(MF.FAB_TEXT)}x{g(MF.FAB_TEXT)} mm, {g(MF.FAB_TEXT_WIDTH)} thick'
    else:
        # 0.05 mm over the fit is fine on tiny parts (stock 0402 text is 0.17 for a 0.15 fit)
        ok = max(h, w) <= fit + 0.05 + 0.001 and t['thick'] <= MF.FAB_TEXT_WIDTH + 0.001
        need = f'small body: at most {g(fit)} mm (+0.05) to fit, <= {g(MF.FAB_TEXT_WIDTH)} thick'
    return [f'{"PASS" if ok else "WARN"}  {name} ({need})']


def checks(fp, stencil, crt_req):
    out = []

    def say(kind, msg):
        out.append(f'{kind}  {msg}')

    sq = [p['num'] or 'paste' for p in fp.pads
          if p['shape'] == 'rect' and p not in fp.eps and p not in fp.bottom]
    if sq:
        say('WARN', f'square pad corners: {compress([n for n in sq if n != "paste"]) or ""}'
            f'{" +%d paste apertures" % sq.count("paste") if "paste" in sq else ""}'
            ' (use roundrect, ratio 0.1 to 0.25)')
    else:
        say('PASS', 'no square pad corners (exposed and B.Cu pads may stay square)')
    say('PASS' if fp.value_hidden else 'WARN',
        'Value property hidden' if fp.value_hidden else 'Value property visible (set hide yes)')

    worst = []
    for b, src, r in fp.paste:
        if src != 'aperture':
            continue
        over = 0.0
        cand = [c for c, cb in zip(fp.copper, fp.copper_boxes) if near(cb, b, 0.5)]
        cx, cy = center(b)
        poly = r if isinstance(r, list) else [(cx + x, cy + y) for x, y in rrect_poly(*dims(b), r, 4)]
        for x, y in poly:
            d = min((poly_dist(x, y, c) for c in cand), default=1e9)
            over = max(over, d)
        if over > 0.002:
            c, d = center(b), dims(b)
            worst.append(f'({g(c[0])}, {g(c[1])}) {g(d[0])}x{g(d[1])} by {g(over)} mm')
    if worst:
        say('WARN', f'paste outside copper: {"; ".join(worst)}')
    else:
        say('PASS', 'all paste inside copper')

    for e in fp.eps:
        ca = poly_union_area(e['polys'])
        pb = [b for b, _, _ in fp.paste if e['box'][0] - EPS <= center(b)[0] <= e['box'][2] + EPS
              and e['box'][1] - EPS <= center(b)[1] <= e['box'][3] + EPS]
        pa = union_area(pb)
        if not ca:
            say('WARN', f'exposed pad {e["num"]}: no area')
            continue
        cov = pa / ca
        kind = 'INFO' if 0.5 <= cov <= 0.8 else 'WARN'
        say(kind, f'exposed pad {e["num"]}: copper {g(ca)} mm2, paste {g(pa)} mm2, coverage {100 * cov:.1f}%'
            + ('' if kind == 'INFO' else ' (KLC F6.3: 50 to 80%, unless the datasheet says otherwise)'))
        others = [p for p in fp.main_pads if p['num'] != e['num'] and front(p)
                  and near(p['box'], e['box'], 0.5)]
        gap = min((poly_poly_dist(a, b) for p in others for a in e['polys'] for b in p['polys']),
                  default=None)
        if gap is not None and gap < 0.2 - 0.001:
            say('WARN', f'exposed pad {e["num"]} is {g(gap)} mm from another pad (KLC F6.3: >= 0.2 mm)')
        if 'pad_prop_heatsink' not in e['props'] or e['zone'] != 2:
            say('WARN', f'exposed pad {e["num"]}: set heatsink fab property and solid zone connection (KLC F6.3)')
    for v in fp.vias:
        r = v['drill'][0] / 2
        hole = (v['x'] - r, v['y'] - r, v['x'] + r, v['y'] + r)
        if any(overlap(hole, b) for b, _, _ in fp.paste):
            if v['drill'][0] >= 0.3 - EPS:
                say('WARN', f'via at ({g(v["x"])}, {g(v["y"])}) drill {g(v["drill"][0])} is under paste '
                    '(KLC F4.4.3: plug it or move the aperture)')
            else:
                say('INFO', f'via at ({g(v["x"])}, {g(v["y"])}) drill {g(v["drill"][0])} is under paste '
                    '(allowed under 0.3 mm, KLC F4.4.3)')
        owner = [e for e in fp.eps if e['box'][0] < v['x'] < e['box'][2]
                 and e['box'][1] < v['y'] < e['box'][3]]
        if owner and owner[0]['num'] != v['num']:
            say('WARN', f'via at ({g(v["x"])}, {g(v["y"])}) has number "{v["num"]}", '
                f'exposed pad is "{owner[0]["num"]}" (KLC F4.3)')
    if fp.vias:
        bad = [v for v in fp.vias if 'pad_prop_heatsink' not in v['props']]
        if bad:
            say('WARN', f'{len(bad)} thermal via(s) without the heatsink fab property (KLC F6.3)')
        nums = {v['num'] for v in fp.vias}
        if not any(b['num'] in nums for b in fp.bottom):
            say('WARN', 'thermal vias have no B.Cu pad (KLC F4.4.2, unless the datasheet says otherwise)')
    if fp.loose_cu:
        say('WARN', f'{len(fp.loose_cu)} copper graphic(s) are not part of a pad (no net)')

    if not fp.crtyd:
        say('WARN', 'no courtyard')
    else:
        ext = [b for p in fp.pads if p['cu'] and front(p) for b in p['pieces']]
        if fp.fab:
            ext.append(fp.fab)
        if ext:
            e = (min(b[0] for b in ext), min(b[1] for b in ext),
                 max(b[2] for b in ext), max(b[3] for b in ext))
            c = fp.crtyd
            margin = min(e[0] - c[0], e[1] - c[1], c[2] - e[2], c[3] - e[3])
            size = dims(fp.fab) if fp.fab else dims(e)
            req = crt_req if crt_req is not None else (0.15 if max(size) < 1.5 else 0.25)
            if margin < req - 0.001:
                say('WARN', f'courtyard clearance {g(margin)} mm, needs {g(req)} mm (KLC F5.3)')
            else:
                say('PASS', f'courtyard clearance {g(margin)} mm (needs {g(req)})')
        off = [pt for pt in fp.crtyd_pts
               if abs(pt[0] * 100 - round(pt[0] * 100)) > 1e-4
               or abs(pt[1] * 100 - round(pt[1] * 100)) > 1e-4]
        if off:
            say('WARN', 'courtyard not on the 0.01 mm grid')

    if fp.silk:
        worst, need = 1e9, 0.0
        mm = max([p['mask_margin'] or 0 for p in fp.pads if p['cu']] + [0])
        for gr in fp.silk:
            for a, b in gr['segs']:
                sb = box_of([a, b])
                for c, cb in zip(fp.copper, fp.copper_boxes):
                    if near(cb, sb, 1.0):
                        d = seg_poly_dist(a, b, c) - gr['width'] / 2
                        if d < worst:
                            worst, need = d, max(gr['width'], mm)
            if gr['filled'] and gr['pts']:
                for c in fp.copper:
                    if any(poly_contains(x, y, gr['pts']) for x, y in c[:1]):
                        worst, need = min(worst, -gr['width'] / 2), max(gr['width'], mm)
        need = max(need, SILK_MIN_CLEARANCE)
        if worst >= 1e8:
            say('PASS', 'silkscreen to copper > 1 mm')
        elif worst < need - 0.001:
            say('WARN', f'silkscreen to copper {g(worst)} mm, needs at least {g(need)} mm '
                f'(DFM {g(SILK_MIN_CLEARANCE)} mm; KLC F5.1 line width and mask margin)')
        elif worst < 0.2 - 0.001:
            say('INFO', f'silkscreen to copper {g(worst)} mm, KLC recommends 0.2 mm')
        else:
            say('PASS', f'silkscreen to copper {g(worst)} mm')
    else:
        say('WARN', 'no silkscreen')
    out += silk_dfm(fp) + fab_reference(fp) + graphic_grid(fp)
    auto = [t['text'] for t in fp.texts if t['auto']]
    if auto:   # house rule: every text states its thickness
        say('WARN', f'{len(auto)} text(s) with auto thickness: {", ".join(sorted(set(auto))[:5])}')

    p1 = next((p for p in fp.main_pads if p['num'] in ('1', 'A1')), None)
    if p1 is None:
        say('INFO', 'no pad 1 or A1')
    elif p1['x'] > 0.001 or p1['y'] > 0.001:
        say('WARN', f'pad {p1["num"]} at ({g(p1["x"])}, {g(p1["y"])}) is not top left (KLC F4.2)')
    else:
        say('PASS', f'pad {p1["num"]} at the top left')

    thin = []
    for p in fp.pads:
        if p['kind'] == 'thru_hole' and p['drill']:
            w, h = (p['h'], p['w']) if round(p['rot']) % 180 == 90 else (p['w'], p['h'])
            ring = min(w - p['drill'][0], h - p['drill'][1]) / 2
            if p['shape'] == 'circle':
                ring = (p['w'] - max(p['drill'])) / 2
            if ring < 0.15 - 0.001:
                thin.append(f'{p["num"] or "?"} {g(ring)}')
    if thin:
        say('WARN', f'annular ring < 0.15 mm (KLC F7.5): {", ".join(thin[:6])}')
    tht = [p for p in fp.main_pads if p['kind'] == 'thru_hole']
    if tht and p1 is not None and p1['kind'] == 'thru_hole':
        others = {p['shape'] for p in tht if p['num'] != p1['num']}
        if p1['shape'] not in ('rect', 'roundrect') or others - {'circle', 'oval'}:
            say('INFO', f'THT pin 1 is {p1["shape"]}, others {"/".join(sorted(others)) or "none"} '
                '(KLC F7.3: pin 1 rect or roundrect, others circle or oval, unless non-polarized)')

    bad = {}
    for b, _, _ in fp.paste:
        w, h = dims(b)
        if w <= 0 or h <= 0:
            continue
        ar = w * h / (2 * (w + h) * stencil)
        asp = min(w, h) / stencil
        if ar < 0.66 or asp < 1.5:
            fails = (([f'area ratio {ar:.2f} < 0.66'] if ar < 0.66 else [])
                     + ([f'aspect {asp:.2f} < 1.5'] if asp < 1.5 else []))
            bad.setdefault(f'{g(min(w, h))}x{g(max(w, h))} ({", ".join(fails)})', []).append(b)
    if bad:
        say('WARN', f'stencil {g(stencil)} mm: {sum(len(v) for v in bad.values())} aperture(s) '
            'fail IPC-7525: ' + '; '.join(f'{len(v)}x {k}' for k, v in bad.items()))
    else:
        say('PASS', f'stencil {g(stencil)} mm: all apertures area ratio >= 0.66, aspect >= 1.5')
    return out


SHAPE_CLASS = {'rect': 'rect', 'roundrect': 'rect', 'trapezoid': 'rect', 'circle': 'round',
               'oval': 'round', 'custom': 'custom'}


def compare(a, b, tol):
    out = []
    recs = []   # (kind, name, group key, text): grouped into DIFF / INFO lines at the end

    def note(kind, name, key, text, level='DIFF'):
        recs.append((level, kind, name, key, text))

    def same(x, y):
        return abs(x - y) <= tol + EPS

    def shape(k):
        return tuple(sorted(round(v, 3) for v in k[2:]))

    def pair(la, lb, what, fmt, keyf, name=''):
        """Match closest pairs first (over both lists, so one extra item does not shift the
        rest). Vias, holes and paste more than 1 mm from any partner are reported as only in
        one footprint; pads with the same number are paired at any distance."""
        la = sorted(la, key=keyf)
        lb = sorted(lb, key=keyf)
        grid = {}
        for j, y in enumerate(lb):
            grid.setdefault((math.floor(keyf(y)[0]), math.floor(keyf(y)[1])), []).append(j)
        cand = []
        for i, x in enumerate(la):
            kx = keyf(x)
            cx, cy = math.floor(kx[0]), math.floor(kx[1])
            for gx in (cx - 1, cx, cx + 1):
                for gy in (cy - 1, cy, cy + 1):
                    for j in grid.get((gx, gy), ()):
                        ky = keyf(lb[j])
                        d = math.hypot(kx[0] - ky[0], kx[1] - ky[1])
                        if d <= 1.0:
                            size = sum(abs(u - v) for u, v in zip(kx[2:], ky[2:]))
                            cand.append((round(d, 6), size, i, j))
        cand.sort()
        if name:   # same pad number: leftovers are the same pad, however far it moved
            far = []
            for i, x in enumerate(la):
                for j, y in enumerate(lb):
                    d = math.hypot(keyf(x)[0] - keyf(y)[0], keyf(x)[1] - keyf(y)[1])
                    if d > 1.0:
                        far.append((round(d, 6), 0, i, j))
            cand += sorted(far)
        ua, ub, pairs = set(), set(), []
        for d, _, i, j in cand:
            if i in ua or j in ub:
                continue
            ua.add(i)
            ub.add(j)
            x, y = la[i], lb[j]
            pairs.append((x, y))
            if not all(same(u, v) for u, v in zip(keyf(x), keyf(y))):
                note(what, name, (shape(keyf(x)), shape(keyf(y)), round(d, 3)),
                     f'{a.label} {fmt(x)} / {b.label} {fmt(y)}')
        for i, x in enumerate(la):
            if i not in ua:
                note(what, name, ('only', a.label, shape(keyf(x))), f'{fmt(x)} only in {a.label}')
        for j, y in enumerate(lb):
            if j not in ub:
                note(what, name, ('only', b.label, shape(keyf(y))), f'{fmt(y)} only in {b.label}')
        return pairs

    def padkey(p):
        c, d = center(p['box']), dims(p['box'])
        return (c[0], c[1], d[0], d[1])

    def padfmt(p):
        c, d = center(p['box']), dims(p['box'])
        side = '' if front(p) else ' ' + '/'.join(l for l in p['layers'] if l.endswith('.Cu'))
        return f'({g(c[0])}, {g(c[1])}) {g(d[0])}x{g(d[1])}{side}'

    def attrs(x, y, n):
        def put(what, va, vb, level='DIFF'):
            note('pad ' + what, n, (what, str(va), str(vb)), f'{a.label} {va} / {b.label} {vb}', level)
        if x['kind'] != y['kind']:
            put('type', x['kind'], y['kind'])
        dx, dy = x['drill'], y['drill']
        if (dx is None) != (dy is None) or (dx and (not all(same(u, v) for u, v in zip(dx, dy))
                                                    or x['drill_oval'] != y['drill_oval'])):
            put('drill', f'{"oval " if x["drill_oval"] else ""}{dx}', f'{"oval " if y["drill_oval"] else ""}{dy}')
        if sorted(x['layers']) != sorted(y['layers']):
            put('layers', ' '.join(sorted(x['layers'])), ' '.join(sorted(y['layers'])))
        if not same(x['mask_margin'] or 0, y['mask_margin'] or 0):
            put('mask margin', x['mask_margin'] or 0, y['mask_margin'] or 0)
        if SHAPE_CLASS.get(x['shape']) != SHAPE_CLASS.get(y['shape']):
            put('shape', x['shape'], y['shape'])
        elif x['shape'] != y['shape'] or not same(x['ratio'] or 0, y['ratio'] or 0):
            put('corner', f'{x["shape"]} {x["ratio"] or ""}'.strip(), f'{y["shape"]} {y["ratio"] or ""}'.strip(), 'INFO')
        if x['props'] != y['props'] or x['zone'] != y['zone']:
            put('fab property', f'{"/".join(sorted(x["props"])) or "-"} zone {x["zone"]}',
                f'{"/".join(sorted(y["props"])) or "-"} zone {y["zone"]}', 'INFO')
        if 'custom' in (x['shape'], y['shape']):
            ax, bx = poly_union_area(x['polys']), poly_union_area(y['polys'])
            if abs(ax - bx) > 0.02 * max(ax, bx):
                put('copper area', f'{g(ax)} mm2', f'{g(bx)} mm2')

    nums = sorted({p['num'] for p in a.main_pads} | {p['num'] for p in b.main_pads}, key=natkey)
    for n in nums:
        pa = [p for p in a.main_pads if p['num'] == n]
        pb = [p for p in b.main_pads if p['num'] == n]
        for x, y in pair(pa, pb, 'pad', padfmt, padkey, name=n or '""'):
            attrs(x, y, n or '""')
    vf = lambda v: f'({g(v["x"])}, {g(v["y"])}) pad {g(v["w"])} drill {g(v["drill"][0])}'
    pair(a.vias, b.vias, 'via', vf, lambda v: (v['x'], v['y'], v['w'], v['drill'][0]))
    pair(a.npth, b.npth, 'npth',
         lambda h: f'({g(h["x"])}, {g(h["y"])}) drill {g(h["drill"][0])}x{g(h["drill"][1])}',
         lambda h: (h['x'], h['y'], h['drill'][0], h['drill'][1]))
    pair([x[0] for x in a.paste], [x[0] for x in b.paste], 'paste',
         lambda bx: f'({g(center(bx)[0])}, {g(center(bx)[1])}) {g(dims(bx)[0])}x{g(dims(bx)[1])}',
         lambda bx: (*center(bx), *dims(bx)))
    groups = {}
    for level, kind, name, key, text in recs:
        groups.setdefault((level, kind, key), []).append((name, text))
    for (level, kind, _), items in sorted(groups.items(), key=lambda kv: kv[0][0]):
        names = [nm for nm, _ in items if nm]
        label = f'{kind} {compress(names)}' if names else kind
        if len(items) == 1:
            out.append(f'{level}  {label}: {items[0][1]}')
        else:
            eg = f'{items[0][0]}: ' if items[0][0] else ''
            out.append(f'{level}  {label} ({len(items)}x), e.g. {eg}{items[0][1]}')
    for what, x, y in (('courtyard', a.crtyd, b.crtyd), ('fab outline', a.fab, b.fab)):
        if x and y and not all(same(u, v) for u, v in zip(x, y)):
            out.append(f'INFO  {what}: {a.label} {[g(v) for v in x]} / {b.label} {[g(v) for v in y]}')
    if a.model != b.model:
        out.append(f'INFO  model: {a.label} {a.model} / {b.label} {b.model}')
    if not any(l.startswith('DIFF') for l in out):
        out.insert(0, f'PASS  pads, vias, holes and paste match within {g(tol)} mm')
    return out


def load_spec_text(path):
    with open(path, encoding='utf-8') as fh:
        return MF.build_text(json.load(fh))[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('fp')
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument('--ref', help='make_footprint.py spec JSON with the datasheet values')
    grp.add_argument('--vs', help='another .kicad_mod to compare with')
    ap.add_argument('--tol', type=float, default=0.01)
    ap.add_argument('--stencil', type=float, default=0.125, help='stencil thickness, mm')
    ap.add_argument('--courtyard', type=float, help='required courtyard clearance, mm')
    ap.add_argument('--quiet', action='store_true', help='skip the measurement table')
    a = ap.parse_args()
    with open(a.fp, encoding='utf-8') as fh:
        fp = Footprint(fh.read(), os.path.basename(a.fp))
    if not a.quiet:
        table(fp)
    for line in checks(fp, a.stencil, a.courtyard):
        print(line)
    other = None
    if a.ref:
        other = Footprint(load_spec_text(a.ref), 'spec')
    elif a.vs:
        with open(a.vs, encoding='utf-8') as fh:
            other = Footprint(fh.read(), os.path.basename(a.vs))
        if other.label == fp.label:
            other.label = 'other'
    rc = 0
    if other:
        if a.vs and not a.quiet:
            table(other)
        print(f'== compare {fp.label} with {other.label}')
        res = compare(fp, other, a.tol)
        for line in res:
            print(line)
        rc = 1 if any(l.startswith('DIFF') for l in res) else 0
    sys.exit(rc)


if __name__ == '__main__':
    main()
