# Project Registry

One row per project. Add the row when the project starts. Never reuse a number.

## ID format

```text
NP-<YY><NN>         own project            NP-2602
NP-<PP>-<YY><NN>    co-op with partner PP  NP-AO-2601
```

- `NP`: owner and designer. Always first.
- `PP`: 2-letter partner code. Only for co-op projects. See Partner codes.
- `YY`: year the project started.
- `NN`: running number in that year, shared by all NP projects with or without a partner. The ID stays unique without the partner tag.
- The ID never changes, even if the project is renamed.
- `Doc code`: 2 to 4 letter code for the project's document numbers. See DOCUMENT_REGISTRY.md in the document-archive repo.

## Revision

- Title block `rev` field (`${REVISION}`), in the schematic and the PCB Page Settings: `<major>.<minor>`, for example `1.0`. New major for each fabricated board, new minor for changes that need no respin.
- KiCad text variable `PROJECT_ID` (Schematic Setup > Text Variables) holds the ID plus the version: `<ID>-V<major>-<minor>`, for example `NP-AO-2601-V1-0` for rev `1.0`.
- Update `PROJECT_ID` by hand when the revision changes, so its `V` part matches `rev`.
- PCB silkscreen mark: a text item `${PROJECT_ID}`, placed by hand.

## Partner codes

| Code | Partner |
| ---- | ------- |
| AO | AeroOptix Club |

## Projects

| ID | Doc code | Name | Started | Path |
| -- | -------- | ---- | ------- | ---- |
| NP-AO-2601 | AOH | AeroOptix-Horizon | 2026-10-08 | `D:\KiCAD\KiCAD Project\AeroOptix-Horizon` |
