# Shared KiCad Library

Reusable KiCad libraries collected from earlier projects, merged into one layout.

| Directory | Contents | Count |
|---|---|---|
| `symbols/` | `0_<Name>.kicad_symdir/`, one `.kicad_sym` per symbol | 30 libraries, 74 symbols |
| `footprints/` | `0_<Name>.pretty/` | 32 libraries, 120 footprints |
| `3D/` | `<Name>/` with `.step` / `.stp` models | 23 folders, 72 files |
| `_extras/` | Files that are not libraries (zip, csv pin maps) | 5 files |

## Naming

- Library nickname = folder name without the extension, for example `0_Switch`. Nicknames are case-sensitive.
- 3D folder = footprint library name without the `0_` prefix, with the same letter case (`0_C_SMD.pretty` uses `3D/C_SMD/`).
- Local 3D path in a footprint: `${KIPRJMOD}/library/3D/<Name>/<file>`. Copy this folder into a project as `library/` so the path resolves.
- Footprints that use `${KICAD10_3DMODEL_DIR}/...` refer to KiCad's own models and are not stored here.

## Categories

**Symbols:** AMD_Zynq, Conn_Mezzanine, Conn_USB, Connectors, Crystal, CurrentSensors, Diode, EEPROM, E-Fuse, eMMC, GateDrivers, Inductor, Interface_Ethernet, Interface_USB, MagJack, Memory_DDR3, Miscellaneous, Mosfet, OPAMP, Oscillator, PMICs, Power_Switch, Protection, QSPI_Flash, Regulators, SN47xSeries, STM32G4, Switch, TempSense, VREF.

**Footprints:** ACS3703X, AMD_SoC, BGA, C_SMD, Conn, Conn_FFC, Conn_JST, Conn_Mezzanine, Conn_USB, Crystal, DFN, Diode, Diode_SMD, GateDrivers, Inductor, Infineon_MOSFET, LED, LQFP, MagJack, Miscellaneous, net_tie, Oscillator, QFN, R_SMD, SOD, SOIC, SOT, Switch, symbols, TestPoints, VSON, WSON.

## Known state

- 18 footprints have no 3D link on purpose: test points, net ties, logos, mounting holes, layer markers.
- Some 3D files are not referenced by any footprint yet (for example Molex Mini-Fit colour variants, `USB3320C-EZK-TR`, `ECS_2520MV`). They sit in the folder of their part type.
- `CP_Elec_*_WCAP-ASLI` and `L_AOTA-B201208S` were merged from two sources whose 3D files differed. Their 3D link was filled with the remaining file; the other version was dropped.
- Symbols with an empty `Footprint` property are generic parts and are left as they are.
- `fp-lib-table` and `sym-lib-table` are not kept here. Add the libraries from the project that uses them.
- Not verified in KiCad itself: library loading and 3D rendering.

## Licensing warning

The 3D models, footprints and symbols here were copied from earlier projects and vendor downloads (for example Molex, TI, GCT, Amphenol, Würth, Murata). Their licenses and redistribution terms have not been checked. Verify them before making this repository public or sharing it outside your team, and remove anything you cannot redistribute.

## Maintenance

Use the `lib-organize` skill (`.claude/skills/lib-organize/`) when adding more libraries copied from other projects. Rules for Claude are in the root `CLAUDE.md`.
