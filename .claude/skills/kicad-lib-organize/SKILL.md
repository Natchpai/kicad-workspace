---
name: kicad-lib-organize
description: Import KiCad symbols, footprints and 3D models from a staging folder (libDump/) into a local library tree's families with KLC names, or rename existing library items to KLC. Use when the user asks to categorize, organize or import a library from another project, or to KLC-rename library files. Keeps Footprint links and 3D paths working; leaves differing conflicts in the staging folder.
---

# KiCad Library Organize

Works in any repository or KiCad project that keeps its own library tree: a library folder (`library/` by default) holding `symbols/0_<Family>.kicad_symdir/`, `footprints/0_<Family>.pretty/` and `3D/<Family>/`, with model paths `${KIPRJMOD}/<library folder>/3D/...`. For another folder name, pass `--lib <folder>` to both scripts.

Two branches share one procedure:

- **Import**: the source is the staging folder, libDump/ unless the user names another. Each file moves into its library family and takes its KLC name in the same run.
- **Rename**: the source is the library folder itself, when the user asks to rename existing items to KLC.

A direct request to import, categorize or rename authorizes the moves and renames below. Finish the run without pausing for approval of routine items; leave conflicts and uncertain items as described and report them.

## Authority

- Naming: the global `kicad-naming` skill. Call it for every family, symbol, footprint and 3D model name; it holds the KLC rules and the house rules (`0_` prefix, 3D folder and model file names). A project `CLAUDE.md` with its own naming rules adds to it.
- Layout and families: the live library tree and any index files that list its members. Inspect them; never hardcode a family list.
- kicad-cli: the location the project `CLAUDE.md` gives; else `kicad-cli` on PATH; else the KiCad install folder (Windows: `C:/Program Files/KiCad/<version>/bin/kicad-cli.exe`).

## The map

Every action comes from one **map**: a JSON file in the scratchpad with one entry per symbol, footprint and model (format in the docstring of `scripts/klc_apply.py`). Build the whole map before touching any file. The script applies it; you never rename by hand.

What goes in the map:

- **Family**: symbols by electrical function, footprints by physical package or connector family, models by the footprints that actually reference them. Reuse an existing family; create one only when no family fits and the items clearly belong together.
- **Name**: the KLC name. A size, pitch, layout, maker or orientation field goes in only when it is confirmed, from footprint geometry (pad pitch, pad count, pad rows) or from a source. Use the `web-research` agent for datasheet facts, one agent per group of parts, in parallel. Leave unconfirmed fields out of the name. If not even a base name is clear, keep the imported name and list it as uncertain.
- **3D model**: named by the `kicad-naming` 3D model rule. A model shared by several footprints gets one map entry per footprint (the script copies it). A model no footprint uses keeps its part-number name; fix only its characters and extension. Global `${KICAD10_3DMODEL_DIR}` references stay as they are.
- **Link fixes**: stale `Footprint` nicknames found during inspection, under `link_fixes`.

Collisions, checked case-insensitively against the destination:

- Byte-identical file already in the destination: keep the destination, drop the import (confirm equality directly), and leave it out of the map.
- Same name, different content: leave the import in the staging folder and report it. Never overwrite, merge, or pick a version without the user.
- Two different items that would get the same KLC name: name the second by its real difference (`_ThermalVias_Via0.4mm`, `_NoCourtyard`), and list it as a conflict in the report.

## Steps

1. **Inspect.** Check `git status`. For an import, inventory the staging folder by type and source library, and skip project files. Split packed multi-symbol `.kicad_sym` libraries into `.kicad_symdir` first (`kicad-cli sym upgrade --force -o <name>.kicad_symdir <lib>.kicad_sym`). Read each symbol's `Footprint` property and each footprint's `(model ...)` paths.
   Done when every source file is listed as symbol, footprint, model or other, and every footprint-to-model and symbol-to-footprint reference is known.

2. **Build the map**, using the rules above.
   Done when every symbol, footprint and model file has a map entry, a consolidation note, or a reason to stay in place.

3. **Apply**, in order, from the folder that holds the library folder, with a dry run before each real run:
   ```
   python -I <skill dir>/scripts/klc_apply.py <map.json> sym|fp|3d [--dry] [--lib <folder>]
   ```
   `sym` renames symbols. `fp` renames footprints and rewrites matching symbol `Footprint` properties. `3d` moves or copies models and rewrites their footprint paths. The script edits bytes (line endings kept), changes only name, Value, Footprint and model lines, and stops on a collision or an unexpected edit.
   Done when all three steps have run with no stop.

4. **Verify.**
   - Run `python -I <skill dir>/scripts/klc_verify.py [--lib <folder>]`. It must print `all checks passed`.
   - Parse every new or renamed file with kicad-cli: `sym export svg` and `fp export svg --fp <name>`, with output in the scratchpad. Footprint export is slow (about 10 s each), so run it in the background.
   - Rename branch: compare each renamed file against its HEAD version. Only name, Value, Footprint and model lines may differ, and model bytes must match.
   - Optionally, have a read-only agent re-check names and links against the map.
   Done when every check passes, or each failure is reported with its path.

5. **Refresh indexes**: every doc that lists library members or counts (find them by Grep for an old name and for a family name, for example `*DIRECTORY.md` and README member tables), and any doc line naming a renamed item. With no such docs, skip this step.
   Done when every count and name in those files matches the disk.

6. **Report**:
   - counts moved, renamed, copied and consolidated, plus final library counts;
   - what stays in the staging folder and why;
   - conflicts, and names built on unconfirmed facts;
   - checks run, with `NOT_VERIFIED` for KiCad GUI loading and 3D rendering;
   - pre-existing Git changes, preserved.

   List every case-only rename (for example `.STEP` to `.step`). Git on Windows ignores case, so at commit time each one needs `git rm --cached <old>` plus `git add <new>`, or the old case stays in the repository. Do not stage or commit unless asked.

## Never changed

Pins, units, graphics, hidden fields and other symbol properties; footprint pads, geometry and `ki_fp_filters`; model file contents and model transforms (offset, scale, rotate); projects, schematics, PCB files, and fp-lib-table / sym-lib-table (use hw-footprint-sync or hw-symbol-sync for those, when asked).
