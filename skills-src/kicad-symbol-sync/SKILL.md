---
name: kicad-symbol-sync
description: >-
  Split .kicad_sym into .kicad_symdir, align sym-lib-table, and fix symbol
  footprint links and filters (edits only with approval).
disable-model-invocation: true
argument-hint: "[split <lib> | sym-lib-table | footprint-links]"
---

# Symbol Sync

Symbol scope only. Footprint libraries, 3D models, and `fp-lib-table` are out
of scope (`kicad-footprint-sync` covers them, if installed). Edit only library folders, `sym-lib-table`, and the
`Footprint` and `ki_fp_filters` properties; leave pins, graphics and other
symbol content unchanged.

## Locate the project layout first
Do not assume paths. Find them, then use them for the rest of the task:
- **Project dir:** the folder with the `.kicad_pro` and `sym-lib-table`
  (this is what `${KIPRJMOD}` expands to).
- **Symbol root:** the folder holding the `*.kicad_symdir` / `*.kicad_sym`
  libraries, taken from the `uri` entries in `sym-lib-table`.
- **Footprint root:** the folder holding the `*.pretty` directories, taken from
  `fp-lib-table`.
- **kicad-cli:** on PATH, or under the KiCad install (on Windows usually
  `C:/Program Files/KiCad/<ver>/bin/kicad-cli.exe`). Check `--version` and
  `sym upgrade --help` before relying on the splitting behavior below.

## Authorization
- Follow the project's own rules first (for example `CLAUDE.md`, rule files).
  Native KiCad files and libraries are often read-only by default. Act only
  after the engineer explicitly authorizes the conversion, edits, and any
  deletion of a source `.kicad_sym` in the current conversation.
- Never edit hooks or permission settings to gain access. If a hook or deny rule
  blocks an authorized action, report it and let the human adjust it. Do not
  bypass it.
- Do not stage, commit, or push without separate approval; follow
  `rules/git-workflow.md` if present.

## Naming convention (follow the reference library)
Reference: the shared KiCad library repo whose path the human gives at the start
of the task. Ask for the path; never assume it, and never write a local path into
this file or any committed file. It is **read-only**: never edit, move, or copy
into it except when the human asks for a specific copy. Its `README.md` and
`SYMBOLS_DIRECTORY.md` / `FOOTPRINTS_DIRECTORY.md`, if present, list the correct
names. If no reference is given, say so and do not invent names. All names in it
are treated as correct.
- **Library folder:** `0_<Family>.kicad_symdir`, holding one `<Symbol>.kicad_sym`
  per symbol. The `0_` prefix belongs to the `.kicad_symdir` (and `.pretty`)
  folder name only. `<Family>` is `<Category>[_<Subcategory>]`, for example
  `MCU_ST_STM32H7`, `Regulator_Linear`, `Protection_ESD`.
- **Nickname** = folder name without `.kicad_symdir`, including `0_`
  (for example `0_MCU_ST_STM32H7`). Nicknames are case-sensitive.
- **`sym-lib-table` entry:** `name` = nickname, `uri` =
  `${KIPRJMOD}/<path to symbol root>/<folder>`, identical letter case.
- **Symbol `Footprint` property:** `0_<Family>:<footprint file name without
  .kicad_mod>`, where `0_<Family>` is a `.pretty` library from `fp-lib-table`.
- **Files inside** (`<Symbol>.kicad_sym` names and symbol names) use the
  reference's names exactly. The reference follows the KiCad Library Convention
  (KLC). Names come from the reference, never from your own KLC rebuild:
  renaming library items is the reference repo's job (`kicad-lib-organize`).
  When adding a symbol, find the comparable one in the reference and use its
  family.
- **Family not in the reference:** propose a name with the `kicad-naming` skill
  (it holds the KLC rules and the `0_` house rules), or, without that skill, a
  KLC library name (`0_` + function, sub-function, qualifier, manufacturer,
  series). Wait for the human to choose.
- **Renamed upstream:** when the reference renamed a symbol or footprint, build
  the old-to-current map with `kicad-link-audit`'s `scripts/rename_map.py` on the
  reference repo (`LINK old new` lines). Without that script or Git history,
  report the mismatches and ask.
- If the project's folder name differs from the reference for the same family
  (missing `0_`, case, spelling), report it and propose renaming the project's
  folder to the reference name. A rename changes the nickname, so also list
  every schematic `lib_id` and `sym-lib-table` reference to the old nickname.

## Split a .kicad_sym into a .kicad_symdir
`kicad-cli sym upgrade` splits a library only when the output path is an
**existing directory**. Without the directory it writes a single file named
`.kicad_symdir`, which is wrong. `--force` is required because the file is
usually already in the current format.

1. **Inspect (read-only).** List the symbol root, count source symbols with
   `grep -c '^	(symbol "' <lib>.kicad_sym` (top-level symbols only, one tab),
   and confirm no `<lib>.kicad_symdir` already exists.
2. **Check recoverability.** `git ls-files --error-unmatch <path>`. If the
   source is untracked, deleting it is irreversible: back it up to the scratch
   directory first.
3. **Convert.**
   ```bash
   cd <symbol root>
   mkdir 0_<Family>.kicad_symdir
   kicad-cli sym upgrade --force -o 0_<Family>.kicad_symdir <Lib>.kicad_sym
   ```
4. **Verify.** The file count in the new folder equals the source symbol count,
   and a sample file has the same header (`version`, `generator`) as another
   `.kicad_symdir` in the project, if any.
5. **Remove the source** `.kicad_sym` only when the human asked for it, after
   steps 2 and 4 succeed. Never delete before verification.

## Align sym-lib-table
Make `sym-lib-table` contain exactly one `lib` entry per `*.kicad_symdir`
folder (no extra, no missing), with `name` and `uri` matching the folder name
exactly. Keep empty libraries unless the human says to remove them.

## Audit symbol footprint links and ki_fp_filters
Read-only first. If `kicad-link-audit` is installed, run it to classify every
symbol's `Footprint` link and `ki_fp_filters` (its tables define the
categories). If it is not installed or cannot run, read
the `Footprint` and `ki_fp_filters` properties of every
`*.kicad_symdir/*.kicad_sym` (Grep with `-n false`; `grep -L` for files lacking
either) and compare with `*.pretty/*.kicad_mod` (`ls`).

Decide the action for each class:
- **Linked to a project-local footprint, file exists:** correct, except for a
  nickname whose letter case differs from the `.pretty` folder (fix the case).
- **Nickname not in `fp-lib-table`** (missing `0_`, or an old or unknown
  nickname such as `Package_QFP` or `0_LQFP`): if a `0_<Family>.pretty` library
  with the same footprint file exists, propose repointing to
  `0_<Family>:<footprint>`. Otherwise report it and ask which library is meant.
- **Linked to a global library:** report it. If an equivalent project-local
  footprint exists and the human wants local links, repoint to it.
- **Old upstream name** (the link text is a `LINK` old name in the rename map):
  propose repointing to the current `nickname:name` from the map.
- **Linked to local, file missing** (or library missing) and not in the rename
  map: keep as is and report footprint and library.
- **Empty Footprint:** generic parts (R, C, connectors, jumpers) stay as is
  unless the human says otherwise.

`ki_fp_filters` rules:
- Patterns are space-separated globs (`*`, `?`); a space splits a pattern, so
  `SOD 882` is two patterns and does not match `D_SOD-882`.
- Edit a filter only when it does not match the linked footprint name AND that
  footprint file exists. Leave correct filters untouched.
- If a symbol linked to an existing footprint has no filter, add one.
- Whether a pattern without a library prefix is matched against the name only
  or the full `lib:name` is `NOT_VERIFIED`; cite KiCad documentation before
  relying on it.

Edit procedure (these files are easy to break):
1. Make one file at a time, never a batch of edits across files.
2. Property blocks are indented with **tabs** (2 for the property line, 3
   inside). Copy the indentation from the file, not from a line-numbered Read
   view, which adds one extra tab.
3. A new `ki_fp_filters` property copies the block layout of the sibling
   `ki_keywords` property (`at`, `show_name`, `do_not_autoplace`, `hide yes`,
   `effects`), placed right after it.
4. After each file, re-grep the two properties and report the result.

## Check schematics
Grep `(lib_id "..."` in `*.kicad_sch`. For every nickname that refers to a
project-local library, confirm it matches `sym-lib-table` (case-sensitive) and
that the symbol exists in that library. Global libraries (`Device:`, etc.) are
out of scope. For a `lib_id` that is an old name in the rename map, report the
current name and suggest KiCad's Change Symbols or Update Symbols from Library
tool. Change schematics only when the human asks; a text edit must change both
the `lib_id` and the matching `(symbol "<lib_id>"` entry in the schematic's
`lib_symbols` cache.

## Report
- List created folders, removed files, and `sym-lib-table` changes.
- State where the backup of any removed untracked file was saved.
- State `NOT_VERIFIED` for anything not confirmed in KiCad itself: no content
  diff of pins/properties was done, and the library table must be reloaded by
  reopening the project.
