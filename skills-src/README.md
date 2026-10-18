# Global skill sources

Git-tracked sources of the Claude Code skills that run globally, from `~/.claude/skills/`. Claude does not load skills from this folder, so each skill runs from one place only: the global copy.

| Skill | What it does | Global install |
|---|---|---|
| `kicad-naming` | Proposes and checks KLC names for symbols, footprints, 3D models and library families. Holds the KLC rules in `references/KLC/` | `~/.claude/skills/kicad-naming/` |
| `kicad-lib-organize` | Imports, publishes from a project, or renames library items with KLC names. User manual: [kicad-lib-organize/MANUAL.md](kicad-lib-organize/MANUAL.md) | `~/.claude/skills/kicad-lib-organize/` |

The per-project skills (`hw-link-audit`, `hw-footprint-sync`, `hw-symbol-sync`) stay in `.claude/skills/` and are copied into each project.

## Install or update

Edit here, commit, then copy to the global folder:

```
cp -r skills-src/kicad-naming/. ~/.claude/skills/kicad-naming/
cp -r skills-src/kicad-lib-organize/. ~/.claude/skills/kicad-lib-organize/
```

Check with `diff -r skills-src/<skill> ~/.claude/skills/<skill>`. Edit only here; changes made in the global copy are lost at the next install.

`kicad-naming/references/KLC/` is a copy of `library/KLC/`. When the KLC rules are updated, update both.
