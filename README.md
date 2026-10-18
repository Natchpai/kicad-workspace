# KiCad Workspace

This repository keeps reusable KiCad project templates and shared symbols, footprints, and 3D models.

It is a personal archive, not an official KiCad library and not meant for contribution to the KiCad libraries. It follows the KiCad Library Convention (KLC) where that helps: names and working symbol, footprint and 3D model links. Some KLC rules are applied loosely or not at all.

## Repository contents

- project_template/ — Starter KiCad projects and project-specific resources.
- library/ — Shared KiCad symbol, footprint, and 3D model libraries.
- libDump/ — Temporary staging area for libraries imported from other projects, ignored by Git. Import moves usable files into library/ and gives them KLC names; files with unresolved conflicts may remain here for review.
- LICENSE — Repository license. It covers the author's own work only; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party files.

## Shared library directories

- [Symbol directory](library/SYMBOLS_DIRECTORY.md) — Symbol libraries grouped by electrical function.
- [Footprint directory](library/FOOTPRINTS_DIRECTORY.md) — Footprint libraries grouped by package or physical family.
- [3D model directory](library/3D_DIRECTORY.md) — 3D models organized to match footprint families.
- [Library guidance](library/README.md) — Naming and organization conventions.

## Naming

The shared library uses the [KiCad Library Convention](https://klc.kicad.org) (KLC) as a naming guide, with a local `0_` prefix on library names (for example `0_Package_QFP`, `0_Conn_USB`). Upstream-only details (fab layer text, model transforms, metadata polish) are not enforced.

- Rules: [library/KLC/](library/KLC/README.md), one file per KLC rule (general, symbols, footprints, 3D models).
- Checklist for new items: [library/KLC_CHECKLIST.md](library/KLC_CHECKLIST.md), with rules ranked by priority, script versus human checks, and step-by-step naming.
- 3D model file: footprint name plus an extra descriptor when one exists, for example `LED_0603_1608Metric_LiteOn_LTST-C190KFKT.step`.
- The library was renamed to these rules on 2026-10-18. Projects that still use old names can list old and current names with `python -I .claude/skills/hw-link-audit/scripts/rename_map.py .`.

## Workflow

1. Start new designs from a suitable project under project_template/.
2. Keep project-specific design files and resources with their project.
3. Reuse shared resources from library/ when appropriate.
4. To import reusable libraries, stage them under libDump/ and request categorization. Files are moved into their matching shared library families and renamed to KLC; identical duplicates are consolidated, while differing conflicts are retained for review.
5. Review each design and its manufacturing outputs before fabrication.

## Claude Code skills

Project skills live in .claude/skills/; rules for Claude are in [CLAUDE.md](CLAUDE.md). Global skills run from `~/.claude/skills/` in every project; their sources are in [skills-src/](skills-src/README.md).

- kicad-naming (global): proposes and checks KLC names.
- kicad-lib-organize (global): imports libraries from libDump/ with KLC names, publishes new parts made in a project straight into library/ (without copying them here first), or renames library items to KLC. How to use it: [MANUAL.md](skills-src/kicad-lib-organize/MANUAL.md).
- hw-link-audit: read-only check of symbol, footprint, 3D and library-table links.
- hw-footprint-sync, hw-symbol-sync: fix footprint and symbol links and library tables in a project, only when asked.

## Authority and scope

Native KiCad design and library files remain authoritative. README files and directory indexes document repository organization; they do not replace or modify KiCad design data. Each project still requires its own design review, verification, and release checks.
