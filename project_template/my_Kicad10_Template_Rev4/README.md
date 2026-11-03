# my_Kicad10_Template_Rev4

Reusable KiCad 10 project template.

## Layout

- `documents/` — Design, image, manufacturing, schematic, and verification documents.
- `library/` — Project-local 3D, footprint, and symbol library locations.
- `meta/` — Template metadata and icon files.
- `templates/` — Reusable notes, themes, and worksheet templates.
- `*.kicad_pro`, `*.kicad_sch`, `*.kicad_pcb` — Native KiCad project, schematic, and PCB files.

Native KiCad files in this directory are the design authority.

## Revisions

Set the revision in the schematic and PCB title blocks (`rev`). Sheets and worksheets show it through `${REVISION}`.

- Revisions use letters: `A`, `B`, `C`, ...
- A revision with variants adds a number: `A-1`, `A-2`, ...
- A revision without variants keeps the single letter: `A`, `B`.
- The `Rev4` in the template name is the template version, not a project revision.

## Directory tree

```text
my_Kicad10_Template_Rev4/
├── documents/
│   ├── README.md
│   ├── design/
│   │   └── README.md
│   ├── images/
│   │   ├── README.md
│   │   └── Logos/
│   │       ├── README.md
│   │       ├── NP_logo_black_smallsize.png
│   │       └── NP_logo_color.png
│   ├── manufacturing/
│   │   ├── README.md
│   │   ├── Assembly/
│   │   │   ├── README.md
│   │   │   └── BOM/
│   │   │       └── README.md
│   │   └── Fabrication/
│   │       ├── README.md
│   │       └── Gerbers/
│   │           └── README.md
│   ├── schematic/
│   │   └── README.md
│   └── verification/
│       └── README.md
├── library/
│   ├── README.md
│   ├── 3D/
│   │   └── README.md
│   ├── footprints/
│   │   └── README.md
│   └── symbols/
│       └── README.md
├── meta/
│   ├── README.md
│   ├── icon.png
│   └── info.html
├── templates/
│   ├── README.md
│   ├── assembly_notes.txt
│   ├── fabrication_notes.txt
│   ├── impedance_table.txt
│   ├── my_Theme.json
│   ├── V2-0_MyCustomTemplate_A3_CGFont_Fabri.kicad_wks
│   ├── V2-0_MyCustomTemplate_A3_CGFont_Sche.kicad_wks
│   ├── V2-0_MyCustomTemplate_A3_CGFont.kicad_wks
│   ├── V2-0_MyCustomTemplate_A4_CGFont_Fabri.kicad_wks
│   ├── V2-0_MyCustomTemplate_A4_CGFont_Sche.kicad_wks
│   └── V2-1_MyCustomTemplate_A3_CGFont_Sche.kicad_wks
├── my_Kicad10_Template_Rev4.kicad_pcb
├── my_Kicad10_Template_Rev4.kicad_prl
├── my_Kicad10_Template_Rev4.kicad_pro
├── my_Kicad10_Template_Rev4.kicad_sch
└── README.md
```
