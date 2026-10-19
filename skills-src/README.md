# Global skill sources

Git-tracked sources of the Claude Code skills that run globally, from `~/.claude/skills/`. Claude does not load skills from this folder, so each skill runs from one place only: the global copy.

| Skill | What it does | Global install |
|---|---|---|
| `kicad-naming` | Proposes and checks KLC names for symbols, footprints, 3D models and library families. Holds the KLC rules in `references/KLC/` | `~/.claude/skills/kicad-naming/` |
| `kicad-lib-organize` | Imports, publishes from a project, or renames library items with KLC names. User manual: [kicad-lib-organize/MANUAL.md](kicad-lib-organize/MANUAL.md) | `~/.claude/skills/kicad-lib-organize/` |
| `kicad-link-audit` | Read-only check of symbol, footprint, 3D model and library-table links in a project; `scripts/rename_map.py` lists old and new names from this repo's history | `~/.claude/skills/kicad-link-audit/` |
| `kicad-footprint-sync` | Aligns footprint libraries, local 3D folders and paths, `fp-lib-table` and schematic footprint nicknames in a project. Runs only when you ask | `~/.claude/skills/kicad-footprint-sync/` |
| `kicad-symbol-sync` | Splits `.kicad_sym` into `.kicad_symdir`, aligns `sym-lib-table`, fixes symbol footprint links and filters in a project. Runs only when you ask | `~/.claude/skills/kicad-symbol-sync/` |

Projects keep no copies of these skills; they all run from the global folder.

## Install or update

Edit here, commit, then copy to the global folder:

```
for s in kicad-naming kicad-lib-organize kicad-link-audit kicad-footprint-sync kicad-symbol-sync; do
  cp -r skills-src/$s/. ~/.claude/skills/$s/
done
```

Check with `diff -r skills-src/<skill> ~/.claude/skills/<skill>`. Edit only here; changes made in the global copy are lost at the next install.

`kicad-naming/references/KLC/` is a copy of `library/KLC/`. When the KLC rules are updated, update both.
