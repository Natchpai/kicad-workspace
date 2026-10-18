---
name: kicad-naming
description: Propose or check KLC names for a KiCad symbol, footprint, 3D model or library family, with the user's 0_ library prefix and 3D model naming rules. Use when the user asks what to name a new part, package or library, or whether a name follows KLC. Advises only; does not create or rename files.
argument-hint: "[MPN, package or name to check]"
---

# KiCad Naming Guide

Two branches:

- **Propose**: the user has a part (MPN, datasheet, package) and wants names for its symbol, footprint, 3D model and library family.
- **Check**: the user gives one name, a list, or a whole library. Grade each name and give the corrected name.

This skill writes no library files. It works in any repository, or with no repository at all.

## Authority

1. The **house rules** below: the user's own conventions on top of KLC.
2. The **KLC rule files** in `references/KLC/`: one file per rule, converted from the official KLC source (version and commit in `references/KLC/README.md`). They win over the quick rules below when the two differ.
3. A repository's own naming rules (its CLAUDE.md or library README), if the current repository has them and they are stricter.
4. **Stock KiCad names.** A name that is exactly the stock KiCad library name for the same item passes (`Jumper:Jumper_2_Open`, `SW_SPDT_PCM12`, `Package_SO`).

Read the KLC rule files that match the item before naming or grading it. Paths are under `references/KLC/`:

| Item | Read |
|---|---|
| Any name: characters, singular, case, units | `general/G1.1.md`, `G1.4.md` to `G1.6.md`, `G1.9.md` |
| Library family | `general/G1.3.md`, `symbol/S1.1.md`, `footprint/F1.1.md`, `footprint/F1.2.md` (connectors) |
| Generic or fully specified symbol | `general/G2.1.md` |
| Symbol name, MPN wildcard, package variants | `symbol/S2.1.md` to `S2.3.md` |
| Footprint field order and prefixes | `footprint/F2.1.md`, `F2.2.md`; `F2.3.md` maker-specific; `F2.4.md` omitted pins; `F2.5.md` specific components |
| Footprint for a known type | `footprint/F3.1.md` SMD chip, `F3.2.md` resistor, `F3.3.md` capacitor, `F3.4.md` SMD IC (gullwing, no-lead, BGA), `F3.5.md` THT IC (DIP, TO), `F3.6.md` connector, `F3.7.md` fuse |
| 3D model content (not file names; those follow the house rules) | `model/M1.1.md` to `M2.3.md` |

`references/KLC/README.md` lists every rule with its title. The F3 patterns write `<Field>` for a variable field and `[ ]` around optional parts; every field outside `[ ]` is required.

## Strictness

KLC is a guideline. Sort each rule you apply as **critical** or **cosmetic**.

- **Critical**, always enforced: allowed characters (G1.1); no false facts in a name (a wrong size, pitch or pin count is worse than a missing one); functional variants kept in symbol names (package, pinout, voltage, current range); family by function or package; file name equals inner name; generic/fully specified Footprint rule; links and 3D paths that resolve.
- **Cosmetic**, relaxed when confirming it needs datasheet digging or the user says so: optional or hard-to-source F3 fields (BGA ball and pad diameter, pitch, height); the exact wildcard form of non-functional MPN suffixes; word order inside extra descriptors.

A relaxed cosmetic rule is reported as RELAXED with a one-line reason; it is not a failure. Ask the user before relaxing a critical rule.

## House rules

**Library folders.** `0_` + KLC library name: `0_<Family>.kicad_symdir` for symbols (one `.kicad_sym` file per root symbol), `0_<Family>.pretty` for footprints. The KLC name joins, with `_` and in this order, skipping unused ones: function, sub-function, tertiary qualifier, manufacturer, series, extra descriptor (`0_Sensor_Temperature`, `0_MCU_ST_STM32G4`, `0_Conn_USB`). The library nickname is the folder name without its extension, case-sensitive.

**3D folder.** Footprint library name without `0_`, same case: `0_Capacitor_SMD.pretty` uses `3D/Capacitor_SMD/`.

**3D model file.** `<footprint name>[_<extra>].step`. Add the extra descriptor only for information the footprint name lacks: vendor MPN, stand-in part, color, cable, or state (`LED_0603_1608Metric_LiteOn_LTST-C190KFKT.step`). Each footprint has its own model file. A model no footprint uses keeps its part-number name.

**3D path string.** `${KIPRJMOD}/library/3D/<3D folder>/<file>`; the project holds the library tree as its `library/` folder. A stock KiCad model keeps `${KICAD10_3DMODEL_DIR}/...` and needs no local file.

**Symbol Footprint property.** Fully specified symbols set it to `<footprint library nickname>:<footprint name>` (`0_Diode_SMD:D_SMA`). Generic symbols (device type, connector, switch, logic function) leave it empty, even when a project only ever uses one part.

## Quick KLC rules

**General (G1).** Characters only `A-Z a-z 0-9 _ - . , +`, no spaces. Singular words, American English, real words (no typos such as `NoSlik`). Acronyms in capitals (`MCU`), maker names as the maker writes them (`ROHM`, `Texas`), CamelCase inside a field (`TestPoint`). Dimensions always carry units, millimeters preferred, order X x Y [x Z], unit written once (`3x4x7mm`).

**Families.** Symbol libraries group by electrical function, never by maker alone. Footprint libraries group by package or mounting type (`Package_QFP`, `Resistor_SMD`). Connector footprints group by function first (`Conn_USB`), then mechanical type (`Conn_PinHeader`), and a multi-purpose series may group by maker (`Conn_JST`, `Conn_AMASS`). Words like `Generic` or `Misc` are neither a function nor a mechanical type; flag them in a footprint library name.

**Symbols (S2, G2).**
- Do not repeat the library name in the symbol name. Exception: a generic symbol named by its device type may start with the same word as its library (`Jumper:Jumper_2_Open`, `Crystal_GND24`).
- Fully specified: the MPN, with non-functional parts (packaging/reel, RoHS/lead-free such as `LF`, temperature grade) as lowercase `x` and a trailing wildcard dropped (`INA180Ax`). Keep functional variants (voltage, current range, gain, package). No wildcard when only one functional variant exists.
- Compatible parts from several makers with different package suffixes: common base part plus package (`L78L05_TO92`). Same name from several makers: maker first.
- Generic: device type (`Conn_01x06`, `D`, `C`); arrays add the count (`_x8`); modified variants append the reason (`Q_NPN_CBE`, `_Split`).
- One symbol per package option; pin-compatible variants derive from the base symbol.

**Footprints (F2, F3).**
- Field order, joined by `_`, each optional: `<Package>-<pins>[-<n>EP|SH|MP]`, body `LxW[xH]mm`, pin layout (`1x10`), pitch `P<x>mm`, modifiers (`Drill1.0mm`, `Pad2.4x5.2mm`), orientation (`Horizontal`, `Vertical`), modification reason (`ThermalVias`, `HandSoldering`). Example: `QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm_ThermalVias`.
- Prefixes: `B` body, `D` diameter, `H` height, `L` length, `W` width, `O` offset, `T` thickness, `P` pitch, `EP` exposed pad. Spell other parameters in full (`Layout14x14`, `StackHeight`).
- Footprint specific to one maker: maker and MPN first (`Texas_S-PVQFN-N48_...`, `JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal`).
- Packages with omitted pins: `<Package>-<remaining>-<total>` (`MSOP-12-16`).
- Type traps: BGA lists `_Ball<d>_Pad<d>_<NSMD|SMD>` (F3.4, cosmetic per Strictness); SMD electrolytic is `CP_Elec[_<Mfr>]_<X>x<Y>[_H<h>]`, with no `D` field (F3.3); chip sizes carry `_<metric>Metric` (F3.1).

## Propose steps

1. **Collect facts.** Manufacturer, full MPN and its ordering-code breakdown, function, package name, pin count, body size (L x W, and H when it matters), pitch, exposed or mounting pads, pin layout, mounting (SMD/THT), orientation. Take them from the user or the datasheet; use the `web-research` agent for a missing datasheet fact.
   Done when every field the matching KLC section asks for is known with a source, marked unconfirmed, or skipped as cosmetic (Strictness).

2. **Find siblings.** Look for an existing library in the current working tree (Glob `**/0_*.kicad_symdir` and `**/0_*.pretty`, plus any library index files). Note the families and the nearest item of the same package type. With no library present, skip this and rely on KLC.
   Done when the existing families and nearest siblings are listed, or no library was found.

3. **Library family.** Reuse an existing `0_<Family>` that fits. Propose a new one only when none fits, built by the house rule. Name the 3D folder.
   Done when symbol library, footprint library and 3D folder are each named.

4. **Symbol name.** Decide generic or fully specified (G2), then apply S2. State the derived-symbol plan when there are package variants, and the `Footprint` value.
   Done when the name, the generic/fully-specified choice and the Footprint value are fixed.

5. **Footprint name.** Use the generic KLC package name when the land pattern is standard; add maker and MPN only when the footprint is specific to one maker. Build the fields in F2.1 order, then apply the F3 section for the type. Match the nearest sibling's pattern where it is KLC-correct.
   Done when every field in the name traces to a confirmed fact and a KLC rule.

6. **3D model.** File name and path string by the house rules, or the stock path.
   Done when the file name and path string are fixed.

7. **Final check.** Run the Check list below on every proposed name, and Glob the target folders for a case-insensitive clash: the same part means reuse it; a different part gets a name that states its real difference (`_NoCourtyard`, `_ThermalVias_Via0.4mm`).
   Done when every name has passed or has its failure listed.

## Check list

Run the list for each name and record every failure. For a whole library, check family names first, then items; split items by type across parallel read-only agents when there are many.

**Every name**
1. Characters only `A-Z a-z 0-9 _ - . , +`; no spaces. (G1.1)
2. Real English words, singular, American spelling. (G1.4, G1.5)
3. Case: acronyms in capitals, maker as the maker writes it, CamelCase inside a field. (G1.6)
4. Every dimension has a unit, written once at the end of the field (`3x4x7mm`). (G1.9)

**Library family** (`0_<Family>`)
5. Starts with `0_`; fields in order function, sub-function, qualifier, maker, series, extra. (G1.3, S1.1, F1.1)
6. Symbols: grouped by electrical function. Footprints: by package, mounting, or connector function / mechanical type / multi-purpose maker series. (F1.2)
7. A footprint library with local models has a 3D folder of the same name without `0_`. (house)

**Symbol** (file name, `(symbol "NAME"`, `Footprint` property)
8. File name equals the inner symbol name.
9. Generic or fully specified? Generic: device type name (S2.1 item 4) and empty Footprint (house). Fully specified: MPN name and Footprint set to an existing `<0_lib>:<footprint>` (house).
10. Fully specified MPN: non-functional parts are `x`, trailing wildcard dropped, functional parts kept. Decide with the ordering-code table. Without it: NEEDS-DATASHEET when a functional variant is in doubt, RELAXED when only a non-functional suffix is unclear. (S2.2)
11. Does not repeat the library name, except the device-type case. (S2.1 item 1)

**Footprint** (file name, `(footprint "NAME"`)
12. File name equals the inner footprint name. (F9.1)
13. Pick the F3 section for the type and compare field by field: every required field present, order right, prefixes right. Without a matching F3 section, use F2.1 order.
14. Confirm fields from the file: count uniquely numbered pads (pins), `EP`/`MP`/`SH` pads, pitch from pad positions, pad layout. A field the file cannot confirm is NEEDS-DATASHEET when critical, RELAXED when cosmetic; neither is a failure.
15. A maker-specific land pattern starts with maker and MPN or maker package code. (F2.3)

**3D model**
16. File in `3D/<footprint library without 0_>/`, named `<footprint name>[_<extra>].step`, one file per footprint. (house)
17. Path string is `${KIPRJMOD}/library/3D/...` and the file exists, or it is a stock `${KICAD10_3DMODEL_DIR}/...` path. (house)

**Before reporting a failure:** check authority 4 (an exact stock KiCad name passes) and the device-type exception in line 11.

## Report

**Propose:** one table, then notes:

| Item | Name | Where | Rule |
|---|---|---|---|
| Symbol library | `0_...` | `symbols/0_....kicad_symdir` | S1.1 |
| Symbol | ... | `.../<name>.kicad_sym` | S2.x / G2 |
| Footprint library | `0_...` | `footprints/0_....pretty` | F1.x |
| Footprint | ... | `.../<name>.kicad_mod` | F2.x, F3.x |
| 3D model | ... `.step` | `3D/<folder>/` | house 3D rule |

Notes: the symbol `Footprint` value and the footprint `(model ...)` path string; each field built on an unconfirmed fact, and what would confirm it.

**Check:** a count table (checked / pass / fail / needs datasheet / relaxed, per item type), then one table of failures:

| Item | Current name | Problem | Rule | Corrected name |
|---|---|---|---|---|

Then the NEEDS-DATASHEET list with the missing fact for each, and the RELAXED list with the rule and reason for each. Say that a rename must also update symbol `Footprint` properties and 3D paths, and list any existing item a rename would make stale.
