# F2 General Footprint Naming Guidelines

## F2.1 General footprint naming conventions

Each footprint is a `.kicad_mod` file (stored within a `.pretty` directory). The naming convention for a given footprint depends largely on the _type_ of footprint, however a general guide is presented below:

1. Specific package type is written first, e.g.
  * `QFN` - Quad Flat No-Lead package
  * `C` - Capacitor
2. Package name and number of pins are separated by a hyphen
  * `TO-90`
  * `QFN-48`
  * `DIP-20`
3. Packages with special pads add an identifier to the pin count field separated by a hyphen
  * The field includes the count of uniquely numbered pads of this type.
  ** For exposed pads (large copper pad below the part) `[count]EP`
  ** For shield pads `[count]SH` (Unless such a pin is already expected for the part. An example would be a HDMI connector.)
  ** For pads connecting pure mechanical mounting leads `[count]MP`
  * Examples from the library.
  ** `DFN-6-1EP_2x2mm_P0.5mm_EP0.61x1.42mm`
  ** `Samtec_LSHM-110-xx.x-x-DV-S_2x10-1SH_P0.50mm_Vertical`
  ** `Molex_PicoBlade_53261-0271_1x02-1MP_P1.25mm_Horizontal`
4. Unique _fields_ (parameters) in the footprint name are separated by `_` character.
5. Package dimensions are specified as `length` x `width` (and optionally `height`)
  * `3.5x3.5x0.2mm`
  * `1x1in`
  * If necessary for clarity, footprint body dimensions may be prefixed with a leading `B`
6. Pin layout
  * `1x10`
  * `2x15`
7. Pitch is specified with a leading `P`:
  * `P1.27mm` - 1.27mm pitch
  * `P5.0mm` - 5.0mm pitch
8. Modifiers to standard footprint values
  * `Drill1.25mm`
  * `Pad2.4x5.2mm`
9. Orientation e.g. `Horizontal`, `Vertical`
10. Any modification to the original footprint, indicated by appending the reason
  * `_HandSoldering`
  * `_ThermalVias`
  * `_CircularHoles`

Not all of the fields defined above are strictly required for a particular footprint. Additional fields may also be added as needed.

## F2.2 Footprint naming field prefixes

A footprint name has to convey a lot of information to clearly specify the purpose and parameters of the footprint. Some fields in footprint names are *common* to many footprints and can be shortened using special abbreviations.

Not all footprints will require the use of these abbreviations - they are provided as a method of standardising the manner in which footprint parameters are called out when encountered.

In many cases, the major dimensions (x/y/z) of a footprint may be specified without a prefix, as the body dimensions are assumed to have the greatest priority in the footprint name. Therefore, the "3.2x5.7mm" part of the example name below requires no 'B' prefix, and is not required to be written as "B3.2x5.7mm".

e.g. `SOIC-8_3.2x5.7mm_P1.27mm`

In cases where potential conflicts exist, however, the body dimensions must be explicitly named with the prefix `B`.

Refer to the table below for accepted prefix abbreviations.

| Prefix | Field Description | Notes |
| --- | --- | --- |
| B | Body dimensions | - Body size (`X` x `Y` x `Z`) - Height parameter `Z` may be omitted - Prefix `B` may be omitted if the body size is the major dimension used to define the footprint |
| D | Diameter | - Diameter of major axis for cylindrical component - e.g. `D10mm` - 10mm diameter |
| H | Height | - Height of component measured from PCB - Body size `B` should be used in preference, where possible - e.g. `H1.1mm` - component measures 1.1mm above PCB |
| L | Length | - Length along major axis of component - Body size `B` should be used in preference, where possible - e.g. `L15.3mm` - 15mm length |
| O | Offset | - Offset, where no other name is more appropriate - For example, the distance between pads and the body. Affects silkscreen diagram. - e.g. `O3.81mm` - 3.81mm from pads to body. |
| W | Width | - Width along minor axis of component - Body size `B` should be used in preference, where possible - e.g. `W4.75mm` - 4.75mm width |
| EP | Exposed pad dimensions | - Packages that include a single exposed pad include the size of this pad. e.g. `EP2.4x3.6mm` - for a single 2.4mm x 3.6mm pad. |
| P | Pad pitch | - Pitch (distance) between pins, pads or leads - e.g. `P0.63mm` - 0.63mm pitch between pads |
| T | Thickness | Component thickness, where appropriate |

**Examples:**

- `LQFP-32_4x4x1.1mm_P1.65mm` - LQFP package, 32 pins, 4x4mm body, 1.1mm height, 1.65mm pitch
- `CP_Radial_D4.5mm_P2.5mm_H10mm` - Radial polarized capacitor, 4.5mm diameter, 2.5mm pitch, 10mm height

If the parameter is not found in the table above, the name of the parameter should be entered in full.

Following is a list of examples of (non-abbreviated) parameter names used in footprint naming

| Prefix | Field Description |
| --- | --- |
| Ball | BGA Ball diameter |
| CenterHeight | Height of centerline of a component above the board surface. For example, elevated connectors. Usually defined explicitly in the datasheet. |
| Clearance | Clearance between pin rows |
| Drill | Drill diameter |
| Layout | Specific footprint layout   e.g. `Layout3x7` for a BGA with 21 balls arranged in 3 columns and 7 rows |
| Lead | Lead dimensions |
| Mask | Custom soldermask dimensions |
| Pad | Custom pad dimensions |
| StackHeight | The height that a component contributes to a mated stack height, above the board surface. Usually defined explicitly in the datasheet. |
| Tab | Tab dimensions |

## F2.3 Manufacturer specific version of generic footprints

If a manufacturer footprint deviates from the "standard" footprints available, then this should be added to the library and designated as manufacturer-specific.

1. If a footprint is specific to a single manufacturer, this must be indicated by prepending the manufacturer name and MPN to the footprint name.
	- `Texas_S-PVQFN-N48_`

2. Sometimes the component datasheet will have specific requirements which do not conform to KLC requirements. A common example is specific requirements for the shape of stencil (solder paste layer).

In such cases, the KLC requirements can be superseded by the datasheet requirements, at the discretion of the KiCad library team.

### F2.4 Footprint naming for non-standard pin numbering

Generally, a footprint should include a field of the format `<pkg>-<pincount>`, e.g.

- `SOIC-8`
- `QFN-24`

In the majority of cases, the pin quantity is self explanatory and is sufficient to describe the number of pins on the symbol.

However there may be cases where this numbering is insufficient. Where the number of footprint pins does not match the number of package pins, exceptions must be made.

**Exception: Omitted pins, missing pin numbers are skipped**

*Example: LTC3638*

The LTC3638 comes in an `MSOP-16` package which has four missing pins, for increased voltage isolation.

[![F2.4a](https://klc.kicad.org/img/klc/F2.4a.png "MSOP-16 package with 4 missing pins")](https://klc.kicad.org/img/klc/F2.4a.png)

In this case, the numbers for the missing pins are **skipped** and the normal pin numbers are assigned to the remaining pins.

To indicate this, the footprint should be named as follows:

`PKG-<xx>-<yy>` where:

- `xx` = number of remaining pins
- `yy` = number of remaining pins + number of removed pins

In the LTC3638 example above, this would result in:

`MSOP-12-16`

The footprint pads should be numbered like so:

[![F2.4_msop_12-16](https://klc.kicad.org/img/klc/F2.4_msop_12-16.png "MSOP-12-16 footprint in KiCad")](https://klc.kicad.org/img/klc/F2.4_msop_12-16.png)

## F2.5 Footprint naming conventions for specific components

Footprint naming is sufficiently complex that a general rule is not enough to fully define a naming scheme that fits the wide range of footprints.

In addition to the general footprint naming guidelines defined in [KLC 2.1](https://klc.kicad.org/footprint/f2/f2.1/), a set of footprint naming guidelines for specific footprint types is provided in [KLC F3.x](https://klc.kicad.org/footprint/f3).


## Sources

- https://klc.kicad.org/footprint/f2/
- https://klc.kicad.org/footprint/f2/f2.1/
- https://klc.kicad.org/footprint/f2/f2.2/
- https://klc.kicad.org/footprint/f2/f2.3/
- https://klc.kicad.org/footprint/f2/f2.4/
- https://klc.kicad.org/footprint/f2/f2.5/
