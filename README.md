# KiCad Workspace

This repository keeps reusable KiCad project templates and shared symbols, footprints, and 3D models.

## Repository contents

- project_template/ — Starter KiCad projects and project-specific resources.
- library/ — Shared KiCad symbol, footprint, and 3D model libraries.
- libDump/ — Temporary staging area for libraries imported from other projects. Categorization moves usable files into library/; files with unresolved conflicts may remain here for review.
- LICENSE — Repository license. It covers the author's own work only; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party files.

## Shared library directories

- [Symbol directory](library/SYMBOLS_DIRECTORY.md) — Symbol libraries grouped by electrical function.
- [Footprint directory](library/FOOTPRINTS_DIRECTORY.md) — Footprint libraries grouped by package or physical family.
- [3D model directory](library/3D_DIRECTORY.md) — 3D models organized to match footprint families.
- [Library guidance](library/README.md) — Naming and organization conventions.

## Workflow

1. Start new designs from a suitable project under project_template/.
2. Keep project-specific design files and resources with their project.
3. Reuse shared resources from library/ when appropriate.
4. To import reusable libraries, stage them under libDump/ and request categorization. Files are moved into their matching shared library families; identical duplicates are consolidated, while differing conflicts are retained for review.
5. Review each design and its manufacturing outputs before fabrication.

## Authority and scope

Native KiCad design and library files remain authoritative. README files and directory indexes document repository organization; they do not replace or modify KiCad design data. Each project still requires its own design review, verification, and release checks.
