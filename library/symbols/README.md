# Custom Symbol Libraries

KiCad 10 unpacked symbol libraries. Each **.kicad_symdir/** directory is one library; each **.kicad_sym** file contains one root symbol and its units. See [the complete directory index](../SYMBOLS_DIRECTORY.md).

| Library | Symbol count | Members |
|---|---:|---|
| **0_Amplifier_Operational** | 1 | **TLV9061xDBV** |
| **0_Conn_Ethernet** | 2 | **JXD0-0019NL**, **MGB005-1CF1B002H** |
| **0_Conn_Generic** | 12 | **Conn_01x02**, **Conn_01x02_MountingPin**, **Conn_01x04_MountingPin**, **Conn_01x05_MountingPin**, **Conn_01x06**, **Conn_01x06_MountingPin**, **Conn_01x08_MountingPin**, **Conn_01x16_MountingPin**, **Conn_02x02_Top_Bottom**, **Conn_02x03_Top_Bottom**, **Conn_JTAG_STDC10**, **SolderPad** |
| **0_Conn_Mezzanine** | 1 | **10144518-101802LF** |
| **0_Conn_USB** | 3 | **USB_B_Micro**, **USB_B_Mini**, **USB_C_Receptacle_USB2.0_16P** |
| **0_Crystal** | 1 | **Crystal_GND24** |
| **0_Diode** | 5 | **BAT54XV2**, **BAT60J**, **MBR0520L**, **MBRA340**, **SL34A** |
| **0_Driver_FET** | 1 | **UCC27282DRC** |
| **0_Inductor** | 1 | **L_dot** |
| **0_Interface_Ethernet** | 1 | **KSZ9131RNX** |
| **0_Interface_USB** | 2 | **FT2232HQ**, **USB3320C-EZK** |
| **0_Jumper** | 11 | **Jumper_2_Bridged**, **Jumper_2_Open**, **Jumper_2_Small_Bridged**, **Jumper_2_Small_Open**, **Jumper_3_Bridged12**, **Jumper_3_Open**, **SolderJumper_2_Bridged**, **SolderJumper_2_Open**, **SolderJumper_3_Bridged12**, **SolderJumper_3_Bridged123**, **SolderJumper_3_Open** |
| **0_Logic_74x** | 1 | **SN74LVC1G07DCK** |
| **0_MCU_ST_STM32G4** | 1 | **STM32G474R_B-C-E_Tx** |
| **0_MCU_ST_STM32H7** | 1 | **STM32H743VITx** |
| **0_Memory_DDR3** | 1 | **MT41K256M16TW-107** |
| **0_Memory_EEPROM** | 1 | **M93C46-WMN** |
| **0_Memory_eMMC** | 2 | **EMMC04G-M627-M06U**, **FEMC008GTTG7-T14-16** |
| **0_Memory_Flash** | 1 | **W25Q128JVP** |
| **0_Misc** | 1 | **BlankSymbol** |
| **0_Oscillator** | 2 | **ASDMB**, **ECS-2520MV** |
| **0_Power_Management** | 1 | **LM66100DCK** |
| **0_Power_Switch** | 1 | **TPS2051CDBV** |
| **0_Protection_eFuse** | 1 | **STEF05PU** |
| **0_Protection_ESD** | 9 | **DF2S6.2CT**, **ESD5Z3V3**, **ESD9L5.0S**, **GSEWT3U003C**, **PESD4USB5BTBR-Q**, **PUSB3FR4Z**, **SMBJ30A**, **SP3031-01E**, **USBLC6-2SC6** |
| **0_Reference_Voltage** | 1 | **MCP1501-30xCHY** |
| **0_Regulator_DDR_VTT** | 1 | **TPS51200DRC** |
| **0_Regulator_Linear** | 2 | **LDLN025M33**, **SPX3819M5-L-3-3** |
| **0_Regulator_Switching** | 2 | **LMR54410DBV**, **TPS62A0x** |
| **0_Sensor_Current** | 3 | **ACS37030LLZA**, **INA180Ax**, **INA187Ax** |
| **0_Sensor_Temperature** | 1 | **TMP235A4DCK** |
| **0_SoC_AMD_Zynq** | 1 | **XC7Z010-xCLG400** |
| **0_Switch** | 5 | **SW_DIP_x03**, **SW_SPDT**, **SW_Tactile_2SMD**, **SW_Tactile_4SMD**, **SW_Tactile_PTS815SJM250** |
| **0_Transistor_FET** | 6 | **2N7002K**, **BSZ018N04LS6**, **GS2N7002KW**, **IQE013N04LM6**, **PJC7409**, **SSF2320Y** |


## How to naming

### Symbol Directory (.kicad_symdir)

- **Library folder:** `0_<Family>.kicad_symdir`.
- `<Family>` is`<Category>[_<Subcategory>]`, for example .

    0_`<Category>`_`<Subcategory>`.pretty
    0_`<Component>`.pretty

### Symbol Files (.kicad_sym)

`<Package>`-`<pin_count>`_`<diamension>`_`<pitch>`_`<option>`.kicad_sym

- **Files inside**`.kicad_sym` names, are flexible: keep
  them as they are and do not rename them to enforce a pattern.

Follow the KLC S rules in [../KLC/symbol/](../KLC/README.md).

