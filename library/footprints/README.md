# Footprint Libraries

The shared footprint libraries use family-based `0_*.pretty` names. There are 29 libraries containing 122 footprints. The empty LGA target was omitted because the inventory contains no verified LGA footprint.

```text
library/
└── footprints/
    ├── 0_Capacitor_SMD.pretty/
    ├── 0_Conn_AMASS.pretty/
    ├── 0_Conn_Barrel.pretty/
    ├── 0_Conn_Ethernet.pretty/
    ├── 0_Conn_FFC.pretty/
    ├── 0_Conn_JST.pretty/
    ├── 0_Conn_Mezzanine.pretty/
    ├── 0_Conn_Molex.pretty/
    ├── 0_Conn_PinHeader.pretty/
    ├── 0_Conn_RF.pretty/
    ├── 0_Conn_USB.pretty/
    ├── 0_Crystal.pretty/
    ├── 0_Diode_SMD.pretty/
    ├── 0_Graphics.pretty/
    ├── 0_Inductor_SMD.pretty/
    ├── 0_LED_SMD.pretty/
    ├── 0_MountingHole.pretty/
    ├── 0_NetTie.pretty/
    ├── 0_Oscillator.pretty/
    ├── 0_Package_BGA.pretty/
    ├── 0_Package_DFN_QFN.pretty/
    ├── 0_Package_QFP.pretty/
    ├── 0_Package_SO.pretty/
    ├── 0_Package_SON.pretty/
    ├── 0_Package_TO_SOT_SMD.pretty/
    ├── 0_Resistor_SMD.pretty/
    ├── 0_SolderJumper.pretty/
    ├── 0_Switch.pretty/
    └── 0_TestPoint.pretty/
```

See [FOOTPRINTS_DIRECTORY.md](../FOOTPRINTS_DIRECTORY.md) for the full footprint index.

## How to naming

### Footprint Directory (.pretty)

- **Library folder:** `0_<Family>.pretty`.
- `<Family>` is`<Category>[_<Subcategory>]`, for example `Package_QFP`, `Conn_USB`, `Resistor_SMD`.

    0_`<Category>`_`<Subcategory>`.pretty
    0_`<Component>`.pretty

### Footprint Files (.kicad_mod)

`<Package>`-`<pin_count>`_`<diamension>`_`<pitch>`_`<option>`.kicad_mod

- **Files inside**`.kicad_mod` names, are flexible: keep
  them as they are and do not rename them to enforce a pattern.
- `<Package>` : QFN, LQFP, SOT-23, LED
- `<pin_count>` : 3, 5, 6
- `<diamension>` : [y.y]x[x.x]mm (for example, 2.5x3mm, 3x3mm, 10x10mm)
- `<pitch>` : P0.5mm, P0.8mm, P51.27mm, P2.54mm, P5.00mm
- `<option>` : reference, from Part number (for example, STM32G474,), Logo

Follow the KLC F rules in [../KLC/footprint/](../KLC/README.md).