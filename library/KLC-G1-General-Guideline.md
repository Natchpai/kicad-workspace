# G1 General Guidelines

## G1.1 Only standard characters are used for naming libraries and components

Filenames, symbol names, footprint names, model names, 3D model names, and template names must contain only valid characters, as determined below:

1. Alphanumeric characters (`A-Z`, `a-z`, `0-9`)
2. Underscore `_`
3. Hyphen / dash `-`
4. Period / dot `.`
5. Comma `,`
6. Plus symbol `+`

This character set ensures that symbols will be compatible with all filesystems, and will not cause any issues due to character rendering.

Further, filenames and symbol names must **not use the space character**. This can cause issues with string escaping and is best avoided.

## G1.2 Withdrawn

This rule was withdrawn.

## G1.3 Libraries are organized by functionality

Rather than grouping components (e.g. symbols, footprints) by their manufacturer, KiCad libraries are organized by component functionality. This grouping strategy has a number of key benefits:

- Similar components are grouped together, allowing alternative parts to be easily substituted
- If possible, symbols should be *derived* from existing symbols to reduce library size
- Generic parts which are produced by multiple manufacturers are supported

Library organization should follow the general form as described below, with each element separated by the underscore (`_`) character:

*Note: Some of the elements listed above may be omitted if not required.*

For specific examples, refer to the guidelines for organizing [symbol libraries](https://klc.kicad.org/symbol/s1/s1.1) and [footprint libraries](https://klc.kicad.org/footprint/f1/f1.1).

## G1.4 English language should be used throughout libraries

KiCad software is used by people who speak many different languages. The KiCad software provides translations for these languages, but *the library files do not provide translations*.

Library files should be written using English, excepting where specific component names are non-English (for non-English manufacturers).

Where potential differences in spelling and grammar exist, American English should be given preference.

- `Color` instead of `Colour`

## G1.5 Plural naming is to be avoided

In general, plural naming (e.g. for libraries) should be avoided, as pluralisation of some words is inconsistent. Non pluralized names should be used in preference:

- `Sensor_Temperature` instead of `Sensors_Temperature`
- `Memory_Flash` instead of `Memories_Flash`
- `TerminalBlock` instead of `TerminalBlocks`

## G1.6 Capitalization conventions

1. Acronyms should be capitalized
	- `MCU` (microcontroller)
	- `FPGA` (field programmable gate array)
2. Manufacturer names should be capitalized according to the manufacturer
	- `Microchip`
	- `ROHM`
	- `Texas`
	- `NEC`
3. Unless separated by delimiters such as `_`, `-`, `.`, words should be separated using *CamelCase* convention, with the first letter of each word capitalised
	- `TestPoint`
	- `BatteryHolder`

## G1.7 Library files use Unix style line endings

Library files must always be commited to GitLab using Unix-style line endings. This means that lines are terminated using the **LF** (line feed) character, rather than the DOS style **CR+LF** line endings.

KiCad library files must be compatible across multiple operating systems, and users should be able to contribute without generating unnecessary *noise* in the files by constantly changing line endings.

When using the KiCad libraries on a Windows PC, the line endings in the library files may be automatically converted to **CR+LF**. This is fine, as long as any contributions made to the libraries observe the **LF** line ending requirements.

This issue is addressed by insisting that all KiCad libraries include a [.gitattributes](https://git-scm.com/docs/gitattributes) file. This file ensures that the line endings are automatically converted by Git.

An example of a simple.gitattributes file which ensures footprint files have correct line endings is as follows:

```
*.kicad_mod text
```

*Note: The KiCad library repositories should already have the correct.gitattributes file in place to achieve this*

## G1.8 Contributions to the official library must be made using the current stable version

Contributions of library assets must be created in the latest **stable** version of KiCad.

This is to avoid problems caused by changes in how assets are stored in different versions of KiCad. (Changes in how line ordering is determined, how strings are escaped, etc.) Another reason is to avoid including features not supported by the latest stable release.

## G1.9 Dimensional units

1. When specifying a dimension (e.g. in a footprint name) the *units* must always be provided:
2. When specifying areas or volumes, the coordinate order is `X-Y[-Z]`, which is equivalent to `width-height[-thickness]`.
3. When specifying multidimensional units (e.g. `width` x `height` x `thickness`) then the units only need to be appended once
	- `3x4x7mm` - 3mm x 4mm x 7mm
4. Metric units are preferred, where appropriate
5. Linear dimensions should be specified in millimeters
6. Angular dimensions should be specified in degrees
7. Temperature should be specified in degrees Celsius

## G1.10 Embedding files
Symbols and Footprints must not contain embedded files. Thus the embedded fonts checkbox also should never be set.

The feature is intended to embed datasheets, 3D models or fonts. All of those most likely are not compatible with the library license. Also, this would vastly increase the file size of the repositories.

Possible exceptions from this rule:

1. SPICE models in symbols

## G1.11 Default font

Exceptions:

1. Text in 3D models may use "real" fonts as appropriate. Open source fonts should be used to allow others to edit the models.
2. Text in graphical symbols may use graphical polygons as text when they require a specific font as part of a logo, but may not embed their own fonts (see G1.10).

## Sources
- https://klc.kicad.org/general/
- https://klc.kicad.org/general/g1/
- https://klc.kicad.org/general/g1/g1.1/
- https://klc.kicad.org/general/g1/g1.2/
- https://klc.kicad.org/general/g1/g1.3/
- https://klc.kicad.org/general/g1/g1.4/
- https://klc.kicad.org/general/g1/g1.5/
- https://klc.kicad.org/general/g1/g1.6/
- https://klc.kicad.org/general/g1/g1.7/
- https://klc.kicad.org/general/g1/g1.8/
- https://klc.kicad.org/general/g1/g1.9/
- https://klc.kicad.org/general/g1/g1.10/
- https://klc.kicad.org/general/g1/g1.11/