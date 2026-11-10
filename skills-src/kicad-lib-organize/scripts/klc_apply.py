"""Apply a KLC rename map: move/rename symbols, footprints and 3D models and keep links working.

Usage (from the project or repo root, the folder that holds the library folder):
    python -I klc_apply.py <map.json> sym|fp|3d [--dry] [--lib <library folder>] [--root <dir>] [--copy]

--lib defaults to "library". The library folder holds symbols/, footprints/ and 3D/, and model paths are
written as ${KIPRJMOD}/<library folder>/3D/<Folder>/<file>.
--root runs from <dir> instead of the current folder (the destination repo or project).
--copy leaves every source file untouched: the renamed copy is written to the destination and models are
copied. Use it when the source is another project (publish); "src" paths may then be absolute.

Map format (paths relative to the root unless absolute, forward slashes):
{
  "symbols":    [{"src": "<path>.kicad_sym", "dst_lib": "0_Diode", "new": "MBRA340"}],
  "footprints": [{"src": "<path>.pretty/<old>.kicad_mod", "dst_lib": "0_Package_SO", "new": "SOIC-8_3.9x4.9mm_P1.27mm"}],
  "models":     [{"src": "<path to model>", "dst": "<library folder>/3D/<Folder>/<new>.step", "footprint": "0_Lib:<new fp name>"}],
  "link_fixes": {"<old lib:name>": "<new lib:name>"}
}

- sym: renames each symbol file and its internal names (root, unit sub-symbols, Value when equal to the old name),
       then rewrites (extends "<old>") in the derived symbols of the same library folder.
- fp:  renames each footprint file and its internal name (and Value when equal), then rewrites every symbol
       Footprint property that pointed at "<src .pretty name>:<old name>" (plus link_fixes) across <library>/symbols.
- 3d:  moves each model to dst (a second entry with the same src copies it, so each footprint owns its file)
       and rewrites the one (model "...") path in that footprint whose file name matches src.
Edits are byte-level, so CRLF/LF line endings are kept. Each edited file is checked: only name, Value,
extends, Footprint and model lines may change. Refuses to overwrite (case-insensitive check); case-only renames go
through a temporary name.
"""
import json, os, re, shutil, sys

MAP = json.load(open(sys.argv[1], encoding='utf-8'))
STEP = sys.argv[2]
DRY = '--dry' in sys.argv
COPY = '--copy' in sys.argv
LIB = sys.argv[sys.argv.index('--lib') + 1].strip('/') if '--lib' in sys.argv else 'library'
if '--root' in sys.argv:
    os.chdir(sys.argv[sys.argv.index('--root') + 1])
SYM_ROOT = f'{LIB}/symbols'
FP_ROOT = f'{LIB}/footprints'
ALLOWED = re.compile(rb'^\s*(\(footprint "|\(symbol "|\(extends "|\(property "Value" "|\(property "Footprint" "|\(model ")')
LOG = []


def rd(p):
    with open(p, 'rb') as f:
        return f.read()


def check(p, old, new):
    a, b = old.splitlines(), new.splitlines()
    if len(a) != len(b) or any(x != y and not (ALLOWED.match(x) and ALLOWED.match(y)) for x, y in zip(a, b)):
        sys.exit(f'UNEXPECTED EDIT in {p}: only name/Value/Footprint/model lines may change')


def wr(p, old, new):
    check(p, old, new)
    if not DRY and new != old:
        with open(p, 'wb') as f:
            f.write(new)


def put(src, old, new, dst):
    """Move mode: edit src in place, then move it. Copy mode: write the edited bytes to dst; src untouched."""
    if not COPY:
        if not DRY and not same_ci(src, dst) and exists_ci(dst):   # before src is edited
            sys.exit(f'COLLISION: {dst}')
        wr(src, old, new)
        move(src, dst)
        return
    check(src, old, new)
    if exists_ci(dst):
        if not DRY:
            sys.exit(f'COLLISION: {dst}')
        LOG.append(f'WARN dry run, target exists: {dst}')
    LOG.append(f'cp  {src} -> {dst}')
    if not DRY:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(new)


def exists_ci(path):
    d, n = os.path.split(path)
    return os.path.isdir(d) and any(x.lower() == n.lower() for x in os.listdir(d))


def same_ci(a, b):
    """a and b name the same file but for letter case: a case-only rename. os.path.normcase folds case
    only on Windows, and macOS disks ignore case too, so ask the disk when b is there."""
    a, b = os.path.abspath(a), os.path.abspath(b)
    return a.lower() == b.lower() and (a == b or not os.path.exists(b) or os.path.samefile(a, b))


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
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def stem(p, ext):
    return os.path.basename(p)[:-len(ext)]


def do_sym():
    renamed = {}   # old name -> (new name, source folder, destination folder)
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
        put(src, b0, b, dst)
        if old != new:
            renamed.setdefault(old, (new, os.path.dirname(src), os.path.dirname(dst)))
    # derived symbols: (extends "<old>") follows its renamed parent. KiCad needs parent and child in one
    # library, so look in the parent's new folder and, unless --copy, in the folder it came from.
    ext_re = re.compile(rb'\(extends "([^"]+)"\)')
    dirs = set()
    for _, sdir, ddir in renamed.values():
        dirs.update([ddir] if COPY else [sdir, ddir])
    for d in sorted(x for x in dirs if os.path.isdir(x)):
        here = os.listdir(d)
        for f in sorted(here):
            if not f.endswith('.kicad_sym'):
                continue
            p = f'{d}/{f}'
            b0 = rd(p)
            m = ext_re.search(b0)
            old = m.group(1).decode() if m else None
            if old not in renamed:
                continue
            new, sdir, ddir = renamed[old]
            if os.path.abspath(d) not in (os.path.abspath(sdir), os.path.abspath(ddir)):
                continue   # another library's symbol of the same name
            if not DRY and f'{old}.kicad_sym' in here:
                continue   # a symbol with the old name is still in this folder: the child is its child
            LOG.append(f'extends {p}: {old} -> {new}')
            if os.path.abspath(d) != os.path.abspath(ddir):
                LOG.append(f'WARN {p} is not in its parent\'s library {ddir}; move it there too')
            wr(p, b0, b0[:m.start(1)] + new.encode() + b0[m.end(1):])


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
        put(src, b0, b, dst)
        links[f'{src_lib}:{old}'] = f"{e['dst_lib']}:{new}"
    link_re = re.compile(rb'(\(property "Footprint" ")(' + b'|'.join(
        re.escape(o.encode()) for o in sorted(links, key=len, reverse=True)) + rb')"') if links else None
    for d, _, files in os.walk(SYM_ROOT):
        for f in files:
            if not f.endswith('.kicad_sym'):
                continue
            p = os.path.join(d, f)
            b0 = rd(p)
            b = b0
            if link_re:   # one pass, so a new name that is also an old name is not renamed twice
                b = link_re.sub(lambda m: m.group(1) + links[m.group(2).decode()].encode() + b'"', b0)
            if b != b0:
                LOG.append(f'link {p}')
                wr(p, b0, b)


def do_3d():
    moved = {}
    for e in MAP.get('models', []):
        src, dst = e['src'], e['dst']
        lib, name = e['footprint'].split(':', 1)
        fpath = f'{FP_ROOT}/{lib}.pretty/{name}.kicad_mod'
        if not os.path.isfile(fpath):   # checked before the model moves
            sys.exit(f'{fpath}: footprint not found')
        b0 = rd(fpath)
        base = os.path.basename(src).lower().encode()
        hits = [m for m in re.finditer(rb'\(model "([^"]+)"', b0) if os.path.basename(m.group(1).decode()).lower().encode() == base]
        if len(hits) != 1:
            sys.exit(f'{fpath}: expected one model path ending in {os.path.basename(src)}, found {len(hits)}')
        if src in moved:
            copy(moved[src], dst)
        elif COPY:
            copy(src, dst)
            moved[src] = dst
        else:
            move(src, dst)
            moved[src] = dst
        folder, f = dst.split('/')[-2:]
        b = b0[:hits[0].start(1)] + f'${{KIPRJMOD}}/{LIB}/3D/{folder}/{f}'.encode() + b0[hits[0].end(1):]
        LOG.append(f'    model {fpath}: {hits[0].group(1).decode()} -> {folder}/{f}')
        wr(fpath, b0, b)


{'sym': do_sym, 'fp': do_fp, '3d': do_3d}[STEP]()
print('\n'.join(LOG))
print(f'{"DRY RUN " if DRY else ""}done: {STEP}')
