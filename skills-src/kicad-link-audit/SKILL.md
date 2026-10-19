---
name: hw-link-audit
description: >-
  Read-only audit of KiCad library links: symbol Footprint properties and
  ki_fp_filters, footprint 3D model paths, fp-lib-table and sym-lib-table
  against folders, and schematic nicknames. Use when the user asks whether
  symbols, footprints, 3D models and library tables are linked correctly, or
  wants a link check before or after reorganizing libraries. Reports only;
  does not fix links.
argument-hint: "[project dir]"
---

# Link Audit

Static, read-only check of the link chain:

```
schematic symbol (lib_id) -> symbol (Footprint, ki_fp_filters)
  -> footprint file (.kicad_mod) -> 3D model file (.step/.stp/.wrl)
fp-lib-table / sym-lib-table <-> library folders on disk
```

This skill checks links and files, not electrical correctness. A
datasheet-level check of one part's symbol or footprint (pinout, land pattern)
is separate work (`component-check`, if installed).

This skill never edits files. Fixes need the engineer's explicit
authorization; if installed, `hw-footprint-sync` (3D paths, `fp-lib-table`,
schematic footprint nicknames) and `hw-symbol-sync` (symbol links, filters,
`sym-lib-table`) apply them.

## Run
```bash
python -I <skill dir>/scripts/audit_links.py <project dir>
```
- `<project dir>` is the folder with `.kicad_pro` and the library tables; the
  script also searches a few parent folders for it.
- Standard library only.
- A library whose files yield no parsed symbols (for example unexpected
  indentation) is reported under the table issues, never as a pass.
- If the script cannot run (no Python, unusual layout), do the same checks by
  hand with `ls`, Grep, and the rules below, and say so in the report.

## What it checks and how to read the result

**Library tables vs folders**
- A table entry whose path does not exist, a nickname that differs from its
  folder name, or a library folder with no table entry.
- Entries using variables other than `${KIPRJMOD}` are not resolved: report them.

**Symbol -> footprint link** (`link=`)

| Value | Meaning | Action |
|---|---|---|
| `LOCAL_OK` | local library, footprint file exists | none |
| `LOCAL_FILE_MISSING` | local library, no such `.kicad_mod` | report; keep link |
| `LOCAL_NAME_CASE` | file exists but name differs in case | report |
| `NICKNAME_CASE` | nickname differs from the table only in case | report |
| `GLOBAL` | nickname maps to a non-project library | report |
| `GLOBAL_OR_UNKNOWN` | nickname is not in `fp-lib-table` (global library or typo) | report; confirm which |
| `EMPTY` | no footprint assigned | normal for generic parts |
| `MALFORMED` | no `lib:name` form | report |

**`ki_fp_filters`** (`filter=`): `MATCH`, `NO_MATCH` (no pattern matches the
linked, existing footprint), `MISSING`, `EMPTY`, `SUSPECT` (several
space-separated tokens and no wildcard, so each token is a separate exact
pattern, e.g. `SOD 882`), `UNCHECKED` (footprint file missing, nothing to
compare). Matching follows KiCad (`common/footprint_filter.cpp`): a pattern
with `:` is matched against `nickname:name`, any other pattern against the
name only; case-insensitive, whole string. So `Connector*:*_1x??_*` never
matches a local library whose nickname does not start with `Connector`.

**Footprint -> 3D model**
`LOCAL_OK`, `LOCAL_MISSING` (file not found), `LOCAL_CASE_MISMATCH` (found only
with different letter case; breaks on case-sensitive systems), `GLOBAL`
(standard variable such as `${KICAD10_3DMODEL_DIR}`, not checked),
`UNRESOLVED_VAR`, `NO_MODEL`.

**Schematics**
Footprint nicknames not in `fp-lib-table` (or differing in case), local
footprints that do not exist, `lib_id` nicknames that differ in case or whose
symbol is missing from a local library. Global libraries (`Device:` and so on)
are ignored.

## Renamed upstream
A link can break because the shared library the project copied from renamed
the item (for example a library `Conn_BarrelJack` renamed to `Conn_Barrel`).
When that reference library repo, with its Git history, is available, build the
old-to-current name map:
```bash
python -I <skill dir>/scripts/rename_map.py <library repo dir>
```
It prints `LINK old new` for footprint and symbol links (`nickname:name`, the
text in `Footprint` properties and `lib_id`), `3D old new` for model files,
chained across every rename in history. For each `LOCAL_FILE_MISSING`,
`GLOBAL_OR_UNKNOWN`, or missing local model, look the old text up and report the
current name next to the defect. The `3D` lines are hints only: a model copied
for a second footprint maps to the first footprint's file, so the model path
inside the current reference footprint is the authority.

## Report
1. Counts per category, then the failing items grouped by library, with the
   current upstream name for items found in the rename map.
2. Separate **confirmed defects** (missing file, case mismatch, filter that
   cannot match an existing footprint) from **items needing a decision**
   (global links, empty footprints, links to files not yet created).
3. Do not propose creating 3D or footprint files; say what is missing.
4. State `NOT_VERIFIED` for what a static check cannot show: library table
   reload, filter behavior in the footprint chooser, model rendering. Remind the
   human that only saved files are inspected and that open editors may hold
   unsaved changes.
