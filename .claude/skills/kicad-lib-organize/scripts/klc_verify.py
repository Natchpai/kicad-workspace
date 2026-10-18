"""Read-only library checks.
Usage (from the folder that holds the library folder): python -I klc_verify.py [--lib <library folder>]

--lib defaults to "library" (with symbols/, footprints/ and 3D/ inside).
Checks: counts; file name == internal name (symbols, units, footprints); every symbol Footprint
property resolves to a footprint file; every ${KIPRJMOD}/<library folder>/3D model path resolves
with exact letter case; KLC G1.1 characters in file and folder names.
"""
import glob, os, re, sys

LIB = sys.argv[sys.argv.index('--lib') + 1].strip('/') if '--lib' in sys.argv else 'library'
OK = re.compile(r'^[A-Za-z0-9_.,+-]+$')
bad = []

syms = glob.glob(f'{LIB}/symbols/*.kicad_symdir/*.kicad_sym')
fps = glob.glob(f'{LIB}/footprints/*.pretty/*.kicad_mod')
models = [p for p in glob.glob(f'{LIB}/3D/*/*') if os.path.isfile(p) and not p.endswith('.md')]
print(f'symbols={len(syms)} footprints={len(fps)} models={len(models)}')

fp_set = set()
for p in fps:
    lib = os.path.basename(os.path.dirname(p))[:-len('.pretty')]
    name = os.path.basename(p)[:-len('.kicad_mod')]
    fp_set.add(f'{lib}:{name}')
    t = open(p, encoding='utf-8').read()
    m = re.match(r'\(footprint "([^"]+)"', t)
    if not m or m.group(1) != name:
        bad.append(f'footprint name mismatch: {p} internal={m and m.group(1)}')
    for mp in re.findall(r'\(model "([^"]+)"', t):
        if mp.startswith(f'${{KIPRJMOD}}/{LIB}/3D/'):
            folder, f = mp.split(f'{LIB}/3D/')[1].split('/')
            d = f'{LIB}/3D/{folder}'
            if not os.path.isdir(d) or f not in os.listdir(d):
                bad.append(f'missing model (exact case): {p} -> {mp}')

for p in syms:
    name = os.path.basename(p)[:-len('.kicad_sym')]
    t = open(p, encoding='utf-8').read()
    names = re.findall(r'^\s*\(symbol "([^"]+)"', t, re.M)
    roots = [n for n in names if not re.search(r'_\d+_\d+$', n)]
    if roots != [name]:
        bad.append(f'symbol name mismatch: {p} roots={roots}')
    bad += [f'unit name mismatch: {p} unit={u}' for u in names if u not in roots and not u.startswith(name + '_')]
    bad += [f'broken Footprint link: {p} -> {fp}' for fp in re.findall(r'\(property "Footprint" "([^"]*)"', t)
            if fp and fp not in fp_set]

for p in syms + fps + models:
    if not OK.match(os.path.basename(p)):
        bad.append(f'G1.1 characters: {p}')
for sub in ('symbols', 'footprints', '3D'):
    bad += [f'G1.1 characters: {LIB}/{sub}/{d}' for d in os.listdir(f'{LIB}/{sub}')
            if os.path.isdir(f'{LIB}/{sub}/{d}') and not OK.match(d)]

print('\n'.join(bad) if bad else 'all checks passed')
