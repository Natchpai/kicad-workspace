# CLAUDE.md

Instructions for working in this KiCad 10 workspace. See README.md for the repository overview and library/README.md for the shared library guide.

## Layout

- project_template/ contains reusable KiCad project templates and project-local resources.
- library/ contains shared symbols, footprints, and 3D models. Its directory indexes are library/SYMBOLS_DIRECTORY.md, library/FOOTPRINTS_DIRECTORY.md, and library/3D_DIRECTORY.md.
- libDump/ is the temporary staging area for imported libraries. It may be absent when there is no pending import.

## Library organization

- Use the current library directories and indexes as the source of truth; do not hardcode family lists or create empty libraries.
- Preserve the 0_ prefix and existing library spelling. Classify symbols by electrical function, footprints by physical package or connector family, and 3D models using actual footprint references and package evidence.
- When the user asks to categorize or organize an import in libDump/, move unique files into library/. Do not copy them first or create backup archives. Consolidate a same-name file only after directly confirming it is byte-identical to the destination.
- Leave differing collisions, uncertain classifications, shared models without a safe destination, and unknown files in libDump/ and report them. Never overwrite, delete, merge, or rename a differing item without explicit direction.
- Preserve symbols, inheritance, pins, properties, footprint pads and geometry, model files, and model transforms. Do not rename individual symbols or footprints for cosmetic consistency.
- Update only local 3D path strings made stale by a model move. Keep global KiCad model references unchanged and follow the path convention already used in the affected library.
- Do not edit symbol Footprint properties, perform Symbol–Footprint linking, or synchronize fp-lib-table/sym-lib-table during categorization. Use the dedicated sync skills only when separately requested.
- Do not modify projects, schematics, PCB files, or files outside the requested library scope.
- Refresh the existing library indexes after membership changes. Do not create migration reports, manifests, hashes, or scripts unless requested.
- Validate moved files and affected local 3D references with KiCad tools when available; state NOT_VERIFIED for checks that could not be performed.

## Licensing

Vendor model and library redistribution terms may be unchecked. Before publishing or sharing the repository, remind the user to verify applicable licenses. Do not add vendor files without recording their source when known.

## Skills

- Local: lib-organize at .claude/skills/lib-organize/SKILL.md handles move-based import categorization from libDump/.
- Global: hw-footprint-sync and hw-symbol-sync handle separately requested 3D/footprint and symbol/footprint synchronization.

## Git and workspace safety

- Inspect Git status before edits and preserve unrelated working-tree changes.
- Do not stage, commit, or push unless asked.
- Do not bypass filesystem permissions or edit hooks/settings to get around a block.
- Report pre-existing changes and scope any cleanup to files the user named.
- KiCad CLI parsing does not by itself verify interactive library loading or rendered 3D appearance; report those checks separately when relevant.
