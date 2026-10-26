---
name: kicad-footprint-make
description: Draw a KiCad 10 footprint (.kicad_mod) from datasheet land-pattern and stencil values, or check an existing footprint against those values or another footprint. Use when stock KiCad has no fitting footprint, when the user asks to make or draw a footprint, or to check a vendor, archive or stock footprint against the datasheet.
---

# KiCad footprint make

Two stdlib scripts in this skill's `scripts/` folder, run with `python -I`:
- `make_footprint.py <spec.json> <out.kicad_mod>` writes a footprint from a JSON spec. Spec format: [`SPEC.md`](SPEC.md).
- `fp_check.py <fp.kicad_mod> [--ref <spec.json> | --vs <other.kicad_mod>]` measures a footprint, runs the KLC and stencil checks on it (only the first file), and compares it with the spec or another footprint. The compare covers copper pads (position, size, type, shape, drill, layers, mask margin, custom pad area), thermal vias, NPTH holes and paste; courtyard, fab outline, fab properties and model are INFO only; silkscreen is not compared. Identical differences are grouped into one line. Exit code 1 on any DIFF. Options: `--tol`, `--stencil` (thickness, default 0.125 mm), `--courtyard` (required clearance), `--quiet` (skip the measurement tables).

**Scope.** Writes only the new `.kicad_mod`, plus the `.pretty` folder and its `fp-lib-table` line for a new family. Never overwrites a file (the script refuses). Does not stage or commit.

**Authority.** Every land-pattern and stencil value comes from the datasheet or the user; the script only computes positions from pitch and span and draws the generated layers. Names: `kicad-naming`. Datasheet evidence: the project rules when they exist; never open a PDF. Evidence labels go in the report, not in the file; `descr` holds the document number and land-pattern figure.

**House style** (script defaults, see `SPEC.md` options): rounded pad and aperture corners (roundrect ratio 0.25 for pads, 0.1 for apertures, radius at most 0.25 mm); square exposed pads, since rounded tab and pad primitives leave notches where they join; F.Fab body as a plain rectangle with one pin 1 mark: a filled dot (house rule in place of the KLC F5.2 bevel; sizes and places in `SPEC.md`: body diagonal for ICs, pad 1's outer end for diodes and LEDs, ball A1 for BGA), `fab_pin1: "arrow"` for connectors and DIP switches, `"none"` for non-polarized parts such as R/C/L, tactile switches and plain power connectors (no silk mark either); silk pin 1 mark a filled 0.3 x 0.4 mm arrow with a 0.1 mm line beside pin 1 pointing at it, `silk_pin1: "plus"` for polarized SMD capacitors (a `Polar` "+" text on silk, a drawn + on fab, with `body.chamfer` and `body.d` for the can base and can), never a dot; the courtyard grows the same on every side to hold it; F.Fab `${REFERENCE}` 1 x 1 mm, 0.1 mm thick, smaller only when 5 characters do not fit inside the body (C0402, 3x3 QFN); silkscreen 0.15 mm wide at body + 0.1 mm, cut 0.2 mm back from copper, REF** 1 x 1 mm, 0.15 mm thick. DFM minimums on silkscreen: lines and text 0.15 mm, text 1 x 1 mm, 0.15 mm from copper; a filled pin 1 arrow over 0.15 mm across may use 0.1 mm lines; silkscreen and fab points and text positions on a 0.05 mm grid (courtyard stays on 0.01 mm); courtyard 0.25 mm around body and copper (0.15 mm when the body is under 1.5 mm both ways, 1.0 mm for a grid; set `"courtyard": 0.5` for connectors, canned capacitors and crystals, KLC F5.3); Value property hidden. KLC F6.3 / F4.4: exposed pads and thermal vias get the heatsink fab property and solid zone connection, thermal vias get a B.Cu pad, grid pads get the BGA property.

## Steps

1. **Inspect.** List the target library's `.pretty` folders and Glob for the footprint name, case-insensitive. If it exists, report it and stop. If the family folder does not exist, it is a new family: create the `.pretty` folder and add its `fp-lib-table` line in the form of its neighbours.
   Done when the footprint is confirmed new and its family folder is known.

2. **Data.** Collect from the datasheet (user text, official web page, or NotebookLM full text): body size, pad count and numbering, pitch, row span or grid, pad sizes, exposed pad with tabs, thermal vias, and the stencil drawing (aperture sizes and positions, or the coverage %). Give each value an evidence label. Pin 1 corner, numbering direction and which grid axis holds letters come from drawings: `VERIFIED` only with a citation that holds them, else a human check. KiCad footprints are top view; mirror a bottom-view drawing.
   Values printed only inside a drawing (most Bosch and TDK land patterns, pin 1 corner, view, numbering direction) never appear in NotebookLM `cited_text`, so they stay `NOT_VERIFIED` and go on the human check list with the figure number; derive what you can from text values (for example span = (outer + inner)/2) and label it `ESTIMATED`.
   TI and similar drawings put their dimension text in the PDF text (`16X (0.24)`, `(0.58) TYP`, `85% PRINTED SOLDER COVERAGE`). The number is `VERIFIED` when the full text or `cited_text` holds it; what it measures (center to center or edge, drill or pad, how many vias, which axis) comes from the drawing, so label that reading `ESTIMATED` and say how you read it. Thermal vias that only the drawing shows are still drawn, with count and position on the human check list.
   A corner radius the datasheet gives (`(R0.05) ALL PAD CORNERS`) wins over the house ratio (KLC F4.1): set it as `"radius"` on the pads, on the exposed pad when the note says ALL, and on `paste` when the stencil drawing gives one. Otherwise exposed pads stay square. A generic mask note (`0.07 MIN ALL AROUND` in a non-solder-mask-defined detail) is the board default, not a pad `mask_margin`.
   When the datasheet has no land pattern: say so and name the document it points to (an app note or PCB guideline). Draw from the terminal sizes only when the datasheet says to use the package outline as the land pattern; otherwise stop at a hand comparison of the terminals against the existing pads, and ask the user for the app note.
   Done when every value the spec needs has a label, or the missing land pattern is reported.

3. **Name.** From `kicad-naming`. The spec `name` must equal the file name. When stock already has the generic package name with a different land pattern, put the maker and package code in front (`Texas_RGT0016C_VQFN-16-1EP_...`, KLC F2.3) so the two never collide.
   Model path: the stock STEP path of the same package body; else leave `model` out. Report when the file is missing in this install; the caller (`kicad-part-start` step 4) then asks the user for a STEP.

4. **Spec.** Write the spec JSON in the scratchpad, then run `make_footprint.py` into the target `.pretty` (or the scratchpad for a dry run). Read the printed summary: pad counts, exposed-pad paste coverage, and every WARN (via under paste, coverage outside 50 to 80%, annular ring, pin 1 silk mark on copper).
   Done when the file is written. A `spec error` names the bad key; fix the spec and run again.

5. **Check.**
   - `fp_check.py <fp> --ref <spec.json>`: every pad, via and aperture matches the spec; read each WARN.
   - When a stock or vendor footprint exists for the same package, `fp_check.py <fp> --vs <other>` and explain each DIFF.
   - `kicad-cli fp export svg -o <scratch dir> <.pretty> --fp <name>` parses it (create the output folder first). kicad-cli: the path the project `CLAUDE.md` gives, else PATH, else the KiCad install `bin` folder.
   - `klc_verify.py` from `kicad-lib-organize` when the library is a `0_` tree.
   - When a symbol exists, its pin numbers match the pad numbers.
   Done when each check passes or each failure is reported with its line.

6. **Report.** The file path; the measurement table; each datasheet value with its label; the WARN lines and what they mean for assembly (via under paste: plug or tent it, or move the aperture; low area ratio: thinner stencil or bigger aperture); and the human checks: pin 1 and mirroring against the datasheet figure, the stencil choice, opening it in the KiCad footprint editor, 3D model fit, DRC on a board (`NOT_VERIFIED`). A `--vs` PASS means the copper, holes and paste match; say that silkscreen and courtyard were not compared.
