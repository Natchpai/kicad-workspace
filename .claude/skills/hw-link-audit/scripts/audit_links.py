#!/usr/bin/env python3
"""Read-only audit of KiCad library links.

Checks, for one KiCad project directory:
  1. fp-lib-table / sym-lib-table entries vs. folders on disk
  2. symbol Footprint property -> footprint library -> .kicad_mod file
  3. symbol ki_fp_filters (missing, or not matching the linked footprint)
  4. footprint (model ...) paths -> existing 3D file (exact letter case)
  5. schematic Footprint / lib_id nicknames vs. the library tables

Never writes to the project. Usage:
  python -I audit_links.py <project_dir>
"""
import fnmatch
import os
import re
import sys

LIB_RE = re.compile(r'\(lib\s+\(name\s+"([^"]*)"\).*?\(uri\s+"([^"]*)"\)', re.S)
SYM_SPLIT = re.compile(r'^\t\(symbol "([^"]+)"', re.M)
PROP_RE = r'\(property "%s" "([^"]*)"'
MODEL_RE = re.compile(r'\(model\s+"([^"]+)"')
VAR_RE = re.compile(r'\$\{([^}]+)\}')


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read().replace('\r\n', '\n')


def has_pro(d):
    try:
        return any(n.endswith('.kicad_pro') for n in os.listdir(d))
    except OSError:
        return False


def find_project_dir(start):
    """Return (dir, error). Search start, its parents, then children (depth 3)."""
    d = os.path.abspath(start)
    cur = d
    for _ in range(6):
        if has_pro(cur):
            return cur, None
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    found = []
    base_depth = d.rstrip(os.sep).count(os.sep)
    for root, dirs, _ in os.walk(d):
        dirs[:] = [x for x in dirs if not x.startswith('.')]
        if root.count(os.sep) - base_depth >= 3:
            dirs[:] = []
        if has_pro(root):
            found.append(root)
    if len(found) == 1:
        return found[0], None
    if not found:
        return d, f'no .kicad_pro found at, above, or within 3 levels below {d}'
    return d, 'several projects found, pass one: ' + '; '.join(found)


def expand(uri, proj):
    out = uri.replace('${KIPRJMOD}', proj)
    return os.path.normpath(out), VAR_RE.findall(out)


def load_table(proj, name):
    path = os.path.join(proj, name)
    if not os.path.isfile(path):
        return None, []
    entries = []
    for nick, uri in LIB_RE.findall(read(path)):
        real, leftover = expand(uri, proj)
        entries.append({'name': nick, 'uri': uri, 'path': real,
                        'local': uri.startswith('${KIPRJMOD}'),
                        'unresolved': leftover})
    return path, entries


def exact_case_exists(path, proj):
    """True if every component under proj matches on-disk letter case."""
    rel = os.path.relpath(path, proj)
    if rel.startswith('..'):
        return os.path.exists(path), None
    cur = proj
    for part in rel.split(os.sep):
        try:
            names = os.listdir(cur)
        except OSError:
            return False, None
        if part in names:
            cur = os.path.join(cur, part)
            continue
        hit = [n for n in names if n.lower() == part.lower()]
        return False, (hit[0] if hit else None)
    return True, None


def table_vs_disk(entries, kind_ext, proj, label, issues):
    """Compare table entries with folders of the given extension."""
    folders = {e['name'] for e in entries}
    on_disk = {}
    for e in entries:
        if e['local']:
            parent = os.path.dirname(e['path'])
            if os.path.isdir(parent):
                for n in os.listdir(parent):
                    if n.endswith(kind_ext) and os.path.isdir(os.path.join(parent, n)):
                        on_disk[n[:-len(kind_ext)]] = os.path.join(parent, n)
    for e in entries:
        if not e['local']:
            continue
        if not os.path.exists(e['path']):
            ok, real = exact_case_exists(e['path'], proj)
            hint = f' (on disk: {real})' if real else ''
            issues.append(f'{label}: table entry "{e["name"]}" -> missing path '
                          f'{e["uri"]}{hint}')
        elif e['name'] != os.path.basename(e['path'])[:-len(kind_ext)]:
            issues.append(f'{label}: nickname "{e["name"]}" differs from folder '
                          f'"{os.path.basename(e["path"])}"')
    for n in sorted(on_disk):
        if n not in folders:
            issues.append(f'{label}: folder "{n}{kind_ext}" has no table entry')


def footprint_index(fp_entries):
    idx = {}
    for e in fp_entries:
        names = set()
        if os.path.isdir(e['path']):
            for f in os.listdir(e['path']):
                if f.endswith('.kicad_mod'):
                    names.add(f[:-len('.kicad_mod')])
        idx[e['name']] = {'entry': e, 'names': names}
    return idx


def split_symbols(path):
    text = read(path)
    marks = list(SYM_SPLIT.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        yield m.group(1), text[m.start():end]


def prop(block, key):
    m = re.search(PROP_RE % re.escape(key), block)
    return m.group(1) if m else None


def audit_symbols(sym_entries, fp_idx, rows, issues):
    for e in sym_entries:
        if not e['local'] or not os.path.exists(e['path']):
            continue
        if os.path.isdir(e['path']):
            files = [os.path.join(e['path'], f) for f in sorted(os.listdir(e['path']))
                     if f.endswith('.kicad_sym')]
        else:
            files = [e['path']]
        for fpath in files:
            syms = list(split_symbols(fpath))
            if not syms:
                issues.append(f'sym-lib-table: no symbols parsed from {fpath} '
                              '(unexpected format or indentation; results for it are NOT '
                              'a pass)')
            for sym, block in syms:
                rows.append(classify_symbol(e['name'], sym, block, fp_idx))


def classify_symbol(lib, sym, block, fp_idx):
    fp = prop(block, 'Footprint')
    filt = prop(block, 'ki_fp_filters')
    row = {'lib': lib, 'symbol': sym, 'footprint': fp, 'filters': filt,
           'link': '', 'filter': '', 'notes': []}
    if not fp:
        row['link'] = 'EMPTY'
    elif ':' not in fp:
        row['link'] = 'MALFORMED'
    else:
        nick, name = fp.split(':', 1)
        if nick not in fp_idx:
            ci = [k for k in fp_idx if k.lower() == nick.lower()]
            if ci:
                row['link'] = 'NICKNAME_CASE'
                row['notes'].append(f'table has "{ci[0]}"')
            else:
                row['link'] = 'GLOBAL_OR_UNKNOWN'
        elif not fp_idx[nick]['entry']['local']:
            row['link'] = 'GLOBAL'
        elif name in fp_idx[nick]['names']:
            row['link'] = 'LOCAL_OK'
        else:
            ci = [n for n in fp_idx[nick]['names'] if n.lower() == name.lower()]
            row['link'] = 'LOCAL_NAME_CASE' if ci else 'LOCAL_FILE_MISSING'
    # ki_fp_filters
    if filt is None:
        row['filter'] = 'MISSING'
    elif not filt.strip():
        row['filter'] = 'EMPTY'
    elif row['link'] in ('LOCAL_OK', 'LOCAL_NAME_CASE'):
        # KiCad (common/footprint_filter.cpp): a pattern with ':' matches
        # "nickname:name", any other pattern matches the name only
        name = fp.split(':', 1)[1]
        pats = filt.split()
        hit = [p for p in pats
               if fnmatch.fnmatchcase((fp if ':' in p else name).lower(), p.lower())]
        row['filter'] = 'MATCH' if hit else 'NO_MATCH'
        if not hit and len(pats) > 1 and not any(c in filt for c in '*?'):
            row['notes'].append('space splits patterns; no wildcard used')
    else:
        row['filter'] = 'UNCHECKED'
        if len(filt.split()) > 1 and not any(c in filt for c in '*?'):
            row['filter'] = 'SUSPECT'
            row['notes'].append('space splits patterns; no wildcard used')
    return row


def audit_models(fp_entries, proj, rows):
    for e in fp_entries:
        if not e['local'] or not os.path.isdir(e['path']):
            continue
        for f in sorted(os.listdir(e['path'])):
            if not f.endswith('.kicad_mod'):
                continue
            text = read(os.path.join(e['path'], f))
            models = MODEL_RE.findall(text)
            if not models:
                rows.append({'lib': e['name'], 'footprint': f[:-10],
                             'model': None, 'status': 'NO_MODEL'})
            for m in models:
                rows.append(classify_model(e['name'], f[:-10], m, proj))


def classify_model(lib, fp, model, proj):
    row = {'lib': lib, 'footprint': fp, 'model': model, 'status': ''}
    vars_ = VAR_RE.findall(model)
    if vars_ and vars_[0] != 'KIPRJMOD':
        row['status'] = 'GLOBAL'
        return row
    real, leftover = expand(model, proj)
    if leftover:
        row['status'] = 'UNRESOLVED_VAR'
        return row
    ok, hint = exact_case_exists(real, proj)
    if ok:
        row['status'] = 'LOCAL_OK'
    elif os.path.exists(real):
        row['status'] = 'LOCAL_CASE_MISMATCH'
        row['model'] += f'  (on disk differs in case: {hint or "?"})'
    else:
        row['status'] = 'LOCAL_MISSING'
    return row


def audit_schematics(proj, fp_idx, sym_names, issues):
    fp_re = re.compile(r'\(property "Footprint" "([^"]*)"')
    id_re = re.compile(r'\(lib_id "([^"]+)"')
    for root, _, files in os.walk(proj):
        for f in files:
            if not f.endswith('.kicad_sch'):
                continue
            rel = os.path.relpath(os.path.join(root, f), proj)
            text = read(os.path.join(root, f))
            for fp in sorted(set(fp_re.findall(text))):
                if not fp:
                    continue
                nick, _, name = fp.partition(':')
                if nick in fp_idx:
                    if fp_idx[nick]['entry']['local'] and name not in fp_idx[nick]['names']:
                        issues.append(f'{rel}: Footprint "{fp}" -> footprint file missing in {nick}')
                else:
                    ci = [k for k in fp_idx if k.lower() == nick.lower()]
                    if ci:
                        issues.append(f'{rel}: Footprint "{fp}" -> nickname case differs '
                                      f'from table "{ci[0]}"')
            for lid in sorted(set(id_re.findall(text))):
                nick, _, name = lid.partition(':')
                if nick in sym_names:
                    if name not in sym_names[nick]:
                        issues.append(f'{rel}: lib_id "{lid}" -> symbol not in {nick}')
                else:
                    ci = [k for k in sym_names if k.lower() == nick.lower()]
                    if ci:
                        issues.append(f'{rel}: lib_id "{lid}" -> nickname case differs '
                                      f'from table "{ci[0]}"')


def symbol_names(sym_entries):
    out = {}
    for e in sym_entries:
        if not e['local'] or not os.path.exists(e['path']):
            continue
        names = set()
        paths = ([os.path.join(e['path'], f) for f in os.listdir(e['path'])
                  if f.endswith('.kicad_sym')]
                 if os.path.isdir(e['path']) else [e['path']])
        for p in paths:
            names.update(n for n, _ in split_symbols(p))
        out[e['name']] = names
    return out


def main(argv):
    proj, err = find_project_dir(argv[1] if len(argv) > 1 else '.')
    if err:
        print(f'ERROR: {err}', file=sys.stderr)
        return 2
    fp_path, fp_entries = load_table(proj, 'fp-lib-table')
    sym_path, sym_entries = load_table(proj, 'sym-lib-table')
    if fp_path is None and sym_path is None:
        print(f'ERROR: no fp-lib-table or sym-lib-table in {proj}; nothing to audit '
              '(not a pass).', file=sys.stderr)
        return 2
    report = {'project': proj, 'table_issues': [], 'symbols': [],
              'models': [], 'schematic_issues': [], 'notes': []}
    if fp_path is None:
        report['notes'].append('fp-lib-table not found (project has no local footprint table)')
    if sym_path is None:
        report['notes'].append('sym-lib-table not found (project has no local symbol table)')

    table_vs_disk(fp_entries, '.pretty', proj, 'fp-lib-table', report['table_issues'])
    table_vs_disk(sym_entries, '.kicad_symdir', proj, 'sym-lib-table', report['table_issues'])
    for e in fp_entries + sym_entries:
        if e['unresolved'] and e['unresolved'] != ['KIPRJMOD']:
            report['table_issues'].append(
                f'table entry "{e["name"]}" uses variable(s) {e["unresolved"]} '
                '(not resolved by this tool)')

    fp_idx = footprint_index(fp_entries)
    audit_symbols(sym_entries, fp_idx, report['symbols'], report['table_issues'])
    audit_models(fp_entries, proj, report['models'])
    audit_schematics(proj, fp_idx, symbol_names(sym_entries), report['schematic_issues'])

    print_report(report)
    return 0


def print_report(r):
    print(f'Project: {r["project"]}')
    for n in r['notes']:
        print(f'NOTE: {n}')
    print('\n== Library tables vs folders ==')
    print('\n'.join(r['table_issues']) or 'OK (no issues)')

    print('\n== Symbol -> footprint link, ki_fp_filters ==')
    by = {}
    for s in r['symbols']:
        by.setdefault(s['link'], []).append(s)
    for k in sorted(by):
        print(f'  {k}: {len(by[k])}')
    for s in r['symbols']:
        bad_link = s['link'] not in ('LOCAL_OK', 'EMPTY')
        bad_filter = s['filter'] in ('MISSING', 'EMPTY', 'NO_MATCH', 'SUSPECT')
        if bad_link or bad_filter:
            note = ('  [' + '; '.join(s['notes']) + ']') if s['notes'] else ''
            print(f'  {s["lib"]}/{s["symbol"]}: link={s["link"]} '
                  f'fp="{s["footprint"] or ""}" filter={s["filter"]} '
                  f'"{s["filters"] or ""}"{note}')

    print('\n== Footprint -> 3D model ==')
    by = {}
    for m in r['models']:
        by.setdefault(m['status'], []).append(m)
    for k in sorted(by):
        print(f'  {k}: {len(by[k])}')
    for m in r['models']:
        if m['status'] not in ('LOCAL_OK', 'GLOBAL'):
            print(f'  {m["lib"]}/{m["footprint"]}: {m["status"]} {m["model"] or ""}')

    print('\n== Schematics ==')
    print('\n'.join(r['schematic_issues']) or 'OK (no issues)')
    print('\nNOTE: read-only static check. Not verified inside KiCad '
          '(table reload, footprint chooser list, model rendering).')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
