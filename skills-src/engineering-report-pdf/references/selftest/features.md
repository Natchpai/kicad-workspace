---
title: Selftest: Every Dialect Construct
subtitle: Fixture for scripts/selftest.py; each section uses one group of features
short_title: Selftest features
date: Oct 28, 2026
doc_no: ST-01
revision: A
subscripts: Vin, Rd, Z0
italic_titles: Buck Converter Design Report
kicker: Selftest
project: ST
specs: Input = 12 V | Output = 3.3 V | Ratio = ≫ 1
note: Selftest fixture; all values are illustrative.
license: CC0-1.0
cover_logo: ../../assets/logo.png
footer: Selftest · footer text
---

Lead paragraph with **bold**, *italic*, `code Ω`, a [link](https://www.kicad.org), R_{d} and x^{2}, Vin and Z0 written plainly, an escaped \* star and \_ underscore, and the cited title Buck Converter Design Report. Fallback glyphs: ≫ ∠ √ ≈ µ Ω.

## 1. Equations

The damping resistor follows Eq. (@rd), which uses the characteristic impedance of Eq. (@z0):

```latex
Z_0 = \sqrt{\frac{L}{C}} \label{z0}

R_d = \frac{Z_0^2}{\frac{Z_0}{Q} - r_L} \label{rd}
```

$$ Q = \frac{R_d}{Z_0} \nonumber $$

$$
f_0 = \frac{1}{2 \pi \sqrt{L C}}
\label{f0}
$$

An unnumbered equation with notag:

$$ \omega_0 = 2 \pi f_0 \notag $$

Eq. (@f0) is the third numbered equation, and Eq. (3) written by hand is in range.

## 2. Figures

The efficiency plot, an SVG at a decimal width:

![Efficiency against load](../fig_efficiency.svg){width=70.5%}

A PNG with an empty caption, so it has no number:

![](../../assets/logo.png){width=20%}

## 3. Tables

Table: Two short columns give a narrow table; the cell holds an escaped \| pipe
| Input | Value |
| --- | --- |
| Vin | 12 V |
| Peak \|Zo\| | 1.06 Ω |

Table: More than ten rows, so the table may break across pages
| No. | Item | Value | Note |
| --- | --- | --- | --- |
| 1 | Input voltage | 12 V | nominal |
| 2 | Output voltage | 3.3 V | set by the divider |
| 3 | Output current | 2 A | continuous |
| 4 | Switching frequency | 2.2 MHz | fixed |
| 5 | Inductor | 1 µH | shielded |
| 6 | Output capacitor | 2 × 22 µF | X7R |
| 7 | Input capacitor | 10 µF | X7R |
| 8 | Ripple current | 0.95 A p-p | 47 % of Io |
| 9 | Output ripple | 4 mV p-p | ceramic |
| 10 | Efficiency | 91 % | full load |
| 11 | Junction rise | 22 K | estimate |
| 12 | Phase margin | 55° | estimate |

## 4. Lists and notes

1. First step.
2. Second step that continues
   on an indented line.

5. Numbering continues from the number written.

- Bullet one.
- Bullet two, the lead-in for the code block:

```python
# a comment that is not a title
print("code panel with Ω and µ from the fallback font")
```

> A note box with the default label.

> **Assumption:** a note that starts with its own bold label.

\pagebreak

### 4.1 Sub-heading after a page break

#### Minor heading

Text after a minor heading closes the fixture.
