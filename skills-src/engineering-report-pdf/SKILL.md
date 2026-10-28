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

0. **Ask the setup questions, before any content work.** Run `python <skill>/scripts/build_report.py <report.md> --show-theme` (on a stub with just the front matter if the report does not exist yet) and tell the user which theme applies now: the skill default, or a `report-theme.yml` / `theme:` file already in the folder. Then ask these in one round, always, as multiple-choice questions (AskUserQuestion when the host has it): the default is the first option and is marked "(default)", and the user may answer in their own words instead:
   1. Style: **default** or **custom**?
   2. Pages: **full report** (default: cover page, contents page, then the report), **content only** (the report pages alone), or **cover and report** (no contents page)? Skip it for a book: a book always has a cover and contents.
   3. Page header (logo, short title and rule on every page): **on** (default) or off?
   4. Document number and revision (`doc_no`, `revision`): the values, or none.

   Then act on the answers:
   - Default style: write no theme keys.
   - Custom style: ask which groups to change, then only those values: identity (`author`, `logo`, `footer`), colors (`text_color`, `accent_color`, `muted_color`, `heading_color`, `number_color`), equations (`eq_style`, `eq_color`, `eq_numbers`), title block and lines (`header_rule_color`, `title_color`, `title_rule`). Then ask where to save them: **this report only** (front matter) or **every report in this folder** (`report-theme.yml`).
   - Full report, cover and report, or a book: ask a second round for the cover fields: `kicker` (small accent line above the title), `project`, `specs` (`Key = value | Key = value`), `note` (bottom-left), `license` (bottom-right) and `cover_logo` (default: the vector NP logo). Write only the fields the user gives.
   - Write `pages: content` or `pages: cover` (nothing for the default full report), `header: off`, `doc_no`, `revision` and the cover fields in the front matter, show `--show-theme` again, and only then start the content.
   - To show the user a style before writing it anywhere, build with `--set key=value` (repeatable, any theme or front-matter key, this build only).
   - Edit `<skill>/theme.yml` only when the user asks to change the defaults themselves: it restyles every future report.
1. **Get the content.** Write the report in Markdown (dialect below), next to its figures, in the user's working directory. If the content is in a Claude Doc, export the tab as Markdown, then replace each `[embedded content: …]` placeholder with a `![caption](figure.svg)` line pointing at a figure you regenerate.
2. **Make figures as SVG** with `<skill>/scripts/report_figs.py` (vector, theme colors, mathtext labels). Run figure scripts from the report folder so they pick up its `report-theme.yml`. See "Figures" below.
3. **Build:**
   ```bash
   pip install -r <skill>/requirements.txt -q     # once; add --break-system-packages on a managed system Python
   python <skill>/scripts/build_report.py report.md Report_Name.pdf --strict --preview preview
   ```
   Fonts are bundled in `assets/fonts` (IBM Plex Sans for text, IBM Plex Mono for code, DejaVu Sans as a per-character fallback), so output is the same on Linux, macOS and Windows. Every problem the build can see prints a `WARNING:` line and the build ends with the count; `--strict` makes it exit with code 1, so no warning goes unnoticed. Fix each one and rebuild: an equation that fell back to raw TeX (see the limits below), an unknown equation label, an "Eq. (n)" above the equation count, a nested list item, an image line it could not read, a cover title or specs item it had to cut. An unclosed `$$` or ```` ``` ```` stops the build with its line number.
4. **Look at every page.** Overflowing labels, a figure stranded on its own page, or a cramped table only show up in the render. `--preview preview` above wrote `preview/p-1.png`, `p-2.png` ...; for a long document add `--sheet 8` (8 pages per image, page number under each), then render single pages where something looks wrong:
   ```bash
   python <skill>/scripts/preview.py Report_Name.pdf preview --pages 3,7     # or --sheet 8; --dpi 80 default
   ```
   It clears old page images first, uses pypdfium2 and falls back to poppler's `pdftoppm`; if neither works, ask the user to open the PDF. On each page, check that every lead-in line (one ending in `:`) sits on the same page as the equation, figure or table after it. Equation numbers cited with labels need no check; any "Eq. (n)" written by hand must still match the number beside that equation.
5. **Deliver** the PDF: in claude.ai write it to `/mnt/user-data/outputs/` and call `present_files`; in Claude Code leave it in the working directory and give its path.

## Combining reports

When the user wants several reports in one file, write a `book.md` next to them and build it with `scripts/build_book.py`. It rebuilds every listed report (without their own covers), then adds a cover page, contents pages (each report with its `## N.` sections, page numbers and links), PDF bookmarks and an overall "n / N" page number in each footer. The book's theme (`report-theme.yml` next to `book.md`, or `theme:`, then theme keys in `book.md`) styles the cover and contents and sits under each report's own theme, so `author: Full Name` in `book.md` reaches every page. `--show-theme` works on a book too.

```markdown
---
title: 2-Phase Interleaved Sync-Buck Converter      # cover title, wraps to 3 lines
kicker: Schematic Design Reports                     # small accent line above the title
subtitle: 24 V to 12 V at 20 A, 200 kHz per phase
short_title: Schematic Design Reports                # header text on the contents pages
project: LQRx                                        # cover top-right and header tag (doc_no wins if set)
revision: 1.1
date: Oct 28, 2026
author: Natchanon Thuentham                          # theme key; any theme key may be set here
specs: Input = 15–28 V | Output = 12 V, 20 A | Controller = STM32G474   # key-figure panel, optional
note: Schematic design only.                         # bottom-left line, optional
license: CERN-OHL-S-2.0                              # bottom-right, optional
cover_logo: logo_large.svg                           # optional, .svg or .png; default is the vector assets/logo.svg
page_stamp: on                                       # off removes the overall "n / N"
report_numbers: on                                   # off restarts (1), Figure 1, Table 1 in each report
---

- 01_System/report.md        # reports in reading order, paths relative to book.md
- 02_Power_Stage/report.md
```

```bash
python <skill>/scripts/build_book.py book.md Combined.pdf --strict --preview preview --sheet 8
```

The contents takes each `## N.` heading's page from the report build itself, so its page numbers and links are exact. Each report takes its place in the list as a number: report 3's equations, figures and tables read (3.1), Figure 3.1, Table 3.1, and the 3 stands before its title, contents row and bookmark. `(@key)` cites follow; a hand-written "Eq. (n)" without the report number is a warning in a book. `paper:` in `book.md` reaches every report, and theme keys given with `--set` reach every report too. Then look at the sheets as in Workflow step 4: check that the cover title and the specs panel fit (`WARNING: cover title cut` means shorten the title or subtitle). `references/example-book.md` is a one-report sample.

## Full report or content only

The `pages` theme key sets what a single report's PDF holds:
- `full` (default): the book's cover page and a contents page (the report row with its `## N.` sections, page numbers, links and bookmarks), then the report. It is one document: the footer counts every page ("Page 3 of 8" on the first report page) and the contents shows the same numbers, so there is no "n / N" stamp.
- `content`: the report pages only, "Page 1 of N" from the first page.
- `cover`: the cover page, then the report, which still counts from "Page 1 of N".

The cover takes the cover fields above (`kicker`, `project`, `specs`, `note`, `license`, `cover_logo`) plus `title`, `subtitle`, `doc_no`, `revision`, `date` and the theme `author`; without `kicker`, `subtitle` and `specs` it looks bare, so ask for them. `--pages full|cover|content` on the build command overrides the key for one build. Inside a book, every report is built as `content`.

## Changing the layout

Every distance, font size and fixed word is in `scripts/page_layout.py`, one commented line each: `LAYOUT` (page margins, header, footer, cover and contents pages), `STYLES` (font, size, leading and spacing of each paragraph style: title, headings, body, cells, captions, code, notes), `BLOCKS` (equation, code and note panels, tables, figures, lists) and `LABELS` (fixed words: "Contents", "Revision", "Page X of Y" …). Both builders read them, so one edit there changes reports and books alike. User choices (colors, logo, paper, full report or content only) are theme keys instead: see "Theme". After any edit to the skill, run the selftest (see "Testing the skill").

## Theme

Four layers, each overriding the one before:
1. `<skill>/theme.yml`: the defaults, and the list of every theme key with a comment on what it sets. Read it when you need a key.
2. `report-theme.yml` next to the report, or the file named by `theme: path.yml` in the front matter: a folder-wide style (for example a club logo and accent). `references/example-theme.yml` is a sample.
3. Theme keys in the report's front matter: this report only.
4. `--set key=value` on the build command: this build only (a path is relative to the current folder).

A logo path is relative to the file that sets it. Color keys take `text`, `accent`, `muted` or `#RRGGBB` (`header_rule_color` also takes `title`, its default, and `none`); switches take `on` or `off`; `eq_style` takes `panel`, `bar` or `plain`; `paper` takes `a4` or `letter`. A typo or bad value stops the build with a one-line message naming the key and the file. `--show-theme` prints every resolved key and where it came from. Figures see layers 1 and 2 only, so put any color a figure must match in `report-theme.yml`.

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
paper: a4                                 # a4 (default) or letter; a theme key, so report-theme.yml can set it too
theme: ../club-theme.yml                  # optional; default is report-theme.yml in this folder, if present
eq_style: bar                             # any theme key overrides the theme for this report only
pages: content                            # full (default: cover, contents, report), cover or content; see "Full report or content only"
---

Lead paragraph: state the result first.

## 1. Section heading            (number and text in the text color by default)
### Sub-heading                   (bold)
#### Minor heading                (small, dark accent)

Body with **bold**, *italic*, `code`, [links](https://…), explicit R_{d} subscripts and x^{2} superscripts.

The damping resistor follows Eq. (@rd):

```latex
R_d = \frac{Z_0^2}{\frac{Z_0}{Q} - r_L} \label{rd}
```

$$ Z_0 = \sqrt{L/C} \nonumber $$

![Input filter with Rd–Cd damping](fig_filter.svg){width=85%}

Table: Design inputs
| Input | Value |
| --- | --- |
| Vin | 48 V |
| Peak \|Zo\| | 1.06 Ω |

1. Numbered step (numbers continue from the number you write)
- Bullet (one level only: an indented sub-item is flattened, with a warning)

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
- **Figures**: `![caption](path){width=NN%}` alone on its line (default 88%; decimals such as `70.5%` work). Paths are relative to the Markdown file. SVG preferred; PNG and JPG accepted. An empty caption gives an unnumbered figure.
- **Equations**: one per ```` ```latex ```` block (separate several with a blank line inside the block), or `$$ … $$`. Each gets a number, (1), (2) …, through the whole document ((3.1), (3.2) … for report 3 of a book); put `\nonumber` or `\notag` in an equation to leave it unnumbered, or set the theme key `eq_numbers: off` to number none. To cite one, put `\label{key}` in it and write `Eq. (@key)` in the text: the build prints its number, before or after the equation, and stays right when equations are added or removed. Use labels for every citation. A hand-written "Eq. (n)" larger than the equation count is a warning, but a wrong number within range is not caught. Equations are rendered by matplotlib *mathtext*, not full LaTeX. `\frac` is upgraded to display-size `\dfrac` automatically; `\operatorname{}` and `\text{}` become `\mathrm{}`. Not supported: `\begin{aligned}`, `\begin{cases}`, matrices, `\boldsymbol`. Split a multi-line derivation into one equation per line.
- **Fonts**: text is IBM Plex Sans (SemiBold for headings and bold), code is IBM Plex Mono, equations are Computer Modern (mathtext `cm`) so they read like LaTeX. Unicode symbols (Ω µ ≈ ≥ √ − ² · × ≫ ∝ ∠) are fine in text, tables, code, headers and the cover: glyphs Plex lacks are drawn from the DejaVu fallback automatically, so type the real symbol. No bundled font covers Thai or CJK script.

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

## Testing the skill

After editing any script, `theme.yml` or a `page_layout.py` value, run:

```bash
python <skill>/scripts/selftest.py             # add a folder name to keep its PDFs and inputs
```

It builds the buck example, the fixtures in `references/selftest/` (`features.md` uses every dialect construct, `plain.md` with `alt-theme.yml` changes every theme value, `book.md` combines them) and a set of broken inputs. It checks exit codes, warnings and errors, page sizes, equation labels, the book's contents and bookmark pages, `preview.py` and the figure helpers, then prints PASS or FAIL per case. All must pass. When a change adds a construct or a warning, add a case for it.

## Reference

`references/buck_converter_design_report.md` is a complete worked example of the dialect (front matter with `revision`, captioned tables, numbered equations with units in `\mathrm{}`, bold lead-ins, lists, `###` subsections). `references/figures.py` builds its three figures, one of each common graph type: a horizontal bar chart (loss breakdown, largest bar in the accent), a line plot with annotated points (efficiency against load) and a log-log Bode plot with a labelled limit line (filter impedance against |Rn|). Read them when unsure how a construct is written. The example has no schematic, note box, unnumbered equation or "Eq. (n)" reference; for those, follow the Markdown dialect and Figures sections above.
