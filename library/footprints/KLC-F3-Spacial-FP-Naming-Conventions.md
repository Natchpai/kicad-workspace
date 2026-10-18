# F3 Specific Naming Conventions

## F3.1 SMD chip package naming conventions

The following footprint naming conventions should be used as *examples* for naming SMD chip package footprints.

If you do not find an appropriate convention that matches a particular footprint type, either contact the KiCad library team or try to match a convention set by existing library components.

In the entries below, variable fields are denoted as follows:

\- Fixed fields
\- Mandatory fields
\- Optional fields

\[*Prefix*\] \_\[*Imperial size*\] \_\[*Metric size*\] **Metric** \_\[*Modifiers*\] \_\[*Options*\]

- **Prefix** - Device type
- **Imperial size** - Imperial case size (Optional)
- **Metric size** - Metric case size (Optional)
- **Modifiers** - Modifiers to footprint if non standard (Optional)
- **Options** - Extra footprint options (Optional)

Example:

LED\_0805\_2012Metric\_ReverseMount

Notes:

The prefix is determined by the default reference designator of the device, e.g.

- Capacitor = `C`
- Capacitor (polarised) = `CP`
- Resistor = `R`
- Diode = `D`

Case size codes:

| Imperial Code | Metric Code | Size Imperial | Size Metric |
| --- | --- | --- | --- |
| 01005 | 0402 | 0.0157 in × 0.0079 in | 0.4 mm × 0.2 mm |
| 0201 | 0603 | 0.024 in × 0.012 in | 0.6 mm × 0.3 mm |
| 0402 | 1005 | 0.039 in × 0.020 in | 1.0 mm × 0.5 mm |
| 0603 | 1608 | 0.063 in × 0.031 in | 1.6 mm × 0.8 mm |
| 0805 | 2012 | 0.079 in × 0.049 in | 2.0 mm × 1.25 mm |
| 1008 | 2520 | 0.098 in × 0.079 in | 2.5 mm × 2.0 mm |
| 1206 | 3216 | 0.126 in × 0.063 in | 3.2 mm × 1.6 mm |
| 1210 | 3225 | 0.126 in × 0.098 in | 3.2 mm × 2.5 mm |
| 1806 | 4516 | 0.177 in × 0.063 in | 4.5 mm × 1.6 mm |
| 1812 | 4532 | 0.18 in × 0.13 in | 4.5 mm × 3.2 mm |
| 1825 | 4564 | 0.18 in × 0.25 in | 4.5 mm × 6.4 mm |
| 2010 | 5025 | 0.197 in × 0.098 in | 5.0 mm × 2.5 mm |
| 2512 | 6332 | 0.25 in × 0.13 in | 6.3 mm × 3.2 mm |
| 2920 | 7451 | 0.29 in × 0.20 in | 7.4 mm × 5.1 mm |

## F3.2 Resistor naming conventions

The following footprint naming conventions should be used as *examples* for naming resistor footprints.

If you do not find an appropriate convention that matches a particular footprint type, either contact the KiCad library team or try to match a convention set by existing library components.

In the entries below, variable fields are denoted as follows:

\- Fixed fields
\- Mandatory fields
\- Optional fields

### Axial Resistors

**R\_Axial** \_ **L** \[*Length*\] \_ **D** \[*Diameter*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **Length** - Resistor body length
- **Diameter** - Body diameter
- **Pitch** - Lead spacing
- **Modifiers** - Modifiers to footprint specifications (Optional)
- **Orientation** - Resistor orientation (Vertical / Horizontal) (Optional)
- **Options** - Extra footprint options (Optional)

Example:

R\_Axial\_L3.6mm\_D1.6mm\_P2.54mm\_Vertical

## F3.3 Capacitor naming conventions

The following footprint naming conventions should be used as *examples* for naming capacitor footprints.

If you do not find an appropriate convention that matches a particular footprint type, either contact the KiCad library team or try to match a convention set by existing library components.

In the entries below, variable fields are denoted as follows:

\- Fixed fields
\- Mandatory fields
\- Optional fields

### SMD Chip Capacitor

\[*C/CP*\] \_\[*Imperial size*\] \_\[*Metric size*\] **Metric** \_\[*Modifiers*\] \_\[*Options*\]

- **C/CP** - Capacitor style (polarised or non-polarised)
- **Imperial size** - Imperial case size (Optional)
- **Metric size** - Metric case size (Optional)
- **Modifiers** - Footprint modifiers if non standard (Optional)
- **Options** - Footprint options (Optional)

Example:

C\_0805\_2012Metric

Notes:

1. At least one case size (either imperial or metric) must be specified
2. Metric case size must have the suffix `Metric`

### SMD Tantalum Capacitor

**CP\_Tantalum** \_ **EIA-** \[*Metric size*\] \_\[*Size code*\] \_\[*Modifiers*\] \_\[*Options*\]

- **Metric size** - EIA metric size code
- **Size code** - Letter size code including naming standard (\[Standard\]-\[Letter\])
- **Modifiers** - Footprint modifiers if non standard (Optional)
- **Options** - Footprint options (Optional)

Example:

CP\_Tantalum\_EIA-3126-18\_Kemet-A\_Pad1.53x1.40mm\_HandSolder

| EIA Metric size | Body size (XxYxZ) | Kemet Code | AVX Code |
| --- | --- | --- | --- |
| 1608-08 | 1,6 x 0,8 x 0,8 mm | — | J |
| 1608-10 | 1,6 x 0,85 x 1,05 mm | — | L |
| 2012-12 | 2,05 x 1,35 x 1,2 mm | R | R |
| 2012-15 | 2,05 x 1,35 x 1,5 mm | — | P |
| 3216-10 | 3,2 x 1,6 x 1,0 mm | I | K |
| 3216-12 | 3,2 x 1,6 x 1,2 mm | S | S |
| 3216-18 | 3,2 x 1,6 x 1,8 mm | A | A |
| 3528-12 | 3,5 x 2,8 x 1,2 mm | T | T |
| 3528-15 | 3,5 x 2,8 x 1,5 mm | — | H |
| 3528-21 | 3,5 x 2,8 x 2,1 mm | B | B |
| 6032-15 | 6,0 x 3,2 x 1,5 mm | U | W |
| 6032-20 | 6,0 x 3,2 x 2,0 mm | — | F |
| 6032-28 | 6,0 x 3,2 x 2,8 mm | C | C |
| 7343-15 | 7,3 x 4,3 x 1,5 mm | W | X |
| 7343-20 | 7,3 x 4,3 x 2,0 mm | V | Y |
| 7343-30 | 7,3 x 4,3 x 3,0 mm | — | N |
| 7343-31 | 7,3 x 4,3 x 3,1 mm | D | D |
| 7343-40 | 7,3 x 4,3 x 4,0 mm | Y | — |
| 7343-43 | 7,3 x 4,3 x 4,3 mm | X | E |
| 7360-38 | 7,3 x 6,0 x 3,8 mm | E | — |
| 7361-38 | 7,3 x 6,1 x 3,8 mm | — | V |
| 7361-438 | 7,3 x 6,1 x 4,3 mm | — | U |

### SMD Electrolytic Capacitor

**CP\_Elec** \_\[*Manufacturer*\] \_\[*X*\] x\[*Y*\] \_ **H** \[*Height*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Options*\]

- **Manufacturer** - Manufacturer name (Optional)
- **X** - Case size in x dimension
- **Y** - Case size in y dimension
- **Height** - Case height (Optional)
- **Pitch** - Lead spacing (Optional)
- **Modifiers** - Footprint modifiers if non-standard (Optional)
- **Options** - Footprint options (Optional)

Example:

CP\_Elec\_10x10.5mm\_H6mm

### THT Capacitor

\[*C/CP*\] \_\[*Style*\] \_ **L** \[*Case size*\] \_ **D** \[*Diameter*\] \_ **W** \[*Width*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Options*\]

- **C/CP** - Capacitor polarisation
- **Style** - Capacitor case style (see notes below)
- **Case size** - Body length (Optional)
- **Diameter** - Case diameter (Optional)
- **Width** - Body width (Optional)
- **Pitch** - Lead spacing
- **Modifiers** - Footprint modifiers if non-standard
- **Options** - Footprint options (Optional)

Example:

C\_Axial\_L67.0mm\_D26.0mm\_P75.0mm

Notes:

1. There are different capacitor styles available:
	- Axial: Cylindrical body with axial lead attachment.
	- Radial: Cylindrical body, both leads enter at same end.
	- Disc: Disc shaped body (sometimes enclosed), leads enter tangent to the inner disc
	- Rect: Box shaped body (Bottom face in contact with the board)
2. Body size:
    - For Axial body styles: L[length]_D[diameter]
    - For Radial body style: D[diameter]{_H[height]}
    - For Disc body style: D[diameter]_W[width]{_H[overall height]}
    - For box shaped body styles: [X]x[Y]{x[Z]}

## F3.4 SMD IC package naming conventions

The following footprint naming conventions should be used as *examples* for naming SMD IC package footprints.

If you do not find an appropriate convention that matches a particular footprint type, either contact the KiCad library team or try to match a convention set by existing library components.

In the entries below, variable fields are denoted as follows:

\- Fixed fields
\- Mandatory fields
\- Optional fields

### Gullwing Packages

The format below provides a guide for naming Gullwing IC packages.

Examples:

- SOIC
- SOP
- QFP
- J-Lead

\[*PKG*\] \-\[*Pin count*\] \-\[*EP Qty*\] **EP** \_\[*X*\] x\[*Y*\] x\[*Z*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Options*\]

- **PKG** - Package name
- **Pin count** - Number of (unique) pins
- **EP Qty** - Number of exposed pads under the device (if greater than zero) (Optional)
- **X** - Major dimension of part on x axis
- **Y** - Major dimension of part on y axis
- **Z** - Major dimension of part on z axis (Optional)
- **Pitch** - Lead pitch
- **Modifiers** - Footprint modifiers (Optional)
- **Options** - Extra footprint options (Optional)

Example:

SOIC-16\[-\]\[1\]\[EP\]\[\_\]\[3.9\]\[x\]\[9.9mm\]\[\_\]\[P\]\[1.27mm\]

Notes:

1. \[`PKG`\] - refers to the name most commonly used in the industry. Generally this implies JEDEC naming but some other standard may be used as required.
2. \[`Pin count`\] - the number of *uniquely numbered* pads (excluding any exposed pads under the device)
3. \[`Modifiers`\] - may vary for individual IC footprint types. Includes:
	- Clearance
	- Lead size
	- Pad size
	- Exposed pad size
	- Soldermask expansion

### No-Lead Packages

Examples:

- DFN
- QFN
- LCC

\[*PKG*\] \-\[*Pincount*\] \-\[*EP Qty*\] **EP** \_\[*X*\] x\[*Y*\] x\[*Z*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Options*\]

- **PKG** - Package name
- **Pincount** - Number of (unique) pins
- **EP Qty** - Number of exposed pads under the device (if greater than zero) (Optional)
- **X** - Major dimension of part on x axis
- **Y** - Major dimension of part on y axis
- **Z** - Major dimension of part on z axis (Optional)
- **Pitch** - Lead pitch
- **Modifiers** - Footprint modifiers (Optional)
- **Options** - Extra footprint options (Optional)

Example:

DFN-12\[-\]\[1\]\[EP\]\[\_\]\[4\]\[x\]\[4\]\[x\]\[0.9mm\]\[\_\]\[P\]\[0.5mm\]

Notes:

1. The lead length is the nominal lead length for which the footprint is designed
2. Optionally the nominal lead width can also be provided

### Ball Grid Array Packages

\[*PKG*\] \-\[*Pincount*\] \_\[*X*\] x\[*Y*\] x\[*Z*\] \_ **Layout** \[*Columns*\] x\[*Rows*\] \_ **P** \[*Pitch X*\] x\[*Pitch Y*\] \_ **Ball** \[*Ball*\] \_ **Pad** \[*Pad*\] \_\[*NSMD/SMD*\] \_\[*Modifiers*\] \_\[*Options*\]

- **PKG** - Package name
- **Pincount** - Number of (unique) pins
- **X** - Major dimension of part on x axis
- **Y** - Major dimension of part on y axis
- **Z** - Major dimension of part on z axis (Optional)
- **Columns** - Number of ball columns
- **Rows** - Number of ball rows
- **Pitch X** - Ball pitch in x direction
- **Pitch Y** - Ball pitch in y direction (if different from x direction (Optional)
- **Ball** - Ball diameter
- **Pad** - Pad diameter
- **NSMD/SMD** - Solder Mask Defined or Non Solder Mask Defined
- **Modifiers** - Footprint modifiers (Optional)
- **Options** - Extra footprint options (Optional)

Example:

BGA-24\[\_\]\[3.2\]\[x\]\[4.4mm\]\[\_\]\[Layout\]\[3\]\[x\]\[4\]\[\_\]\[P\]\[0.5mm\]\[\_\]\[Ball\]\[0.25mm\]\[\_\]\[Pad\]\[0.2mm\]\[\_\]\[NSMD\]

Notes:

1. For BGA simply providing the pin count is not sufficient. It is also necessary to provide the number of \[`Columns`\] (x direction) and \[`Rows`\] (y direction).
2. Some BGA packages have different pitch in x and y directions. If this is the case then both \[`Pitch`\] dimensions need to be provided
3. The \[`Ball`\] diameter for which the footprint is designed needs to be provided
4. \[`NSMD/SMD`\]
	- NSMD means the footprint is designed for `non solder mask defined` (mask cutout is larger than copper pad)
	- SMD means the footprint is designed for `solder mask defined` (mask cutout is smaller than copper pad)


## F3.5 THT IC package naming conventions

The following footprint naming conventions should be used as *examples* for naming THT IC package footprints.

If you do not find an appropriate convention that matches a particular footprint type, either contact the KiCad library team or try to match a convention set by existing library components.

In the entries below, variable fields are denoted as follows:

\- Fixed fields
\- Mandatory fields
\- Optional fields

### Through Hole Packages (DIP)

\[*PKG*\] \-\[*Pincount*\] \_\[*X*\] x\[*Y*\] x\[*Z*\] \_ **W** \[*Lead span*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Options*\]

- **PKG** - Package name
- **Pincount** - Number of (unique) pins
- **X** - Major dimension of part on x axis
- **Y** - Major dimension of part on y axis
- **Z** - Major dimension of part on z axis (Optional)
- **Lead span** - Distance between leads
- **Pitch** - Lead pitch
- **Modifiers** - Modifiers to footprint specifications
- **Options** - Extra footprint options (Optional)

Example:

DIP-14\[\_\]\[W\]\[10.16mm\]\[\_\]\[Clearance\]

Notes:

1. Drill size (if specified) must be given in `mm`

### Through Hole Packages (TO)

\[*PKG*\] \-\[*Pincount*\] \_\[*X*\] x\[*Y*\] x\[*Z*\] \_ **W** \[*Lead span*\] \_ **P** \[*Pitch x*\] x\[*Pitch y*\] \_\[*Stagger*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **PKG** - Package name
- **Pincount** - Number of (unique) pins
- **X** - Major dimension of part on x axis (Optional)
- **Y** - Major dimension of part on y axis (Optional)
- **Z** - Major dimension of part on z axis (Optional)
- **Lead span** - Distance between leads (Optional)
- **Pitch x** - Lead pitch in x dimension (Optional)
- **Pitch y** - Lead pitch in y dimension (if different from x dimension) (Optional)
- **Stagger** - Pin staggering options (Optional)
- **Modifiers** - Modifiers to footprint specifications (Optional)
- **Orientation** - Component orientation (see notes below)
- **Options** - Extra footprint options (Optional)

Example:

TO-220-5\_Vertical

Notes:

1. Drill size (if specified) must be given in `mm`
2. `Orientation` can be chosen from:
3. `Stagger` can be chosen from:

**Size Parameter:**

[![to-body_dim](https://klc.kicad.org/img/klc/to-body_dim.png "Body dimension details")](https://klc.kicad.org/img/klc/to-body_dim.png)

Orientation:

[![to-THT_orientation](https://klc.kicad.org/img/klc/to-THT_orientation.png "TO THT orientation")](https://klc.kicad.org/img/klc/to-THT_orientation.png)

## F3.6 Connector naming conventions
The following footprint naming conventions should be used as *examples* for naming connector footprints.

If you do not find an appropriate convention that matches a particular footprint type, either contact the KiCad library team or try to match a convention set by existing library components.

In the entries below, variable fields are denoted as follows:

\- Fixed fields
\- Mandatory fields
\- Optional fields

### Conventions for Connectors

Connector footprints are extremely diverse and the naming conventions for connectors can be complicated. This section details some examples of naming schemes for various connector types. While there are variations between connectors, the general format for naming connectors is as follows:

\[*Series*\] \_\[*Subseries*\] \-\[*Pins*\] \_\[*MPN*\] \_\[*Pin layout*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **Series** - Generic series name (Optional)
- **Subseries** - Series secondary identifier (Optional)
- **Pins** - Pin count (Optional)
- **MPN** - Manufacturer specific identifier (Optional)
- **Pin layout** - Pin configuration, specific to connector type (Optional)
- **Pitch** - Pin pitch, if not implied by connector standard (Optional)
- **Modifiers** - Modifiers to connector specifications (pad size, etc) (Optional)
- **Orientation** - Orientation of connector relative to board (Optional)
- **Options** - Extra footprint options (Optional)

Notes:

1. \[`Series`\] - a versatile field which could contain:
	- Functional description (e.g. `USB`)
	- Connector type (e.g. `PinHeader` or `TerminalBlock`)
	- Industry standard (e.g. `DSUB-15`)
	- Manufacturer specific series (e.g. `Hirose_DF13`)
2. \[`MPN`\] (manufacturer part number) - uniquely identifies a connector according to that manufacturer’s internal naming conventions
3. \[`Pin layout`\] - dependent on the connector type
	- Single row connectors: 1x\[`number of pins`\]
	- Multi row connectors with equal number of pins in each row: \[`number of rows`\]x\[`number of pins per row]`
	- Other connectors: \[`number of rows`\]Rows\_\[`number of pins overall`\]Pins
	- Connectors for standardized interfaces do not need to include the pin configuration information (e.g. USB)
4. Number format:
	- \[`number of rows`\] number of rows no leading zero.
	- \[`number of pins per row`\] and \[`number of pins`\] two digit number with leading zero. (can have more digits for connectors with > 99 pins)
5. \[`Pitch`\] - if the connector standard does not imply the pin pitch, then this field is required
6. \[`Modifiers`\] - multiple fields may be added here, detailing modifications or devations from the standard footprint design. Examples include:
	- Pad size variation
	- Drill size variation
7. \[`Orientation`\] - The orientation of the connector with reference to the board plane

[![connector_orientation](https://klc.kicad.org/img/klc/connector_orientation.png "The orientation of connectors is determined by the plug direction.")](https://klc.kicad.org/img/klc/connector_orientation.png)

7. \[`Options`\] - Extra footprint options

In addition to these conventions, additional schemes are employed for specific connector types - these are detailed below.

#### Connectors for Specific Functions

Many connectors are designed for specific functions (e.g. USB, HDMI, SD-Card, etc). In these cases, specific naming conventions should be followed:

\[*Function*\] \_\[*Standard*\] \_\[*Size*\] \-\[*Type*\] \_\[*MAN*\] \_\[*MPN*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **Function** - Functional purpose of the connector
- **Standard** - Standard to which the connector complies, if applicable (Optional)
- **Size** - Connector size (e.g. Micro/Mini) (Optional)
- **Type** - Connector sub-type (e.g. A/B/C) (Optional)
- **MAN** - Manufacturer name (Optional)
- **MPN** - Manufacturer part number (Optional)
- **Modifiers** - Footprint modifiers (Optional)
- **Orientation** - Connector orientation (Optional)
- **Options** - Extra footprint options (Optional)

Example:

USB\_Micro-B\_Molex\_105133-0001\_Vertical

Notes:

1. Some *examples* of functional connector naming are provided below:
	- `USB_Micro-B_Wuerth_614105150721_Vertical_CircularHoles`
	- `HDMI_Micro-D_Molex_46765-2x0x`
	- `MicroSD_Wuerth_WR-CRD_693072010801`
2. In most cases, pin layout does not need to be explicitly specified

#### Connectors with Standardised Shape

Many connectors are provided by multiple manufacturers in an industry standard package or physical layout. These connectors should use the accepted industry naming at the beginning of the footprint name:

\[*Standard*\] \-\[*Pins*\] \_\[*Series modifier*\] \_\[*MAN*\] \_\[*Series*\] \_\[*MPN*\] \_\[*Pin layout*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **Standard** - Generic connector standard (see notes below)
- **Pins** - Number of pins
- **Series modifier** - Series Modifier (see notes below)
- **MAN** - Manufacturer name (Optional)
- **Series** - Manufacturer series name (Optional)
- **MPN** - Manufacturer part number (Optional)
- **Pin layout** - Pin configuration, if not fully defined by applicable standard (Optional)
- **Pitch** - Pin pitch, if not fully defined by applicable standard (Optional)
- **Modifiers** - Footprint modifier field(s) (Optional)
- **Orientation** - Connector orientation (if multiple options exist) (Optional)
- **Options** - Extra footprint options (Optional)

Example:

DSUB-15\[\_\]\[HighDensity\]\[\_\]\[Vertical\]

Notes:

1. The generic connector type \[`Standard`\] defines the shape of the connector
	- e.g. `DSUB` `Tab` `Circular`

#### Generic Connector Types

Examples of generic arrayed connectors:

- PinHeader
- PinSocket
- TerminalBlock

\[*Connector type*\] \_\[*MPN*\] \_\[*Pin layout*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **Connector type** - Generic connector style (see notes below)
- **MPN** - Manufacturer specific identifier (Optional)
- **Pin layout** - Pin configuration layout (see notes below)
- **Pitch** - Pin pitch
- **Modifiers** - Modifiers to connector specifications (pad size, etc) (Optional)
- **Orientation** - Orientation of connector relative to board
- **Options** - Extra footprint options (Optional)

Example:

PinHeader\_1x10\_P2.54mm\_Drill1.25mm\_Horizontal

#### Manufacturer Specific Connectors

Manufacturer series connectors are those which are particular to a particular manufacturer standard.

\[*MAN*\] \_\[*Series*\] \_\[*MPN*\] \_\[*Pin layout*\] \_ **P** \[*Pitch*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **MAN** - Manufacturer name (Optional)
- **Series** - Manufacturer series name
- **MPN** - Manufacturer part number
- **Pin layout** - Pin layout information (see notes below)
- **Pitch** - Pad pitch
- **Modifiers** - Modifiers to connector specifications (pad size, etc)
- **Orientation** - Direction of connector insertion relative to board plane
- **Options** - Extra footprint options (Optional)

Example:

JST\_GH\_S12B-EH\_1x13\_P2.50mm\_Pad1.80mm\_Horizontal

Notes:

1. If the footprint is located in a library dedicated to a single manufacturer, then the `MAN` prefix is not required

## F3.7 Fuse naming conventions

The following footprint naming conventions should be used as *examples* for naming fuse and fuse holder footprints.

If you do not find an appropriate convention that matches a particular footprint type, either contact the KiCad library team or try to match a convention set by existing library components.

In the entries below, variable fields are denoted as follows:

\- Fixed fields
\- Mandatory fields
\- Optional fields

### Fuse Holders

**FuseHolder** \_\[*Fuse Type*\] \_\[*MAN*\] \_\[*Series*\] \_\[*MPN*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **Fuse Type** - Type of fuse (Optional)
- **MAN** - Manufacturer name (Optional)
- **Series** - Manufacturer series name (Optional)
- **MPN** - Manufacturer part number (Optional)
- **Modifiers** - Footprint modifiers if non-standard (Optional)
- **Orientation** - Orientation of fuse, if multiple orientations are available (Optional)
- **Options** - Extra footprint options (Optional)

Example:

FuseHolder\_Littelfuse\_TE5\_395

Examples of `Fuse Type` field:

- Automotive fuses:
	- Automotive-Micro2
	- Automotive-Micro3
	- Automotive-LowProfile
	- Automotive-Mini
	- Automotive-ATO
	- Automotive-Maxi
	- Automotive-Bosch
	- Automotive-SFE-\[SizeCode\]
- Industrial fuses
	- Cylinder-\[diameter\]x\[length\]mm

### Fuses

#### Cylindrical Fuse

**Fuse** \_\[*MAN*\] \_\[*Series*\] \_\[*MPN*\] \_\[*Body size*\] \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **MAN** - Manufacturer name (Optional)
- **Series** - Manufacturer series name (Optional)
- **MPN** - Manufacturer part number (Optional)
- **Body size** - Major fuse dimensions
- **Modifiers** - Footprint modifiers if non standard (Optional)
- **Orientation** - Orientation of fuse, if multiple orientations are available (Optional)
- **Options** - Extra footprint options (Optional)

Example:

Fuse\_Littelfuse\_LVR100

#### Rectangular SMD Fuses

**Fuse** \_\[*Imperial size*\] \_\[*Metric size*\] **Metric** \_\[*Modifiers*\] \_\[*Orientation*\] \_\[*Options*\]

- **Imperial size** - Imperial case size (Optional)
- **Metric size** - Metric case size (Optional)
- **Modifiers** - Footprint modifiers if non standard (Optional)
- **Orientation** - Orientation with respect to board plane (Optional)
- **Options** - Footprint options (Optional)

Example:

Fuse\_0805


## Sources

- https://klc.kicad.org/footprint/f3/
- https://klc.kicad.org/footprint/f3/f3.1/
- https://klc.kicad.org/footprint/f3/f3.2/
- https://klc.kicad.org/footprint/f3/f3.3/
- https://klc.kicad.org/footprint/f3/f3.4/
- https://klc.kicad.org/footprint/f3/f3.5/
- https://klc.kicad.org/footprint/f3/f3.6/
- https://klc.kicad.org/footprint/f3/f3.7/