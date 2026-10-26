# Symbol input (make_symbol.py)

Two files: `pins.csv`, the pin table, which holds every pin; and `layout.json`, which is optional and holds the fields and any layout overrides. The same `pins.csv` feeds `sym_check.py --ref`, so the pin data lives in one place.

## pins.csv

Header row required. Columns `number`, `name` and `type` are required; `unit`, `side`, `alt` and `shape` are optional. UTF-8; rows starting with `#` are comments, also above the header.

| Column | Meaning |
|---|---|
| `number` | Pin number as on the footprint (`5`, `A3`, `EP` number given by the footprint). A KiCad 10 pin stack `"[2,5,8]"` (quoted, the commas are inside) is read too, for stock round trips; the house style writes one row per pin. |
| `name` | Datasheet name. `nRESET`, `RESET#` and `/RESET` become `~{RESET}` (KLC S4.7; the script prints each rename). Write `~{CS}` for an overbar, `IO_{1}` for a subscript. Empty for an unnamed pin (op-amp output). |
| `type` | KiCad pin type: `input`, `output`, `bidirectional`, `tri_state`, `passive`, `free`, `unspecified`, `power_in`, `power_out`, `open_collector`, `open_emitter`, `no_connect`. |
| `unit` | Unit number, 1 to N with no gap. Empty = 1. |
| `side` | `left`, `right`, `top`, `bottom` or `hidden`. Empty = auto grouping (below). `hidden` is only for `no_connect` pins (KLC S4.6); the body grows until each hidden pin has a grid node inside it. Auto grouping hides NC pins; give one a side to show it. |
| `alt` | Alternate functions (KLC S4.1): a pin name carries at most two functions in slash form (`SDO/AD0`); more go here, with the primary or strapping function in the name. Names that are one function in several bus modes (`SDA/SDIO/SDI`) may keep the datasheet form; `sym_check` reports them as INFO. Format: `NAME:type` separated by `|` (`USART1_TX:bidirectional|TIM1_CH2:output`). The type defaults to the pin type. |
| `shape` | KiCad pin shape (`line` default, `inverted`, `clock`, ...). An inverted shape with an overbar name is refused (double inversion, S4.4). |

A row with no number and no name is an empty row on its `side` (explicit sides only).

```
number,name,type,unit,side,alt
1,SW,power_out,,,
2,SW,power_out,,,
4,PG,open_collector,,,
5,FB,input,,,
10,AVIN,power_in,,,
11,PVIN,power_in,,,
13,EN,input,,,
15,PGND,power_in,,,
16,NC,no_connect,,,
```

### Types (house rule)

Supply and ground `power_in`; regulator output and switch node `power_out`; chip select, clock, enable, feedback and sense `input`; data and address `bidirectional`; MCU I/O `bidirectional` (S4.4); push-pull interrupt `output`; open-drain interrupt, flag or power-good `open_collector` (the datasheet's pin description or interrupt section says which); reserved "connect to ground" `passive`; NC `no_connect`. An exposed pad gets its own pin with the footprint's pad number, typed like the net it joins.

### Separate pins (house rule) and stacks (KLC S4.3)

The house style draws every pin on its own: `GND` on pins 4, 9 and 17 is three pins side by side, like the `VDD` pins and the NC pins. The default `stack` off keeps it so, and a `"[2,5,8]"` row prints a note that the house style draws pins separately. With `"stack": true` (KLC S4.3), pins on one unit with the same name and a power type (`power_in`, `power_out`) become one native stack (`[4,9,17]`). Refused: a `no_connect` stack, and a number that is in a stack and also alone. Same-name power pins whose CSV sides differ stay apart (a NOTE says so); a stack takes the side and the alternates of all its pins.

### Auto grouping (KLC S4.2)

For pins with an empty `side`, per unit:
- Ground (`GND*`, `AGND`, `PGND`, `VSS*`, `VEE*`, `V-`, `EP`, `PAD`, typed `power_in` or `passive`): bottom, centered.
- `no_connect`: hidden, connection point on a grid node inside the body (KLC S4.6).
- Reserved (`RES`, `RESV`, `RSV`, `RESERVED`, `DNC`, with an optional number): bottom, right of the ground pins after one empty grid step.
- Other `power_in`: top. In a unit with a `power_out` pin (power conversion), input power goes first on the left instead, and `power_out` first on the right.
- Serial bus part (two or more pins whose first function is a bus name: `SCL`, `SCK`, `SCLK`, `SPC`, `SDA`, `SDI`, `SDIO`, `MOSI`, `SDO`, `MISO`, `CS`, `CSB`, `CSN`, `NCS`, `SS`, with an optional prefix such as `AP_` or `AUX1_`): the prefix group of the first bus pin in the file is the host bus. Left: the host bus in the order clock, data, data out, select, then interrupt (`INT*`, `DRDY`, `IRQ`, `ALERT`, `RDY`) and reset (`RST*`, `NRST*`, `RESET*`) pins. Right: the other bus groups in the same order, then every other signal pin (strap and address inputs, other outputs, passives) in file order. Interrupt and reset pins move to the right when the right side has pins and that makes the symbol lower.
- Otherwise: `output`, `open_collector`, `open_emitter`, `tri_state`, `power_out`: right.
- Other `passive` pins (set resistors and capacitors): together on the shorter of left and right (left on a tie).
- Everything else: left, in file order.
- MCU (16 or more `P<letter><n>` pins in the unit): ports sorted by letter and number, one empty row between ports, the first ports on the right until it holds half of them, the rest on the left below the control pins. No bus sorting.

Write `side` for any pin the auto grouping places badly (bus order per the KiCad library wiki, strapping pins, power-good next to enable). Pins with a `side` keep their CSV order; the sorts above move only auto-placed pins.

## layout.json

```json
{"reference": "U", "footprint": "0_Package_DFN_QFN:Texas_RGT0016C_VQFN-16-1EP_3x3mm_P0.5mm",
 "fp_filters": ["Texas*RGT0016C*"], "datasheet": "https://www.ti.com/product/TPS62142",
 "description": "3A step-down converter, 3-17V input, VQFN-16", "keywords": "buck DCDC"}
```

| Key | Meaning |
|---|---|
| `name` | Optional; must equal the output file name. |
| `reference` | Default `U`. Checked against the KLC S6.1 table (WARN). |
| `footprint` | `lib:name` (S5.1); empty for a generic symbol. |
| `fp_filters` | List. Each filter gets `-` and `_` written as `?` and a trailing `*` (S5.2). A WARN when a filter holds the pin count. |
| `datasheet`, `description`, `keywords` | Fields. Description: comma-separated, ends with the simplified package name (S6.2). Keywords: no word already in the description, phrases joined with `-`. |
| `pin_length` | 2.54 to 7.62 in 1.27 steps. Default 2.54 when every pin number has 1 character, 5.08 (200 mil) when any has 2 or more (house rule; KLC S4.1 asks at least 2.54 for 2 characters, 3.81 for 3). 6.35 from 5 characters, as S4.1 asks. With 3.81 or 6.35 the body edge moves 1.27 out, so pin ends stay on the 2.54 grid. |
| `pin_pitch` | Step between left and right pins: `2.54` or `5.08`. Default 5.08 (200 mil, house rule), 2.54 for an MCU (stock style). `sym_check --dump` writes the dumped symbol's pitch. |
| `stack` | Default `false`: every pin drawn separately (house rule). `true` stacks same-name power pins (KLC S4.3). |
| `units` | Unit names, `{"1": "A", "2": "B", "3": "PWR"}`. |
| `interchangeable` | Multi-unit only. Default `false` writes `ki_locked` (units not interchangeable), as stock op-amps with a power unit do. |

## Multi-unit symbols (KLC S3.8)

Use the `unit` column when the datasheet's units are drawn apart: op-amp channels, logic gates, a part split by function. Shared power pins then go in their own last unit. A single-unit symbol keeps its power pins on the one unit; this includes MCUs, as stock STM32 symbols do.

## Output

KiCad 10 format (`version 20251024`), one root symbol per file, pins in KiCad's save order, so a save in KiCad changes nothing. The name offset is 0.508 (KiCad's default, so the file has no `pin_names` block), text 1.27, body stroke 0.254 filled with background, origin at the body center. Left and right rows are centered on y = 0 with one grid step of body above the top row and below the bottom row. Reference and Value are visible, 1.27 above the body at its top-left (left-justified) and top-right (right-justified) corners; the body widens until they clear the top pins. Footprint, Datasheet and Description are hidden. The body size comes from the estimated text width: at 5.08 pitch the lowest body that fits, then the narrowest; at 2.54 the smallest area. The result is a starting point and the user sets the final look.
