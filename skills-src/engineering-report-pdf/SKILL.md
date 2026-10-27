---
name: engineering-report-pdf
description: Build a PDF engineering document in Natchanon's NP template (small NP logo in the header, IBM Plex text, navy text with a blue accent, numbered LaTeX equations in panels, numbered figures and tables, "Page X of Y" footer). Use for a design, calculation or test report, technical memo, specification or any engineering write-up delivered as a PDF, for "my template", "the NP template" or "same style as before", or to export a report or Claude Doc to a styled PDF.
disable-model-invocation: true
---

# Engineering report PDF (NP template)

This skill turns report content written in a simple Markdown dialect into a branded PDF. The script fixes the look, so every report matches. Your job is the content, the figures, and checking the result.

The template, and why it looks this way:
- **White page, navy-black text (`INK`, `#16202E`) in IBM Plex Sans.** It prints well and reads like a formal engineering document. Plex keeps 0/O and 1/l/I distinct, which matters for part values and references.
- **Blue (`#1F63D6`, from the logo) is the only accent**: section numbers, the header rule, list numbers, links, the bar beside equations. Headings themselves are `INK`. Figures use the same palette, so the document reads as one piece.
- **Small logo top-left on every page**, short title top-right, author and date bottom-left, "Page X of Y" bottom-right. The logo is small on purpose; keep it that size.
- **Equations sit in numbered panels** so derivations are easy to scan and cite. Figures and tables are numbered too.

## Workflow

`<skill>` below means the folder that holds this SKILL.md (e.g. `~/.claude/skills/engineering-report-pdf` in Claude Code).

1. **Get the content.** Write the report in Markdown (dialect below), next to its figures, in the user's working directory. If the content is in a Claude Doc, export the tab as Markdown, then replace each `[embedded content: …]` placeholder with a `![caption](figure.svg)` line pointing at a figure you regenerate.
2. **Make figures as SVG** with `<skill>/scripts/report_figs.py` (vector, theme colors, mathtext labels). See "Figures" below.
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

## Markdown dialect

````markdown
---
title: Design Report: Damped Input Filter for a Switching Converter
subtitle: Optional second line
short_title: Damped Input Filter          # header text, top-right (defaults to title)
author: Natchanon
date: Oct 27, 2026
doc_no: DR-0012                           # optional, shown in meta line and header
revision: A                               # optional
subscripts: Z0, rL, Rs, Rd, Cd, Vin, Rtot # optional: tokens auto-rendered as Z₀, r_L, R_s ...
italic_titles: Calculation Report: L-Match Network | Another Doc Title   # optional, italicised when cited
logo: assets/other_logo.png               # optional; default = bundled NP logo; "none" hides it
paper: a4                                 # a4 (default) or letter
footer: Natchanon · Confidential          # optional override of the bottom-left text
---

Lead paragraph: state the result first.

## 1. Section heading            (number in blue, text in INK)
### Sub-heading                   (INK, bold)
#### Minor heading                (small, dark blue)

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
- **Title**: from front matter `title`, or the first `# ` line. Front matter is optional but gives the header and footer their text.
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

Plot conventions (they keep figures readable and on-brand): blue for the series the conclusion is about, gray for comparisons, navy dashed for limits and references with a text label on the line; light-blue grid; axis labels with units; no chart titles (the numbered caption is the title); plain tick labels on log axes via `plain_log_ticks`. For bold figure text use `weight="semibold"`, the heaviest Plex weight bundled. `report_figs.py` is the single source of the palette; `build_report.py` reads its colors from there.

`Schematic(w, h)` draws circuits and simple block diagrams on a y-down canvas: `wire`, `res_h`, `res_v`, `ind_h`, `cap_v`, `source`, `ground`, `dot`, `box` (dashed group or solid block), `arrow`, `text` (mathtext labels like `r"$R_d$"`). Navy for normal parts, `c=BLUE` to highlight the parts the report is about. Check that labels stay inside boxes after rendering.

## Writing the content

The template sets the look; good reports also share a shape. Start with a one-paragraph lead that states the result with its numbers. Use numbered sections (`## 1. …`). Put assumptions and inputs in tables, derivations as numbered steps with one equation each, then a verification (exact check, simulation, or measurement compared with the hand calculation), then a short conclusion. Mark illustrative values as illustrative.

## Reference

`references/example_report.md` is a complete worked example of the dialect (front matter, numbered and unnumbered equations, "Eq. (n)" references, schematic and plot, captioned tables, note box). `references/example_figures.py` builds its two figures. Read them when unsure how a construct is written.
