"""Read-only: compare a project's library with the archive library, to find what a publish should bring over.

Usage:
    python -I lib_diff.py <source library dir> [--root <archive root>] [--lib <library folder>]

The source may use any layout: every *.kicad_symdir/*.kicad_sym, *.pretty/*.kicad_mod and model file
(.step .stp .wrl) under it is checked. The archive is <root>/<lib> (defaults: current folder, "library").

Each item is one of:
  IDENTICAL        same name in the archive, same content (line endings ignored): nothing to do
  DIFFERS          same name in the archive, different content: report, never overwrite
  OTHER NAME       not found by name, but the archive has the same content under another name
                   (name, Value, Footprint and model lines ignored; whole file for models):
                   usually the archive renamed it
  NEW              not in the archive: a map candidate
  PACKED           multi-symbol .kicad_sym library: split it into a .kicad_symdir first
Names are matched case-insensitively and across families. Line endings are ignored everywhere, models
included: STEP and WRL are text, and Git with eol=lf stores them with LF while project copies may be CRLF. For NEW items the Footprint link (symbols)
and model paths (footprints) are printed, to build the map from.
"""
import hashlib, os, re, sys

ARGS = sys.argv[1:]
SRC = ARGS[0]
ROOT = ARGS[ARGS.index('--root') + 1] if '--root' in ARGS else '.'
LIB = ARGS[ARGS.index('--lib') + 1] if '--lib' in ARGS else 'library'
MODEL_EXT = ('.step', '.stp', '.wrl')
NAME_LINE = re.compile(rb'^\s*(\(footprint "|\(symbol "|\(property "Value" "|\(property "Footprint" "|\(model ")')


def scan(top):
    """Return {kind: [(family, name, path)]} for kind in sym, fp, model, packed."""
    out = {'sym': [], 'fp': [], 'model': [], 'packed': []}
    for d, _, files in os.walk(top):
        parent = os.path.basename(d)
        for f in files:
            p = os.path.join(d, f)
            low = f.lower()
            if low.endswith('.kicad_sym'):
                if parent.endswith('.kicad_symdir'):
                    out['sym'].append((parent[:-len('.kicad_symdir')], f[:-len('.kicad_sym')], p))
                else:
                    out['packed'].append(('', f, p))
            elif low.endswith('.kicad_mod') and parent.endswith('.pretty'):
                out['fp'].append((parent[:-len('.pretty')], f[:-len('.kicad_mod')], p))
            elif low.endswith(MODEL_EXT):
                out['model'].append((parent, f, p))
    return out


def raw(p):
    with open(p, 'rb') as f:
        return f.read()


def text(p):
    return raw(p).replace(b'\r\n', b'\n')


def body_hash(p, kind):
    if kind == 'model':  # STEP and WRL are text; Git may store them with LF, so ignore line endings
        return hashlib.sha256(text(p)).hexdigest()
    return hashlib.sha256(b'\n'.join(l for l in text(p).split(b'\n') if not NAME_LINE.match(l))).hexdigest()


def links(p, kind):
    t = text(p).decode('utf-8', 'replace')
    if kind == 'sym':
        return re.findall(r'\(property "Footprint" "([^"]*)"', t)
    if kind == 'fp':
        return re.findall(r'\(model "([^"]*)"', t)
    return []


src, arc = scan(SRC), scan(os.path.join(ROOT, LIB))
rows = {k: [] for k in ('IDENTICAL', 'DIFFERS', 'OTHER NAME', 'NEW', 'PACKED')}
for _, f, p in src['packed']:
    rows['PACKED'].append(('sym', os.path.relpath(p, SRC), ''))
for kind in ('sym', 'fp', 'model'):
    by_name = {}
    for fam, name, p in arc[kind]:
        by_name.setdefault(name.lower(), []).append((fam, p))
    by_hash = {}
    for fam, name, p in arc[kind]:
        by_hash.setdefault(body_hash(p, kind), []).append(f'{fam}:{name}' if kind != 'model' else f'{fam}/{name}')
    for fam, name, p in src[kind]:
        rel = os.path.relpath(p, SRC)
        hits = by_name.get(name.lower(), [])
        if hits:
            same = [h for h in hits if text(h[1]) == text(p)]
            if same:
                note = '' if any(h[0] == fam for h in same) else f'archive family {same[0][0]}'
                rows['IDENTICAL'].append((kind, rel, note))
            else:
                rows['DIFFERS'].append((kind, rel, 'archive: ' + ', '.join(os.path.relpath(h[1], ROOT) for h in hits)))
            continue
        other = by_hash.get(body_hash(p, kind))
        if other:
            rows['OTHER NAME'].append((kind, rel, 'archive: ' + ', '.join(other)))
        else:
            ls = links(p, kind)
            rows['NEW'].append((kind, rel, ('links: ' + ', '.join(ls)) if ls else ''))

print(f'source: {SRC}\narchive: {os.path.join(ROOT, LIB)}')
print('counts: ' + ', '.join(f'{k} {len(v)}' for k, v in rows.items()))
for status in ('NEW', 'OTHER NAME', 'DIFFERS', 'PACKED', 'IDENTICAL'):
    if rows[status]:
        print(f'\n== {status} ==')
        for kind, rel, note in sorted(rows[status]):
            print(f'  [{kind}] {rel}' + (f'  ({note})' if note else ''))
