# KiCad Library Conventions (KLC)

One Markdown file per KLC rule, converted from the official KLC source.

- Site: <https://klc.kicad.org/>
- Source: <https://gitlab.com/kicad/libraries/klc> (`content/`, commit `6e8cbad95563`)
- KLC version: 3.0.67 (2026-06-20)
- Converted: 2026-10-18
- License: the KLC text is dual licensed under GPL-3.0-or-later or CC BY 3.0 or later, by the KiCad library team. These files are an unofficial Markdown conversion. Check the source for the current text.

## Conversion notes

- Images are links to `https://klc.kicad.org/img/klc/`. They are not stored here.
- Footprint naming patterns (F3) are written as `<Field>` for variable fields and `[ ]` around optional parts. The site shows this with colors.
- Nested ordered lists use numbers. The site shows the 2nd level as letters (a, b) and the 3rd level as roman numerals (i, ii).
- Typos and numbering in the source are kept as they are.

## General Guidelines (G)

### G1 General Guidelines

- [G1.1 Only standard characters are used for naming libraries and components](general/G1.1.md)
- [G1.2 Withdrawn](general/G1.2.md)
- [G1.3 Libraries are organized by functionality](general/G1.3.md)
- [G1.4 English language should be used throughout libraries](general/G1.4.md)
- [G1.5 Plural naming is to be avoided](general/G1.5.md)
- [G1.6 Capitalization conventions](general/G1.6.md)
- [G1.7 Library files use Unix style line endings](general/G1.7.md)
- [G1.8 Contributions to the official library must be made using the current stable version](general/G1.8.md)
- [G1.9 Dimensional units](general/G1.9.md)
- [G1.10 Embedding files](general/G1.10.md)
- [G1.11 Default font](general/G1.11.md)

### G2 Generic and Fully Specified Symbols

- [G2.1 Definition of terms: Generic and fully specified symbols](general/G2.1.md)

### G3 Special Pin Numbering

- [G3.1 Relays](general/G3.1.md)
- [G3.2 Audio Connectors](general/G3.2.md)

## Symbol Guidelines (S)

### S1 Symbol Libraries

- [S1.1 Symbol libraries should be categorized by function](symbol/S1.1.md)

### S2 Symbol Naming

- [S2.1 General symbol naming guidelines](symbol/S2.1.md)
- [S2.2 Non-functional variations in part number should be replaced with wildcard](symbol/S2.2.md)
- [S2.3 Where parts are available in multiple footprint options, a separate symbol must be drawn for each footprint](symbol/S2.3.md)

### S3 General Symbol Requirements

- [S3.1 Origin is centered on the middle of the symbol](symbol/S3.1.md)
- [S3.2 Text fields should use a common text size of 50mils](symbol/S3.2.md)
- [S3.3 Symbol outline and fill requirements](symbol/S3.3.md)
- [S3.4 Symbols with complex functionality may incorporate simple functional diagrams](symbol/S3.4.md)
- [S3.5 Pin connection points must be placed outside of the symbol](symbol/S3.5.md)
- [S3.6 Pin name position offset](symbol/S3.6.md)
- [S3.7 Pin numbering for specialized pads](symbol/S3.7.md)
- [S3.8 Multi unit symbols](symbol/S3.8.md)
- [S3.9 De-Morgan representation](symbol/S3.9.md)

### S4 Pin Requirements

- [S4.1 General pin requirements](symbol/S4.1.md)
- [S4.2 Pins should be grouped by function](symbol/S4.2.md)
- [S4.3 Rules for pin stacking](symbol/S4.3.md)
- [S4.4 Pin electrical type](symbol/S4.4.md)
- [S4.5 Pins not connected on the footprint may be omitted from the symbol](symbol/S4.5.md)
- [S4.6 Hidden pins](symbol/S4.6.md)
- [S4.7 Active low pins should be designated using a bar above the symbol name](symbol/S4.7.md)

### S5 Footprint Association

- [S5.1 Symbols with a default footprint link to a valid footprint file](symbol/S5.1.md)
- [S5.2 Footprint filters must match all appropriate footprints. They should be designed to result in no false suggestions.](symbol/S5.2.md)

### S6 Symbol Metadata

- [S6.1 Component Reference Designator (RefDes)](symbol/S6.1.md)
- [S6.2 Symbol fields and metadata filled out as required](symbol/S6.2.md)

### S7 Special Symbols

- [S7.1 Power symbols](symbol/S7.1.md)
- [S7.2 Graphical symbols](symbol/S7.2.md)

## Footprint Guidelines (F)

### F1 Footprint Libraries

- [F1.1 Footprint libraries are categorized by function](footprint/F1.1.md)
- [F1.2 Connector footprint libraries](footprint/F1.2.md)

### F2 General Footprint Naming Guidelines

- [F2.1 General footprint naming conventions](footprint/F2.1.md)
- [F2.2 Footprint naming field prefixes](footprint/F2.2.md)
- [F2.3 Manufacturer specific version of generic footprints](footprint/F2.3.md)
- [F2.4 Footprint naming for non-standard pin numbering](footprint/F2.4.md)
- [F2.5 Footprint naming conventions for specific components](footprint/F2.5.md)

### F3 Specific Footprint Naming Guidelines

- [F3.1 SMD chip package naming conventions](footprint/F3.1.md)
- [F3.2 Resistor naming conventions](footprint/F3.2.md)
- [F3.3 Capacitor naming conventions](footprint/F3.3.md)
- [F3.4 SMD IC package naming conventions](footprint/F3.4.md)
- [F3.5 THT IC package naming conventions](footprint/F3.5.md)
- [F3.6 Connector naming conventions](footprint/F3.6.md)
- [F3.7 Fuse naming conventions](footprint/F3.7.md)

### F4 General Footprint Requirements

- [F4.1 Datasheet recommendations take priority](footprint/F4.1.md)
- [F4.2 Pin 1 should be located at the top left](footprint/F4.2.md)
- [F4.3 Connected copper elements have the same pad number](footprint/F4.3.md)
- [F4.4 Thermal pads](footprint/F4.4.md)
- [F4.5 Specifying footprint keepout areas](footprint/F4.5.md)
- [F4.6 Local clearance and settings should be set to zero](footprint/F4.6.md)

### F5 Layer Requirements

- [F5.1 Silkscreen layer requirements](footprint/F5.1.md)
- [F5.2 Fabrication layer requirements](footprint/F5.2.md)
- [F5.3 Courtyard layer requirements](footprint/F5.3.md)
- [F5.4 Elements on the graphic layer should not overlap](footprint/F5.4.md)

### F6 Surface Mount Components

- [F6.1 Footprint component type must be set to surface mount](footprint/F6.1.md)
- [F6.2 Footprint anchor should be placed in the middle of the component body](footprint/F6.2.md)
- [F6.3 Pad requirements for SMD footprints](footprint/F6.3.md)

### F7 Through Hole Components

- [F7.1 Footprint placement type must be set to Through Hole](footprint/F7.1.md)
- [F7.2 Footprint anchor should placed at the location of Pin-1](footprint/F7.2.md)
- [F7.3 Pin 1 should be rectangular or a rounded rectangle. Other pads circular or oval](footprint/F7.3.md)
- [F7.4 Pad requirements for THT footprints](footprint/F7.4.md)
- [F7.5 Minimum annular ring width](footprint/F7.5.md)
- [F7.6 THT hole diameter](footprint/F7.6.md)
- [F7.7 Oval holes (plated milled slots)](footprint/F7.7.md)

### F8 Virtual Components

- [F8.1 Non SMD/THT components](footprint/F8.1.md)

### F9 Footprint Properties

- [F9.1 Footprint meta-data is filled in as appropriate](footprint/F9.1.md)
- [F9.2 Footprint properties are as default values unless otherwise required in datasheet](footprint/F9.2.md)
- [F9.3 Footprint 3D model requirements](footprint/F9.3.md)

## 3D Model Guidelines (M)

### M1 Contributing Models

- [M1.1 The contributor must own the rights to share the 3D model](model/M1.1.md)
- [M1.2 Withdrawn](model/M1.2.md)
- [M1.3 Source files for 3D models must be supplied](model/M1.3.md)

### M2 3D File Requirements

- [M2.1 3D models must be supplied in STEP format](model/M2.1.md)
- [M2.2 Model alignment and scaling](model/M2.2.md)
- [M2.3 Freecad is the preferred design tool](model/M2.3.md)
