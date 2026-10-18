# G2 Generic and Fully Specified Symbols

## G2.1 Definition of terms: Generic and fully specified symbols

KiCad has two workflows regarding what a symbol represents and when it is assigned a footprint. It can be done in the library in which case the symbol represents an exact part or using the "Assign Footprints" tool at the end of the design process.

**Generic symbols**

Generic symbols can be used with multiple footprints. They *do not* have a default footprint assigned. Generic symbols allow flexibility in the design workflow. For this workflow the symbol placed into the schematic is typically selected to fit the intended function instead of fitting a particular part. The footprint assignment happens later when the exact part number is selected. Using generic symbols allows a small number of library symbol elements to represent a *very large number* of possible component combinations.

An example of the use of generic symbols are the **Resistor** and **Capacitor** symbols available in the KiCad library. These symbols do not have an assigned default footprint, as there are *many* possible compatible footprints.

 [![G2.1a](https://klc.kicad.org/img/klc/G2.1a.png "Single schematic symbol")](https://klc.kicad.org/img/klc/G2.1a.png)[![G2.1b](https://klc.kicad.org/img/klc/G2.1b.png "Associated with multiple footprints")](https://klc.kicad.org/img/klc/G2.1b.png)

**Fully specified symbols**

Fully specified symbols define a matching footprint, and are named based on the `MPN` (manufacturer part number). Such symbols do not depend on the user to select the correct footprint later but can have alternative footprints defined using footprint filters such that the user can select an alternate footprint.

[![G2.1c](https://klc.kicad.org/img/klc/G2.1c.png "Fully specified symbol")](https://klc.kicad.org/img/klc/G2.1c.png)

*A fully specified symbol together with a footprint specialized to one component are called an atomic part. A library of only such parts is called an atomic library. Confusingly, some users refer to a fully specified symbol as an atomic symbol.*

**Where to use which type**

The official library requires fully specified symbols except for a small number of libraries that contain only generic symbols. These generic libraries are:
- Device
- All Connector libraries
- The logic family libraries like 74xx, 4xxx, …​

## Sources
- https://klc.kicad.org/general/g2/
- https://klc.kicad.org/general/g2/g2.1/
