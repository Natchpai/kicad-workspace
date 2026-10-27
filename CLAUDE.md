# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

KiCad 10 workspace with reusable project templates and a shared library of symbols, footprints, and 3D models. There is no build or test system; the content is KiCad library data.

This is the user's personal archive on GitHub, not an official KiCad library and not an upstream contribution. See README.md for the repository overview and library/README.md for the shared library guide.

## Layout

- project_template/ contains reusable KiCad project templates and project-local resources.
- library/symbols/0_<Family>.kicad_symdir/ holds unpacked symbol libraries, one .kicad_sym file per root symbol.
- library/footprints/0_<Family>.pretty/ holds footprint libraries.
- library/3D/<Family>/ holds models. The folder name is the footprint library name without `0_`, same letter case (`0_Capacitor_SMD.pretty` uses `3D/Capacitor_SMD/`).
- library/_extras/ holds non-library files (zip, csv pin maps).
- Directory indexes: library/SYMBOLS_DIRECTORY.md, library/FOOTPRINTS_DIRECTORY.md, library/3D_DIRECTORY.md. Counts and member lists also appear in library/README.md, library/symbols/README.md, and library/footprints/README.md.
- libDump/ is the temporary staging area for imported libraries. It may be absent or empty when there is no pending import.
- Local 3D paths use `${KIPRJMOD}/library/3D/<Family>/<file>`; a project copies this tree in as its own library/ folder. `${KICAD10_3DMODEL_DIR}/...` points to KiCad's stock models, which are not stored here.
- fp-lib-table and sym-lib-table are not kept here; projects add the libraries themselves.

## Commands

kicad-cli is not on PATH. Use `"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"` (10.0.7). Its `sym` and `fp` commands offer only `export` and `upgrade`; there is no library linter. Use SVG export into the scratchpad as a parse check:

```sh
kicad-cli sym export svg -o <scratch dir> library/symbols/0_Diode.kicad_symdir/SL34A.kicad_sym
kicad-cli fp export svg -o <scratch dir> --fp D_SMA library/footprints/0_Diode_SMD.pretty
```

Do not use `sym upgrade` or `fp upgrade` as a check; they rewrite files.

Read-only link audit (needs a folder with a .kicad_pro and library tables, such as a project):

```sh
python -I ~/.claude/skills/kicad-link-audit/scripts/audit_links.py <project dir>
```

## Naming rules (KiCad KLC)

The KLC rule files are the naming authority. library/KLC/ holds one file per rule, converted from the official KLC source (klc.kicad.org), with library/KLC/README.md as the index:

- library/KLC/general/G*.md (general), library/KLC/symbol/S*.md (symbols), library/KLC/footprint/F*.md (footprints), library/KLC/model/M*.md (3D models)
- Naming rules: G1.1 to G1.6, G1.9, G2.1, S1.1, S2.1 to S2.3, F1.1, F1.2, F2.1 to F2.5, F3.1 to F3.7

The "How to naming" sections in library/symbols/README.md and library/footprints/README.md are short summaries. Where they differ from the KLC files, follow the KLC files.

**Strictness.** KLC is a guideline here. Always keep the critical parts: allowed characters, true facts in names, functional variants (package, pinout, voltage, current range) in symbol names, and symbol, footprint and 3D links that resolve. Cosmetic or upstream-only rules (hard-to-source optional fields such as BGA ball diameter or pitch, exact MPN wildcard form, fab text, model transforms, metadata polish) may be relaxed; say which rule was relaxed and why.

**Scope.** The library was renamed to these rules on 2026-10-18. Apply them to new library families, to symbols and footprints you create, to imports (kicad-lib-organize renames them on import), and to any name you propose. An item keeps its current name only when its KLC name cannot be confirmed; report it. A rename must also update the symbol `Footprint` properties and 3D model paths that point to the renamed item.

**3D model files.** A local model is named `<footprint name>[_<extra>].step`. The extra descriptor is added when the model carries information the footprint name does not: vendor MPN, stand-in part, color, cable, or state (for example `LED_0603_1608Metric_LiteOn_LTST-C190KFKT.step`). Each footprint has its own model file. Models not used by any footprint keep their part-number names.

**Library names (G1.3, S1.1, F1.1, F1.2)**

- Folder name is `0_` + KLC library name. The KLC name joins these elements with `_`, in this order, skipping unused ones: function, sub-function, tertiary qualifier, manufacturer, series, extra descriptor. Examples: `0_Sensor_Temperature`, `0_MCU_ST_STM32G4`, `0_Conn_USB`.
- Symbol libraries group by electrical function, not by manufacturer.
- Connector footprint libraries group by primary function first (`Conn_USB`, `Conn_Ethernet`). Connectors without a specific function group by mechanical type (`Conn_PinHeader`, `Conn_Barrel`). Multi-purpose connector series may group by manufacturer and series (`Conn_JST`, `Conn_Molex`).
- Use an existing family when one fits before creating a new one.

**General (G1)**

- Allowed characters in file, library, symbol, footprint, and model names: `A-Z a-z 0-9 _ - . , +`. No spaces.
- Singular words (`Sensor_Temperature`, not `Sensors_Temperature`). American English (`Color`).
- Acronyms in capitals (`MCU`, `FPGA`). Manufacturer names as the maker writes them (`ROHM`, `Texas`). CamelCase inside a field (`TestPoint`, `BatteryHolder`).
- Dimensions always carry units, millimeters preferred, order X x Y [x Z], unit written once (`3x4x7mm`).
- LF line endings in library files. No embedded files or fonts in symbols or footprints.

**Symbol names (S2, G2)**

- Do not repeat the library name in the symbol name.
- Fully specified symbols use the MPN. Replace non-functional MPN parts with lowercase `x` and drop a trailing wildcard (`INA180Ax`). Keep functional variants (voltage, package, pinout) in the name. Skip the wildcard when only one functional variant exists.
- Compatible parts from several makers with different package suffixes: common base part plus package suffix (`L78L05_TO92`). Same symbol name from several manufacturers: manufacturer first.
- Generic symbols use the device type; short forms are fine (`Conn_01x06`, `D`, `C`). Arrays add the element count (`_x8`). Modified variants append the reason (`Q_NPN_CBE`, `_Split`).
- One symbol per package option. Pin-compatible variants derive from the base symbol.
- Generic symbols (Device-type parts, connectors, logic families) leave Footprint empty. Fully specified symbols set it.

**Footprint names (F2, F3)**

- Field order, joined by `_`, each field optional: `<Package>-<pins>[-<n>EP|SH|MP]`, body `LxW[xH]mm`, pin layout (`1x10`), pitch `P<x>mm`, modifiers (`Drill1.0mm`, `Pad2.4x5.2mm`), orientation (`Horizontal`, `Vertical`), modification reason (`ThermalVias`, `HandSoldering`). Examples: `QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias`, `JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal`.
- Prefixes (F2.2): `B` body, `D` diameter, `H` height, `L` length, `W` width, `O` offset, `T` thickness, `P` pitch, `EP` exposed pad. Spell other parameters in full (`Ball`, `Layout14x14`, `Clearance`, `StackHeight`).
- A footprint specific to one manufacturer starts with manufacturer and MPN (`Texas_S-PVQFN-N48_...`).
- Packages with omitted pins: `<Package>-<remaining>-<total>` (`MSOP-12-16`).
- Type-specific schemes are in KLC F3 (library/KLC/footprint/F3.1.md to F3.7.md): SMD chip packages, resistors, capacitors (chip, tantalum, electrolytic, THT), SMD ICs (gullwing, no-lead, BGA), THT ICs (DIP, TO), connectors, fuses. Read the matching section before naming that type.

## Library organization

- Use the current library directories and indexes as the source of truth; do not hardcode family lists or create empty libraries.
- Preserve the 0_ prefix and existing library spelling. Classify symbols by electrical function, footprints by physical package or connector family, and 3D models using actual footprint references and package evidence.
- When the user asks to categorize or organize an import in libDump/, move unique files into library/. Do not copy them first or create backup archives. Consolidate a same-name file only after directly confirming it is byte-identical to the destination.
- Leave differing collisions, uncertain classifications, shared models without a safe destination, and unknown files in libDump/ and report them. Never overwrite, delete, merge, or rename a differing item without explicit direction.
- Preserve symbols, inheritance, pins, properties, footprint pads and geometry, model files, and model transforms. Names change only to KLC names, through the kicad-lib-organize map.
- Update only local 3D path strings made stale by a model move or rename. Keep global KiCad model references unchanged.
- Edit symbol Footprint properties only to follow a renamed or moved footprint. Other Symbol–Footprint linking and fp-lib-table/sym-lib-table sync belong to the dedicated sync skills, when separately requested.
- Do not modify projects, schematics, PCB files, or files outside the requested library scope.
- Refresh the existing library indexes after membership or name changes. Keep maps and helper output in the scratchpad; do not add migration reports, manifests, hashes, or scripts to the repository unless requested.
- Validate moved files and affected local 3D references with KiCad tools when available; state NOT_VERIFIED for checks that could not be performed.

## Licensing

Vendor model and library redistribution terms may be unchecked. Before publishing or sharing the repository, remind the user to verify applicable licenses. Do not add vendor files without recording their source when known.

## Skills

All eight KiCad skills, plus engineering-report-pdf, run globally from `~/.claude/skills/`; their Git sources are in skills-src/, which Claude does not load. This repo and the projects keep no local copies. Edit a skill in skills-src/, then copy it over the global folder (skills-src/README.md).

- kicad-naming: proposes and checks KLC names; the naming authority for every other skill.
- kicad-lib-organize: imports from libDump/ into library families with KLC names, publishes a project's new parts into this library (copies only; the project is not written), KLC-renames existing items, or copies stock KiCad symbols and footprints unchanged (stock_copy.py). Map-driven, with bundled diff, apply and verify scripts. User manual: skills-src/kicad-lib-organize/MANUAL.md.
- kicad-part-start: makes a new part's starting point in a project library: stock symbol, footprint and 3D model when they fit the datasheet, else a first-cut symbol from a pin spec (make_symbol.py), plus lib-table lines. Datasheet tables come through NotebookLM.
- kicad-footprint-make: draws a footprint from a JSON spec of datasheet land-pattern and stencil values (make_footprint.py), and checks a footprint against a spec or another footprint (fp_check.py). Used by kicad-part-start when stock has no fit.
- kicad-link-audit: read-only audit of symbol Footprint properties, 3D paths, library tables, and schematic nicknames.
- kicad-footprint-sync and kicad-symbol-sync: user-invoked only (`disable-model-invocation`). They handle separately requested 3D/footprint and symbol/footprint synchronization.
- engineering-report-pdf: user-invoked only. Builds a PDF engineering report in the NP template from Markdown; not a KiCad library skill.

## Git and workspace safety

- Inspect Git status before edits and preserve unrelated working-tree changes.
- Do not stage, commit, or push unless asked.
- Do not bypass filesystem permissions or edit hooks/settings to get around a block.
- Report pre-existing changes and scope any cleanup to files the user named.
- KiCad CLI parsing does not by itself verify interactive library loading or rendered 3D appearance; report those checks separately when relevant.
