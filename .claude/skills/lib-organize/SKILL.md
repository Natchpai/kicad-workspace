---
name: lib-organize
description: Move imported KiCad symbols, footprints, and 3D models from libDump into this repository's existing library families. Use when the user asks to categorize, organize, or import a library from another project. Preserves differing conflicts in libDump and updates only local 3D paths affected by a move.
---

# Library Organize

Categorize imported KiCad library files in this repository. The normal source is libDump/; the destination is the existing library/ tree. Treat a direct request to categorize or organize the import as authorization to carry out the moves in this skill. Do not stop after presenting a proposal or ask for approval for routine, reversible moves.

## Scope

- Move library files into existing symbol, footprint, and 3D family directories.
- Update directory indexes already maintained in the repository when membership changes.
- Change only local 3D model path strings made stale by a model move.
- Leave unresolved files in libDump/ and report them.

Do not modify project files, schematics, PCB files, symbol pin or graphic data, symbol Footprint properties, footprint geometry, model transforms, or 3D model contents. Do not synchronize library tables or perform Symbol–Footprint linking; use the dedicated sync skills when separately requested. Ignore project directories and project files inside an import folder.

## Repository layout

Use the live repository and directory indexes as the authority. Typical locations are:

- library/symbols/0_<Family>.kicad_symdir/
- library/footprints/0_<Family>.pretty/
- library/3D/<Family>/ (family name without the 0_ prefix)
- libDump/ for incoming libraries and files that cannot yet be safely categorized

Do not hardcode a family list. Inspect current nonempty libraries and indexes before choosing destinations. Preserve existing 0_ nicknames and spelling. Create a new family only when the imported content clearly belongs together and no current family is suitable. Do not create empty libraries.

## Move and collision rules

- Move unique files with a filesystem move/rename. Do not copy first, make backup copies, or create archive zips.
- Before moving, detect exact and case-insensitive name collisions across the source and destination.
- If a destination file is byte-identical, keep the destination and consolidate the redundant import. Confirm equality directly; do not calculate hashes.
- If a same-name destination differs, leave the imported file in libDump/. Never overwrite, rename to an _alt name, merge, or choose a preferred version without explicit direction.
- Preserve uncertain classifications in libDump/ and continue with the files that can be safely categorized.
- Keep unrelated documents and assets in the import folder unless they are clearly part of the library index update. Do not discard unreferenced models or unknown files.
- Remove only empty source library directories after their contents have been accounted for.

## Classification

- Classify symbols by electrical function and inspect each symbol, especially in mixed source libraries. Preserve symbol names, inheritance, pins, units, graphics, properties, and hidden fields.
- Classify footprints by physical package or connector family using footprint metadata and geometry, not just the symbol function or filename. Preserve filenames and all footprint content.
- Classify 3D models by actual footprint references and package evidence. Preserve model filename, extension, bytes, and transforms. Do not infer a package family from a model filename alone.
- For a model referenced by multiple families, a collision, or a model with no reliable family evidence, preserve it in libDump/ until its destination is clear. Do not duplicate a model merely to satisfy multiple folders.
- Preserve global model references such as KICAD10_3DMODEL_DIR. For local references, inspect the repository's existing convention; do not assume KIPRJMOD points to the repository root.
- When a moved local model makes an imported footprint path stale, update only the model path string. Keep offset, scale, rotation, and all other footprint text unchanged. Do not edit unrelated existing footprints to repair broad link issues.

## Workflow

1. **Inspect**
   - Check Git status and read applicable repository instructions.
   - Inventory import files by type and source library. Exclude project files/directories from the categorization scope.
   - Enumerate current destination libraries and indexes.
   - Detect name collisions, exact duplicates, inheritance, footprint-to-model references, shared models, missing models, and uncertain items.
   - Do not generate hashes, checksum manifests, or scripts unless requested.

2. **Categorize and move**
   - Apply clear source-to-family mappings and move the files.
   - Consolidate only byte-identical destination duplicates.
   - Leave differing collisions and uncertain files in libDump/; continue safe moves without pausing for a proposal approval.
   - Update only local model paths affected by moved models.
   - Do not modify tables, projects, symbol footprint links, or unrelated files.

3. **Verify**
   - Account for every imported library file as moved, consolidated with an identical destination, or preserved in libDump/ with a reason.
   - Recount destination libraries, symbols, footprints, and models; refresh existing indexes.
   - Check that moved files exist at their destinations and no destination was overwritten.
   - Validate moved symbols and footprints with KiCad CLI when available. For unpacked symbol libraries, validate the individual symbol files with a supported KiCad command.
   - Verify all affected local 3D paths resolve and that path edits did not change transforms.
   - Report checks that cannot be confirmed as NOT_VERIFIED. Do not claim a full library-link audit unless separately performed.

4. **Report**
   - Summarize moved and consolidated counts, final library counts, files left in libDump/, differing collisions, uncertain classifications, path updates, and validation results.
   - Mention pre-existing unrelated Git changes and confirm they were preserved.
   - Do not commit or push.

## Completion

Finish the requested categorization in the current repository. Do not stop at an inventory or migration plan. Preserve unresolved data for review and state clearly what remains in libDump/ and why.
