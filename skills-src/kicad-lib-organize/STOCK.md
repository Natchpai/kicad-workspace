# Stock copy

Copies a symbol or footprint from KiCad's stock library into a local `0_<Family>` library, unchanged. A stock name is already a KLC name (`kicad-naming` authority 4), so nothing is renamed and no map is built. This branch only copies; the user draws anything stock KiCad does not have.

Script: `scripts/stock_copy.py` (usage in its docstring). Run it from the folder that holds the library folder, with `-X utf8` on Windows.

## Steps

1. **Find** each requested item:
   ```
   python -I -X utf8 <skill dir>/scripts/stock_copy.py find "<glob>"
   ```
   Search by part number and by package (`TPS6214*`, `*LGA-14*3x2.5mm*`). Footprint lines show pad count, smallest pad spacing, pad sizes and model paths.
   - Several footprints for one package with different pads (Bosch and ST `LGA-14_3x2.5mm`): compare them with the part's datasheet package table (lead width, lead length, pitch, body size). Pick the one whose pads sit on the leads, and show the calculation. Without the datasheet, list the candidates and let the user choose.
   - No stock match: report the item with its KLC names from `kicad-naming` (Propose), and stop for that item.
   Done when every requested item has one chosen stock item or is reported as not in stock.

2. **Family**, by `kicad-naming`: reuse a local family that already holds that kind of item (stock `Connector_JST` goes to an existing `0_Conn_JST`), else `0_` + the stock library name.
   Done when every item has its destination family.

3. **Copy**, footprints first so symbol links find them, each with `--dry` before the real run:
   ```
   python -I -X utf8 <skill dir>/scripts/stock_copy.py fp|sym <StockLib>:<name> <0_Family> [--dry] [--lib <folder>] [--root <dir>]
   ```
   - `fp` copies byte for byte. The model path stays the stock `${KICAD10_3DMODEL_DIR}/...`; copy a local model only when the user asks.
   - `sym` brings a derived symbol's `extends` parents into the same family, and points the Footprint at the local copy when one exists.
   - Identical targets are skipped. `COLLISION` means a local item with that name differs from stock, usually a project edit: report it and leave it.
   Done when every item is copied, skipped or reported.

4. **Lib tables.** In a project (a folder with `.kicad_pro`), add one line per new family to `sym-lib-table` or `fp-lib-table`, in the same form as its neighbours. The archive keeps no tables.
   Done when every new family has its table line.

5. **Verify.**
   - `python -I <skill dir>/scripts/klc_verify.py` prints `all checks passed`.
   - kicad-cli parses each touched `.kicad_symdir` folder (`sym export svg`) and each footprint (`fp export svg --fp <name>`), output in the scratchpad.
   - In a project, the `kicad-link-audit` script shows no new issue.
   Done when every check passes, or each failure is reported with its path.

6. **Report**: items copied, skipped and in collision; items not in stock with their proposed KLC names; each footprint choice with its reasoning; table lines added; checks run, with `NOT_VERIFIED` for KiCad GUI loading and 3D rendering. Do not stage or commit.
