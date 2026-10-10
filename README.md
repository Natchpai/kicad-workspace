# KiCad Workspace

This repository is a collection of reusable KiCad resources. It is intended to keep project templates and KiCad libraries that have been created or collected for reuse across future projects.

## Repository contents

- `project_template/` — KiCad project templates, including their starter project files, documentation folders, worksheet templates, and project-local library locations.
- `library/` — Shared, repository-level KiCad libraries created for reuse across projects. This is the home for reusable symbols, footprints, and 3D models.
- `LICENSE` — Repository license.

## Intended workflow

1. Start a new KiCad project from a suitable directory under `project_template/`.
2. Rename the new project and update its project-specific metadata.
3. Reuse shared resources from `library/` when appropriate.
4. Keep project-specific resources inside the project when they should not be shared globally.
5. Review the schematic, PCB, libraries, and generated manufacturing outputs before fabrication.

## Authority and scope

Native KiCad files such as `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `.kicad_sym`, and footprint library files remain authoritative. README files describe directory purpose and usage; they do not replace or modify KiCad design data.

This repository stores reusable starting points and libraries. Each project created from a template still requires its own design review, verification, and release checks.
