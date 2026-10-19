---
name: hw-footprint-sync
description: >-
  Align footprint libraries, local 3D model folders and paths, fp-lib-table,
  and schematic footprint nicknames (edits only with approval).
disable-model-invocation: true
argument-hint: "[3d | fp-lib-table | schematic-nicknames | all]"
---

# Footprint Sync

Footprint scope only. Symbol libraries and `sym-lib-table` are out of scope
(`hw-symbol-sync` covers them, if installed). Edit only 3D folder names, local model path strings,
`fp-lib-table`, and nickname text in schematic Footprint properties; leave
connectivity, values, net names and geometry unchanged.

Keep the footprint libraries, the local 3D model folders, `fp-lib-table`, and
schematic Footprint references consistent. List the mismatches first, and
again after the edits to confirm them: with `hw-link-audit` if installed;
otherwise read the `(model ...)` paths, `fp-lib-table` entries and schematic
Footprint nicknames you will change and compare them with the folders on disk.

## Locate the project layout first
Do not assume paths. Find them, then use them for the rest of the task:
- **Project dir:** the folder with the `.kicad_pro` and `fp-lib-table`
  (this is what `${KIPRJMOD}` expands to).
- **Footprint root:** the folder holding the `*.pretty` directories, taken from
  the `uri` entries in `fp-lib-table`.
- **Local 3D root:** the folder holding project 3D models, taken from existing
  `(model "${KIPRJMOD}/...` paths in `.kicad_mod` files, or confirmed by the
  user if there is none yet.
- **Reference library:** the read-only naming reference (see Naming convention).
  Confirm the path exists before using it.

## Authorization
- Follow the project's own rules first (for example `CLAUDE.md`, rule files).
  Native KiCad files and libraries are often read-only by default. Edit only
  after the engineer explicitly authorizes it in the current conversation.
- Never edit hooks or permission settings to gain access. If a hook or deny rule
  blocks an authorized edit, report the blocker and let the human adjust it. Do
  not bypass it with shell commands.
- Do not stage, commit, or push without separate approval; follow
  `rules/git-workflow.md` if present.

## Naming convention (follow the reference library)
Reference: the shared KiCad library repo whose path the human gives at the start
of the task. Ask for the path; never assume it, and never write a local path into
this file or any committed file. It is **read-only**: never edit, move, or copy
into it except when the human asks for a specific copy. Its `README.md` and
`FOOTPRINTS_DIRECTORY.md` / `3D_DIRECTORY.md`, if present, list the correct
names. If no reference is given, say so and do not invent names. All names in it
are treated as correct.
- **Library folder:** `0_<Family>.pretty`. The `0_` prefix belongs to the
  `.pretty` (and `.kicad_symdir`) folder name only. `<Family>` is
  `<Category>[_<Subcategory>]`, for example `Package_QFP`, `Conn_USB`,
  `Resistor_SMD`.
- **Nickname** = `.pretty` folder name without the extension, including `0_`
  (for example `0_Package_QFP`). Nicknames are case-sensitive.
- **3D folder:** `<3D root>/<Family>/`, the `.pretty` name **without** `0_`, with
  identical letter case (`0_Capacitor_SMD.pretty` uses `3D/Capacitor_SMD/`).
  The 3D folder has no `0_` prefix.
- **Local model path** in `.kicad_mod`:
  `${KIPRJMOD}/<relative path to 3D root>/<Family>/<file>`, same letter case as
  the real folders (matters on case-sensitive systems).
- **Files inside** (`.kicad_mod` names, 3D model file names) use the reference's
  names exactly. The reference follows the KiCad Library Convention (KLC), and
  its 3D files are named `<footprint name>[_<extra>].step`. Names come from the
  reference, never from your own KLC rebuild: renaming library items is the
  reference repo's job (`kicad-lib-organize`). When adding or placing one, find
  the comparable item in the reference and use its family.
- **Family not in the reference:** propose a name with the `kicad-naming` skill
  (it holds the KLC rules and the `0_` house rules), or, without that skill, a
  KLC library name (`0_` + function, sub-function, qualifier, manufacturer,
  series). Wait for the human to choose.
- **Renamed upstream:** a project item whose name differs from the reference
  because the reference renamed it is migrated with step 7 of the procedure.
- If the project's folder name differs from the reference for the same family
  (missing `0_`, case, spelling), report it and propose renaming the project's
  folder to the reference name. A rename changes the nickname, so also list every
  schematic, PCB, symbol and `fp-lib-table` reference to the old nickname.
- Footprints whose model path uses a global variable (for example
  `${KICAD10_3DMODEL_DIR}`) are left unchanged.

## Procedure
1. **Inspect (read-only).** List the `*.pretty` folders (use `ls`; Glob does not
   match directories), list the local 3D root, and grep `(model "${KIPRJMOD}`
   in the `.kicad_mod` files. Re-list before every edit step: the human may
   rename folders in parallel.
2. **Rename 3D folders** to the `.pretty` name without `0_`. For case-only renames on
   Windows, move through a temporary name in two steps. Do not move or modify
   the `.step/.stp/.wrl` files themselves.
3. **Repoint local models.** For each `${KIPRJMOD}` model path, edit only that
   path string so it matches the actual file location and folder case.
4. **Report missing local 3D.** If a footprint references a local model whose
   file does not exist, do not edit it. Report footprint, referenced path, and
   expected folder. Never create 3D files. If the reference library holds a
   file of that name in the same family folder, say so (name only) and let the
   human decide whether to copy it; mention the licensing warning in the
   reference README.
5. **Align `fp-lib-table`.** Make `name` and `uri` of every `lib` entry match
   the `.pretty` folders exactly (no extra, no missing entries).
6. **Check schematics.** Grep `(property "Footprint" "...")` in `*.kicad_sch`
   and compare each nickname with `fp-lib-table`. Fix only the nickname text in
   the Footprint property, and only when the human asks. Do not alter any other
   field.
7. **Migrate upstream renames** (only when the reference renamed items). Build
   the old-to-current map with `hw-link-audit`'s `scripts/rename_map.py` on the
   reference repo; without that script or Git history, report the mismatches and
   ask. For each old name in use:
   - project library copy: propose refreshing the affected `.pretty` folders and
     3D folders from the reference; copy only when the human asks. The model
     path inside the current reference footprint is the authority for its 3D
     file (the map's `3D` lines are hints);
   - `fp-lib-table`: rename the nickname to the current folder name;
   - schematic `Footprint` properties: replace the old `nickname:name` text with
     the current one, only when the human asks;
   - `.kicad_pcb`: list footprints that still carry the old library link and let
     the human update them in KiCad (Tools > Update Footprints from Library, or
     Change Footprints). Do not edit the PCB file.
   On Windows, case-only renames (for example `.STEP` to `.step`) go through a
   temporary name, and Git records them only through `git rm --cached` plus
   `git add`; report them.
8. **Verify.** Re-grep model paths and confirm each local path resolves to an
   existing file. Search `.kicad_sch/.kicad_pcb/.kicad_pro` for old nicknames
   and old `nickname:name` text affected by a rename.

## Report
- List each change as `file: old -> new`.
- List missing local 3D files and unresolved mismatches.
- State `NOT_VERIFIED` for anything not confirmed in KiCad itself (library
  reload, model rendering). Remind the human to reopen the project, and to close
  schematic/PCB editors holding unsaved copies before external edits.
- Update any README in the 3D folder only if asked.
