# KLC Checklist

Checklist for adding a symbol, footprint or 3D model to this library. This is a personal archive, so KLC is a guide, not a contribution standard (see the Strictness rule in `CLAUDE.md`). Rule texts are in [KLC/](KLC/README.md).

T1 ranks every rule. T2 splits each check into script and human work. T3 says how to build and check each name.

**Here** column: **Strict** = always apply. **Relaxed** = apply when cheap; skipping it is fine if you note why. **House** = replaced by a house rule. **N/A** = does not apply to this archive.

## T1. All rules, from critical to low

Use this list when you create a new library item. Work top to bottom.

### Critical: wrong board or broken links

| Rule | Check when creating the item | Here |
|---|---|---|
| [F4.1](KLC/footprint/F4.1.md) | Land pattern matches the datasheet's recommended layout | Strict |
| *(pinout)* | Symbol pin numbers and names match the datasheet pinout | Strict |
| [S2.3](KLC/symbol/S2.3.md) | One symbol per package or pinout option; pin-compatible variants derive from the base | Strict |
| [S4.1](KLC/symbol/S4.1.md) | Pin ends on the 100 mil grid; pin numbers unique; pin names as in the datasheet | Strict |
| [S3.5](KLC/symbol/S3.5.md) | Pin connection points outside the body; no wire has to cross the symbol | Strict |
| [S4.6](KLC/symbol/S4.6.md) | No hidden pins, except unused pins set to Not Connected; no hidden power inputs | Strict |
| [S4.3](KLC/symbol/S4.3.md) | Same-net pins use KiCad 10 pin stacks, not pins placed on top of each other; no NC stacks | Strict |
| [S5.1](KLC/symbol/S5.1.md) | Footprint property points to a footprint that exists | Strict |
| [F4.3](KLC/footprint/F4.3.md) | Copper that is connected (overlapping pads, EP and vias) has the same pad number | Strict |
| [F4.4](KLC/footprint/F4.4.md) | Thermal vias share the EP number, 0.2 to 0.3 mm holes, no paste over vias ≥ 0.3 mm, B.Cu pad added | Strict |
| [F6.3](KLC/footprint/F6.3.md) | SMD pads on F.Cu/F.Mask/F.Paste only; EP paste 50 to 80%; 0.2 mm EP-to-pad clearance; heatsink/BGA property set | Strict |
| [F7.4](KLC/footprint/F7.4.md) | THT pads on all copper layers plus F.Mask and B.Mask; no paste, no silkscreen | Strict |
| [F7.5](KLC/footprint/F7.5.md) | Annular ring ≥ 0.15 mm | Strict |
| [F7.6](KLC/footprint/F7.6.md) | Hole = max lead diameter + 0.2 mm | Strict |
| [F7.7](KLC/footprint/F7.7.md) | Oval holes: 0.2 mm clearance around the lead; only for leads with ratio > 2 | Strict |
| [F5.3](KLC/footprint/F5.3.md) | Closed courtyard on F.CrtYd (0.25 mm clearance; 0.15 for parts < 1.5 mm; 0.5 connectors, crystals, cans; 1.0 BGA) | Strict |
| [F4.6](KLC/footprint/F4.6.md) | Pad local clearance and mask/paste overrides = 0 unless the datasheet asks | Strict |
| [F9.2](KLC/footprint/F9.2.md) | Footprint-level clearance overrides = 0 unless the datasheet asks | Strict |
| [G1.1](KLC/general/G1.1.md) | Names use only `A-Z a-z 0-9 _ - . , +` | Strict |

### High: assembly, ERC and finding parts

| Rule | Check when creating the item | Here |
|---|---|---|
| [F6.1](KLC/footprint/F6.1.md) | SMD footprint type is Surface Mount; not excluded from BOM or position files (test points and logos may be) | Strict |
| [F7.1](KLC/footprint/F7.1.md) | THT footprint type is Through Hole | Strict |
| [F4.2](KLC/footprint/F4.2.md) | Pin 1 top-left (two-terminal and single-row: pin 1 on the left) | Relaxed (strict if you order PCBA) |
| [F6.2](KLC/footprint/F6.2.md) | SMD origin at the body centroid, or where the datasheet puts it | Relaxed (strict if you order PCBA) |
| [F7.2](KLC/footprint/F7.2.md) | THT origin at pin 1 | Relaxed |
| [S4.4](KLC/symbol/S4.4.md) | Each pin's electrical type is right (power in/out, input, output, bidirectional, passive, NC) | Strict |
| [S3.7](KLC/symbol/S3.7.md) | EP numbered pin count + 1; shield pins `SH`; mounting pads `MP`; NPTH gets no pin | Strict |
| [S4.5](KLC/symbol/S4.5.md) | NC pins omitted only if never connected; NC pins the datasheet wants tied stay in | Strict |
| [S5.2](KLC/symbol/S5.2.md) | Footprint filter ends with `*` and matches the linked footprint | Relaxed |
| [F9.1](KLC/footprint/F9.1.md) | Reference `REF**`; Value = file name; description and keywords filled | Strict for Value, Relaxed for the rest |
| [G1.10](KLC/general/G1.10.md) | No embedded files or fonts | Strict |
| [G1.3](KLC/general/G1.3.md), [S1.1](KLC/symbol/S1.1.md), [F1.1](KLC/footprint/F1.1.md), [F1.2](KLC/footprint/F1.2.md) | Library chosen by function (symbols) or package/connector type (footprints) | Strict |
| [G2.1](KLC/general/G2.1.md) | Decide generic or fully specified; generic leaves Footprint empty | Strict |
| [S2.1](KLC/symbol/S2.1.md), [S2.2](KLC/symbol/S2.2.md) | Symbol name: MPN, functional variants kept, non-functional parts as `x` | Relaxed (keep functional variants strict) |
| [F2.1](KLC/footprint/F2.1.md) to [F2.5](KLC/footprint/F2.5.md), [F3.1](KLC/footprint/F3.1.md) to [F3.7](KLC/footprint/F3.7.md) | Footprint name fields and order; type-specific schemes | Relaxed (no false facts) |
| [G1.9](KLC/general/G1.9.md) | Dimensions carry units, written once | Strict |

### Medium: readability and polish

| Rule | Check when creating the item | Here |
|---|---|---|
| [F5.1](KLC/footprint/F5.1.md) | Silkscreen not over pads, visible after assembly, pin-1 marker on F.SilkS | Relaxed |
| [M2.2](KLC/model/M2.2.md) | Model needs no offset, scale or rotation in KiCad | Relaxed (transforms are fine if it lines up) |
| [F9.3](KLC/footprint/F9.3.md) | Real footprints have a 3D model reference; scale 1:1:1 | Relaxed |
| [S3.1](KLC/symbol/S3.1.md) | Symbol centered on the origin (as close as the pin grid allows) | Relaxed |
| [S3.2](KLC/symbol/S3.2.md) | Text 50 mil (pin text down to 20 mil on small symbols) | Relaxed |
| [S3.3](KLC/symbol/S3.3.md) | Body line 10 mil; black-box ICs filled with background, simple parts not filled | Relaxed |
| [S3.6](KLC/symbol/S3.6.md) | Pin name offset 20 to 50 mil (20 preferred) | Relaxed |
| [S3.8](KLC/symbol/S3.8.md) | Multi-unit split makes sense; units not interchangeable unless they are | Relaxed |
| [S4.2](KLC/symbol/S4.2.md) | Pins grouped by function (power top, ground bottom, inputs left, outputs right) | Relaxed |
| [S4.7](KLC/symbol/S4.7.md) | Active-low pins use an overbar (`~{RESET}`) | Relaxed |
| [S6.1](KLC/symbol/S6.1.md) | RefDes prefix fits the part type (U, C, R, J, ...) | Strict |
| [S6.2](KLC/symbol/S6.2.md) | Reference and Value visible; Footprint and Datasheet hidden; Datasheet and Description filled | Relaxed |
| [G1.4](KLC/general/G1.4.md), [G1.5](KLC/general/G1.5.md), [G1.6](KLC/general/G1.6.md) | English, singular, KLC capitalization | Relaxed |

### Low: cosmetic

| Rule | Check when creating the item | Here |
|---|---|---|
| [F5.1](KLC/footprint/F5.1.md) (style) | Silk line 0.12 mm (0.10 to 0.15); RefDes 1.0 mm / 0.15 mm | Relaxed |
| [F5.2](KLC/footprint/F5.2.md) | F.Fab outline 0.10 mm, pin-1 bevel, Value on F.Fab, `${REFERENCE}` on F.Fab | Relaxed |
| [F5.3](KLC/footprint/F5.3.md) (style) | Courtyard line 0.05 mm on a 0.01 mm grid | Relaxed |
| [F5.4](KLC/footprint/F5.4.md) | No overlapping or duplicate graphics | Relaxed |
| [F6.3](KLC/footprint/F6.3.md) (style) | Rounded-rectangle pads instead of rectangles | Relaxed |
| [F7.3](KLC/footprint/F7.3.md) | THT pin 1 rectangular, others round or oval | Relaxed |
| [G1.7](KLC/general/G1.7.md) | LF line endings (`.gitattributes` does this) | Strict (automatic) |
| [G1.11](KLC/general/G1.11.md) | Default KiCad font | Relaxed |
| [S3.4](KLC/symbol/S3.4.md) | Simple functional diagram inside complex symbols | Relaxed |
| [S3.9](KLC/symbol/S3.9.md) | De Morgan alternate body for logic gates | Relaxed |
| [S7.1](KLC/symbol/S7.1.md), [S7.2](KLC/symbol/S7.2.md) | Power and graphic symbol conventions | Relaxed |

### Does not apply

| Rule | Why |
|---|---|
| [G1.8](KLC/general/G1.8.md) | Contribution version rule for the official library |
| [G3.1](KLC/general/G3.1.md), [G3.2](KLC/general/G3.2.md) | Relay and audio connector specifics; use only if you add those parts |
| [F4.5](KLC/footprint/F4.5.md) | Keepout areas; use only when a datasheet asks |
| [F8.1](KLC/footprint/F8.1.md) | Non-SMD/THT parts; use only for that kind of part |
| [M1.1](KLC/model/M1.1.md) | Contributor rights; here, check licenses before making the repo public (see `THIRD_PARTY_NOTICES.md`) |
| [M1.3](KLC/model/M1.3.md), [M2.3](KLC/model/M2.3.md) | Model source files and FreeCAD; upstream only |
| [M2.1](KLC/model/M2.1.md) | STEP format; already a house rule |
| [F9.3](KLC/footprint/F9.3.md) items 2, 3, 7 | House: models in `3D/<Family>/`, named `<footprint>[_<extra>].step`, path `${KIPRJMOD}/library/3D/...` |

## T2. Automated check and human check

**Auto** = a script can check it from the library files. **Human** = needs a datasheet, the KiCad GUI, or judgment. Rules with only cosmetic checks are left out.

| Rule | Auto check (script) | Human check |
|---|---|---|
| [F4.1](KLC/footprint/F4.1.md) | - | Compare the land pattern with the datasheet |
| *(pinout)* | Symbol pin count = footprint pad count | Compare pin numbers and names with the datasheet |
| [S2.3](KLC/symbol/S2.3.md) | - | Check the ordering table for package or pinout variants |
| [S4.1](KLC/symbol/S4.1.md) | Pin ends on the 2.54 mm grid; unique numbers; equal pin lengths | Pin names match the datasheet |
| [S3.5](KLC/symbol/S3.5.md) | Pin connection end outside the body outline | - |
| [S4.6](KLC/symbol/S4.6.md) | List hidden pins; flag hidden pins that are not Not Connected | Decide if a hidden NC pin should be shown |
| [S4.3](KLC/symbol/S4.3.md) | Pins on the same spot (old workaround); NC pins in a stack | Which pins should be stacked |
| [S5.1](KLC/symbol/S5.1.md) | Footprint link resolves (`klc_verify.py`, `kicad-link-audit`) | - |
| [F4.3](KLC/footprint/F4.3.md) | Overlapping copper with different pad numbers | - |
| [F4.4](KLC/footprint/F4.4.md) | Vias share the EP number; hole 0.2 to 0.3 mm; no paste on vias ≥ 0.3 mm; B.Cu pad present | Via count and pattern from the datasheet |
| [F6.3](KLC/footprint/F6.3.md) | Pad layers; EP paste 50 to 80%; EP-to-pad clearance ≥ 0.2 mm; heatsink property | Stencil pattern from the datasheet |
| [F7.4](KLC/footprint/F7.4.md) | THT pad layers (all Cu, both masks, no paste, no silk) | - |
| [F7.5](KLC/footprint/F7.5.md) | Annular ring ≥ 0.15 mm | - |
| [F7.6](KLC/footprint/F7.6.md) | Drill > 0 and smaller than the pad | Hole ≥ max lead diameter + 0.2 mm |
| [F7.7](KLC/footprint/F7.7.md) | Oval drill sits in an oval pad | Lead size and ratio from the datasheet |
| [F5.3](KLC/footprint/F5.3.md) | Courtyard present and closed | Clearance fits the part type |
| [F4.6](KLC/footprint/F4.6.md), [F9.2](KLC/footprint/F9.2.md) | Local clearance and margin overrides are 0 | Keep an override only if the datasheet asks |
| [G1.1](KLC/general/G1.1.md) | Allowed characters in names | - |
| [F6.1](KLC/footprint/F6.1.md), [F7.1](KLC/footprint/F7.1.md) | Footprint type matches the pad types; exclude flags | Exclude flags are intended (test points, logos) |
| [F4.2](KLC/footprint/F4.2.md) | Pad 1 in the top-left quadrant (or left for single-row) | Matches your assembler's rotation convention |
| [F6.2](KLC/footprint/F6.2.md), [F7.2](KLC/footprint/F7.2.md) | Origin at body center (SMD) or pin 1 (THT) | Datasheet origin for odd-shaped parts |
| [S4.4](KLC/symbol/S4.4.md) | Flag power-named pins not typed as power; all pins unspecified | Each pin type matches the datasheet |
| [S3.7](KLC/symbol/S3.7.md) | EP number = pin count + 1; `SH`/`MP` names | Which pads are shield or mechanical |
| [S4.5](KLC/symbol/S4.5.md) | Pin count < pad count, and the filter has the pad count | Omitted pins are truly never connected |
| [S5.2](KLC/symbol/S5.2.md) | Filter ends with `*` and matches the linked footprint | Filter is not too broad |
| [F9.1](KLC/footprint/F9.1.md) | Reference `REF**`; Value = file name; empty description | Description facts are true |
| [G1.10](KLC/general/G1.10.md) | No `embedded_files`, embedded fonts off | - |
| [G2.1](KLC/general/G2.1.md) | Generic symbols have an empty Footprint | Generic or fully specified decision |
| [G1.3](KLC/general/G1.3.md), [S1.1](KLC/symbol/S1.1.md), [F1.1](KLC/footprint/F1.1.md), [F1.2](KLC/footprint/F1.2.md) | Library name format (`0_` + fields) | Right family for the part |
| [S2.1](KLC/symbol/S2.1.md), [S2.2](KLC/symbol/S2.2.md) | File name = inner name; library name not repeated | Functional vs non-functional MPN parts |
| [F2.1](KLC/footprint/F2.1.md) to [F3.7](KLC/footprint/F3.7.md) | Pin count, pitch and pad layout in the name match the pads | Body size and orientation word match the datasheet |
| [G1.9](KLC/general/G1.9.md) | Dimensions in names carry `mm` | - |
| [F5.1](KLC/footprint/F5.1.md) | Silkscreen overlaps pads (approximate); silk width | Readable and visible after assembly (KiCad Footprint Checker) |
| [M2.2](KLC/model/M2.2.md), [F9.3](KLC/footprint/F9.3.md) | Model offset, scale, rotation; model reference present; file exists | Model sits right on the pads (KiCad 3D viewer) |
| [S3.1](KLC/symbol/S3.1.md) | Body center vs origin | - |
| [S3.2](KLC/symbol/S3.2.md) | Text sizes | - |
| [S3.3](KLC/symbol/S3.3.md) | Body line width; fill type | Black box or simple part |
| [S3.6](KLC/symbol/S3.6.md) | Pin name offset 0.508 to 1.27 mm | - |
| [S3.8](KLC/symbol/S3.8.md) | - | Unit split makes sense |
| [S4.2](KLC/symbol/S4.2.md) | - | Pins grouped by function |
| [S4.7](KLC/symbol/S4.7.md) | Active-low names without an overbar (`nRESET`, `RESET_N`) | Which pins are active low |
| [S6.1](KLC/symbol/S6.1.md) | RefDes prefix is in the KLC table | Prefix fits the part type |
| [S6.2](KLC/symbol/S6.2.md) | Field visibility; empty Datasheet or Description | Description facts are true |

## T3. Naming

Build each name with this section, then check it. The KLC files win where this summary differs. The `kicad-naming` skill runs the same checks.

### Every name

| Check | Rule | Here |
|---|---|---|
| Only `A-Z a-z 0-9 _ - . , +`; no spaces | [G1.1](KLC/general/G1.1.md) | Strict |
| Every fact in the name is true. Leave a field out rather than guess a size, pitch or pin count | Strictness in `CLAUDE.md` | Strict |
| Every dimension has a unit, millimeters preferred, X x Y [x Z], unit written once (`3x4x7mm`) | [G1.9](KLC/general/G1.9.md) | Strict |
| English words, singular, American spelling, no typos (`NoSilk`, not `NoSlik`) | [G1.4](KLC/general/G1.4.md), [G1.5](KLC/general/G1.5.md) | Relaxed |
| Acronyms in capitals (`MCU`, `LED`); maker as the maker writes it (`ROHM`, `Texas`); CamelCase inside a field (`TestPoint`) | [G1.6](KLC/general/G1.6.md) | Relaxed |
| No clash with an existing name, ignoring case. Same part: reuse it. Different part: name its real difference (`_NoCourtyard`) | house | Strict |

### Library family

| Check | Example | Rule |
|---|---|---|
| Reuse an existing family first ([SYMBOLS_DIRECTORY.md](SYMBOLS_DIRECTORY.md), [FOOTPRINTS_DIRECTORY.md](FOOTPRINTS_DIRECTORY.md)) | | house |
| Folder = `0_` + KLC name. Fields in order, skip unused: function, sub-function, qualifier, maker, series, extra | `0_Sensor_Temperature`, `0_MCU_ST_STM32G4` | [G1.3](KLC/general/G1.3.md) |
| Symbol libraries group by electrical function, not by maker | `0_Regulator_Switching` | [S1.1](KLC/symbol/S1.1.md) |
| Footprint libraries group by package or mounting type | `0_Package_SO`, `0_Resistor_SMD` | [F1.1](KLC/footprint/F1.1.md) |
| Connector footprints: function first, then mechanical type, then a multi-purpose maker series. `Generic` and `Misc` are none of these | `0_Conn_USB`, `0_Conn_PinHeader`, `0_Conn_JST` | [F1.2](KLC/footprint/F1.2.md) |
| A new footprint library with local models gets `3D/<name without 0_>/`, same case | `0_Capacitor_SMD.pretty` uses `3D/Capacitor_SMD/` | house |

### Symbol name

1. **Generic or fully specified** ([G2.1](KLC/general/G2.1.md)).
   - Generic: device type name (`R`, `C`, `D`, `Conn_01x06`). Arrays add the count (`Resistor_x8`); changed variants add the reason (`Q_NPN_CBE`, `_Split`). Footprint stays empty.
   - Fully specified: MPN name. Footprint = `<0_library>:<footprint>`, and that footprint exists ([S5.1](KLC/symbol/S5.1.md)).
2. **MPN wildcard** ([S2.2](KLC/symbol/S2.2.md)). Read the ordering-code table.
   - Keep functional parts: package, pinout, voltage, current range, gain.
   - Replace non-functional parts with lowercase `x`: reel or tray, RoHS or lead-free (`LF`), temperature grade. Drop a trailing `x` (`INA180Ax`).
   - Only one functional variant: no wildcard, use the plain MPN.
   - Strict for functional parts. The exact wildcard form is Relaxed.
3. **Several makers** ([S2.1](KLC/symbol/S2.1.md)). Compatible parts with different package suffixes: base part + package (`L78L05_TO92`). Same name from different makers: maker first.
4. **Packages** ([S2.3](KLC/symbol/S2.3.md)). One symbol per package or pinout. Pin-compatible variants derive from the base symbol.
5. **No library name repeated** (`0_Sensor_Temperature:TMP235A4DCK`, not `Sensor_TMP235A4DCK`). Device-type names may share the first word (`0_Jumper:Jumper_2_Open`).
6. **File name = inner name**: `TMP235A4DCK.kicad_sym` holds `(symbol "TMP235A4DCK"`.

### Footprint name

Generic package: use the KLC package name. A land pattern for one maker's part starts with maker + MPN or maker package code ([F2.3](KLC/footprint/F2.3.md)): `Texas_S-PVQFN-N48_...`.

Fields join with `_`; skip what does not apply ([F2.1](KLC/footprint/F2.1.md)):

`<Package>-<pins>[-<n>EP|SH|MP]` · body `LxW[xH]mm` · layout `1x10` · pitch `P<x>mm` · modifiers `Drill1.0mm`, `Pad2.4x5.2mm` · orientation `Horizontal`, `Vertical` · reason `ThermalVias`, `HandSoldering`

- Pin count = uniquely numbered pads. EP, shield and mounting pads go in the pin field (`-1EP`, `-1SH`, `-2MP`).
- Omitted pins: `<Package>-<remaining>-<total>` (`MSOP-12-16`) ([F2.4](KLC/footprint/F2.4.md)).
- Prefixes ([F2.2](KLC/footprint/F2.2.md)): `B` body, `D` diameter, `H` height, `L` length, `W` width, `O` offset, `T` thickness, `P` pitch, `EP` exposed pad size. Spell other fields in full (`Ball`, `Layout3x4`, `Clearance`, `StackHeight`).
- File name = inner name: `D_SMA.kicad_mod` holds `(footprint "D_SMA"`.

Read the F3 section for the type. Patterns and examples:

| Type | Pattern | Example | Rule |
|---|---|---|---|
| Chip R, C, L, LED | `<Prefix>_<Imperial>_<Metric>Metric[_<Mod>]` | `C_0805_2012Metric`, `LED_0805_2012Metric_ReverseMount` | [F3.1](KLC/footprint/F3.1.md) |
| Axial resistor | `R_Axial_L<len>_D<dia>_P<pitch>[_<Orientation>]` | `R_Axial_L3.6mm_D1.6mm_P2.54mm_Vertical` | [F3.2](KLC/footprint/F3.2.md) |
| Tantalum | `CP_Tantalum_EIA-<metric>_<Std>-<Letter>[_<Mod>]` | `CP_Tantalum_EIA-3126-18_Kemet-A` | [F3.3](KLC/footprint/F3.3.md) |
| SMD electrolytic | `CP_Elec[_<Mfr>]_<X>x<Y>mm[_H<h>]` (no `D` field) | `CP_Elec_10x10.5mm_H6mm` | [F3.3](KLC/footprint/F3.3.md) |
| THT capacitor | `<C/CP>_<Style>[_L<len>][_D<dia>][_W<w>]_P<pitch>` | `C_Axial_L67.0mm_D26.0mm_P75.0mm` | [F3.3](KLC/footprint/F3.3.md) |
| Gullwing (SOIC, SOP, QFP) | `<PKG>-<pins>[-<n>EP]_<X>x<Y>[x<Z>]mm_P<pitch>` | `SOIC-16-1EP_3.9x9.9mm_P1.27mm` | [F3.4](KLC/footprint/F3.4.md) |
| No-lead (QFN, DFN, SON) | Same as gullwing; add the EP size `EP<x>x<y>mm` when known | `DFN-6-1EP_2x2mm_P0.5mm_EP0.61x1.42mm` | [F3.4](KLC/footprint/F3.4.md), [F2.2](KLC/footprint/F2.2.md) |
| BGA | `<PKG>-<pins>_<X>x<Y>mm_Layout<C>x<R>_P<pitch>_Ball<d>_Pad<d>_<NSMD/SMD>` | `BGA-24_3.2x4.4mm_Layout3x4_P0.5mm_Ball0.25mm_Pad0.2mm_NSMD` | [F3.4](KLC/footprint/F3.4.md) (Ball and Pad Relaxed) |
| DIP | `<PKG>-<pins>_W<span>[_<Mod>]` | `DIP-14_W10.16mm_Clearance` | [F3.5](KLC/footprint/F3.5.md) |
| TO (THT) | `<PKG>-<pins>[_<size>][_P<pitch>]_<Orientation>` | `TO-220-5_Vertical` | [F3.5](KLC/footprint/F3.5.md) |
| Connector, function | `<Function>[_<Std>][_<Size>][-<Type>][_<Mfr>][_<MPN>][_<Orientation>]` | `USB_Micro-B_Molex_105133-0001_Vertical` | [F3.6](KLC/footprint/F3.6.md) |
| Connector, pin header | `PinHeader_<layout>_P<pitch>[_<Mod>]_<Orientation>` | `PinHeader_1x10_P2.54mm_Drill1.25mm_Horizontal` | [F3.6](KLC/footprint/F3.6.md) |
| Connector, maker series | `<Mfr>_<Series>_<MPN>_<layout>[-<n>MP]_P<pitch>_<Orientation>` | `JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal` | [F3.6](KLC/footprint/F3.6.md) |
| Fuse holder, fuse | `FuseHolder[_<Type>][_<Mfr>][_<Series>][_<MPN>]`, `Fuse_<Imperial>[_<Metric>Metric]` | `FuseHolder_Littelfuse_TE5_395`, `Fuse_0805` | [F3.7](KLC/footprint/F3.7.md) |

Check the name against the pads: pin count, EP/MP/SH count, pitch and pin layout must match the file. Body size and orientation come from the datasheet.

### 3D model name

| Check | Example | Rule |
|---|---|---|
| Folder `3D/<footprint library without 0_>/` | `3D/Capacitor_SMD/` | house |
| File `<footprint name>[_<extra>].step`. Add the extra only for facts the footprint name lacks: MPN, stand-in part, color, cable, state | `LED_0603_1608Metric_LiteOn_LTST-C190KFKT.step` | house |
| One model file per footprint. A model no footprint uses keeps its part-number name | | house |
| Path `${KIPRJMOD}/library/3D/<folder>/<file>`, and the file exists. Stock models keep `${KICAD10_3DMODEL_DIR}/...` | | house |

### When you rename

- Rename through the `kicad-lib-organize` map, not by hand.
- Update every symbol `Footprint` property and 3D path that points to the old name.
- Refresh the indexes: `SYMBOLS_DIRECTORY.md`, `FOOTPRINTS_DIRECTORY.md`, `3D_DIRECTORY.md` and the README member lists.
- Projects keep the old name until you sync them (`kicad-footprint-sync`, `kicad-symbol-sync`).
