---
name: lib-organize
description: Merge and categorize KiCad libraries copied from other projects into this workspace's library/{3D,footprints,symbols} layout. Use when the user adds a folder of symbols, footprints and 3D models (for example library/Library_fromXxx) and wants it merged, de-duplicated, renamed to the 0_ convention, and its 3D links repaired. Edits and deletes files only after the engineer approves the plan.
---

# Library Organize

Merge copied KiCad libraries into the shared layout of this repo. Link
verification belongs to `hw-link-audit`; table alignment to `hw-footprint-sync`
and `hw-symbol-sync`. This skill only categorizes and merges.

## Target layout (`library/`)
- `footprints/0_<Name>.pretty/` : one folder per footprint category.
- `symbols/0_<Name>.kicad_symdir/` : one `<Symbol>.kicad_sym` per symbol.
- `3D/<Name>/` : `<Name>` is the `.pretty` name without `0_`, same letter case.
- `_extras/` : non-library files (zip, csv, datasheets).
- No `fp-lib-table` / `sym-lib-table` here unless the user asks.

## Conventions
- Library nicknames are case-sensitive. Pick one spelling per library
  (`0_Switch`, not `0_switch`) and apply it to footprints, 3D folders and symbol
  `Footprint` properties together.
- Local model path: `${KIPRJMOD}/library/3D/<Name>/<file>` (lowercase `library`).
  Leave `${KICAD10_3DMODEL_DIR}/...` paths unchanged.
- Folders without the `.pretty` / `.kicad_symdir` suffix are normalized.
  3D files sitting inside a `.pretty` folder move to `3D/`.
- Symbol libraries of the same family (for example `Regulator_*`) may be merged.
  Ask before merging anything not obviously the same family.

## Procedure
1. **Inspect (read-only).** List sources, count files by extension, find name
   collisions across sources (case-insensitive) with hashes: IDENTICAL or
   DIFFERENT. List which `${KIPRJMOD}` model paths exist and which do not.
2. **Present the plan and ask** before writing: how to treat DIFFERENT
   duplicates, final layout, loose files. Do not guess.
3. **Dry-run script** in the scratchpad (never in the repo). It should print
   every move, rename and rewrite, then run with an `exec` flag.
   - Copy to the target first. Never delete a source until step 5.
   - Identical files are merged into one. Same name with different content is
     handled as the user decided. The usual choice is to keep the primary
     source's name and drop the other, with no `_alt` files left behind.
   - Rewrite only: model path strings, symbol `Footprint` nicknames, and the
     file/symbol name when a duplicate is renamed.
   - Read and write with `newline=''` to keep CRLF/LF as they are.
4. **Verify** (read-only): every local model path resolves, every symbol
   `Footprint` resolves to an existing footprint, parentheses balance in edited
   `.kicad_mod`, no leftover `_alt` or `_unassigned`.
5. **Back up, then delete the sources.** Zip the source folders into the
   scratchpad first (they are usually untracked in git), then remove them.
6. **Report.** Footprints with no 3D link, unreferenced 3D files, and links to
   global libraries are listed, not fixed. Never create 3D or footprint files.
   State `NOT_VERIFIED` for anything not confirmed in KiCad itself.

## 3D handling rules
- Move each model to the folder of the footprint that references it.
- Models no footprint references go to the folder of the matching category
  (by part type), not into a catch-all folder.
- When two footprints of the same name reference different model files and the
  user wants no duplicates, keep the primary footprint and, if the models
  differ, clear the `(model ...)` block and report it. Fill it later only when a
  matching existing file is found, restoring the original offset, scale, rotate.
- Footprints that legitimately have no 3D (test points, net ties, logos,
  mounting holes, layer markers) are not an error.

## Pitfalls
- The Claude Code sandbox may refuse to create folders or delete files in this
  repo (`Could not find file` or `Permission denied`). Report it and let the
  user run the script (`! python -I <script> exec`) or authorize running
  outside the sandbox. Do not work around it silently.
- Windows is case-insensitive: rename case-only changes through a temporary name.
- Do not stage, commit, or push without separate approval.
