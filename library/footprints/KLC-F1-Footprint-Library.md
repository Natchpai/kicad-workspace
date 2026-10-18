# F1 Footprint Library

## F1.1 Footprint libraries are categorized by function

Footprints are grouped into libraries (directories with `.pretty` extension) based on their primary function. As an extension of this, footprint libraries should be named based on this same functionality.

Library names must be defined based on the priority list below, with each element separated by the underscore (`_`) character:

* Function (e.g. `Conn`, `Capacitor`)
* Sub-function (e.g. `HDMI`, `USB`)
* Tertiary qualifier (e.g. `RightAngle`, `SMD`)
* Manufacturer name (e.g. `Texas`, `Microchip`)
* Footprint series name (e.g. `MicroFit`)
* Extra library descriptors as required

Note: Some of the elements listed above may be omitted if not required._

Example footprint library names:

* `Conn_USB_SMD` - Surface mount USB connectors
* `Conn_Molex_MicroFit` - Molex MicroFit series rectangular connectors
* `Capacitor_Tantalum_SMD` - Surface mount Tantalum capacitors


## F1.2 Connector footprint libraries

Categorizing connectors _by function_ can prove difficult as many connectors can be used in a wide variety of applications.

Therefore, categorization of connector footprints is given special consideration as detailed below:

1. Connectors are grouped firstly by their _primary function_ (where such a function exists). Examples of _primary function_ include:

* `Conn_USB`
* `Conn_HDMI`
* `Conn_Ethernet`

2. When primary function libraries become too large, they can be split by sub-function or by manufacturer

* `Conn_USB_Molex`
* `Conn_DSUB_HighDensity`

3. For connectors without a specific function, then connectors are grouped by their _mechanical type_:

* `Conn_Barrel`
* `Conn_DIN`
* `Conn_DSUB`
* `Conn_PinHeader`
* `Conn_PinSocket`
* `Conn_Rectangular`

4. Connector libraries can be further split by another qualifier:
* `Conn_PinHeader_2.54mm`
* `Conn_PinHeader_1.27mm`

5. Connector libraries can also be split by manufacturer and series, _for multi-purpose connectors_

* `TerminalBlock_Phoenix_MKDS`
* `TerminalBlock_Phoenix_PT`
* `TerminalBlock_Wago`
* `Conn_JST`
* `Conn_Hirose_DF13`

## Sources

- https://klc.kicad.org/footprint/
- https://klc.kicad.org/footprint/f1/
- https://klc.kicad.org/footprint/f1/f1.1/
- https://klc.kicad.org/footprint/f1/f1.2/