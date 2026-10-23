---
name: kicad-part-start
description: Make the starting point for a new part (MPN) in a KiCad project library, stock KiCad symbol, footprint and 3D model copied in when they fit the datasheet, else drawn from the datasheet in NotebookLM. Use when the user asks for a part's starting point, or to add a new part, symbol or footprint to a project library.
---

# KiCad part starting point

A **starting point** is a part's symbol, footprint and 3D model in the project library, linked, listed in the lib tables, and checked against the datasheet. Stock KiCad items are copied unchanged; only what stock lacks is drawn. The user finishes style and every other rule.

**Scope.** Do the items the user names ("symbol only" means only the symbol); the default is all three. A request naming the part authorizes writing those items and their lib-table lines. Nothing else in the project is written. Do not stage or commit.

**Authority.** Names and families: `kicad-naming`. Stock search and copy: `kicad-lib-organize`, `STOCK.md` and `scripts/stock_copy.py` (in the `kicad-lib-organize` skill folder; run it from the project folder or with `--root`). Drawn footprints: `kicad-footprint-make`. Pin tables, stock-symbol fit and drawn symbols: `kicad-symbol-make`. Datasheet evidence: the project `engineering.md`; never open a PDF.

## Steps

1. **Inspect.** `git status`; list the `0_*` families under `library/symbols/` and `library/footprints/`; Glob for the MPN, case-insensitive. If the part exists, report it and stop.
   Done when the part is confirmed new.

2. **Datasheet.** `notebooklm list --json`, then `notebooklm source list -n <notebook id> --json` (plain output cuts the IDs) on the notebook named after the MPN or its family. The source title must name the MPN or a family that covers it (`TPS6214x` covers TPS62142); confirm the MPN in the full text's ordering or device table. A wrong or missing PDF stops the run until the user adds the right one. Pull the full text (plain output stops at 2000 characters):
   ```
   notebooklm source fulltext <source id> -n <notebook id> -o <scratch>/<mpn>_fulltext.txt --force
   ```
   Grep it for the pin table, the package outline and the land pattern. Values in the text are `VERIFIED` with document number and revision. Facts only in drawings (pin 1 corner, numbering direction, which grid axis holds letters or numbers) come from `notebooklm ask ... --json`: `VERIFIED` only when `cited_text` holds them, else a human check. In parallel, a `web-research` agent finds the official product page and the lifecycle status.
   When the product page shows a newer datasheet revision than the notebook, report it and ask the user to add it; until then each value is labelled with the notebook's revision. Report an NRND or EOL status at the top of the report.
   Done when the pin table has labels and, when the footprint is in scope, the package and land-pattern sizes, pin 1 corner and numbering direction too.

3. **Footprint.** `stock_copy.py find "<base part number>*"` (stock names hold `TPS62142`, not the order code `TPS62142RGTR`) and by package (`"*LGA-10*2x2mm*"`). For each candidate show the fit:
   - lead span from center `body/2 - inset - length` to `body/2 - inset` against pad span `center ± pad length/2` (or pad diameter and grid against the land pattern for a ball grid);
   - pad width against lead width, pitch, pads per side;
   - pin 1 and numbering. KiCad footprints are top view; a bottom-view drawing is mirrored.
   A candidate **fits** when the datasheet gives a land pattern and the candidate matches it: every pad position and size within 0.05 mm, the same exposed pad, and vias and paste the same or a reasoned choice. With no land pattern in the datasheet, it fits when its pads cover every lead with toe and heel to spare. Covering the leads alone is not a fit when a land pattern exists.
   Copy the fitting one (`stock_copy.py fp`). With no fit, draw it with `kicad-footprint-make` (it names it after the maker when stock already has the generic name) and show its `fp_check.py --vs` against the closest stock candidate.
   Done when one footprint is copied or drawn with its fit shown.

4. **3D model.** The stock model path must resolve: check the file under `<KiCad>/share/kicad/3dmodels/`. This also covers a drawn footprint, which carries the stock path of its package body. If the file is missing, ask the user for a STEP and its source (until then the footprint keeps the stock path and the report lists the missing file), save it as `library/3D/<Family>/<footprint name>.step` (`kicad-naming` 3D rule), and point the footprint's model path at `${KIPRJMOD}/library/3D/...`. A footprint carries one model: when the part needs a different model than another part on the same footprint, copy the footprint under the part maker's name (`Bosch_LGA-10_2x2mm_P0.5mm_LayoutBorder3x2y`), change only its name, Value, descr, tags and model path, and link the symbol to the copy.
   Done when the model file resolves, or the missing model is reported.

5. **Symbol.** Write the datasheet pin table as `pins.csv` and cross-check it (`kicad-symbol-make` steps 2 and 3; format and pin types in its `SPEC.md`). A stock symbol (`find` lists it) is used when `sym_check.py <stock lib> --name <symbol> --ref pins.csv` exits 0. Its DIFF lines show where stock merges pins the datasheet lists apart (AVIN and PVIN shown as VIN, the exposed pad joined to GND) or types a pin differently (SW as `output`). When those are the only differences, stock may still be used: list each one for the user. A copied stock symbol keeps its stock properties, Datasheet URL included. Copy it after the footprint, so its `Footprint` points at the local copy: `stock_copy.py sym <Lib>:<name> <0_Family>`, adding `--fp <0_Family>:<footprint>` when the footprint was drawn under another name (this also adds the name to `ki_fp_filters`). A derived symbol's parent keeps its stock link; `klc_verify` flags it, which is expected. Without a fitting stock symbol, draw it with `kicad-symbol-make` (steps 4 to 6), `Footprint` set to the local copy and `Datasheet` to the product page.
   With the footprint out of scope, link the local footprint when the project already has one for this package (the user names it, or the fit check in step 3 holds); else the symbol keeps the stock `Footprint` or none, and `klc_verify` flags that link, which is expected.
   Done when the symbol is copied or drawn and `sym_check.py --fp` shows its pins match the footprint pads.

6. **Lib tables.** Add one line per new family to `sym-lib-table` or `fp-lib-table`, in the form of its neighbours; in an empty table use `(lib (name "<0_Family>") (type "KiCad") (uri "${KIPRJMOD}/library/footprints/<0_Family>.pretty") (options "") (descr ""))` (symbols: `type "KiCad"`, `uri` to the `.kicad_symdir`).
   Done when every `0_*` folder has its line.

7. **Verify.**
   - `python -I <kicad-lib-organize dir>/scripts/klc_verify.py` prints `all checks passed`. Read its output, not the exit code: it lists broken links and still exits 0.
   - kicad-cli parses the symbol (`sym export svg`) and footprint (`fp export svg --fp <name>`), output in the scratchpad.
   - `python -I <kicad-link-audit dir>/scripts/audit_links.py .` shows no new issue. It prints only problems and does not check stock model paths (step 4 does). Report issues that were there before; the user can run `/kicad-footprint-sync` or `/kicad-symbol-sync` to fix them.
   Done when every check passes, or each failure is reported with its path.

8. **Report**: the written files; the footprint fit; each datasheet value with its label; the human checks (pin 1 and mirroring against the datasheet figure, lifecycle status, land-pattern notes, symbol style); that KiCad needs the project reopened, or the lib tables reloaded, to see a new family; `NOT_VERIFIED` for KiCad GUI loading and 3D rendering.
