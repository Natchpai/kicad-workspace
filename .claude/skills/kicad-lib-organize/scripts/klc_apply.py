"""Apply a KLC rename map: move/rename symbols, footprints and 3D models and keep links working.

Usage (from the repo root):
    python -I klc_apply.py <map.json> sym|fp|3d [--dry]

Map format (all paths relative to the repo root, forward slashes):
{
  "symbols":    [{"src": "<path>.kicad_sym", "dst_lib": "0_Diode", "new": "MBRA340"}],
  "footprints": [{"src": "<path>.pretty/<old>.kicad_mod", "dst_lib": "0_Package_SO", "new": "SOIC-8_3.9x4.9mm_P1.27mm"}],
  "models":     [{"src": "<path to model>", "dst": "library/3D/<Folder>/<new>.step", "footprint": "0_Lib:<new fp name>"}],
  "link_fixes": {"<old lib:name>": "<new lib:name>"}
}

- sym: renames each symbol file and its internal names (root, unit sub-symbols, Value when equal to the old name).
- fp:  renames each footprint file and its internal name (and Value when equal), then rewrites every symbol
       Footprint property that pointed at "<src .pretty name>:<old name>" (plus link_fixes) across library/symbols.
- 3d:  moves each model to dst (a second entry with the same src copies it, so each footprint owns its file)
       and rewrites the one (model "...") path in that footprint whose file name matches src.
Edits are byte-level, so CRLF/LF line endings are kept. Each edited file is checked: only name, Value,
Footprint and model lines may change. Refuses to overwrite (case-insensitive check); case-only renames go
through a temporary name.
"""
import json, os, re, shutil, sys

MAP = json.load(open(sys.argv[1], encoding='utf-8'))
STEP = sys.argv[2]
DRY = '--dry' in sys.argv
SYM_ROOT = 'library/symbols'
FP_ROOT = 'library/footprints'
ALLOWED = re.compile(rb'^\s*(\(footprint "|\(symbol "|\(property "Value" "|\(property "Footprint" "|\(model ")')
LOG = []


def rd(p):
    with open(p, 'rb') as f:
        return f.read()


def wr(p, old, new):
    a, b = old.splitlines(), new.splitlines()
    if len(a) != len(b) or any(x != y and not (ALLOWED.match(x) and ALLOWED.match(y)) for x, y in zip(a, b)):
        sys.exit(f'UNEXPECTED EDIT in {p}: only name/Value/Footprint/model lines may change')
    if not DRY and new != old:
        with open(p, 'wb') as f:
            f.write(new)


def exists_ci(path):
    d, n = os.path.split(path)
    return os.path.isdir(d) and any(x.lower() == n.lower() for x in os.listdir(d))


def same_ci(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def move(src, dst):
    if not same_ci(src, dst) and exists_ci(dst):
        if not DRY:
            sys.exit(f'COLLISION: {dst}')
        LOG.append(f'WARN dry run (earlier moves not simulated), target exists: {dst}')
    LOG.append(f'mv  {src} -> {dst}')
    if DRY:
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if same_ci(src, dst):
        os.rename(src, dst + '.klc_tmp')
        os.rename(dst + '.klc_tmp', dst)
    else:
        os.rename(src, dst)


def copy(src, dst):
    if exists_ci(dst):
        sys.exit(f'COLLISION: {dst}')
    LOG.append(f'cp  {src} -> {dst}')
    if not DRY:
        shutil.copy2(src, dst)


def stem(p, ext):
    return os.path.basename(p)[:-len(ext)]


def do_sym():
    for e in MAP.get('symbols', []):
        src, new = e['src'], e['new']
        old = stem(src, '.kicad_sym')
        dst = f"{SYM_ROOT}/{e['dst_lib']}.kicad_symdir/{new}.kicad_sym"
        b0 = rd(src)
        o, n = old.encode(), new.encode()
        if b0.count(b'(symbol "' + o + b'"') != 1:
            sys.exit(f'{src}: expected one root symbol "{old}" (split packed .kicad_sym libraries first)')
        b = b0.replace(b'(symbol "' + o + b'"', b'(symbol "' + n + b'"')
        b = re.sub(rb'\(symbol "' + re.escape(o) + rb'(_\d+_\d+")', b'(symbol "' + n + rb'\1', b)
        b = b.replace(b'(property "Value" "' + o + b'"', b'(property "Value" "' + n + b'"')
        wr(src, b0, b)
        move(src, dst)


def do_fp():
    links = dict(MAP.get('link_fixes', {}))
    for e in MAP.get('footprints', []):
        src, new = e['src'], e['new']
        old = stem(src, '.kicad_mod')
        src_lib = stem(os.path.dirname(src), '.pretty')
        dst = f"{FP_ROOT}/{e['dst_lib']}.pretty/{new}.kicad_mod"
        b0 = rd(src)
        internal = re.match(rb'\(footprint "([^"]+)"', b0).group(1)
        b = b0.replace(b'(footprint "' + internal + b'"', b'(footprint "' + new.encode() + b'"', 1)
        for v in {internal, old.encode()}:
            b = b.replace(b'(property "Value" "' + v + b'"', b'(property "Value" "' + new.encode() + b'"')
        wr(src, b0, b)
        move(src, dst)
        links[f'{src_lib}:{old}'] = f"{e['dst_lib']}:{new}"
    for d, _, files in os.walk(SYM_ROOT):
        for f in files:
            if not f.endswith('.kicad_sym'):
                continue
            p = os.path.join(d, f)
            b0 = rd(p)
            b = b0
            for o, n in links.items():
                b = b.replace(b'(property "Footprint" "' + o.encode() + b'"', b'(property "Footprint" "' + n.encode() + b'"')
            if b != b0:
                LOG.append(f'link {p}')
                wr(p, b0, b)


def do_3d():
    moved = {}
    for e in MAP.get('models', []):
        src, dst = e['src'], e['dst']
        lib, name = e['footprint'].split(':', 1)
        fpath = f'{FP_ROOT}/{lib}.pretty/{name}.kicad_mod'
        if src in moved:
            copy(moved[src], dst)
        else:
            move(src, dst)
            moved[src] = dst
        b0 = rd(fpath)
        base = os.path.basename(src).lower().encode()
        hits = [m for m in re.finditer(rb'\(model "([^"]+)"', b0) if os.path.basename(m.group(1).decode()).lower().encode() == base]
        if len(hits) != 1:
            sys.exit(f'{fpath}: expected one model path ending in {os.path.basename(src)}, found {len(hits)}')
        folder, f = dst.split('/')[-2:]
        b = b0[:hits[0].start(1)] + f'${{KIPRJMOD}}/library/3D/{folder}/{f}'.encode() + b0[hits[0].end(1):]
        LOG.append(f'    model {fpath}: {hits[0].group(1).decode()} -> {folder}/{f}')
        wr(fpath, b0, b)


{'sym': do_sym, 'fp': do_fp, '3d': do_3d}[STEP]()
print('\n'.join(LOG))
print(f'{"DRY RUN " if DRY else ""}done: {STEP}')
