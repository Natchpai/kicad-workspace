# CLAUDE.md

Workspace of reusable KiCad 10 resources: project templates and shared libraries. See `README.md` for the overview and `library/README.md` for the library layout.

## Layout

- `project_template/` : KiCad project templates. Each has its own project-local `library/` placeholders.
- `library/` : shared symbols, footprints and 3D models.
  - `symbols/0_<Name>.kicad_symdir/`, `footprints/0_<Name>.pretty/`, `3D/<Name>/`, `_extras/`.

## Library rules

- Nicknames are case-sensitive. Library nickname = folder name without extension.
- 3D folder name = `.pretty` name without `0_`, same letter case.
- Local model paths are `${KIPRJMOD}/library/3D/<Name>/<file>` (lowercase `library`). Leave `${KICAD10_3DMODEL_DIR}` paths alone.
- No `*_alt` files and no catch-all folders such as `_unassigned`. When two sources collide, keep the existing name; if their 3D files differ, leave the 3D link empty and report it.
- Do not create 3D or footprint files. Missing items are reported, not invented.
- Edit KiCad library files only when the user asks. Change only what the task needs (paths, nicknames, names), keep line endings, and re-check that parentheses balance.
- Do not edit hooks or permission settings to get around a block.

## Skills

- Local: `lib-organize` (`.claude/skills/lib-organize/`) merges and categorizes libraries copied from other projects.
- Global: `hw-link-audit` checks links read-only, `hw-footprint-sync` and `hw-symbol-sync` fix them. They expect `fp-lib-table` / `sym-lib-table`, which this repo does not keep; run them against a project that has the tables.

## Working notes

- The Claude Code sandbox may refuse to create folders or delete files in this repo. Report it and let the user run the script or authorize running outside the sandbox.
- Put scripts and backups in the scratchpad, not in the repo.
- Source folders copied in from projects are usually untracked. Back them up before deleting.
- Do not stage, commit, or push without being asked.
- Library loading and 3D rendering are `NOT_VERIFIED` until checked in KiCad.
