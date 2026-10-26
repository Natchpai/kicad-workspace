---
name: kicad-symbol-make
description: Draw a KiCad 10 symbol (.kicad_sym) from a datasheet pin table, or check an existing symbol against KLC, a pin table, another symbol or its footprint. Use when stock KiCad has no fitting symbol, when the user asks to make or draw a symbol, or to check a vendor, stock or project symbol's pins.
---

# KiCad symbol make

Two stdlib scripts in this skill's `scripts/` folder, run with `python -I`:
- `make_symbol.py <pins.csv> <out.kicad_sym> [--layout layout.json] [--fp <fp.kicad_mod>]` writes one symbol. Input format: [`SPEC.md`](SPEC.md).
- `sym_check.py <lib.kicad_sym> [--name <symbol>] [--ref pins.csv | --vs <other.kicad_sym>[:name]] [--fp <fp.kicad_mod>] [--dump pins.csv] [--quiet]` prints the pin table (`--quiet` skips it) and the KLC checks (WARN / INFO with the rule number). It also compares the pins with a pin table, another symbol or a footprint: number, name, type, alternates and stacks, with DIFF lines and exit code 1. `--dump` writes a symbol as `pins.csv` plus `<stem>.layout.json`, to start from a stock symbol (hidden power pins come out with an empty side, shared unit-0 pins in a new last unit; it prints a NOTE for each). `--scan` with `--ref` ranks a whole stock library against the table.

**Scope.** Writes only the new `.kicad_sym`, plus the `.kicad_symdir` folder and its `sym-lib-table` line for a new family. Never overwrites a file (the script refuses). Does not stage or commit.

**Authority.** Every pin number, name and type comes from the datasheet or the user; the script only places the pins. Names: `kicad-naming`. Datasheet evidence: the project rules when they exist; never open a PDF. Evidence labels go in the report, not in the file.

**House style** (KLC, script defaults): 2.54 mm grid; left and right pins 5.08 mm (200 mil) apart and centered on the origin, 2.54 mm for an MCU (house rule; `pin_pitch` overrides); top and bottom pins 2.54 mm apart; pins all one length: 2.54 mm (100 mil) when every pin number has 1 character, 5.08 mm (200 mil) when any has 2 or more (house rule; KLC S4.1 minimum is 2.54 for 2 characters, 3.81 for 3; 6.35 for 5 and 7.62 from 6 characters; `pin_length` overrides); name offset 0.508; text 1.27; body a rectangle, stroke 0.254, filled with background; Reference and Value just above the body's top-left and top-right corners; serial bus parts: host bus on the left in the order clock, data, data out, select, then interrupt and reset, other bus groups and strap pins on the right; reserved pins (`RESV`, `DNC`) at the bottom, right of ground; every pin drawn separately, no stacks: same-name power, ground and NC pins each get their own pin (house rule; KLC S4.3 would stack them, `"stack": true` does that); NC pins hidden inside the body (KLC S4.6; a `side` in the table shows one); active-low names as `~{NAME}` (S4.7). MCUs are one unit with alternates, as stock STM32 symbols are; multi-unit with a power unit is for parts drawn apart (op-amps, gates).

## Steps

1. **Inspect.** List the target library's `.kicad_symdir` folders and Glob for the MPN, case-insensitive. If it exists, report it and stop.
   Done when the symbol is confirmed new and its family folder is known.

2. **Pin table.** Write `pins.csv` in the scratchpad from the datasheet pin table (full text: `notebooklm source fulltext`, then grep the pin-function table). Each row is `VERIFIED` with the document number and revision when the full text holds it. For an MCU, add the alternate functions from the datasheet's alternate-function table.
   Cross-check the table with one `notebooklm ask --json` that asks for the pin numbers and names of the exact MPN and package. Compare its `cited_text` with the table. A mismatch stops the run until you or the user settle it.
   Done when every row has a label and the cross-check matches.

3. **Stock first.** Find candidates by name (`stock_copy.py find "<base part number>*"` and the family, `"ICP-201*"`) and by function: `sym_check.py <stock lib of the function, e.g. Sensor_Pressure.kicad_sym> --ref pins.csv --scan` ranks every symbol in that library against the table. For each candidate: `sym_check.py <stock lib> --name <symbol> --ref pins.csv --quiet`. Exit 0 means stock fits: copy it with `kicad-part-start` / `stock_copy.py sym` instead of drawing. A DIFF lists every name merge and type difference; report them. Always check stock first for an MCU.
   Done when stock fits, or each candidate's DIFF is shown.

4. **Layout.** Write `layout.json` with the fields (reference, footprint, filters, datasheet product page, description, keywords). Leave `side` empty in `pins.csv` and let auto grouping place the pins. Set a `side` only for pins it places badly. Pick `unit` only for parts drawn apart.
   Done when the layout covers every field.

5. **Make.** `make_symbol.py pins.csv <family>.kicad_symdir/<MPN>.kicad_sym --layout layout.json --fp <footprint>` (or into the scratchpad for a dry run). Read the printed summary: side pitch, body size, NC pins, house-style notes, `S4.7 renamed` lines, filter notes and WARN lines. A `spec error` names the bad line or key; fix it and run again. A `PIN/PAD MISMATCH` writes nothing: settle it with the footprint first.
   Done when the file is written.

6. **Check.**
   - `sym_check.py <new file> --ref pins.csv --fp <footprint>`: PASS on both; read each WARN.
   - `--vs` the closest stock symbol when one exists, and explain each DIFF.
   - `kicad-cli sym export svg -o <scratch dir> <file>` parses it.
   - `klc_verify.py` from `kicad-lib-organize` when the library is a `0_` tree.
   Done when each check passes or each failure is reported with its line.

7. **Report.** The file path; the pin table with labels; the renames and NC pins; the WARN lines; and the human checks: pin grouping and bus order, the look in the KiCad symbol editor (text overlap, body size), and the description and keywords.
