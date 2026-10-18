# S1 Symbol Libraries

Guidelines in this section:

## S1.1 Symbol libraries should be categorized by function

Symbol library names must be defined based on the priority list below, with each element separated by the underscore (`_`) character:

1. Function (e.g. `Sensor`, `Amplifier`, `MCU`)
2. Sub-function (e.g. `Temperature`, `CurrentSense`)
3. Tertiary qualifier (e.g. `CMOS`)
4. Manufacturer name (e.g. `Atmel`, `Infineon`)
5. Symbol series name (e.g. `PIC24`, `STM32`)
6. Extra library descriptors (e.g. `Deprecated` )

*Note: Some of the elements listed above may be omitted if not required.*

Example symbol library names:

- `Power_Monitor` - Power monitoring components
- `Sensor_Temperature` - Temperature sensors
- `Driver_Motor` - Motor drivers
- `MCU_Microchip_PIC32` - PIC32 microcontrollers from Microchip

## Sources
- https://klc.kicad.org/symbol/s1/
- https://klc.kicad.org/symbol/s1/s1.1/