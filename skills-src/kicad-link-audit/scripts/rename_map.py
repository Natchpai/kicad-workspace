"""Old -> current names for a KiCad library repo, from its Git rename history. Read-only.

Usage: python -I rename_map.py <library repo dir> [--root library]

Prints tab-separated lines, oldest names chained to the name that exists now:
    LINK  <old nickname>:<old name>  <new nickname>:<new name>   (footprints and symbols, the text used
                                                                  in Footprint properties and lib_id)
    3D    <old folder>/<old file>    <new folder>/<new file>
    PATH  <old repo path>            <new repo path>             (everything else under the root)
Only renames whose final path still exists are printed.
"""
import os, subprocess, sys

repo = sys.argv[1]
root = sys.argv[sys.argv.index('--root') + 1] if '--root' in sys.argv else 'library'


def git(*args):
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True, check=True).stdout


current = set(git('ls-files', '--', root).splitlines())
chain = {}  # old path -> newest path
for line in git('log', '--reverse', '-M', '--diff-filter=R', '--name-status', '--format=', '--', root).splitlines():
    parts = line.split('\t')
    if len(parts) != 3 or not parts[0].startswith('R'):
        continue
    old, new = parts[1], parts[2]
    for k, v in chain.items():
        if v == old:
            chain[k] = new
    chain[old] = new


def link(path):
    d, f = os.path.split(path)
    lib = os.path.basename(d)
    for ext_dir, ext_file in (('.pretty', '.kicad_mod'), ('.kicad_symdir', '.kicad_sym')):
        if lib.endswith(ext_dir) and f.endswith(ext_file):
            return f'{lib[:-len(ext_dir)]}:{f[:-len(ext_file)]}'


for old, new in sorted(chain.items()):
    if new not in current or old == new:
        continue
    lo, ln = link(old), link(new)
    if lo and ln:
        if lo != ln:
            print(f'LINK\t{lo}\t{ln}')
    elif old.startswith(f'{root}/3D/'):
        print(f'3D\t{"/".join(old.split("/")[-2:])}\t{"/".join(new.split("/")[-2:])}')
    else:
        print(f'PATH\t{old}\t{new}')
