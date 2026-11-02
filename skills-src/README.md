# Global skill sources

Git-tracked sources of the Claude Code skills that run globally, from `~/.claude/skills/`. Claude does not load skills from this folder directly. Each global skill is a symlink to its folder here, so there is one copy only.

| Skill | What it does | Global install |
|---|---|---|
| `kicad-naming` | Proposes and checks KLC names for symbols, footprints, 3D models and library families. Holds the KLC rules in `references/KLC/` | `~/.claude/skills/kicad-naming/` |
| `kicad-lib-organize` | Imports, publishes from a project, or renames library items with KLC names, or copies stock KiCad parts into a `0_` library. User manual: [kicad-lib-organize/MANUAL.md](kicad-lib-organize/MANUAL.md) | `~/.claude/skills/kicad-lib-organize/` |
| `kicad-part-start` | Makes a new part's starting point in a project library: stock symbol, footprint and 3D model copied in when they fit the datasheet (read through NotebookLM), else drawn with `kicad-symbol-make` and `kicad-footprint-make` | `~/.claude/skills/kicad-part-start/` |
| `kicad-footprint-make` | Draws a footprint from datasheet land-pattern and stencil values (`scripts/make_footprint.py`, spec in `SPEC.md`), and checks any footprint against a spec or another footprint (`scripts/fp_check.py`) | `~/.claude/skills/kicad-footprint-make/` |
| `kicad-symbol-make` | Draws a symbol from a datasheet pin table (`scripts/make_symbol.py`, input in `SPEC.md`), and checks any symbol against KLC, a pin table, another symbol or its footprint (`scripts/sym_check.py`) | `~/.claude/skills/kicad-symbol-make/` |
| `kicad-link-audit` | Read-only check of symbol, footprint, 3D model and library-table links in a project; `scripts/rename_map.py` lists old and new names from this repo's history | `~/.claude/skills/kicad-link-audit/` |
| `kicad-footprint-sync` | Aligns footprint libraries, local 3D folders and paths, `fp-lib-table` and schematic footprint nicknames in a project. Runs only when you ask | `~/.claude/skills/kicad-footprint-sync/` |
| `kicad-symbol-sync` | Splits `.kicad_sym` into `.kicad_symdir`, aligns `sym-lib-table`, fixes symbol footprint links and filters in a project. Runs only when you ask | `~/.claude/skills/kicad-symbol-sync/` |

Projects keep no copies of these skills; they all run through the global symlinks. The `engineering-report-pdf` skill moved to the document-archive repo (`C:\Users\AORUS\Documents\Github\document-archive\skills-src\`).

## Install or update

Each global skill is a symlink to its folder here, so edits take effect at once. Set the links up once per machine, from the repo root:

```
for s in kicad-naming kicad-lib-organize kicad-part-start kicad-footprint-make kicad-symbol-make kicad-link-audit kicad-footprint-sync kicad-symbol-sync; do
  ln -s "$PWD/skills-src/$s" ~/.claude/skills/$s
done
```

Check with `ls -l ~/.claude/skills`. If a real folder is already there, move it away first. After an edit, commit here; there is no copy step.

`kicad-naming/references/KLC/` is a copy of `library/KLC/`. When the KLC rules are updated, update both.
