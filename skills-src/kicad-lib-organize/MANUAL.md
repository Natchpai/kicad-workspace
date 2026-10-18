# kicad-lib-organize: user manual

This skill puts KiCad symbols, footprints and 3D models into a `0_<Family>` library tree, with names that follow the KiCad Library Convention (KLC). It keeps every link working: symbol `Footprint` properties and footprint 3D model paths.

This manual is for you, the engineer. Claude reads `SKILL.md`; you read this file.

## Where it lives

| Copy | Path | Role |
|---|---|---|
| Global (used in every project) | `~/.claude/skills/kicad-lib-organize/` | What Claude runs |
| Source (in Git) | `kicad-workspace/skills-src/kicad-lib-organize/` | Version history; edit here, then reinstall (see [Update the global copy](#update-the-global-copy)). Not loaded as a skill, so only the global copy runs. |

## What you need

- **Claude Code**, with the global `kicad-naming` skill installed. It holds the KLC naming rules this skill follows.
- **Python 3.** The scripts use the standard library only.
- **kicad-cli** (KiCad 10), for the parse check. Claude looks for it on PATH, then in `C:/Program Files/KiCad/<version>/bin/`.
- **A library tree** with this layout. The folder is named `library/` by default; any other name works with `--lib`:

  ```
  library/
    symbols/0_<Family>.kicad_symdir/<Symbol>.kicad_sym    one symbol per file
    footprints/0_<Family>.pretty/<Footprint>.kicad_mod
    3D/<Family>/<model>.step                              folder = footprint library name without 0_
  ```

  Local model paths in footprints are `${KIPRJMOD}/library/3D/<Family>/<file>`.

## The three modes

| Mode | Use it when | Source | What happens to the source |
|---|---|---|---|
| **Import** | You have a library from somewhere else | A staging folder (`libDump/` by default) | Files move out of it into the library |
| **Publish** | You made new parts inside a project and want them in the archive | The project's own library folder | Nothing; only copies go to the archive |
| **Rename** | Items already in the library have non-KLC names | The library itself | Files are renamed in place |

Every mode follows the same steps:
1. Inspect the source.
2. Build one rename **map**.
3. Apply the map: dry run, then the real run.
4. Verify.
5. Refresh the index files.
6. Report.

Claude never renames files by hand; the script applies the map.

### Import

1. Put the files in `libDump/` in the target repo. Any folder structure works. Split packed multi-symbol `.kicad_sym` files first, or let Claude do it.
2. Ask Claude:

   > Import libDump into the library.

3. Claude moves each file into its family with its KLC name, then updates links and 3D paths.
   - Files that are byte-identical to ones already in the library are dropped.
   - Same name with different content stays in `libDump/` and is reported.

### Publish (project to archive)

Use this when you design parts inside a project, for example `AeroOptix-Horizon/hardware/AO-Horizon/library/`, and want them in `kicad-workspace/library/`. You copy nothing by hand.

1. In either session (the project's or the archive's), ask Claude:

   > Publish my new parts from `<project>/hardware/<board>/library` to the archive at `<path to kicad-workspace>`.

2. Claude runs `lib_diff.py` and sorts every item:

   | Result | Meaning | Action |
   |---|---|---|
   | IDENTICAL | The archive already has it, same content | Nothing |
   | DIFFERS | Same name, different content | Reported, never overwritten. You decide. |
   | OTHER NAME | The archive has the same content under another name (usually it was renamed there) | Reported |
   | NEW | Not in the archive | Published |
   | PACKED | A multi-symbol `.kicad_sym` library | Split it first |

3. NEW items are copied into the archive with KLC names. The project is not written; Claude checks this with a hash list before and after.
4. The report has an `old -> new` list for every part the archive named differently. To make the project use the archive names, ask for `hw-footprint-sync` / `hw-symbol-sync` in the project.

**Tip:** name parts with `kicad-naming` while you design them in the project ("what should I name this footprint?"). Then most parts publish with no rename.

### Rename

> Rename the items in `0_Package_SON` to KLC names.

Claude renames files and internal names, and fixes every symbol `Footprint` property and 3D path that pointed at the old names. Projects that use the old names keep them until you sync them.

## What it never changes

- **Symbols:** pins, units, graphics, and properties other than name, Value and Footprint.
- **Footprints:** pads, geometry and `ki_fp_filters`.
- **3D models:** file contents and transforms (offset, scale, rotate).
- **Projects:** schematics, PCB files, `fp-lib-table` and `sym-lib-table`. Use `hw-footprint-sync` / `hw-symbol-sync` for these.

The script checks each edited file: only name, Value, Footprint and model lines may change. Any other change stops it with `UNEXPECTED EDIT`.

## The scripts

All scripts are in `scripts/` under the skill folder. Run them with `python -I`. On Windows with a non-UTF-8 console, add `-X utf8`.

### `lib_diff.py` (read-only)

```
python -I lib_diff.py <source library dir> [--root <archive root>] [--lib <library folder>]
```

Compares a project library with `<root>/<lib>` and prints the five groups above. For NEW items it also prints their links: a symbol's `Footprint`, a footprint's model paths. Names are matched case-insensitively across all families. Line endings are ignored.

### `klc_apply.py`

```
python -I klc_apply.py <map.json> sym|fp|3d [--dry] [--lib <folder>] [--root <dir>] [--copy]
```

- Run the steps in order (`sym`, `fp`, `3d`), each with `--dry` first.
  - `sym` renames symbols.
  - `fp` renames footprints and updates the matching symbol `Footprint` properties.
  - `3d` moves or copies models and updates their footprint paths.
- `--root <dir>`: work in `<dir>`, the destination repo, instead of the current folder.
- `--copy`: never touch the source; write renamed copies to the destination. Publish always uses `--copy --root <archive>`. It also works across drives (project on `D:`, archive on `C:`).
- Each dry run checks only its own step. A `3d` dry run fails until `fp` has really run, because the renamed footprint must exist first.

Map format (JSON). `src` is relative to the root, or an absolute path for Publish:

```json
{
  "symbols":    [{"src": "<path>/X.kicad_sym", "dst_lib": "0_Regulator_Linear", "new": "TPS73533DRB"}],
  "footprints": [{"src": "<path>.pretty/old.kicad_mod", "dst_lib": "0_Package_SON", "new": "VSON-8-1EP_3x3mm_P0.65mm_EP1.5x1.75mm_ThermalVias"}],
  "models":     [{"src": "<path>/old.step", "dst": "library/3D/Package_SON/<new>.step", "footprint": "0_Package_SON:<new footprint>"}],
  "link_fixes": {"<old lib:name>": "<new lib:name>"}
}
```

A model used by two footprints gets two `models` entries; the second one is copied, so each footprint has its own file.

### `klc_verify.py` (read-only)

```
python -I klc_verify.py [--lib <folder>] [--root <dir>]
```

It checks:
- File names equal internal names.
- Every symbol `Footprint` resolves.
- Every `${KIPRJMOD}` model path resolves with exact letter case and lies under `<lib>/3D/`.
- Names use only `A-Z a-z 0-9 _ - . , +`.

It must print `all checks passed`.

## Troubleshooting

| Message or symptom | Cause | What to do |
|---|---|---|
| `COLLISION: <path>` | The target name already exists (case-insensitive) | Check if it is the same part. If yes, drop it from the map; if not, name it by its real difference (`_NoCourtyard`) |
| `UNEXPECTED EDIT in <file>` | The rename would change a line other than name/Value/Footprint/model | Usually the old name also appears in other text. Report it; fix the file by hand first |
| `expected one root symbol` | A packed multi-symbol `.kicad_sym` | Split it: `kicad-cli sym upgrade --force -o <name>.kicad_symdir <lib>.kicad_sym` |
| `missing model (exact case)` | A 3D path points to a file that is missing, or differs in letter case | Fix the path or the file name. Windows ignores case, but Linux and macOS do not |
| `model outside library/3D/` | A local model is stored outside the library's 3D folder | Move it into `3D/<Family>/` through the map |
| An old file name stays in Git after a case-only rename | Git on Windows ignores case | `git rm --cached <old>` then `git add <new>` |

## Update the global copy

Edit the source in `kicad-workspace/skills-src/`, commit it, then copy it over the global one:

```
cp -r kicad-workspace/skills-src/kicad-lib-organize/. ~/.claude/skills/kicad-lib-organize/
```

Check the copy afterwards with `diff -r` between the two folders. Edit only the source; a change made in the global copy is lost at the next install. The same applies to `kicad-naming` (see `skills-src/README.md`).
