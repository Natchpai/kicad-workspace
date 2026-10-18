# Shared KiCad Library

Reusable KiCad libraries collected from earlier projects, merged into one layout.

| Directory | Contents | Count |
|---|---|---|
| `symbols/` | `0_<Family>.kicad_symdir/`, one `.kicad_sym` per symbol | 34 libraries, 86 symbols |
| `footprints/` | `0_<Family>.pretty/` | 29 libraries, 121 footprints |
| `3D/` | `<Name>/` with `.step` models | 23 folders, 77 models |
| `_extras/` | Files that are not libraries (zip, csv pin maps) | 5 files |

## Naming

- Library nickname = folder name without the extension, for example `0_Switch`. Nicknames are case-sensitive.
- 3D folder = footprint library name without the `0_` prefix, with the same letter case (`0_Capacitor_SMD.pretty` uses `3D/Capacitor_SMD/`).
- Local 3D path in a footprint: `${KIPRJMOD}/library/3D/<Name>/<file>`. Copy this folder into a project as `library/` so the path resolves.
- Footprints that use `${KICAD10_3DMODEL_DIR}/...` refer to KiCad's own models and are not stored here.
- Symbol, footprint and library names follow the KLC rules in [`KLC/`](KLC/README.md) (one file per rule), with the local `0_` prefix on library names.
- Local 3D model file = footprint name, plus an extra descriptor when one exists (vendor MPN, color, cable, state), for example `LED_0603_1608Metric_LiteOn_LTST-C190KFKT.step`. Each footprint has its own model file.

## Directory indexes

- [Symbols](SYMBOLS_DIRECTORY.md) lists every symbol library and member symbol.
- [Footprints](FOOTPRINTS_DIRECTORY.md) lists every footprint library and footprint.
- [3D models](3D_DIRECTORY.md) lists model folders and filenames.

## Categories

**Symbols:** Amplifier_Operational, Conn_Ethernet, Conn_Generic, Conn_Mezzanine, Conn_USB, Crystal, Diode, Driver_FET, Inductor, Interface_Ethernet, Interface_USB, Jumper, Logic_74x, MCU_ST_STM32G4, MCU_ST_STM32H7, Memory_DDR3, Memory_EEPROM, Memory_eMMC, Memory_Flash, Misc, Oscillator, Power_Management, Power_Switch, Protection_ESD, Protection_eFuse, Reference_Voltage, Regulator_DDR_VTT, Regulator_Linear, Regulator_Switching, Sensor_Current, Sensor_Temperature, SoC_AMD_Zynq, Switch, Transistor_FET.

**Footprints:** Capacitor_SMD, Conn_AMASS, Conn_Barrel, Conn_Ethernet, Conn_FFC, Conn_JST, Conn_Mezzanine, Conn_Molex, Conn_PinHeader, Conn_RF, Conn_USB, Crystal, Diode_SMD, Graphics, Inductor_SMD, LED_SMD, MountingHole, NetTie, Oscillator, Package_BGA, Package_DFN_QFN, Package_QFP, Package_SO, Package_SON, Package_TO_SOT_SMD, Resistor_SMD, SolderJumper, Switch, TestPoint.

## Known state

- 18 footprints have no 3D link on purpose: test points, net ties, logos, mounting holes, layer markers.
- Some 3D files are not referenced by any footprint yet (for example Molex Mini-Fit colour variants, `USB3320C-EZK-TR`, `ECS_2520MV`). They sit in the folder of their part type.
- `CP_Elec_Wuerth_WCAP-ASLI_*` and `L_Abracon_AOTA-B201208S` were merged from two sources whose 3D files differed. Their 3D link was filled with the remaining file; the other version was dropped.
- Some models are stand-ins from a similar part; the extra descriptor names the real model (for example `L_Chilisin_BDCD00201610_Bourns_CVH201205.step`).
- Symbols with an empty `Footprint` property are generic parts and are left as they are.
- `fp-lib-table` and `sym-lib-table` are not kept here. Add the libraries from the project that uses them.
- Not verified in KiCad itself: library loading and 3D rendering.

## Licensing warning

The 3D models, footprints and symbols here were copied from earlier projects and vendor downloads (for example Molex, TI, GCT, Amphenol, Würth, Murata). Their licenses and redistribution terms have not been checked. Verify them before making this repository public or sharing it outside your team, and remove anything you cannot redistribute.

## Maintenance

Use the `kicad-lib-organize` skill (`.claude/skills/kicad-lib-organize/`) when adding more libraries copied from other projects or renaming library items to KLC. Rules for Claude are in the root `CLAUDE.md`.
