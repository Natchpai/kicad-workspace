# S2 Symbol Naming

Guidelines in this section :

## S2.1 General symbol naming guidelines

1. Library naming should not be duplicated in symbol name
2. If symbol with same name exists for multiple manufacturers, the manufacturer name is written first
3. Fully specified symbols are named based on the manufacturer part number
	1. If multiple manufacturers produce compatible parts but their part number suffixes for specifying the package differ, then the common base part number is used with clear name suffix for the footprint (e.g. `L78L05_TO92`)
	2. Non-functional parts of the MPN must be replaced with a wildcard. (Refer to [requirements for the use of wildcards in MPN](https://klc.kicad.org/symbol/s2/s2.2))
4. Generic symbols use the device type
	1. May be shortened for common components (e.g. `Conn` for `Connector`)
	2. Reference designator may be substituted for common components (e.g. `D`, `C`, `LED`)
5. Indicate quantity of elements for symbol arrays (e.g. resistor array with 8 elements - `Resistor_x8`)
6. Any modification of the original symbol, indicated by appending the reason
	1. Different pin ordering - `Q_NPN_CBE`, `Q_NPN_BCE`
	2. For multi-unit variants of typically single-unit symbols add the suffix `_Split`

## S2.2 Non-functional variations in part number should be replaced with wildcard

Manufacturer Part Numbers (MPN) often include variations that are *non-functional* in terms of schematic entry and PCB layout.

Examples of parameters considered non-functional:

Examples of parameters considered *functional* are those that affect the schematic or layout of the part:

- Electrical variations - these indicate important different characteristics (e.g. different supply voltages)
- Package options - these indicate different footprints and/or pinouts

To capture every possible combination of part variation would require a large number of derived symbols and is to be avoided.

1. Where an MPN has options for such non-functional variations, these portions of the MPN should be replaced with the wildcard character (lowercase `x`).
	1. If these non-functional parts of the MPN are at the end of the symbol name then the wildcard should be omitted.
2. Functional variations should be captured in the symbol name.
3. If there’s only one functional variation of the part, the wildcard does not need to be applied
	1. Example: `TPS3430` has only one variant: `TPS3430WDRCR`. So the name should be `TPS3430WDRC`, rather than `TPS3430xDRC`.

## S2.3 Where parts are available in multiple footprint options, a separate symbol must be drawn for each footprint

Many electronic components are provided in multiple packages. These *may or may not* be pin compatible.

Fully specified symbols require a separate symbol for every package. If they are pin compatible, the **derive from existing symbol** function must be used. Footprints in KiCad have a 1:1 relationship with their 3D model. This means multiple footprints are required where the 3D model has functional differences even if the footprints are identical (for example when 3D model height differs).

e.g. **LTC4357**

[![S2.4a](https://klc.kicad.org/img/klc/S2.4a.png "Multiple footprint options")](https://klc.kicad.org/img/klc/S2.4a.png)

This part comes in two distinct packages each requiring a separate footprint. Hence a symbol for each variant must be drawn.

For naming of the symbols refer to [General symbol naming guidelines](https://klc.kicad.org/symbol/s2/s2.1/)

[![S2.4b](https://klc.kicad.org/img/klc/S2.4b.png "Symbol for each footprint")](https://klc.kicad.org/img/klc/S2.4b.png)

Where possible, the symbols should be drawn such that they can be swapped in the schematic with minimal disruption to wire connections.

As a further example we shall consider the comparator **MCP6566** which is available in three SOT-23-5 versions, *each with a different pinout*.

In this case, a separate symbol must again be drawn for each version, and named according to the convention called out in the datasheet.

## Sources
- https://klc.kicad.org/symbol/s2/
- https://klc.kicad.org/symbol/s2/s2.1/
- https://klc.kicad.org/symbol/s2/s2.2/
- https://klc.kicad.org/symbol/s2/s2.3/