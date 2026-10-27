---
name: engineering-report-pdf
description: Build a PDF engineering document in Natchanon's NP template (small NP logo in the header, IBM Plex text, navy text with a logo-blue accent, numbered LaTeX equations in panels, numbered figures and tables, "Page X of Y" footer). Use for a design, calculation or test report, technical memo, specification or any engineering write-up delivered as a PDF, for "my template", "the NP template" or "same style as before", to export a report or Claude Doc to a styled PDF, or to combine several reports into one PDF with a cover page and table of contents.
disable-model-invocation: true
---

# Engineering report PDF (NP template)

This skill turns report content written in a simple Markdown dialect into a branded PDF. A theme sets the look (see "Theme"), so every report in a folder matches. Your job is the style choice, the content, the figures, and checking the result.

The default template, and why it looks this way:
- **White page, navy-black text (`#16202E`) in IBM Plex Sans.** It prints well and reads like a formal engineering document. Plex keeps 0/O and 1/l/I distinct, which matters for part values and references.
- **Logo blue (`#20A0E0`, the main tone of the NP logo gradient) is the only accent**: links, table lines, the bar beside equations. Headings, section numbers, list numbers and the header, footer and title-block lines use the text color (one setting, `header_rule_color`, same color and weight). Figures use the same palette, so the document reads as one piece.
- **Small logo top-left on every page**, short title top-right, author and date bottom-left, "Page X of Y" bottom-right. The logo is small on purpose; keep it that size.
- **Equations sit in numbered panels** so derivations are easy to scan and cite. Figures and tables are numbered too.

## Workflow

`<skill>` below means the folder that holds this SKILL.md (e.g. `~/.claude/skills/engineering-report-pdf` in Claude Code).

0. **Choose the style, before any content work.** Run `python <skill>/scripts/build_report.py <report.md> --show-theme` (on a stub with just the front matter if the report does not exist yet) and tell the user which theme applies now: the skill default, or a `report-theme.yml` / `theme:` file already in the folder. Then ask once (AskUserQuestion when the host has it): **default** or **custom** style?
   - Default: write no theme keys.
   - Custom: ask which groups to change, then only those values: identity (`author`, `logo`, `footer`), colors (`text_color`, `accent_color`, `muted_color`, `heading_color`, `number_color`), equations (`eq_style`, `eq_color`, `eq_numbers`), page header and title block (`header`, `header_rule_color`, `title_color`, `title_rule`). Then ask where to save them: **this report only** (front matter) or **every report in this folder** (`report-theme.yml`). Write them there and show `--show-theme` again before building.
   - Edit `<skill>/theme.yml` only when the user asks to change the defaults themselves: it restyles every future report.
1. **Get the content.** Write the report in Markdown (dialect below), next to its figures, in the user's working directory. If the content is in a Claude Doc, export the tab as Markdown, then replace each `[embedded content: …]` placeholder with a `![caption](figure.svg)` line pointing at a figure you regenerate.
2. **Make figures as SVG** with `<skill>/scripts/report_figs.py` (vector, theme colors, mathtext labels). Run figure scripts from the report folder so they pick up its `report-theme.yml`. See "Figures" below.
3. **Build:**
   ```bash
   pip install -r <skill>/requirements.txt -q     # once; add --break-system-packages on a managed system Python
   python <skill>/scripts/build_report.py report.md Report_Name.pdf
   ```
   Fonts are bundled in `assets/fonts` (IBM Plex Sans for text, IBM Plex Mono for code, DejaVu Sans as a per-character fallback), so output is the same on Linux, macOS and Windows. The build prints `WARNING: equation not rendered` if an equation fell back to raw TeX: fix the TeX (see the limits below) and rebuild. An unclosed `$$` stops the build with its line number.
4. **Look at every page.** Overflowing labels, a figure stranded on its own page, or a raw-TeX equation only show up in the render:
   ```bash
   python <skill>/scripts/preview.py Report_Name.pdf preview --dpi 80     # preview/p-1.png, p-2.png ...
   ```
   It uses pypdfium2 and falls back to poppler's `pdftoppm`; if neither works, ask the user to open the PDF. On each page, check that every lead-in line (one ending in `:`) sits on the same page as the equation, figure or table after it, and that every "Eq. (n)" reference in the text matches the number printed beside that equation.
5. **Deliver** the PDF: in claude.ai write it to `/mnt/user-data/outputs/` and call `present_files`; in Claude Code leave it in the working directory and give its path.

## Combining reports

When the user wants several reports in one file, write a `book.md` next to them and build it with `scripts/build_book.py`. It rebuilds every listed report, then adds a cover page, a contents page (each report with its `## N.` sections, page numbers and links), PDF bookmarks and an overall "n / N" page number in each footer. The cover and contents use the same theme layers as a report, so `report-theme.yml` in the book's folder applies to both.

```markdown
---
title: 2-Phase Interleaved Sync-Buck Converter      # cover title, wraps to 3 lines
kicker: Schematic Design Reports                     # small accent line above the title
subtitle: 24 V to 12 V at 20 A, 200 kHz per phase
short_title: Schematic Design Reports                # header text on the contents pages
project: LQRx
revision: 1.1
date: Oct 28, 2026
author: Natchanon Thuentham                          # theme key; any theme key may be set here
specs: Input = 15–28 V | Output = 12 V, 20 A | Controller = STM32G474   # key-figure panel, optional
note: Schematic design only.                         # bottom-left line, optional
license: CERN-OHL-S-2.0                              # bottom-right, optional
cover_logo: logo_large.png                           # optional; default is the theme logo
page_stamp: on                                       # off removes the overall "n / N"
---

- 01_System/report.md        # reports in reading order, paths relative to book.md
- 02_Power_Stage/report.md
```

```bash
python <skill>/scripts/build_book.py book.md Combined.pdf
```

Then preview the cover and contents pages with `preview.py`, as in Workflow step 4: check that the title and the specs panel fit, and that every contents entry starts on the page it names. `references/example-book.md` is a one-report sample.

## Theme

Three layers, each overriding the one before:
1. `<skill>/theme.yml`: the defaults, and the list of every theme key with a comment on what it sets. Read it when you need a key.
2. `report-theme.yml` next to the report, or the file named by `theme: path.yml` in the front matter: a folder-wide style (for example a club logo and accent). `references/example-theme.yml` is a sample.
3. Theme keys in the report's front matter: this report only.

A logo path is relative to the file that sets it. Color keys take `text`, `accent`, `muted` or `#RRGGBB` (`header_rule_color` also takes `title`, its default, and `none`); switches take `on` or `off`; `eq_style` takes `panel`, `bar` or `plain`. A typo or bad value stops the build with a one-line message naming the key and the file. `--show-theme` prints every resolved key and where it came from. Figures see layers 1 and 2 only, so put any color a figure must match in `report-theme.yml`.

## Markdown dialect

````markdown
---
title: Design Report: Damped Input Filter for a Switching Converter
subtitle: Optional second line
short_title: Damped Input Filter          # header text, top-right (defaults to title)
date: Oct 27, 2026
doc_no: DR-0012                           # optional, shown in meta line and header
revision: A                               # optional
subscripts: Z0, rL, Rs, Rd, Cd, Vin, Rtot # optional: tokens auto-rendered as Z₀, r_L, R_s ...
italic_titles: Calculation Report: L-Match Network | Another Doc Title   # optional, italicised when cited
paper: a4                                 # a4 (default) or letter
theme: ../club-theme.yml                  # optional; default is report-theme.yml in this folder, if present
eq_style: bar                             # any theme key overrides the theme for this report only
---

Lead paragraph: state the result first.

## 1. Section heading            (number and text in the text color by default)
### Sub-heading                   (bold)
#### Minor heading                (small, dark accent)

Body with **bold**, *italic*, `code`, [links](https://…), explicit R_{d} subscripts and x^{2} superscripts.

The damping resistor is:

```latex
R_d = \frac{Z_0^2}{\frac{Z_0}{Q} - r_L}
```

$$ Z_0 = \sqrt{L/C} \nonumber $$

![Input filter with Rd–Cd damping](fig_filter.svg){width=85%}

Table: Design inputs
| Input | Value |
| --- | --- |
| Vin | 48 V |
| Peak \|Zo\| | 1.06 Ω |

1. Numbered step (numbers continue from the number you write)
- Bullet

> Note box. Gets a bold "Note." label.

> **Assumption:** a note that starts with its own bold label keeps that label instead.

\pagebreak
````

Details that matter:
- **Title**: from front matter `title`, or the first `# ` line. Front matter is optional but gives the header and footer their text. In front matter and theme files, `#` starts a comment (a `#RRGGBB` value is kept); quote a value that must contain ` #`, like `title: "Test #3"`.
- **Auto-subscripts** (`subscripts:`): each listed token becomes first character + subscript rest (`Rtot` → R_tot) wherever it stands alone as a word. Good for engineering symbols written plainly in text; list only symbols, never ordinary words. For anything else write `X_{sub}` explicitly.
- **Lead-ins**: a paragraph, or the last item of a list, that ends with `:` is kept on the same page as the equation, figure, table or code block right after it. End a line with `:` exactly when it introduces that block.
- **Pipes inside table cells** must be escaped: `\|Zo\|`. An unescaped `|` splits the cell.
- **Tables** with 10 rows or fewer are kept on one page. A `Table: caption` line directly above a table numbers and captions it. Two-column tables are drawn narrow; wider ones span the page.
- **Figures**: `![caption](path){width=NN%}` (default 88%). Paths are relative to the Markdown file. SVG preferred; PNG and JPG accepted. An empty caption gives an unnumbered figure.
- **Equations**: one per ```` ```latex ```` block (separate several with a blank line inside the block), or `$$ … $$`. Each gets a number, (1), (2) …, through the whole document; put `\nonumber` or `\notag` in an equation to leave it unnumbered. Cite them by hand as "Eq. (n)", and recheck those numbers after adding or removing an equation. Equations are rendered by matplotlib *mathtext*, not full LaTeX. `\frac` is upgraded to display-size `\dfrac` automatically; `\operatorname{}` and `\text{}` become `\mathrm{}`. Not supported: `\begin{aligned}`, `\begin{cases}`, matrices, `\boldsymbol`. Split a multi-line derivation into one equation per line.
- **Fonts**: text is IBM Plex Sans (SemiBold for headings and bold), code is IBM Plex Mono, equations are Computer Modern (mathtext `cm`) so they read like LaTeX. Unicode symbols (Ω µ ≈ ≥ √ − ² · × ≫ ∝ ∠) are fine in text, tables and code: glyphs Plex lacks are drawn from the DejaVu fallback automatically, so type the real symbol.

## Figures

`scripts/report_figs.py` holds the theme so figures match the page:

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from report_figs import *          # INK, NAVY, BLUE, SKY, GRAY, MUTED, apply_plot_style, plain_log_ticks,
                                   # save_svg, Schematic, equation
fig, ax = plt.subplots(figsize=(6.4, 3.4))
ax.plot(x, y_other, color=GRAY, lw=1.4, label="Baseline")
ax.plot(x, y_main, color=BLUE, lw=2.3, label="Design")      # the one series the finding is about
ax.axhline(limit, color=NAVY, lw=1.1, ls=(0, (5, 4)))       # limit / reference line, labelled on the chart
apply_plot_style(ax, legend_loc="upper left")
save_svg(fig, "fig_result.svg")
```

Plot conventions (they keep figures readable and on-brand): the accent (`BLUE`) for the series the conclusion is about, gray for comparisons, navy dashed for limits and references with a text label on the line; accent-tinted grid; axis labels with units; no chart titles (the numbered caption is the title); plain tick labels on log axes via `plain_log_ticks`. For bold figure text use `weight="semibold"`, the heaviest Plex weight bundled. `BLUE`, `INK`, `MUTED` and the grid tints come from the theme (`accent_color`, `text_color`, `muted_color`); `NAVY`, `SKY` and `GRAY` are fixed figure colors.

`Schematic(w, h)` draws circuits and simple block diagrams on a y-down canvas: `wire`, `res_h`, `res_v`, `ind_h`, `cap_v`, `source`, `ground`, `dot`, `box` (dashed group or solid block), `arrow`, `text` (mathtext labels like `r"$R_d$"`). Navy for normal parts, `c=BLUE` to highlight the parts the report is about. Check that labels stay inside boxes after rendering.

## Writing the content

The template sets the look; good reports also share a shape. Start with a one-paragraph lead that states the result with its numbers. Use numbered sections (`## 1. …`). Put assumptions and inputs in tables, derivations as numbered steps with one equation each, then a verification (exact check, simulation, or measurement compared with the hand calculation), then a short conclusion. Mark illustrative values as illustrative.

## Reference

`references/buck_converter_design_report.md` is a complete worked example of the dialect (front matter with `revision`, captioned tables, numbered equations with units in `\mathrm{}`, bold lead-ins, lists, `###` subsections). `references/figures.py` builds its three figures, one of each common graph type: a horizontal bar chart (loss breakdown, largest bar in the accent), a line plot with annotated points (efficiency against load) and a log-log Bode plot with a labelled limit line (filter impedance against |Rn|). Read them when unsure how a construct is written. The example has no schematic, note box, unnumbered equation or "Eq. (n)" reference; for those, follow the Markdown dialect and Figures sections above.
