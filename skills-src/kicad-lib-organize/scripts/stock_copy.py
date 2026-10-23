"""Find stock KiCad symbols and footprints, and copy them unchanged into a local 0_ library family.

Usage (from the folder that holds the library folder):
    python -I stock_copy.py find <glob> [--stock <dir>]
    python -I stock_copy.py fp  <StockLib>:<name> <0_Family> [--dry] [--lib <folder>] [--root <dir>] [--stock <dir>]
    python -I stock_copy.py sym <StockLib>:<name> <0_Family> [--fp <0_Family>:<footprint>] [--dry] [--lib <folder>]
                               [--root <dir>] [--stock <dir>]

--stock is KiCad's share folder holding symbols/ and footprints/. Default: the parent of $KICAD10_SYMBOL_DIR,
else C:/Program Files/KiCad/10.0/share/kicad. --lib defaults to "library"; --root runs from <dir>.

find: case-insensitive glob on item names (stock names hold the base part number or package, not the order code:
      search "TPS62142*" or "*VQFN-16*", not "TPS62142RGTR"). Footprints print pad count, smallest pad spacing,
      pad sizes and model paths, so look-alike candidates can be compared side by side. Symbols print their extends
      parent and Footprint. No match prints "no match" and exits 1.
fp:   copies the stock .kicad_mod byte for byte. Model paths stay ${KICAD10_3DMODEL_DIR}/...
sym:  cuts the root symbol out of the packed stock library, plus every (extends ...) parent up the chain, one file
      per symbol: in a .kicad_symdir a derived symbol needs its parent in the same library. Each copied file's
      Footprint "<lib>:<name>" is pointed at the local copy when exactly one 0_*.pretty in the library holds <name>;
      that is the only byte that may differ from stock. --fp links the named symbol (not its parents) to a local
      footprint with another name, for example one drawn under the maker's name, and appends that name to
      ki_fp_filters when no filter matches it.
A byte-identical target is skipped; a differing one stops the run before anything is written. Lib tables are
never touched.
"""
import fnmatch, glob, math, os, re, sys

args = sys.argv[1:]


def opt(name, default=None):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


def flag(name):
    if name in args:
        args.remove(name)
        return True
    return False


DRY = flag('--dry')
FP_LINK = opt('--fp')
LIB = opt('--lib', 'library').strip('/')
ROOT = opt('--root')
STOCK = opt('--stock')
if not STOCK:
    env = os.environ.get('KICAD10_SYMBOL_DIR')
    STOCK = os.path.dirname(env.rstrip('/\\')) if env else 'C:/Program Files/KiCad/10.0/share/kicad'
SYM_DIR, FP_DIR = f'{STOCK}/symbols', f'{STOCK}/footprints'
if ROOT:
    os.chdir(ROOT)


def rd(p):
    with open(p, 'rb') as f:
        return f.read()


def block(t, start):
    """Bytes of the s-expression opening at t[start], skipping quoted strings."""
    d, q, i = 0, False, start
    while i < len(t):
        c = t[i:i + 1]
        if q:
            if c == b'\\':
                i += 1
            elif c == b'"':
                q = False
        elif c == b'"':
            q = True
        elif c == b'(':
            d += 1
        elif c == b')':
            d -= 1
            if d == 0:
                return t[start:i + 1]
        i += 1
    sys.exit('unbalanced s-expression')


ROOT_SYM = re.compile(rb'^\t\(symbol "([^"]+)"', re.M)


class Sym:
    """A root symbol in a stock file; the block is cut out only when read (cutting all of them is slow)."""

    def __init__(self, t, start, head):
        self.t, self.start, self.head = t, start, head

    @property
    def body(self):
        return block(self.t, self.start)


def stock_symbols(lib):
    """{name: Sym} for one stock library, packed file or symdir."""
    out = {}
    paths = [f'{SYM_DIR}/{lib}.kicad_sym'] if os.path.isfile(f'{SYM_DIR}/{lib}.kicad_sym') \
        else glob.glob(f'{SYM_DIR}/{lib}.kicad_symdir/*.kicad_sym')
    for p in paths:
        t = rd(p)
        first = ROOT_SYM.search(t)
        if not first:
            continue
        head = t[:first.start()]
        for m in ROOT_SYM.finditer(t):
            out[m.group(1).decode()] = Sym(t, m.start() + 1, head)
    return out


def prop(b, key):
    m = re.search(rb'\(property "' + key + rb'" "([^"]*)"', b)
    return m.group(1).decode() if m else ''


def pad_summary(t):
    pads = re.findall(rb'\(pad "([^"]*)" \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+)[^)]*\)\s*\(size ([\d.]+) ([\d.]+)\)', t)
    nums = {p[0] for p in pads if p[0]}
    pts = [(float(p[1]), float(p[2])) for p in pads if p[0]]
    gap = min((math.dist(a, b) for i, a in enumerate(pts) for b in pts[i + 1:] if math.dist(a, b) > 1e-6), default=0)
    sizes = sorted({f'{p[3].decode()}x{p[4].decode()}' for p in pads})
    return f'pads={len(nums)} min_spacing={gap:g}mm sizes={",".join(sizes)}'


def find(pat):
    pat = pat.lower()
    hits = 0
    for p in sorted(glob.glob(f'{FP_DIR}/*.pretty/*.kicad_mod')):
        name = os.path.basename(p)[:-len('.kicad_mod')]
        if fnmatch.fnmatch(name.lower(), pat):
            hits += 1
            t = rd(p)
            lib = os.path.basename(os.path.dirname(p))[:-len('.pretty')]
            models = [m.decode() for m in re.findall(rb'\(model "([^"]+)"', t)]
            print(f'FP  {lib}:{name}  {pad_summary(t)}  models={models}')
    libs = {os.path.basename(p).split('.kicad_sym')[0] for p in glob.glob(f'{SYM_DIR}/*.kicad_sym*')}
    for lib in sorted(libs):
        for name, s in stock_symbols(lib).items():
            if fnmatch.fnmatch(name.lower(), pat):
                hits += 1
                b = s.body
                ext = re.search(rb'\(extends "([^"]+)"', b)
                print(f'SYM {lib}:{name}  extends={ext.group(1).decode() if ext else "-"}  Footprint="{prop(b, b"Footprint")}"')
    if not hits:
        print(f'no match for "{pat}" (stock names hold the base part number or package; try a shorter glob)')
        sys.exit(1)


def place(data, dst, log):
    """Return True when dst must be written; stop on a differing case-insensitive match."""
    d, n = os.path.split(dst)
    hit = [x for x in (os.listdir(d) if os.path.isdir(d) else []) if x.lower() == n.lower()]
    if hit:
        if rd(os.path.join(d, hit[0])) == data:
            log.append(f'same {os.path.join(d, hit[0])} (identical, skipped)')
            return False
        sys.exit(f'COLLISION: {os.path.join(d, hit[0])} differs from the stock item')
    stem = n.rsplit('.', 1)[0].lower()
    sub = 'symbols' if n.endswith('.kicad_sym') else 'footprints'
    for other in glob.glob(f'{LIB}/{sub}/*/*'):
        if os.path.basename(other).rsplit('.', 1)[0].lower() == stem and os.path.dirname(other) != d:
            log.append(f'WARN same name in another family: {other}')
    log.append(f'cp  {dst}')
    return True


def write_all(items, log):
    for dst, data in items:
        if not DRY:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(data)
    print('\n'.join(log))
    print(f'{"DRY RUN " if DRY else ""}done')


def copy_fp(ref, fam):
    lib, name = ref.split(':', 1)
    src = f'{FP_DIR}/{lib}.pretty/{name}.kicad_mod'
    if not os.path.isfile(src):
        sys.exit(f'not in stock: {src}')
    data, log = rd(src), []
    dst = f'{LIB}/footprints/{fam}.pretty/{name}.kicad_mod'
    write_all([(dst, data)] if place(data, dst, log) else [], log)


def copy_sym(ref, fam):
    lib, name = ref.split(':', 1)
    syms = stock_symbols(lib)
    if name not in syms:
        sys.exit(f'not in stock: {lib}:{name}')
    chain, cur = [], name
    while cur:
        if cur not in syms:
            sys.exit(f'parent {cur} not found in stock {lib}')
        chain.append(cur)
        ext = re.search(rb'\(extends "([^"]+)"', syms[cur].body)
        cur = ext.group(1).decode() if ext else None
    items, log = [], []
    if FP_LINK:
        fam_fp, fp_name = FP_LINK.split(':', 1) if ':' in FP_LINK else ('', '')
        if not (fam_fp.startswith('0_') and os.path.isfile(f'{LIB}/footprints/{fam_fp}.pretty/{fp_name}.kicad_mod')):
            sys.exit(f'--fp {FP_LINK}: no {LIB}/footprints/{fam_fp}.pretty/{fp_name}.kicad_mod')
    for n in chain:
        b, head = syms[n].body, syms[n].head
        fp = prop(b, b'Footprint')
        if FP_LINK and n == name:
            b = b.replace(b'(property "Footprint" "' + fp.encode() + b'"',
                          b'(property "Footprint" "' + FP_LINK.encode() + b'"', 1)
            log.append(f'link {n}: {fp or "-"} -> {FP_LINK}')
            flt = prop(b, b'ki_fp_filters')
            if flt and not any(fnmatch.fnmatch(fp_name.lower(), f.lower()) for f in flt.split()):
                b = b.replace(b'(property "ki_fp_filters" "' + flt.encode() + b'"',
                              b'(property "ki_fp_filters" "' + (flt + ' ' + fp_name).encode() + b'"', 1)
                log.append(f'filter {n}: added {fp_name}')
        elif ':' in fp and not fp.startswith('0_'):
            local = glob.glob(f'{LIB}/footprints/0_*.pretty/{fp.split(":", 1)[1]}.kicad_mod')
            if len(local) == 1:
                new = os.path.basename(os.path.dirname(local[0]))[:-len('.pretty')] + ':' + fp.split(':', 1)[1]
                b = b.replace(b'(property "Footprint" "' + fp.encode() + b'"', b'(property "Footprint" "' + new.encode() + b'"', 1)
                log.append(f'link {n}: {fp} -> {new}')
        eol = b'\r\n' if b'\r\n' in head else b'\n'
        data = head + b'\t' + b + eol + b')' + eol
        dst = f'{LIB}/symbols/{fam}.kicad_symdir/{n}.kicad_sym'
        if place(data, dst, log):
            items.append((dst, data))
    if len(chain) > 1:
        log.append(f'derived chain: {" -> ".join(chain)}')
    write_all(items, log)


if len(args) < 2 or args[0] not in ('find', 'fp', 'sym'):
    sys.exit(__doc__)
if args[0] == 'find':
    find(args[1])
elif len(args) != 3 or not args[2].startswith('0_'):
    sys.exit('need <StockLib>:<name> <0_Family>')
else:
    (copy_fp if args[0] == 'fp' else copy_sym)(args[1], args[2])
