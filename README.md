# KiCad Workspace

This repository keeps reusable KiCad project templates and shared symbols, footprints, and 3D models.

It is a personal archive, not an official KiCad library and not meant for contribution to the KiCad libraries. It follows the KiCad Library Convention (KLC) where that helps: names and working symbol, footprint and 3D model links. Some KLC rules are applied loosely or not at all.

## Repository contents

- project_template/: starter KiCad projects and project-specific resources.
- library/: shared KiCad symbol, footprint, and 3D model libraries (the archive).
- skills-src/: Git sources of the Claude Code skills that maintain the library. They run globally; see [Claude Code skills](#claude-code-skills).
- libDump/: temporary staging area for libraries imported from elsewhere, ignored by Git. Import moves usable files into library/ and gives them KLC names; files with unresolved conflicts may remain here for review.
- LICENSE: repository license. It covers the author's own work only; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party files.

## Shared library directories

- [Symbol directory](library/SYMBOLS_DIRECTORY.md): symbol libraries grouped by electrical function.
- [Footprint directory](library/FOOTPRINTS_DIRECTORY.md): footprint libraries grouped by package or physical family.
- [3D model directory](library/3D_DIRECTORY.md): 3D models organized to match footprint families.
- [Library guidance](library/README.md): naming and organization conventions.

## Naming

The shared library uses the [KiCad Library Convention](https://klc.kicad.org) (KLC) as a naming guide, with a local `0_` prefix on library names (for example `0_Package_QFP`, `0_Conn_USB`). Upstream-only details (fab layer text, model transforms, metadata polish) are not enforced.

- Rules: [library/KLC/](library/KLC/README.md), one file per KLC rule (general, symbols, footprints, 3D models).
- Checklist for new items: [library/KLC_CHECKLIST.md](library/KLC_CHECKLIST.md), with rules ranked by priority, script versus human checks, and step-by-step naming.
- 3D model file: footprint name plus an extra descriptor when one exists, for example `LED_0603_1608Metric_LiteOn_LTST-C190KFKT.step`.
- The library was renamed to these rules on 2026-10-18. Projects that still use old names can list old and current names with `python -I ~/.claude/skills/kicad-link-audit/scripts/rename_map.py .`.

## Workflow

This archive is the master library. Each project keeps its own copy as its `library/` folder, and parts move in two directions:

| Direction | When | How (ask Claude) |
|---|---|---|
| Project → archive | You made new parts in a project | "Publish my new parts from `<project>/library`." `kicad-lib-organize` copies only the parts the archive lacks, with KLC names; the project is not changed. |
| Other library → archive | You got a library from somewhere else | Put it in libDump/ and ask to import it. Files move into their families with KLC names; identical duplicates are dropped, differing conflicts stay in libDump/ for review. |
| Archive → project | The archive has newer or renamed parts | Run `kicad-link-audit` on the project, then ask for `kicad-footprint-sync` / `kicad-symbol-sync`. They change project files only with your approval. |

Day to day:

1. Start new designs from a suitable project under project_template/.
2. Keep project-specific design files and resources with their project.
3. Name new parts with `kicad-naming` while you design them; they then publish without a rename.
4. Publish new parts to the archive, and sync projects from it, as in the table above.
5. Review each design and its manufacturing outputs before fabrication.

## Claude Code skills

The KiCad skills run globally from `~/.claude/skills/`, in every project; their sources are in [skills-src/](skills-src/README.md), with install steps. Rules for Claude are in [CLAUDE.md](CLAUDE.md).

- kicad-naming: proposes and checks KLC names.
- kicad-lib-organize: imports libraries from libDump/ with KLC names, publishes new parts made in a project straight into library/ (without copying them here first), or renames library items to KLC. How to use it: [MANUAL.md](skills-src/kicad-lib-organize/MANUAL.md).
- kicad-link-audit: read-only check of symbol, footprint, 3D and library-table links.
- kicad-footprint-sync, kicad-symbol-sync: fix footprint and symbol links and library tables in a project, only when asked.

On a new machine, install them by running the copy loop in [skills-src/README.md](skills-src/README.md). Edit a skill in skills-src/ and reinstall it; changes made only in `~/.claude/skills/` are lost at the next install.

## Authority and scope

Native KiCad design and library files remain authoritative. README files and directory indexes document repository organization; they do not replace or modify KiCad design data. Each project still requires its own design review, verification, and release checks.
